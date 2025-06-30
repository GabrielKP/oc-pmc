"""
Plot the story relatedness correlated
with the self reported lingering.

"""

import os
from copy import deepcopy
from itertools import product
from typing import Any, Dict, List, cast

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from oc_pmc import get_logger
from oc_pmc.load import (
    load_rated_wordchains,
    load_thought_entries_and_questionnaire,
    load_wordchains,
)
from oc_pmc.utils import config_to_descriptive_string, get_summary_func, save_plot
from oc_pmc.utils.aggregator import aggregator
from oc_pmc.utils.bootstrap import bootstrap_with_groups

log = get_logger(__name__)


def func_load(config: Dict) -> pd.DataFrame:
    if config.get("mode") == "double_press":
        te_df, quest_df = load_thought_entries_and_questionnaire(config)
        te_df["<data>"] = True
        quest_df["<data>"] = False
        te_quest_df = pd.concat((te_df, quest_df))
        return te_quest_df

    if config.get("mode") == "relatedness":
        # adaptive ratings
        if config.get("multiple_ratings"):
            # this allows specifications of following form:
            # "multiple_ratings": (
            #     "story",
            #     {
            #         "carver_original": {
            #             "approach": "human",
            #             "model": "moment",
            #             "story": "carver_original",
            #             "file": "all.csv",
            #         },
            #         "dark_bedroom": {
            #             "approach": "incontext_bulk",
            #             "model": "gpt-4o",
            #             "story": "dark_bedroom",
            #             "file": "0_.csv",
            #         },
            #     },
            # ),
            config = deepcopy(config)
            # match ratings file to current config
            level = config["multiple_ratings"][0]
            level_value = config[level]
            config["ratings"] = config["multiple_ratings"][1][level_value]
        return load_rated_wordchains(config)
    return load_wordchains(config)


def func_plot_by_time(
    config: Dict[str, Any],
    data_df: pd.DataFrame,
) -> go.Figure:
    """For given condition, computes mean and error bars of the story relatedness"""

    log.info(f"Plotting for {config}")

    if config.get("mode") == "double_press":
        # need to separate quest_df and te_df
        quest_df = (
            data_df.loc[~data_df["<data>"]]
            .dropna(axis=1, how="all")
            .drop(columns="<data>")
        )

        data_df = (
            data_df.loc[data_df["<data>"]]
            .dropna(axis=1, how="all")
            .drop(columns="<data>")
        )

    step = config["step"]
    shift = config.get("shift", 0)
    x_shift = shift
    x_column = "timestamp" if not config.get("x_column") else config["x_column"]

    # compute mean over column of interest
    column: str = config["column"]

    # replace specified columns
    if config.get("replace_columns") is not None:
        for colname, col_replace_dct in config["replace_columns"].items():
            if not isinstance(col_replace_dct, dict):
                raise ValueError(
                    f"col_replace_dct has to be a dct not: {type(col_replace_dct)}"
                )
            data_df[colname] = data_df[colname].replace(col_replace_dct)
            if config.get("mode") == "double_press":
                quest_df[colname] = quest_df[colname].replace(col_replace_dct)  # type: ignore

    # shift the words in certain conditions
    if config.get("shift_conditions"):
        shift_locs = data_df["condition"].isin(config["shift_conditions"])
        data_df.loc[shift_locs, x_column] += shift

    if config.get("shift_conditions_2"):
        shift_locs = data_df["condition"].isin(config["shift_conditions_2"])
        data_df.loc[shift_locs, x_column] += 2 * shift
        x_shift = 2 * x_shift

    # update grouping columns
    grouping_columns = ["story", "condition", "position", "bins"]
    if config.get("additional_grouping_columns"):
        grouping_columns += config["additional_grouping_columns"]

    # merge two values (e.g. for colors to be conditioned on both):
    if config.get("merged_columns"):
        data_df["merged_columns"] = data_df[config["merged_columns"][0]]
        for colname in config["merged_columns"][1:]:
            data_df["merged_columns"] = (
                data_df["merged_columns"] + "-" + data_df[colname]
            )
        # take into account quest_df for double_press
        if config.get("mode") == "double_press":
            quest_df["merged_columns"] = quest_df[config["merged_columns"][0]]  # type: ignore
            for colname in config["merged_columns"][1:]:
                quest_df["merged_columns"] = (  # type: ignore
                    quest_df["merged_columns"] + "-" + quest_df[colname]  # type: ignore
                )
        # need to add to grouping columns
        grouping_columns += ["merged_columns"]

        # need to remove the individual columns
        grouping_columns = list(
            filter(lambda x: x not in config["merged_columns"], grouping_columns)
        )

    # Need to determine min x value: take closest multiple to "step"
    min_x = config.get(
        "min_x",
        (min(data_df[x_column]) // step) * step,
    )
    max_x = config.get(
        "max_x",
        # accomodate largest value                            | shift   | don't remember
        int(np.ceil(max(data_df[x_column]) / step)) * step + x_shift + step - 1,
    )

    # bin rows
    bins = np.arange(min_x, max_x + 1, step)
    n_bins = len(bins) - 1
    bin_labels = [i + 0.5 for i in range(n_bins)]
    data_df["bins"] = pd.cut(data_df[x_column], bins=bins, labels=bin_labels)

    # different procedure for double presses & story relatedness
    if config.get("mode") == "double_press":
        grouping_columns_no_bins = list(filter(lambda x: x != "bins", grouping_columns))

        # 1. need to account for participants who did not press in the respective bin

        # add dummy values for each grouping combination without entry for bin
        group_indices_no_bins: list[tuple] = list(
            data_df.groupby(grouping_columns_no_bins).indices.keys()
        )  # type: ignore

        indexed_data_df = (
            data_df.reset_index()
            .set_index([*grouping_columns, "participantID"])
            .sort_index()
        )
        indexed_quest_df = (
            quest_df.reset_index().set_index(grouping_columns_no_bins).sort_index()  # type: ignore
        )
        bins_pos = grouping_columns.index("bins")
        dummy_rows = list()
        for group_index_no_bins in group_indices_no_bins:
            # get all participants in this group
            participantIDs = list(
                indexed_quest_df.loc[group_index_no_bins, "participantID"].unique()  # type: ignore
            )
            # check whether all bin values are contained
            for bin_label, participantID in product(bin_labels, participantIDs):
                index_to_check = (
                    *group_index_no_bins[:bins_pos],
                    bin_label,
                    *group_index_no_bins[bins_pos:],
                    participantID,
                )
                if not indexed_data_df.index.isin([index_to_check]).any():
                    # add dummy
                    dummy_row = data_df.iloc[0].copy()
                    dummy_row.name = participantID
                    dummy_row["double_press"] = 0
                    for grouping_value, grouping_column in zip(
                        index_to_check, grouping_columns
                    ):
                        dummy_row[grouping_column] = grouping_value
                    dummy_rows.append(dummy_row)
        # (it seems to me a significantly faster way to just initialize
        # each combination with 0 and then setting the existing ones, but
        # this works, and that's what really matters)

        # add dummy rows to main dataframe
        data_df = pd.concat((data_df, pd.DataFrame(dummy_rows)))
        data_df.index.name = "participantID"

        # get number of participants for grouping columns
        participant_count = (
            quest_df.reset_index()  # type: ignore
            .groupby(grouping_columns_no_bins)["participantID"]
            .nunique()
        )

        # need to add within participant double-presses before averaging
        mean_aggregated_participant = data_df.groupby(
            [*grouping_columns, "participantID"]
        ).aggregate({"double_press": "sum"})

        mean_aggregated = mean_aggregated_participant.groupby(
            grouping_columns
        ).aggregate({"double_press": "sum"})

        # participant_counts is not indexed by bins, have to remove it:
        index_bins = grouping_columns.index("bins")

        def remove_bins_index(index_bins: int, idx_group: tuple) -> tuple:
            return idx_group[:index_bins] + idx_group[index_bins + 1 :]

        # divide each group to obtain mean
        for idx_group in mean_aggregated.index:
            mean_aggregated.loc[idx_group, "double_press"] = (
                mean_aggregated.loc[idx_group, "double_press"]
                / participant_count.loc[remove_bins_index(index_bins, idx_group)]
            )  # type: ignore

        def sample_agg_te_func(
            data_df: pd.DataFrame,
            grouping_columns: List[str],
            participant_count: pd.DataFrame,
            index_bins: int,
        ) -> pd.DataFrame:
            mean_resampled = (
                data_df.groupby([*grouping_columns, "participantID"], observed=False)
                .aggregate({"double_press": "sum"})  # sum within participant
                .groupby(grouping_columns, observed=True)
                .sample(frac=1, replace=True)  # sample out of participants
                .groupby(grouping_columns, observed=False)
                .aggregate({"double_press": "sum"})  # sum over double presses
            )
            for idx_group in mean_resampled.index:
                mean_resampled.loc[idx_group, "double_press"] = (
                    mean_resampled.loc[idx_group, "double_press"]
                    / participant_count.loc[remove_bins_index(index_bins, idx_group)]
                )  # type: ignore
            return mean_resampled

        bootstrap_func = sample_agg_te_func
        bootstrap_args = dict(
            grouping_columns=grouping_columns,
            participant_count=participant_count,
            index_bins=index_bins,
        )
        bootstrap_df = data_df

        grouped_bins = data_df.groupby(grouping_columns, observed=False).count()
        n_observations_per_bin = grouped_bins[grouped_bins.columns[0]]

    else:
        # story relatedness mode

        if config.get("within_participant_summary", True):
            # 0. get within_participant_summary func
            summary_func = get_summary_func(config)

            # 1. Within participant mean
            sample_df = (
                data_df.groupby(["participantID", *grouping_columns], observed=True)
                .agg({column: summary_func})
                .reset_index()
            )

            # 2. Pivot (unnecessary, but matched with bootstrap to avoid bugs)
            grouping_columns_no_bins = list(
                filter(lambda x: x != "bins", grouping_columns)
            )
            sample_wide_df = sample_df.pivot(
                columns="bins",
                index=["participantID", *grouping_columns_no_bins],
                values=column,
            ).reset_index(list(range(1, len(grouping_columns_no_bins) + 1)))

            # 2. Bin mean
            bin_mean_wide_df = sample_wide_df.groupby(
                grouping_columns_no_bins, as_index=False
            ).mean()

            # 3. Unpivot
            mean_aggregated = bin_mean_wide_df.melt(
                id_vars=grouping_columns_no_bins, value_name=column
            ).set_index([*grouping_columns_no_bins, "bins"])

            # 3. Define bootstrap procedure
            def sample_agg_func_within_participants(
                sample_wide_df: pd.DataFrame,
                sample_wide_pID_grouping,
                grouping_columns_no_bins: List[str],
            ) -> pd.DataFrame:
                # 1. Resample participants
                chosen_ids = sample_wide_pID_grouping.sample(
                    frac=1, replace=True
                ).values
                resample_df: pd.DataFrame = sample_wide_df.loc[chosen_ids]  # type: ignore

                # 2. Bin means
                bin_mean_wide_df = resample_df.groupby(
                    grouping_columns_no_bins, as_index=False
                ).mean()

                # 3. unpivot
                return bin_mean_wide_df.melt(
                    id_vars=grouping_columns_no_bins
                ).set_index([*grouping_columns_no_bins, "bins"])

            bootstrap_func = sample_agg_func_within_participants
            sample_wide_pID_grouping = sample_wide_df.reset_index().groupby(
                grouping_columns_no_bins
            )["participantID"]
            bootstrap_args = dict(
                grouping_columns_no_bins=grouping_columns_no_bins,
                sample_wide_pID_grouping=sample_wide_pID_grouping,
            )
            bootstrap_df = sample_wide_df

            grouped_bins = sample_df.groupby(grouping_columns, observed=False).count()
            n_observations_per_bin = grouped_bins[grouped_bins.columns[0]]

        else:
            mean_aggregated = data_df.groupby(grouping_columns, observed=False).agg(
                {column: "mean"}
            )

            def sample_agg_func(
                data_df: pd.DataFrame,
                grouping_columns: List[str],
                column: str,
            ) -> pd.DataFrame:
                return (
                    data_df.groupby(grouping_columns, observed=False)
                    .sample(frac=1, replace=True)
                    .groupby(grouping_columns, observed=False)
                    .aggregate({column: "mean"})
                )

            bootstrap_func = sample_agg_func
            bootstrap_args = dict(
                grouping_columns=grouping_columns, column=config["column"]
            )
            bootstrap_df = data_df

            grouped_bins = data_df.groupby(grouping_columns, observed=False).count()
            n_observations_per_bin = grouped_bins[grouped_bins.columns[0]]

    # bootstrap
    if config.get("bootstrap"):
        # data_df
        lowers_df, uppers_df = bootstrap_with_groups(
            config, bootstrap_df.copy(), bootstrap_func, bootstrap_args
        )
        # have to subtract/add the actual mean to get 'error' only
        lowers_df["ci_lower"] = mean_aggregated[column] - lowers_df["ci_lower"]
        uppers_df["ci_upper"] = uppers_df["ci_upper"] - mean_aggregated[column]
        mean_aggregated = mean_aggregated.join(lowers_df).join(uppers_df)

    if not config.get("bin_n_as_observations", False):
        # in case in whichin_participant_mean is True, the number of words across
        # participants is still a good estimator for the size of the confidence ints.
        # This allows to use the real observation n as bin n
        grouped_bins = data_df.groupby(grouping_columns, observed=False).count()
        n_observations_per_bin = grouped_bins[grouped_bins.columns[0]]

    # filter bins that are too empty
    # mean_aggregated may have deleted empty bins due to the pivot function, thus need
    # to merge
    n_observations_per_bin.name = "obs_count"
    mean_aggregated_w_count = pd.merge(
        mean_aggregated,
        n_observations_per_bin.to_frame(),
        left_index=True,
        right_index=True,
        how="left",
    )

    mean_aggregated = mean_aggregated[
        mean_aggregated_w_count["obs_count"] >= config.get("min_bin_n", 1)
    ]

    plot_df = mean_aggregated.reset_index()

    # x tickvals
    x_tickvals = [i for i in range(n_bins + 1)]
    if x_column == "timestamp":
        x_ticktext = [f"{int(i // 1000)}s" for i in bins]
    # elif x_column == "word_count":
    #     x_ticktext = [f"{left} - {right}" for left, right in zip(bins[:-1], bins[1:])]
    else:
        x_ticktext = [str(i) for i in bins]

    if config.get("x_skip_first_tick", False):
        x_ticktext[0] = ""

    if config.get("offset_config") is not None:
        for colname, colvalue_offsets in config["offset_config"].items():
            for colvalue, offset in colvalue_offsets:
                plot_df.loc[plot_df[colname] == colvalue, "bins"] += offset

    # plot
    plot_df = plot_df.sort_values(grouping_columns)
    # https://plotly.com/python-api-reference/generated/plotly.express.line
    fig = px.line(
        plot_df,
        x="bins",
        y=column,
        color=config.get("color"),
        symbol=config.get("symbol"),
        facet_row=config.get("facet_row"),
        line_dash=config.get("line_dash", config.get("symbol")),
        color_discrete_sequence=cast(List, config.get("color_sequence")),
        markers=True,
        error_y="ci_upper" if config.get("bootstrap") else None,
        error_y_minus="ci_lower" if config.get("bootstrap") else None,
        category_orders=config.get("category_orders"),
        color_discrete_map=config.get("color_map"),
        symbol_map=config.get("symbol_map"),
        line_dash_map=config.get(
            "line_dash_map"
        ),  # ['solid', 'dot', 'dash', 'longdash', 'dashdot', 'longdashdot']
    )
    fig.update_layout(
        xaxis=dict(
            title=config.get("x_title"),
            title_font_size=config.get("x_title_font_size", 32),
            title_standoff=config.get("x_title_standoff", 25),
            title_font_color=config.get("x_title_font_color", "black"),
            tickmode="array",
            ticks=config.get("x_ticks", "outside"),
            tickwidth=config.get("x_tickwidth"),
            rangemode=config.get("x_rangemode"),
            range=config.get("x_range", (min(x_tickvals), None)),
            tickvals=x_tickvals,
            ticktext=x_ticktext,
            tickcolor=config.get("axes_tickcolor"),
            showline=True,
            linewidth=config.get("axes_linewidth", 6),
            linecolor=config.get("axes_linecolor", "black"),
            tickfont=config.get("x_tickfont", dict(size=32)),
            tickangle=config.get("tickangle", 0),
            showgrid=config.get("x_showgrid", True),
        ),
        yaxis=dict(
            title=config.get("y_title"),
            title_font_size=config.get("y_title_font_size", 32),
            title_standoff=config.get("y_title_standoff", 25),
            title_font_color=config.get("y_title_font_color", "black"),
            range=config.get("y_range"),
            ticks=config.get("y_ticks", "outside"),
            tickwidth=config.get("y_tickwidth", 6),
            tickmode="array",
            tickvals=config.get("y_tickvals"),
            ticktext=config.get("y_ticktext"),
            tickcolor=config.get("axes_tickcolor"),
            showline=True,
            linewidth=config.get("axes_linewidth", 6),
            linecolor=config.get("axes_linecolor", "black"),
            tickfont=config.get("y_tickfont", dict(size=32)),
            showgrid=config.get("y_showgrid", True),
        ),
        font_family=config.get("font_family", "verdana"),
        font_color=config.get("font_color"),
        # https://plotly.com/python/reference/layout/#layout-legend
        legend=config.get("legend"),
        showlegend=config.get("showlegend", True),
        plot_bgcolor=config.get("bgcolor", "white"),
        paper_bgcolor=config.get("bgcolor", "white"),
    )
    fig.update_traces(
        marker=dict(size=config.get("marker_size", 20)),
        line=dict(width=config.get("line_width", 4)),
    )
    if config.get("legend_name_mapping"):
        # https://stackoverflow.com/a/64378982
        fig.for_each_trace(
            lambda t: t.update(name=config["legend_name_mapping"].get(t.name, t.name))
        )

    if config.get("save", False):
        filename = (
            "shifted_"
            if config.get("shift_conditions") or config.get("shift_conditions_2")
            else ""
        )
        filename += config_to_descriptive_string(config)
        if config.get("filepostfix"):
            filename += f"_{config['filepostfix']}"
        filetype = config.get("filetype", "png")

        by_what = "by_time" if x_column == "timestamp" else f"by_{config['x_column']}"
        output_path = os.path.join(
            config.get("study", ""),
            config.get("script_name", by_what),
            config["mode"],
            f"{filename}.{filetype}",
        )  # type: ignore
        save_plot(config, fig, output_path)

    if config.get("show", False):
        fig.show(width=config["width"], height=config["height"])

    return fig


def plot_by_time_shifted(config):
    aggregator(
        config,
        load_func=func_load,
        call_func=func_plot_by_time,
        no_extra_columns=False,
    )


if __name__ == "__main__":
    time_filter = ("filter", {"exclude": [("gte", "timestamp", 180000)]})
    time_load_spec = ("position", {"post": time_filter, "pre": time_filter})
    config = {
        "load_spec": (
            "all",
            {
                "all": (
                    "story",
                    {
                        "carver_original": (
                            "condition",
                            {
                                "neutralcue": time_load_spec,
                                "interference_pause": time_load_spec,
                                "interference_situation": time_load_spec,
                            },
                        ),
                    },
                )
            },
        ),
        "aggregate_on": "story",
        "ratings": {
            "approach": "human",
            "model": "moment",
            "story": "carver_original",
            "file": "all.csv",
        },
        # extra config
        "mode": "relatedness",
        "step": 30000,
        "shift": 30000,
        "shift_conditions": ["interference_pause", "interference_situation"],
        # bootstrap config
        "bootstrap": True,
        "n_bootstrap": 100,
        "ci": 0.95,
        # plot config
        "plotkind": "line",
        "width": 1500,
        "height": 600,
        "scale": 2,
        "color": "condition",
        "symbol": "position",
        # "facet_row": "story",
        "color_sequence": [
            "#F8766D",  # red
            "#ffc000",  # yellow
            "#5996C5",  # light blue
            "#004D40",  # dark green
            "#d6abd7",  # light purple
            "#ed7d31",  # orange
            "#4472c4",  # blue
            "#70ad47",  # green
            "#44546A",  # dark blue
            "purple",
        ],
        "showlegend": True,
        "save": True,
        "filetype": "png",
        "show": False,
    }
    mode = config.get("mode")
    if mode == "relatedness":
        config["column"] = "story_relatedness"
        config["title_y"] = ""
        config["title_x"] = ""
        config["y_range"] = [2.3, 4.2]
        config["y_tickvals"] = [2.5, 3, 3.5, 4]
        config["y_ticktext"] = ["2.5", "3", "3.5", "4"]
    elif mode == "rt":
        config["column"] = "word_time"
        config["title_y"] = ""
        config["title_x"] = ""
    else:
        raise ValueError(f"Unknown mode: {mode}")
    plot_by_time_shifted(config)
