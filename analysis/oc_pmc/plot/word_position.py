import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from oc_pmc import OUTPUTS_DIR, PLOTS_DIR, STUDYPLOTS_DIR, console, get_logger
from oc_pmc.analysis.unique_section_words import (
    get_unique_words_for_section,
    get_uniquely_shared_words_for_sections,
)
from oc_pmc.analysis.word_position import (
    compute_cumulative_match_score,
    get_n_sections,
    get_rho_diff_match_score_with_monotonic_increase_from_matchscores,
)
from oc_pmc.load import (
    load_questionnaire,
    load_rated_wordchains,
    load_story_sentences,
    load_story_sentences_grouped,
    load_word_position,
    load_word_position_count_matching_sections,
)
from oc_pmc.plot.by_time_shifted import func_plot_by_time, func_plot_by_time_pre_post
from oc_pmc.utils import (
    check_make_dirs,
    clean_words,
    remove_words_in_sections,
    save_plot,
)
from oc_pmc.utils.aggregator import aggregator
from oc_pmc.utils.bootstrap import bootstrap_2d

log = get_logger(__name__)


def get_mode_str(config: dict) -> str:
    mode = config["word_position"]["mode"]
    if config.get("only_high_sr", False):
        mode = f"{mode}_high_sr_{config['high_sr_threshold']}"
    if config.get("simulate", False):
        mode = f"{mode}_{config['simulation_case']}"
    if config.get("remove_words_with_multiple_sections", False):
        mode = f"{mode}_single_section"
    return mode


def get_model_name_str(config: dict) -> str:
    model_name = config["word_position"]["model_name"]
    if config["word_position"]["mode"] == "incontext":
        method = config["word_position"].get("method", "raw")  # type: ignore
        model_name = f"{model_name}-{method}"
    return model_name


def load_rated_wordchains_pre_post(config: dict) -> pd.DataFrame:
    if config.get("simulate", False):
        # simulation
        from oc_pmc.simulate.rated_wordchains import simulate_rated_wordchains_from_list

        assert config["story"] == "carver_original", (
            "Only implemented for story=carver_original"
        )

        simulation_case = config.get("simulation_case")
        if simulation_case == "section_1":
            words = get_unique_words_for_section(config["story"], 1)
        elif simulation_case == "section_9":
            words = get_unique_words_for_section(config["story"], 9)
        elif simulation_case == "sections_4_6":
            words = get_unique_words_for_section(
                config["story"], 4
            ) + get_unique_words_for_section(config["story"], 6)
        elif simulation_case == "sections_5_7_9":
            words = (
                get_unique_words_for_section(config["story"], 5)
                + get_unique_words_for_section(config["story"], 7)
                + get_unique_words_for_section(config["story"], 9)
            )
        elif simulation_case == "sections_shared_4_6":
            words = get_uniquely_shared_words_for_sections(config["story"], [4, 6])
        elif simulation_case == "sections_shared_3_5_7":
            words = get_uniquely_shared_words_for_sections(config["story"], [3, 5, 7])
        else:
            raise ValueError(f"Invalid simulation case: {simulation_case=}")

        simulation_config_post = {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "n_participants": 80,
        }
        simulation_config_pre = {
            "story": "carver_original",
            "condition": "word_scrambled",
            "position": "post",
            "n_participants": 80,
        }
        post = simulate_rated_wordchains_from_list(
            config=simulation_config_post, words=words
        )
        pre = simulate_rated_wordchains_from_list(
            config=simulation_config_pre, words=["unrelated"]
        )
        pre["position"] = "pre"
        pre.index = post.index
        data_df = pd.concat([pre, post])
    else:
        # real data
        data_pre_df = load_rated_wordchains(config={**config, "position": "pre"})
        data_pre_df["position"] = "pre"
        data_post_df = load_rated_wordchains(config={**config, "position": "post"})
        data_post_df["position"] = "post"
        data_df = pd.concat([data_pre_df, data_post_df])

    if config.get("remove_words_with_multiple_sections", False):
        count_matching_sections_dct = load_word_position_count_matching_sections(
            config=config["word_position"]
        )
        words_with_single_section = [
            count_matching_sections_dct.get(word, 0) < 2
            for word in data_df["word_text"].tolist()
        ]

        removed_words = data_df[~np.array(words_with_single_section)][
            "word_text"
        ].tolist()
        if STUDYPLOTS_DIR:
            base = STUDYPLOTS_DIR
        else:
            base = Path(OUTPUTS_DIR, PLOTS_DIR)
        path_removed_words = Path(
            base,
            config.get("study", ""),
            "word_position",
            config["story"],
            get_mode_str(config),
            "removed_words_with_multiple_sections",
            f"{config['condition']}.txt",
        )
        check_make_dirs(path_removed_words)
        path_removed_words.write_text("\n".join(removed_words))
        path_removed_words.with_name(f"{config['condition']}_unique.txt").write_text(
            "\n".join(set(removed_words))
        )
        removed_words_high_sr = data_df[
            ~np.array(words_with_single_section)
            & (data_df["story_relatedness"] > config["high_sr_threshold"])
        ]["word_text"].tolist()
        path_removed_words.with_name(
            f"{config['condition']}_unique_high_sr.txt"
        ).write_text("\n".join(set(removed_words_high_sr)))

        data_df = data_df.loc[words_with_single_section]

    return data_df


def func_plot_word_position_distribution(config: dict, data_df: pd.DataFrame):
    wpc = config["word_position"]
    story = config["story"]
    condition = config["condition"]
    mode = get_mode_str(config)
    model_name = get_model_name_str(config)
    raise NotImplementedError("Needs to be updated for new word_position_dct format")
    word_position_dct = load_word_position(config=wpc)
    n_sections = get_n_sections(story=story, word_position_mode=wpc["mode"])

    word_position_counts = np.zeros(n_sections)
    word_position_counts_high_sr = np.zeros(n_sections)

    for idx_word, word in enumerate(data_df["word_text"].unique()):
        word_position = word_position_dct.get(word)
        if word_position is None or word_position < 0 or np.isnan(word_position):
            continue

        word_position_idx = int(np.round(word_position))
        # all words
        word_position_counts[word_position_idx] += 1

        # high SR words
        word_sr = data_df.iloc[idx_word]["story_relatedness"]
        if not (np.isnan(word_sr)) and word_sr > config["high_sr_threshold"]:
            word_position_counts_high_sr[word_position_idx] += 1

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=list(range(n_sections)),
            y=word_position_counts,
            name="All",
            text=[str(int(v)) for v in word_position_counts],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            x=list(range(n_sections)),
            y=word_position_counts_high_sr,
            name=f"High SR (>{config['high_sr_threshold']}) only",
            text=[str(int(v)) for v in word_position_counts_high_sr],
            textposition="outside",
        )
    )
    position_str = ""
    if "position" in config:
        position_str = f" | {config['position']}"

    fig.update_layout(
        barmode="group",
        title=(
            f"{mode} | {model_name} | {story} | {condition}{position_str}"
            " | Number of words matching sections"
        ),
    )
    fig.update_xaxes(
        title_text="Section number",
        tickmode="array",
        tickvals=list(range(n_sections)),
        ticktext=[str(i + 1) for i in range(n_sections)],
    )
    fig.update_yaxes(
        title_text="Count of words",
        range=config.get("number_words_matching_sections_range"),
    )

    if config.get("save", False):
        output_path = Path(
            config.get("study", ""),
            "word_position",
            story,
            mode,
            model_name,
            "number_words_matching_sections",
            f"{condition}.png",
        )
        save_plot(config, fig, output_path, verbose=True)

    return fig


def load_count_matching_sections(config: dict) -> pd.DataFrame:
    count_matching_sections_dct = load_word_position_count_matching_sections(
        config=config["word_position"]
    )
    # load words in condition
    words_df = load_rated_wordchains_pre_post(config=config)

    condition_words = list()
    for word in clean_words(words_df["word_text"].tolist(), remove_duplicates=False):
        if word in count_matching_sections_dct:
            condition_words.append((word, count_matching_sections_dct[word]))
        elif word != "" and word != "nan" and not config.get("simulate", False):
            log.warning(f"Word {word} not found in count_matching_sections_dct")

    condition_count_df = pd.DataFrame(
        condition_words,
        columns=["word", "count"],  # type: ignore
    )
    return condition_count_df


def func_plot_count_matching_sections(config: dict, data_df: pd.DataFrame):
    """Plot the number of words matching a certain number of sections.

    Note that this plot counts each occurrence of a word, even if it is not unique.
    That means if murder shows up 3 times, and is matching 2 sections, the bar for
    for 2 sections will increase by 3.
    """

    story = config["story"]
    condition = config["condition"]
    model_name = get_model_name_str(config)
    mode = get_mode_str(config)

    # Determine the max count to set the range
    max_count = int(data_df["count"].max()) if len(data_df) > 0 else 0

    fig = px.histogram(
        data_df,
        x="count",
        text_auto=True,
        nbins=max_count + 2,  # +2 to include max_count in a bin
        range_x=[-0.5, max_count + 0.5],
    )
    fig.update_layout(
        title=(
            "Number of sections matching a single word"
            f" ({mode} | {model_name} | {story} | {condition})"
        ),
        xaxis_title="Number of sections",
        yaxis_title="Count of words",
        yaxis_type="log",
        xaxis=dict(tickmode="linear", tick0=0, dtick=1, range=[-0.5, max_count + 0.5]),
        yaxis=dict(range=[1, None]),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)

    if config.get("save", False):
        output_path = Path(
            config.get("study", ""),
            "word_position",
            story,
            mode,
            model_name,
            "count_of_matching_sections",
            f"{condition}.png",
        )
        save_plot(config, fig, output_path, verbose=True)


def plot_word_position_distribution(config: dict):
    aggregator(
        config=config,
        load_func=load_rated_wordchains_pre_post,
        call_func=func_plot_word_position_distribution,
    )


def plot_count_matching_sections(config: dict):
    aggregator(
        config=config,
        load_func=load_count_matching_sections,
        call_func=func_plot_count_matching_sections,
    )


def plot_bars_match_score(config: dict):
    """Plots bars of match scores for different time ranges

    If config["diff"] is True:
    - plots show the difference between pre and post

    If config["config_baseline"] is provided:
    - config["diff] is set to True
    - plots will show baseline - condition
    """

    diff = config.get("diff", False) or "config_baseline" in config
    only_high_sr = config.get("only_high_sr", False)

    assert "time_ranges" in config, (
        "time_ranges must be provided in config (e.g. [(0, 30000), ...])"
    )
    time_ranges: list[tuple[int, int]] = config["time_ranges"]
    y_ranges = config.get("y_ranges", [(None, None)])
    if y_ranges is None:
        y_ranges = [(None, None)] * len(time_ranges)
    if len(y_ranges) == 1:
        y_ranges = y_ranges * len(time_ranges)

    assert len(y_ranges) == len(time_ranges), (
        "y_ranges must be the same length as time_ranges"
    )

    n_cols = len(time_ranges)

    subplot_titles = [
        f"{int(start_time / 1000)} - {int(end_time / 1000)}s"
        for start_time, end_time in time_ranges
    ]
    fig = make_subplots(
        rows=1,
        cols=n_cols,
        subplot_titles=subplot_titles,
    )
    # only the subplot-title annotations exist at this point, so this won't
    # affect annotations added later (e.g. the rho annotation)
    fig.update_annotations(font_size=config.get("subplot_title_font_size", 28))

    n_sections = get_n_sections(
        story=config["story"], word_position_mode=config["word_position"]["mode"]
    )

    for idx_time_range, ((start_time, end_time), y_range) in enumerate(
        zip(time_ranges, y_ranges)
    ):
        # load data
        data_df = load_rated_wordchains_pre_post(
            config={
                **config,
                "exclude": [
                    ("lt", "timestamp", start_time),
                    ("gte", "timestamp", end_time),
                ],
            }
        )
        # need to take into account participants who did not generate words
        # during time-frame
        pIDs = list(
            load_questionnaire(
                config={"story": config["story"], "condition": config["condition"]}
            ).index.unique()
        )

        # load baseline if given
        baseline_df = None
        pIDs_baseline = None
        if config.get("config_baseline"):
            baseline_df = load_rated_wordchains_pre_post(
                config={
                    **config["config_baseline"],
                    "exclude": [
                        ("lt", "timestamp", start_time),
                        ("gte", "timestamp", end_time),
                    ],
                }
            )
            pIDs_baseline = list(
                load_questionnaire(
                    config={
                        "story": config["config_baseline"]["story"],
                        "condition": config["config_baseline"]["condition"],
                    }
                ).index.unique()
            )

        # compute match scores
        pre_df = data_df.loc[data_df["position"] == "pre"]
        post_df = data_df.loc[data_df["position"] == "post"]

        # compute match probabilities
        pre_match_score = compute_cumulative_match_score(
            config=config, pIDs=pIDs, data_df=pre_df, only_high_sr=only_high_sr
        )
        post_match_score = compute_cumulative_match_score(
            config=config, pIDs=pIDs, data_df=post_df, only_high_sr=only_high_sr
        )
        diff_match_score = post_match_score - pre_match_score

        if baseline_df is not None:
            baseline_pre_df = baseline_df.loc[baseline_df["position"] == "pre"]
            baseline_post_df = baseline_df.loc[baseline_df["position"] == "post"]
            baseline_pre_match_score = compute_cumulative_match_score(
                config=config,
                pIDs=pIDs_baseline,  # type: ignore
                data_df=baseline_pre_df,
                only_high_sr=only_high_sr,
            ).mean(axis=0)
            baseline_post_match_score = compute_cumulative_match_score(
                config=config,
                pIDs=pIDs_baseline,  # type: ignore
                data_df=baseline_post_df,
                only_high_sr=only_high_sr,
            ).mean(axis=0)
            baseline_diff_match_score = (
                baseline_post_match_score - baseline_pre_match_score
            )
            diff_match_score = baseline_diff_match_score - diff_match_score
        # pre_match_score.shape = (n_participants, n_sections)
        # post_match_score.shape = (n_participants, n_sections)
        # diff_match_score.shape = (n_participants, n_sections)
        mean_pre_match_score = pre_match_score.mean(axis=0)
        mean_post_match_score = post_match_score.mean(axis=0)
        mean_diff_match_score = diff_match_score.mean(axis=0)

        # get rho for display
        rhos = get_rho_diff_match_score_with_monotonic_increase_from_matchscores(
            diff_match_score
        )
        rho_mean_str = str(round(float(rhos.mean()), 2)).replace("0.", ".")
        rho_sd_str = str(round(float(rhos.std()), 2)).replace("0.", ".")

        if diff:
            error_y_dct = None
            if config.get("n_bootstrap", None) is not None:
                lowers, uppers = bootstrap_2d(
                    config, diff_match_score, print_non_nans=False
                )

                error_y_dct = dict(
                    type="data",
                    array=uppers - mean_diff_match_score,
                    arrayminus=mean_diff_match_score - lowers,
                )

            fig.add_trace(
                go.Bar(
                    x=list(range(n_sections)),
                    y=mean_diff_match_score,
                    name="diff",
                    showlegend=idx_time_range == 0,
                    marker_color=config["color"],
                    error_y=error_y_dct,
                ),
                row=1,
                col=idx_time_range + 1,
            )
            # zero line as trace so it draws on top of bars
            fig.add_trace(
                go.Scatter(
                    x=[-0.5, n_sections - 0.5],
                    y=[0, 0],
                    mode="lines",
                    line=dict(color="grey", width=1, dash="solid"),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=idx_time_range + 1,
            )
        else:
            error_y_dct_pre = None
            error_y_dct_post = None
            if config.get("n_bootstrap", None) is not None:
                lowers_pre, uppers_pre = bootstrap_2d(
                    config, pre_match_score, print_non_nans=False
                )
                lowers_post, uppers_post = bootstrap_2d(
                    config, post_match_score, print_non_nans=False
                )

                error_y_dct_pre = dict(
                    type="data",
                    array=uppers_pre - mean_pre_match_score,
                    arrayminus=mean_pre_match_score - lowers_pre,
                )
                error_y_dct_post = dict(
                    type="data",
                    array=uppers_post - mean_post_match_score,
                    arrayminus=mean_post_match_score - lowers_post,
                )
            fig.add_trace(
                go.Bar(
                    x=list(range(n_sections)),
                    y=mean_pre_match_score,
                    name="pre",
                    showlegend=idx_time_range == 0,
                    marker_color=config["color_pre"],
                    error_y=error_y_dct_pre,
                ),
                row=1,
                col=idx_time_range + 1,
            )
            fig.add_trace(
                go.Bar(
                    x=list(range(n_sections)),
                    y=mean_post_match_score,
                    name="post",
                    showlegend=idx_time_range == 0,
                    marker_color=config["color_post"],
                    error_y=error_y_dct_post,
                ),
                row=1,
                col=idx_time_range + 1,
            )

        fig.update_traces(
            error_y=dict(
                # color="grey",
                width=0,
            ),
        )

        y_title = config.get("y_title") if idx_time_range == 0 else None
        fig.update_xaxes(
            title=config.get("x_title"),
            title_font_size=config.get("x_title_font_size", 24),
            title_standoff=config.get("x_title_standoff", 6),
            title_font_color=config.get("x_title_font_color", "black"),
            tickmode="array",
            ticks=config.get("x_ticks", "outside"),
            tickwidth=config.get("x_tickwidth"),
            rangemode=config.get("x_rangemode"),
            range=config.get("x_range"),
            tickvals=list(range(n_sections)),
            ticktext=[str(i + 1) for i in range(n_sections)],
            tickcolor=config.get("axes_tickcolor"),
            showline=True,
            linewidth=config.get("axes_linewidth", 3),
            linecolor=config.get("axes_linecolor", "black"),
            tickfont=config.get("x_tickfont", dict(size=21)),
            tickangle=config.get("tickangle", 0),
            showgrid=config.get("x_showgrid", True),
            col=idx_time_range + 1,
            row=1,
        )
        fig.update_yaxes(
            title=y_title,
            title_font_size=config.get("y_title_font_size", 24),
            title_standoff=config.get("y_title_standoff", 6),
            title_font_color=config.get("y_title_font_color", "black"),
            range=y_range,
            ticks=config.get("y_ticks", "outside"),
            tickwidth=config.get("y_tickwidth", 6),
            tickmode="array",
            tickvals=config.get("y_tickvals"),
            ticktext=config.get("y_ticktext"),
            tickcolor=config.get("axes_tickcolor"),
            showline=True,
            linewidth=config.get("axes_linewidth", 3),
            linecolor=config.get("axes_linecolor", "black"),
            tickfont=config.get("y_tickfont", dict(size=21)),
            showgrid=config.get("y_showgrid", True),
            col=idx_time_range + 1,
            row=1,
        )

        if config.get("show_rho", False):
            y_tickfont = config.get("y_tickfont", dict(size=21))
            fig.add_annotation(
                text=f"\u03c1 = {rho_mean_str} ({rho_sd_str})",
                xref="x domain",
                yref="y domain",
                x=0.99,
                y=0.015,
                xanchor="right",
                yanchor="bottom",
                showarrow=False,
                font=dict(
                    size=y_tickfont.get("size", 21),
                    color="black",
                ),
                row=1,
                col=idx_time_range + 1,
            )

    if diff:
        if "config_baseline" in config:
            title = (
                f"{config['config_baseline']['condition']} - {config['condition']}"
                " Difference in Post - Pre Match Scores"
            )
        else:
            title = f"{config['condition']} Post - Pre Match Scores"
    else:
        title = f"{config['condition']} Match Scores"

    fig.update_layout(
        barmode="group",
        title=config.get(
            "title",
            title,
        ),
        font_family=config.get("font_family", "verdana"),
        font_color=config.get("font_color"),
        # https://plotly.com/python/reference/layout/#layout-legend
        legend=config.get("legend"),
        showlegend=config.get("showlegend", False),
        plot_bgcolor=config.get("bgcolor", "white"),
        paper_bgcolor=config.get("bgcolor", "white"),
    )

    if config.get("save", False):
        suffix = ""
        if only_high_sr:
            suffix += "-only_high_sr"
        if config.get("suffix") is not None:
            suffix += f"-{config.get('suffix')}"
        # only use baseline condition, assuming no comparisons across stories..
        baseline_condition_str = ""
        if "config_baseline" in config:
            baseline_condition_str = config["config_baseline"]["condition"]
            dir_name = "match_score_diff_to_baseline"
        else:
            dir_name = "match_score"
            if diff:
                dir_name += "_diff"

        filetype = config.get("filetype", "png")
        output_path = Path(
            config.get("study", ""),
            "word_position",
            config["story"],
            get_mode_str(config),
            get_model_name_str(config),
            dir_name,
            baseline_condition_str,
            f"{config['condition']}{suffix}.{filetype}",
        )
        save_plot(config, fig, output_path, verbose=True)


def plot_by_time_shifted_without_section(config: dict):
    """Same as plot_by_time_shifted, but removes words from a
    specific section."""

    def func_prep_for_plot_by_time_shifted(config: dict, data_df: pd.DataFrame):
        word_position_dct = load_word_position(config["word_position"])

        removed_sections = config["removed_sections"]
        if not isinstance(removed_sections, list):
            removed_sections = [removed_sections]

        data_df_without_words_in_sections = remove_words_in_sections(
            data_df=data_df,
            word_position_dct=word_position_dct,
            removed_sections=removed_sections,
            unique_in_section=config.get("unique_in_section", False),
        )

        if config.get("show_original", False):
            data_df["group"] = "original"
            data_df_without_words_in_sections["group"] = "removed section"
            data_df = pd.concat(  # type: ignore
                [data_df, data_df_without_words_in_sections]
            )
        else:
            data_df_without_words_in_sections["group"] = "removed section"
            data_df = data_df_without_words_in_sections  # type: ignore

        if "additional_grouping_columns" not in config:
            config["additional_grouping_columns"] = []
        config["additional_grouping_columns"].append("group")

        return func_plot_by_time(config, data_df)

    aggregator(
        config=config,
        load_func=load_rated_wordchains,
        call_func=func_prep_for_plot_by_time_shifted,
        no_extra_columns=False,
    )


def plot_match_score_by_time_sections(config: dict):
    """Plots match scores for each section over time."""

    def func_plot_by_time_sections(config: dict, data_df: pd.DataFrame):
        word_position_dct = load_word_position(config["word_position"])

        n_sections = get_n_sections(
            story=config["story"],
            word_position_mode=config["word_position"]["mode"],
        )

        # prep for normalization
        any_word_re = re.compile(r"\b\w+\b", flags=re.IGNORECASE)
        if config["word_position"]["mode"] == "exact_match_sentences":
            section_lengths = np.array(
                [
                    len(any_word_re.findall(sent))
                    for sent in load_story_sentences(story=config["story"])
                ]
            )
        else:
            section_sentences = load_story_sentences_grouped(story=config["story"])
            section_lengths = np.array(
                [
                    len(any_word_re.findall("\n".join(section_sentences_)))
                    for section_sentences_ in section_sentences
                ]
            )
        normalization_factor = (sum(section_lengths) / (section_lengths)) / n_sections

        if config.get("normalize", False):
            for key in word_position_dct:
                word_position_dct[key] = word_position_dct[key] * normalization_factor

        def assign_match_score(word: str, idx_section: int) -> float:
            if word not in word_position_dct:
                return 0
            return word_position_dct[word][idx_section]

        plot_df_ls: list[pd.DataFrame] = list()
        for idx_section in range(n_sections):
            plot_df = data_df.copy()
            plot_df["section"] = f"Section {idx_section + 1}"

            plot_df["match_score"] = plot_df["word_text"].apply(
                lambda word: assign_match_score(word, idx_section)
            )

            plot_df_ls.append(plot_df)

        return func_plot_by_time_pre_post(config, pd.concat(plot_df_ls))

    config["color"] = "section"
    config["additional_grouping_columns"] = ["section"]
    config["column"] = "match_score"
    config["mode"] = config.get("mode", "match_score")

    aggregator(
        config=config,
        load_func=load_rated_wordchains_pre_post,
        call_func=func_plot_by_time_sections,
        no_extra_columns=False,
    )


def plot_match_score_across_conditions(config: dict):
    """Plots match score diff for each condition together across all sections."""

    assert "time_range" in config, (
        "time_range must be provided in config (e.g. (0, 180000))"
    )

    only_high_sr = config.get("only_high_sr", False)
    time_range: tuple[int, int] = config["time_range"]

    n_sections = get_n_sections(
        story=config["story"], word_position_mode=config["word_position"]["mode"]
    )

    start_time, end_time = time_range

    # compute baseline match score
    baseline_df = load_rated_wordchains_pre_post(
        config={
            **config,
            **config["config_baseline"],
            "exclude": [
                ("lt", "timestamp", start_time),
                ("gte", "timestamp", end_time),
            ],
        }
    )
    pIDs_baseline = list(
        load_questionnaire(
            config={
                **config,
                **config["config_baseline"],
            }
        ).index.unique()
    )
    baseline_pre_df = baseline_df.loc[baseline_df["position"] == "pre"]
    baseline_post_df = baseline_df.loc[baseline_df["position"] == "post"]
    baseline_pre_match_score = compute_cumulative_match_score(
        config=config,
        pIDs=pIDs_baseline,  # type: ignore
        data_df=baseline_pre_df,
        only_high_sr=only_high_sr,
    ).mean(axis=0)
    baseline_post_match_score = compute_cumulative_match_score(
        config=config,
        pIDs=pIDs_baseline,  # type: ignore
        data_df=baseline_post_df,
        only_high_sr=only_high_sr,
    ).mean(axis=0)
    baseline_diff_match_score = baseline_post_match_score - baseline_pre_match_score

    name_start_chars: list[str] = list()  # for saving later on
    names: list[str] = list()
    section_indcs: list[int] = list()
    mean_match_scores_ls: list[np.ndarray] = list()
    lowers_rel_ls: list[Union[np.ndarray, None]] = list()
    uppers_rel_ls: list[Union[np.ndarray, None]] = list()
    for config_ in config["configs"]:
        name = config_.get("name", config_["condition"])
        if "_" in name:
            name_start_chars.append(name.split("_")[1][0])
        else:
            name_start_chars.append(name[0])
        data_df = load_rated_wordchains_pre_post(
            config={
                **config,
                **config_,
                "exclude": [
                    ("lt", "timestamp", start_time),
                    ("gte", "timestamp", end_time),
                ],
            }
        )
        # need to take into account participants who did not generate words
        # during time-frame
        pIDs = list(load_questionnaire(config={**config, **config_}).index.unique())

        # compute match scores
        pre_df = data_df.loc[data_df["position"] == "pre"]
        post_df = data_df.loc[data_df["position"] == "post"]

        # compute match probabilities
        pre_match_score = compute_cumulative_match_score(
            config=config, pIDs=pIDs, data_df=pre_df, only_high_sr=only_high_sr
        )
        # pre_match_score.shape = (n_participants, n_sections)
        post_match_score = compute_cumulative_match_score(
            config=config, pIDs=pIDs, data_df=post_df, only_high_sr=only_high_sr
        )
        # post_match_score.shape = (n_participants, n_sections)
        diff_match_score = post_match_score - pre_match_score
        # diff_match_score.shape = (n_participants, n_sections)

        # diff to baseline
        diff_match_score = baseline_diff_match_score - diff_match_score

        # mean
        mean_diff_match_scores = diff_match_score.mean(axis=0)

        lowers_rel = [None] * len(mean_diff_match_scores)
        uppers_rel = [None] * len(mean_diff_match_scores)
        if config.get("n_bootstrap", None) is not None:
            lowers, uppers = bootstrap_2d(
                config, diff_match_score, print_non_nans=False
            )
            lowers_rel = mean_diff_match_scores - lowers
            uppers_rel = uppers - mean_diff_match_scores

        # append to lists
        names.extend([name] * len(mean_diff_match_scores))
        mean_match_scores_ls.extend(mean_diff_match_scores)
        lowers_rel_ls.extend(lowers_rel)
        uppers_rel_ls.extend(uppers_rel)
        section_indcs.extend(list(range(len(mean_diff_match_scores))))

    plot_df = pd.DataFrame(
        {
            "name": names,
            "mean_match_scores": mean_match_scores_ls,
            "lowers_rel": lowers_rel_ls,
            "uppers_rel": uppers_rel_ls,
            "section_indcs": section_indcs,
        }
    )

    fig = px.scatter(
        plot_df,
        x="section_indcs",
        y="mean_match_scores",
        color="name",
        error_y="uppers_rel" if uppers_rel_ls[0] is not None else None,
        error_y_minus="lowers_rel" if lowers_rel_ls[0] is not None else None,
        color_discrete_sequence=config.get("color_sequence"),
        category_orders=config.get("category_orders"),
        color_discrete_map=config.get("color_map"),
        symbol_map=config.get("symbol_map"),
    )

    fig.update_xaxes(
        title=config.get("x_title"),
        title_font_size=config.get("x_title_font_size", 24),
        title_standoff=config.get("x_title_standoff", 6),
        title_font_color=config.get("x_title_font_color", "black"),
        tickmode="array",
        ticks=config.get("x_ticks", "outside"),
        tickwidth=config.get("x_tickwidth"),
        rangemode=config.get("x_rangemode"),
        range=config.get("x_range"),
        tickvals=list(range(n_sections)),
        ticktext=[str(i + 1) for i in range(n_sections)],
        tickcolor=config.get("axes_tickcolor"),
        showline=True,
        linewidth=config.get("axes_linewidth", 3),
        linecolor=config.get("axes_linecolor", "black"),
        tickfont=config.get("x_tickfont", dict(size=21)),
        tickangle=config.get("tickangle", 0),
        showgrid=config.get("x_showgrid", True),
    )
    fig.update_yaxes(
        title=config.get("y_title"),
        title_font_size=config.get("y_title_font_size", 24),
        title_standoff=config.get("y_title_standoff", 6),
        title_font_color=config.get("y_title_font_color", "black"),
        range=config.get("y_range", (None, None)),
        ticks=config.get("y_ticks", "outside"),
        tickwidth=config.get("y_tickwidth", 6),
        tickmode="array",
        tickvals=config.get("y_tickvals"),
        ticktext=config.get("y_ticktext"),
        tickcolor=config.get("axes_tickcolor"),
        showline=True,
        linewidth=config.get("axes_linewidth", 3),
        linecolor=config.get("axes_linecolor", "black"),
        tickfont=config.get("y_tickfont", dict(size=21)),
        showgrid=config.get("y_showgrid", True),
        zeroline=config.get("y_zeroline", True),
        zerolinecolor=config.get("y_zerolinecolor", "#b9b9b9"),
        zerolinewidth=config.get("y_zerolinewidth", 2),
    )

    fig.update_layout(
        scattermode="group",
        # higher scattergap -> narrower groups, so tighter packing *within* a
        # group AND more space *between* groups (no within-group gap param exists)
        scattergap=config.get("scattergap", 0.4),
        title=config.get(
            "title",
            "",
        ),
        font_family=config.get("font_family", "verdana"),
        font_color=config.get("font_color"),
        # https://plotly.com/python/reference/layout/#layout-legend
        legend=config.get("legend"),
        showlegend=config.get("showlegend", False),
        plot_bgcolor=config.get("bgcolor", "white"),
        paper_bgcolor=config.get("bgcolor", "white"),
    )
    fig.update_traces(
        marker=dict(size=config.get("marker_size", None)),
        line=dict(width=config.get("line_width", 4)),
        error_y=dict(
            thickness=config.get("error_bar_thickness", 3.6),
            width=config.get("error_bar_cap_width", 0),
        ),
    )

    # alternatively / additionally, draw grey dotted separators between groups
    # if config.get("group_separators", False):
    #     for boundary in range(n_sections - 1):
    #         fig.add_vline(
    #             x=boundary + 0.5,
    #             line_width=config.get("group_separator_width", 1),
    #             line_dash=config.get("group_separator_dash", "dot"),
    #             line_color=config.get("group_separator_color", "grey"),
    #         )

    fig.update_annotations(font_size=config.get("subplot_title_font_size", 28))

    if config.get("save", False):
        suffix = ""
        if only_high_sr:
            suffix += "-only_high_sr"
        if config.get("suffix") is not None:
            suffix += f"-{config.get('suffix')}"
        # only use baseline condition, assuming no comparisons across stories..
        baseline_condition_str = ""
        if "config_baseline" in config:
            baseline_condition_str = config["config_baseline"]["condition"]
            dir_name = "match_score_diff_to_baseline"
        else:
            dir_name = "match_score"

        filetype = config.get("filetype", "png")
        output_path = Path(
            config.get("study", ""),
            "word_position",
            config["story"],
            get_mode_str(config),
            get_model_name_str(config),
            dir_name,
            baseline_condition_str,
            f"scatter_{''.join(name_start_chars).upper()}{suffix}.{filetype}",
        )
        save_plot(config, fig, output_path, verbose=True)
