import os

import numpy as np
import pandas as pd
import plotly.express as px

from oc_pmc.load import load_per_participant_data
from oc_pmc.utils import save_plot
from oc_pmc.utils.aggregator import aggregator


def func_load_data(config: dict) -> pd.DataFrame:
    return load_per_participant_data(config)


def func_plot_distribution(
    config: dict,
    data_df: pd.DataFrame,
) -> None:
    measure = config["measure"]
    if config.get("within_participant_summary", False):
        data_df = data_df.groupby("participantID").aggregate({measure: "mean"})
    if config.get("group_column"):
        # the column which indicates which group a datapoint pertains to
        # 1. bin
        bins = np.linspace(
            config.get("min_x", data_df[measure].min()),
            config.get("max_x", data_df[measure].max()),
            config.get("nbins", 21) + 1,
        )
        bin_labels = (bins[1:] + bins[:-1]) / 2
        data_df["bins"] = pd.cut(
            data_df[measure], bins=bins, labels=bin_labels, include_lowest=True
        )
        data_df["dummy_value"] = 1
        data_df = data_df.reset_index()

        # randomly shuffle data so that colors are not assigned in order
        if not config.get("no_group_column_shuffle", False):
            data_df = data_df.sample(frac=1)

        auto_x_range = None
        if config.get("min_x") and config.get("max_x"):
            auto_x_range = (config["min_x"], config["max_x"])

        fig = px.bar(
            data_df,
            x="bins",
            y="dummy_value",
            color=config["group_column"],
            title=config.get("title", config["measure"]),
            range_x=config.get("x_range", auto_x_range),
            range_y=config.get("y_range"),
            color_discrete_sequence=config.get("color_sequence"),
            color_continuous_scale=config.get("color_sequence"),
            category_orders=config.get("category_orders"),
        )

    else:
        fig = px.histogram(
            data_df,
            x=config["measure"],
            color=config.get("color"),
            nbins=config.get("nbins"),
            title=config.get("title", config["measure"]),
            range_x=config.get("x_range"),
            range_y=config.get("y_range"),
            color_discrete_sequence=config.get("color_sequence"),
            histnorm=config.get("histnorm"),
            category_orders=config.get("category_orders"),
        )

    fig.update_layout(
        xaxis=dict(
            title=config.get("x_title", measure),
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
            title=config.get("y_title"),
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

    fig.update_layout(
        font_family=config.get("font_family", "verdana"),
        showlegend=config.get("showlegend", True),
        plot_bgcolor=config.get("bgcolor", "white"),
        paper_bgcolor=config.get("bgcolor", "white"),
        barmode=config.get("barmode"),
        bargap=config.get("bargap", 0),
        font_color=config.get("font_color"),
        legend=config.get("legend"),
    )
    fig.update_traces(opacity=config.get("opacity"))
    if config.get("marker") is not None:
        # Not sure if bug, but if you call update_traces(marker=None) the colors
        # of the plot are reset
        fig.update_traces(marker=config.get("marker"))

    # each hline/vline has to be a dict with the args:
    # https://plotly.com/python/horizontal-vertical-shapes/
    # https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html?highlight=add_hline#plotly.graph_objects.Figure.add_hline
    hlines = config.get("hlines")
    if hlines is not None:
        for hline in hlines:
            if "x" in hline and "y" not in hline:
                hline["y"] = hline.pop("x")
            fig.add_hline(**hline)
    vlines = config.get("vlines")
    # https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html?highlight=add_vline#plotly.graph_objects.Figure.add_vline
    if vlines is not None:
        for vline in vlines:
            if "y" in vline and "x" not in vline:
                vline["x"] = vline.pop("y")
            fig.add_vline(**vline)

    diff_category_name = config.get("color")
    if config.get("mean_lines"):
        if config.get("color"):
            means = data_df.groupby(config["color"])[measure].mean()
            for mean_line in config["mean_lines"]:
                condition = mean_line.pop(diff_category_name)
                if (
                    config.get("color_sequence")
                    and config.get("category_orders")
                    and not mean_line.get("color")
                ):
                    mean_line["line"]["color"] = config["color_sequence"][
                        config["category_orders"][diff_category_name].index(condition)
                    ]
                fig.add_vline(x=means[condition], **mean_line)

    if config.get("descriptive_lines"):
        mean = data_df[config["measure"]].mean()

        quant1 = config.get("quantile_1", 0.25)
        quant2 = config.get("quantile_2", 0.75)
        quantile25 = data_df[config["measure"]].quantile(quant1)
        quantile75 = data_df[config["measure"]].quantile(quant2)

        fig.add_vline(x=mean, annotation_text="mean")
        fig.add_vline(x=quantile25, annotation_text=f"{int(quant1 * 100)}th quantile")
        fig.add_vline(x=quantile75, annotation_text=f"{int(quant2 * 100)}th quantile")

    if config.get("custom_lines"):
        for line in config["custom_lines"]:
            fig.add_vline(**line)

    if config.get("legend_name_mapping"):
        # https://stackoverflow.com/a/64378982
        fig.for_each_trace(
            lambda t: t.update(name=config["legend_name_mapping"].get(t.name, t.name))
        )

    if config.get("show"):
        fig.show()
    if config.get("save"):
        filename = config["measure"].replace("/", "_").replace(" ", "-")
        if config.get("filepostfix"):
            filename += f"_{config['filepostfix']}"
        for key, value in config.items():
            if f"<{key}>" in filename:
                filename = filename.replace(f"<{key}>", value)
        filetype = config.get("filetype", "png")
        output_path = os.path.join(
            config.get("study", ""),
            config.get("script_name", "distribution"),
            f"{filename}.{filetype}",
        )  # type: ignore
        save_plot(config, fig, output_path)


def plot_distribution(config: dict):
    config["keep_columns"] = config["measure"]
    aggregator(
        config,
        load_func=func_load_data,
        call_func=func_plot_distribution,
    )


if __name__ == "__main__":
    no_filter = ("filter", {})
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
                                "neutralcue2": no_filter,
                                "interference_story": no_filter,
                                "interference_story_control": no_filter,
                                "interference_geometry": no_filter,
                                "interference_situation": no_filter,
                                "interference_tom": no_filter,
                                "suppress": no_filter,
                                "button_press": no_filter,
                                "button_press_suppress": no_filter,
                            },
                        ),
                    },
                ),
            },
        ),
        # data
        "measure": "spr/char",
        "aggregate_on": "all",
        # settings
        "descriptive_lines": True,
        "quantile_1": 0.1,
        "quantile_2": 0.9,
        # plotting
        "width": 900,
        "height": 900,
        "scale": 2,
        "save": True,
        "filetype": "png",
        "show": False,
    }
    plot_distribution(config)
