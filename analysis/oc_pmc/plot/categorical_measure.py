import os
from collections import defaultdict
from typing import Any, Dict, List, cast

import numpy as np
import pandas as pd
import plotly.express as px

from oc_pmc import get_logger
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import save_plot
from oc_pmc.utils.aggregator import aggregator

log = get_logger(__name__)


def func_load_questionnaire(config: Dict[str, Any]) -> pd.DataFrame:
    """This was a "nofilter" function at some point. I am not sure why.
    Now filtering can be decided by the caller function (config['filter'] = True/False).

    """
    return load_questionnaire({**config})


def func_plot_categorical_measure(
    config: Dict[str, Any], data_df: pd.DataFrame
) -> pd.DataFrame:
    category_name = config["measure_name"]

    # process category (e.g. replace certain values, rename nans)
    if config.get("replace_measure"):
        data_df[category_name] = data_df[category_name].replace(
            config["replace_measure"]
        )
        log.warning("Use 'replace_columns' instead of 'replace_measure'!")
    if config.get("replace_columns") is not None:
        for colname, col_replace_dct in config["replace_columns"].items():
            if not isinstance(col_replace_dct, dict):
                raise ValueError(
                    f"col_replace_dct has to be a dct not: {type(col_replace_dct)}"
                )
            data_df[colname] = data_df[colname].replace(col_replace_dct)

    category_counts_df = (
        data_df[category_name].value_counts(normalize=True).to_frame().reset_index()
    )
    category_counts_df["count"] = (
        data_df[category_name].value_counts(normalize=False).reset_index()["count"]
    )

    return category_counts_df


def plot_categorical_measure(config: Dict):
    data = aggregator(
        config,
        load_func=func_load_questionnaire,
        call_func=func_plot_categorical_measure,
    )

    measure = config["measure_name"]
    x = config.get("x", measure)
    y = "proportion" if config.get("normalize") else "count"
    color = config.get("color", measure)

    plot_ls = list()
    for data_config, data_df in data:
        # add measure as col name
        data_df[x] = data_config[x]
        plot_ls.append(data_df)

    plot_df = pd.concat(plot_ls)

    # remove category_order entries and color entries for categories which are not used
    # (because px.bar will create empty bars for them, if they are in between entries
    # which are used.)
    temp_category_orders = config.get("category_orders")
    temp_color_discrete_sequence = cast(List, config.get("color_sequence"))
    category_orders = None
    if temp_category_orders is not None:
        category_orders = defaultdict(list)
        color_discrete_sequence = list()
        for category_name in temp_category_orders:
            for idx, category in enumerate(temp_category_orders[category_name]):
                if category in plot_df[category_name].to_list():
                    category_orders[category_name].append(category)
                    # handle colors if given
                    if (
                        temp_color_discrete_sequence is not None
                        and category_name == color
                    ):
                        color_discrete_sequence.append(
                            temp_color_discrete_sequence[idx]
                        )

        if temp_color_discrete_sequence is None:
            color_discrete_sequence = None
    else:
        category_orders = temp_category_orders
        color_discrete_sequence = temp_color_discrete_sequence

    # make the plot
    if config.get("latex"):
        if config.get("latex_columns"):
            print(
                plot_df.loc[:, config["latex_columns"]].to_latex(
                    index=False, float_format="%.2f"
                )
            )
        else:
            print(plot_df.to_latex(index=False, float_format="%.2f"))
    else:
        print(plot_df)
    if config.get("orientation") == "h":
        # if orientation is horizontal, swap the x and y
        # arguments.
        fig = px.bar(
            plot_df,
            x=y,
            y=x,
            color=color,
            barmode=config.get("barmode", "relative"),
            title=config.get("title", config["measure_name"]),
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
                showticklabels=config.get("x_showticklabels"),
                showline=config.get("x_showline"),
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
            xaxis=dict(
                title=config.get("y_title", config["measure_name"]),
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
                showticklabels=config.get("y_showticklabels"),
                showline=config.get("y_showline"),
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
        )
    else:
        fig = px.bar(
            plot_df,
            x=x,
            y=y,
            color=color,
            barmode=config.get("barmode", "relative"),
            title=config.get("title", config["measure_name"]),
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
                showticklabels=config.get("x_showticklabels"),
                showline=config.get("x_showline"),
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
            yaxis=dict(
                title=config.get("y_title", config["measure_name"]),
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
                showticklabels=config.get("y_showticklabels"),
                showline=config.get("y_showline"),
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                showgrid=config.get("y_showgrid", True),
            ),
        )
    fig.update_traces(
        marker_line_width=0,
        # https://plotly.com/python/reference/bar/#bar-textposition
        textposition=config.get("textposition"),
        # https://github.com/d3/d3-format/tree/v1.4.5#d3-format
        texttemplate=config.get("texttemplate"),
        # https://plotly.com/python/reference/bar/#bar-textfont
        textfont=config.get("textfont"),
    )
    fig.update_layout(
        font_family=config.get("font_family", "verdana"),
        showlegend=config.get("showlegend", True),
        plot_bgcolor=config.get("bgcolor", "white"),
        paper_bgcolor=config.get("bgcolor", "white"),
        bargap=config.get("bargap", 0),
    )

    if config.get("save", False):
        no_file_postfix = (config.get("filepostfix") is not None) or (
            config.get("filepostfix") == ""
        )
        filepostfix = f"_{config['filepostfix']}" if no_file_postfix else ""
        filetype = config.get("filetype", "png")
        output_path = os.path.join(
            config.get("study", ""),
            "categorical_measure",
            f"{config['measure_name']}{filepostfix}.{filetype}",
        )
        save_plot(config=config, fig=fig, path=output_path)
    if config.get("show", False):
        fig.show(width=config["width"], height=config["height"])
