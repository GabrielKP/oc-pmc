import os
from typing import Dict, List, Optional, Union

import pandas as pd
import plotly.express as px

from oc_pmc import OUTPUTS_DIR, console, get_logger
from oc_pmc.utils import check_make_dirs

log = get_logger(__name__)

BASEDIR = os.path.join(OUTPUTS_DIR, "plots/exclusions")


def plot_exclusion_plots(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: float,
    colname: str,
    title: str,
    nbins: Optional[int] = None,
    x_range: Optional[List] = None,
    skip_to_compare: bool = False,
) -> None:
    condition_name = config.get("to_exclude_name", "to_exclude")

    plot_path = os.path.join(
        BASEDIR, condition_name, f"{colname.replace('/', '-').replace(' ', '_')}.png"
    )
    check_make_dirs(plot_path)

    to_exclude["condition"] = condition_name
    data_df = to_exclude
    if not skip_to_compare:
        to_compare["condition"] = config.get("to_compare_name", "to_compare")
        data_df = pd.concat([to_exclude, to_compare])

    if x_range is not None and any(data_df[colname] > x_range[1]):
        log.info(f"Cutting off data > {x_range[1]}")
        data_df = data_df[data_df[colname] <= x_range[1]]

    plot = px.histogram(
        data_df,
        x=colname,
        nbins=nbins,
        title=title,
        range_x=x_range,
        color="condition",
        barmode="overlay",
    ).add_vline(x=threshold)
    plot.write_image(plot_path)
    print("---")


def exclusion_spr_char_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: float,
    interference: bool = False,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with spr/char correlation
    being lower than the threshold."""

    colname = "spr/char" if not interference else "spr/char_interference"

    print(f"Corr: {colname} threshold: {threshold}")
    spr_char_exclusion = to_exclude[colname] < threshold
    spr_char_exclusion.name = colname
    print(f"Exclusions: {spr_char_exclusion.sum()}")

    # plot
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        "Distribution spr/char correlations. exclusions < threshold",
        15,
        [-0.5, 1],
    )

    return spr_char_exclusion


def exclusion_spr_char(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with spr/char correlation
    being lower than 25th percentile - 1.5  * iqr."""

    iqr = to_compare["spr/char"].quantile(0.75) - to_compare["spr/char"].quantile(0.25)
    threshold = to_compare["spr/char"].quantile(0.25) - 1.5 * iqr

    return exclusion_spr_char_abs(config, to_exclude, to_compare, threshold)


def exclusion_spr_wcg_break(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with time between reading
    and wcg being higher than 75th percentile + 1.5  * iqr."""

    iqr = to_compare["spr-wcg-break"].quantile(0.75) - to_compare[
        "spr-wcg-break"
    ].quantile(0.25)

    threshold = to_compare["spr-wcg-break"].quantile(0.75) + 1.5 * iqr
    print(f"spr-wcg-break threshold: {threshold}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "spr-wcg-break",
        "Distribution spr-wcg-break times. threshold < exclusions",
        40,
    )

    spr_wcg_break_exclusion = to_exclude["spr-wcg-break"] > threshold

    return spr_wcg_break_exclusion


def exclusion_spr_wcg_break_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: int,
    colname: str = "spr-wcg-break",
    skip_to_compare: bool = False,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with time between reading
    and wcg being higher than threshold given."""

    print(f"{colname} threshold: {threshold}")
    spr_wcg_break_exclusion = to_exclude[colname] > threshold
    spr_wcg_break_exclusion.name = colname
    print(f"Exclusions: {spr_wcg_break_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        "Distribution spr-wcg-break times. threshold < exclusions",
        40,
        x_range=[0, 200_000],
        skip_to_compare=skip_to_compare,
    )

    return spr_wcg_break_exclusion


def exclusion_reaction_time_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: Union[int, float],
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a mean
    reaction time higher than the threshold."""
    print(f"rt_mean threshold: {threshold}")
    rt_time_exclusion = to_exclude["rt_mean"] > threshold
    rt_time_exclusion.name = "rt_mean"
    print(f"Exclusions: {rt_time_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "rt_mean",
        "Distribution rt_mean. threshold < exclusions",
        40,
        x_range=[0, 25_000],
    )

    return rt_time_exclusion


def exclusion_reaction_time(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a mean
    reaction time higher than 75th percentile + 1.5  * iqr."""

    iqr = to_compare["rt_mean"].quantile(0.75) - to_compare["rt_mean"].quantile(0.25)
    threshold = to_compare["rt_mean"].quantile(0.75) + 1.5 * iqr

    return exclusion_reaction_time_abs(config, to_exclude, to_compare, threshold)


def exclusion_reaction_time_max(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: int = 20000,
    post_only: bool = False,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a max reaction
    time bigger than given threshold."""
    print(f"rt_max threshold: {threshold}")
    excl_col = "rt_max_post" if post_only else "rt_max"
    rt_time_exclusion = to_exclude[excl_col] > threshold
    rt_time_exclusion.name = excl_col
    print(f"Exclusions: {rt_time_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        excl_col,
        f"Distribution {excl_col}. threshold < exclusions",
        40,
        x_range=[0, 100_000],
    )

    return rt_time_exclusion


def exclusion_comp_prop(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: float = 0.25,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a comprehension
    proportion of smaller/equal to given threshold."""
    print(f"comp_prop threshold: {threshold}")
    comp_prop_exclusion = to_exclude["comp_prop"] <= threshold
    comp_prop_exclusion.name = "comp_prop"
    print(f"Exclusions: {comp_prop_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "comp_prop",
        "Distribution comp_prop. threshold <= Exclusions",
        40,
        [0, 1],
    )

    return comp_prop_exclusion


def exclusion_catch_prop(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: float = 0.5,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a comprehension
    proportion of smaller to given threshold."""
    print(f"catch_prop threshold: < {threshold}")
    catch_prop_exclusion = to_exclude["catch_prop"] < threshold
    print(f"Exclusions: {catch_prop_exclusion.sum()}")

    print(f"Catch prop   0: {(to_exclude['catch_prop'] == 0).sum()}")
    print(f"Catch prop 0.5: {(to_exclude['catch_prop'] == 0.5).sum()}")
    print(f"Catch prop   1: {(to_exclude['catch_prop'] == 1).sum()}")
    print("---")

    return catch_prop_exclusion


def exclusion_story_read(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded which already
    read the story."""

    print("read_story threshold: Y")
    comp_prop_exclusion = to_exclude["read_story"] == "Y"
    print(f"Exclusions: {comp_prop_exclusion.sum()}")

    print(f"Story read Y: {comp_prop_exclusion.sum()}")
    print(f"Story read N: {(~comp_prop_exclusion).sum()}")
    print("---")

    comp_prop_exclusion.name = "read_story"
    return comp_prop_exclusion


def exclusion_time_away(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a time away
    higher than 75th percentile + 1.5  * iqr."""

    iqr = to_compare["time away (m)"].quantile(0.75) - to_compare[
        "time away (m)"
    ].quantile(0.25)

    threshold = to_compare["time away (m)"].quantile(0.75) + 1.5 * iqr
    print(f"time away (m) threshold: {threshold}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "time away (m)",
        "Distribution time away (m). threshold < exclusions",
        40,
        [0, 80],
    )

    rt_time_exclusion = to_exclude["time away (m)"] > threshold

    return rt_time_exclusion


def exclusion_exp_time_away_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: float,
) -> pd.Series:
    """Returns bool Series marking all participants excluded which where longer away
    than threshold during main_experiment stages.
    """

    print(f"exp_time threshold: {threshold}")
    exp_time_exclusion = to_exclude["exp_time_away"] > threshold
    exp_time_exclusion.name = "time_exp"
    print(f"Exclusions: {exp_time_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "exp_time_away",
        "Distribution exp_time times. threshold < exclusions",
        40,
        [0, 100_000],
    )

    return exp_time_exclusion


def exclusion_focusevents_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: Union[int, float],
) -> pd.Series:
    print(f"focusevents threshold: {threshold}")
    focus_events_exclusion = to_exclude["focusevents"] > threshold
    focus_events_exclusion.name = "focusevents"
    print(f"Exclusions: {focus_events_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "focusevents",
        "Distribution focusevents. threshold < exclusions",
        40,
        [0, 50],
    )

    return focus_events_exclusion


def exclusion_focusevents(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with focusevents outlier:
    All data points above 75th percentile + 1.5  * iqr the comparison df."""

    iqr = to_compare["focusevents"].quantile(0.75) - to_compare["focusevents"].quantile(
        0.25
    )
    threshold = to_compare["focusevents"].quantile(0.75) + 1.5 * iqr

    return exclusion_focusevents_abs(config, to_exclude, to_compare, threshold)


def exclusion_suppress_probe(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    handle_typo: bool = False,
) -> pd.Series:
    """Returns a bool series marking participants as excluded if they do not
    answer with "food" or "story" in the suppression probe.

    handle_typo is for the 'suppress' condition, in which 'guess_suppress_2' was
    mistakingly written as 'guess_suppres_2'
    """

    print("suppress_probe threshold: 'food', 'story'")

    def _not_food(row):
        probe = str(row["guess_suppress_1"]).lower()
        return (
            "food" not in probe
            and "aliments" not in probe
            and "foot" not in probe
            and "eat" not in probe
        )

    def _not_story(row):
        field_key = "guess_suppres_2" if handle_typo else "guess_suppress_2"
        probe = str(row[field_key]).lower()
        return (
            "story" not in probe
            and "stories" not in probe
            and "sotry" not in probe
            and "passage" not in probe
            and "the text" not in probe
            and "in the read" not in probe
        )

    not_food = to_exclude.apply(_not_food, axis=1)
    not_story = to_exclude.apply(_not_story, axis=1)

    suppress_probe_exclusion = not_food | not_story

    print((f"Not Food: {not_food.sum()}"))
    print((f"Not Story: {not_story.sum()}"))
    print(f"Excluded: {suppress_probe_exclusion.sum()}")
    print("---")

    return suppress_probe_exclusion


def exclusion_time_unpressed(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: float,
) -> pd.Series:
    """Returns a bool series marking participants as excluded if they unpressed the
    pause button for longer than threshold."""

    print(f"time_unpressed threshold: {threshold}")

    time_unpressed = to_exclude["time_unpressed"] > threshold

    time_unpressed.name = "time_unpressed"
    return time_unpressed


def exclusion_spr_max(
    config: Dict, to_exclude_df: pd.DataFrame, threshold: int
) -> pd.Series:
    print(f"spr_max threshold: {threshold}")

    plot_exclusion_plots(
        config,
        to_exclude_df,
        pd.DataFrame(),
        threshold,
        "spr_max",
        "SPR max",
        nbins=15,
        x_range=[0, 100000],
        skip_to_compare=True,
    )

    spr_max = to_exclude_df["spr_max"] > threshold
    spr_max.name = "spr_max"
    return spr_max


def exclusion_spr_time(
    config: Dict, to_exclude_df: pd.DataFrame, threshold: int
) -> pd.Series:
    print(f"spr_time threshold: {threshold}" + "\n---")
    spr_time = (
        to_exclude_df["reading_stage_end"] - to_exclude_df["reading_stage_start"]
        < threshold
    )
    spr_time.name = "spr_time"
    return spr_time


def print_stage_times(pID_stage_times: pd.DataFrame):
    stage_time_names = [
        name for name in pID_stage_times.columns if name.endswith("_time")
    ]
    max_len = max(map(len, stage_time_names))
    console.print("Stage Times (post-excluded)", style="yellow")
    for stage_time_name in stage_time_names:
        stage_time_mean = (pID_stage_times[stage_time_name] / 1000).mean()
        stage_time_std = (pID_stage_times[stage_time_name] / 1000).std()
        stage_time_mean_min = stage_time_mean / 60

        whitespaces = " " * (max_len - len(stage_time_name))
        print(
            f"{stage_time_name}{whitespaces} | {round(stage_time_mean, 2):6.2f}s"
            f" ({round(stage_time_std, 2):6.2f})"
            f" | {round(stage_time_mean_min, 2):6.2f}m"
        )
