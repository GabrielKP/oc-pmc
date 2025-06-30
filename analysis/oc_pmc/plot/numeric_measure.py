import os
from collections import defaultdict
from copy import deepcopy
from typing import Any, Callable, Optional, Union, cast

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from oc_pmc import get_logger
from oc_pmc.load import load_per_participant_data
from oc_pmc.utils import save_plot
from oc_pmc.utils.aggregator import aggregator
from oc_pmc.utils.bootstrap import bootstrap_with_groups

log = get_logger(__name__)


def func_plot_numeric_measure(
    config: dict[str, Any],
    data_df: pd.DataFrame,
) -> go.Figure:
    measure = config.get("measure_name")
    if measure is None:
        measure = config["measure"]
    column = measure
    category_name = config.get("x", "condition")
    summary_func: Callable = config.get("summary_fun", "mean")

    # update grouping columns
    grouping_columns = ["story", "condition", "position"]
    if config.get("additional_grouping_columns"):
        grouping_columns += config["additional_grouping_columns"]

    means_df = data_df.groupby(grouping_columns, observed=False).aggregate(
        {column: summary_func}
    )

    def sample_agg_func(
        data_df: pd.DataFrame,
        grouping_columns: list[str],
        column: str,
        summary_func: Callable,
    ) -> pd.DataFrame:
        return (
            data_df.groupby(grouping_columns, observed=False)
            .sample(frac=1, replace=True)
            .groupby(grouping_columns, observed=False)
            .aggregate({column: summary_func})
        )

    if config.get("bootstrap"):
        lowers_df, uppers_df = bootstrap_with_groups(
            config,
            data_df,
            sample_agg_func,
            aggregation_args=dict(
                grouping_columns=grouping_columns,
                column=column,
                summary_func=summary_func,
            ),
        )
        lowers_df["ci_lower"] = means_df[column] - lowers_df["ci_lower"]
        uppers_df["ci_upper"] = uppers_df["ci_upper"] - means_df[column]
        means_df = means_df.join(lowers_df).join(uppers_df)

    plot_df = means_df.reset_index()

    # remove category_order entries and color entries for categories which are not used
    # (because px.bar will create empty bars for them, if they are in between entries
    # which are used.)
    temp_category_orders = config.get("category_orders")
    temp_color_discrete_sequence = cast(list, config.get("color_sequence"))
    if (
        temp_category_orders is not None
        and temp_category_orders.get(category_name) is not None
    ):
        category_orders = defaultdict(list)
        color_discrete_sequence = []
        for idx, category in enumerate(temp_category_orders[category_name]):
            if category in data_df[category_name].to_list():
                category_orders[category_name].append(category)
                # handle colors if given
                if temp_color_discrete_sequence is not None:
                    color_discrete_sequence.append(temp_color_discrete_sequence[idx])

        if len(color_discrete_sequence) == 0:
            raise ValueError(
                "No entry in category_order matches actual data categories."
            )

        if temp_color_discrete_sequence is None:
            color_discrete_sequence = None
    else:
        category_orders = temp_category_orders
        color_discrete_sequence = temp_color_discrete_sequence

    # make the plot
    if config.get("orientation") == "h":
        # if orientation is horizontal, swap the x and y
        # arguments.
        fig = px.bar(
            plot_df,
            x=column,
            y=category_name,
            error_x="ci_upper" if config.get("bootstrap") else None,
            error_x_minus="ci_lower" if config.get("bootstrap") else None,
            color=config.get("color", category_name),
            text=config.get("text"),
            barmode=config.get("barmode", "relative"),
            title=config.get("title", measure),
            color_discrete_sequence=color_discrete_sequence,
            orientation=config.get("orientation"),
            category_orders=category_orders,
        )
        fig.update_layout(
            yaxis=dict(
                title=config.get("x_title"),
                title_font_size=config.get("x_title_font_size", 32),
                title_font_color=config.get("x_title_font_color", "black"),
                title_standoff=config.get("x_title_standoff", 25),
                range=config.get("x_range"),
                tickmode="array",
                ticks=config.get("x_ticks", "outside"),
                tickwidth=config.get("x_tickwidth"),
                tickfont=config.get("x_tickfont", dict(size=32)),
                tickvals=config.get("x_tickvals"),
                ticktext=config.get("x_ticktext"),
                tickangle=config.get("x_tickangle"),
                tickcolor=config.get("axes_tickcolor"),
                showticklabels=config.get("x_showticklabels"),
                showline=True,
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
            xaxis=dict(
                title=config.get("y_title", measure),
                title_font_size=config.get("y_title_font_size", 32),
                title_font_color=config.get("y_title_font_color", "black"),
                title_standoff=config.get("y_title_standoff", 25),
                tickmode="array",
                range=config.get("y_range"),
                ticks=config.get("y_ticks", "outside"),
                tickwidth=config.get("y_tickwidth", 6),
                tickfont=config.get("y_tickfont", dict(size=32)),
                tickvals=config.get("y_tickvals"),
                ticktext=config.get("y_ticktext"),
                tickangle=config.get("y_tickangle"),
                tickcolor=config.get("axes_tickcolor"),
                showticklabels=config.get("y_showticklabels"),
                showline=True,
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
        )
        # swapped axes!
        hlines = config.get("vlines")
        vlines = config.get("hlines")
    else:
        fig = px.bar(
            plot_df,
            x=category_name,
            y=column,
            error_y="ci_upper" if config.get("boostrap") else None,
            error_y_minus="ci_lower" if config.get("boostrap") else None,
            color=config.get("color", category_name),
            text=config.get("text"),
            barmode=config.get("barmode", "relative"),
            title=config.get("title", measure),
            color_discrete_sequence=color_discrete_sequence,
            orientation=config.get("orientation"),
            category_orders=category_orders,
        )
        fig.update_layout(
            xaxis=dict(
                title=config.get("x_title"),
                title_font_size=config.get("x_title_font_size", 32),
                title_font_color=config.get("x_title_font_color", "black"),
                title_standoff=config.get("x_title_standoff", 25),
                range=config.get("x_range"),
                tickmode="array",
                ticks=config.get("x_ticks", "outside"),
                tickwidth=config.get("x_tickwidth"),
                tickfont=config.get("x_tickfont", dict(size=32)),
                tickvals=config.get("x_tickvals"),
                ticktext=config.get("x_ticktext"),
                tickangle=config.get("x_tickangle"),
                tickcolor=config.get("axes_tickcolor"),
                showticklabels=config.get("x_showticklabels"),
                showline=True,
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
            yaxis=dict(
                title=config.get("y_title", measure),
                title_font_size=config.get("y_title_font_size", 32),
                title_font_color=config.get("y_title_font_color", "black"),
                title_standoff=config.get("y_title_standoff", 25),
                tickmode="array",
                range=config.get("y_range"),
                ticks=config.get("y_ticks", "outside"),
                tickwidth=config.get("y_tickwidth", 6),
                tickfont=config.get("y_tickfont", dict(size=32)),
                tickvals=config.get("y_tickvals"),
                ticktext=config.get("y_ticktext"),
                tickangle=config.get("y_tickangle"),
                tickcolor=config.get("axes_tickcolor"),
                showticklabels=config.get("y_showticklabels"),
                showline=True,
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
        )
        hlines = config.get("hlines")
        vlines = config.get("vlines")
    fig.update_traces(
        error_x=dict(
            thickness=12,
            width=0,
        ),
        error_y=dict(
            thickness=12,
            width=0,
        ),
    )
    fig.update_layout(
        font_family=config.get("font_family", "verdana"),
        showlegend=config.get("showlegend", True),
        plot_bgcolor=config.get("bgcolor", "white"),
        paper_bgcolor=config.get("bgcolor", "white"),
        bargap=config.get("bargap", 0),
        font_color=config.get("font_color"),
        legend=config.get("legend"),
    )

    # each hline/vline has to be a dict with the args:
    # https://plotly.com/python/horizontal-vertical-shapes/
    # https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html?highlight=add_hline#plotly.graph_objects.Figure.add_hline
    # https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html?highlight=add_vline#plotly.graph_objects.Figure.add_vline
    if hlines is not None:
        for hline in hlines:
            if "x" in hline and "y" not in hline:
                hline["y"] = hline.pop("x")
            fig.add_hline(**hline)
    if vlines is not None:
        for vline in vlines:
            if "y" in vline and "x" not in vline:
                vline["x"] = vline.pop("y")
            fig.add_vline(**vline)

    # Bootstrap annotation
    if config.get("show_bootstrap_text") and config.get("bootstrap"):
        n_bootstrap = config.get("n_bootstrap", 5000)
        ci = config.get("ci", 0.95)
        fig.add_annotation(
            text=f"{ci * 100}% CI, n={n_bootstrap}",
            xref="paper",
            yref="paper",
            x=1,
            y=-0.06,
            showarrow=False,
        )

    # N for each sample
    if config.get("show_n_samples", False):
        n_samples_texts = [f"{key} n={len(value)}" for key, value in data_df.items()]
        fig.add_annotation(
            text=",  ".join(n_samples_texts),
            xref="paper",
            yref="paper",
            x=1,
            y=0.8,
            showarrow=False,
        )

    # Save the plot
    if config.get("save", False):
        no_file_postfix = (config.get("filepostfix") is not None) or (
            config.get("filepostfix") == ""
        )
        filepostfix = f"_{config['filepostfix']}" if no_file_postfix else ""
        filetype = config.get("filetype", "png")
        output_path = os.path.join(
            config.get("study", ""),
            "numeric_measure",
            f"{measure}{filepostfix}.{filetype}",
        )
        save_plot(config=config, fig=fig, path=output_path)

    # Show the plot
    if config.get("show", False):
        fig.show(width=config["width"], height=config["height"])

    if config.get("kruskal", False):
        raise DeprecationWarning("Use test_two or test_multiple in oc_pmc.stats")
    return fig


def plot_numeric_measure(config: dict):
    # get data to plot
    aggregator(
        config,
        load_func=load_per_participant_data,
        call_func=func_plot_numeric_measure,
    )


if __name__ == "__main__":
    nofilter = ("position", {"post": ("filter", {})})
    config = {
        # Data
        "load_spec": (
            "all",
            {
                "all": (
                    "story",
                    {
                        "carver_original": (
                            "condition",
                            {
                                # "button_press": nofilter,
                                # "button_press_suppress": nofilter,
                                "neutralcue": nofilter,
                                "suppress": nofilter,
                                # "word_scrambled": nofilter,
                            },
                        ),
                    },
                )
            },
        ),
        "aggregate_on": "story",
        # on what measure
        "measure_name": "linger_rating",
        "summary_func": np.mean,
        # plot config
        "y_range": [1, 7],
        "color_sequence": [
            "#4472c4",  # blue
            "#70ad47",  # green
            "#F8766D",  # red
            "#ffc000",  # yellow
            # "#5996C5",  # light blue
        ],
        "showlegend": False,
        # "tickvals": [0, 1],
        # "ticktext": ["Intact", "Word-<br>scrambled"],
        # bootstrap
        "n_bootstrap": 5000,
        # save config
        "width": 900,
        "height": 900,
        "scale": 2.0,
        # kruskal
        "show": True,
    }
    plot_numeric_measure(config=config)
