"""
Plot a scatter plot between two measures.

"""

import os
from typing import Any, Dict, List, Tuple, cast

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm

from oc_pmc import get_logger
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import config_to_descriptive_string, save_plot
from oc_pmc.utils.aggregator import aggregator

log = get_logger(__name__)


def short_coefs(coefs: List) -> str:
    if len(coefs) == 0:
        return ""
    if len(coefs) == 1:
        return round(coefs[0], 2)
    return ", ".join([f"{coef:.2f}" for coef in coefs[1:]])


def summary_str(predictor_names, outcome_names, result) -> str:
    return (
        f"Predictor(s): {predictor_names} -> "
        f"Outcome: {outcome_names}"
        "\n"
        f"coeffs: {short_coefs(result.params)},"
        f" r(+/-) {result.rsquared**0.5:.3f},"
        f" r2: {result.rsquared:.3f},"
        f" f({result.df_model}, {result.df_resid}) = {result.fvalue:.2f},"
        f" p = {result.f_pvalue:.3f}"
    )


def func_plot_scatter_sr_srl(
    config: Dict[str, Any],
    data_df: pd.DataFrame,
) -> go.Figure:
    """For given condition, computes mean and error bars of the story relatedness"""

    log.info(f"Plotting for {config}")

    x_measure = cast(str, config.get("x_measure"))
    y_measure = cast(str, config.get("y_measure"))

    plot_df = data_df[[x_measure, y_measure]]

    # pick the right color if category_orders and color_sequence are given
    category_orders = config.get("category_orders")
    color_discrete_sequence = cast(List, config.get("color_sequence"))
    if (
        category_orders is not None
        and category_orders.get("condition") is not None
        and color_discrete_sequence is not None
        and config.get("condition") is not None
    ):
        color_idx = category_orders["condition"].index(config["condition"])
        colors = [color_discrete_sequence[color_idx]]
    elif color_discrete_sequence is not None:
        colors = color_discrete_sequence
    else:
        colors = None

    # plot and correlate
    fig = px.scatter(
        plot_df,
        x=x_measure,
        y=y_measure,
        trendline="ols",
        trendline_color_override=config.get("trendline_color", "black"),
        marginal_x="histogram",
        marginal_y="histogram",
        color_discrete_sequence=colors,
        title=config.get("title"),
    )
    fig.update_layout(
        xaxis=dict(
            title=config.get("x_title", x_measure),
            title_font_size=config.get("x_title_font_size", 32),
            title_font_color=config.get("x_title_font_color", "black"),
            title_standoff=config.get("x_title_standoff", 25),
            range=config.get("x_range"),
            ticks="outside",
            tickwidth=config.get("y_tickwidth", 6),
            tickmode="array",
            tickcolor=config.get("tickcolor"),
            tickvals=config.get("x_tickvals"),
            ticktext=config.get("x_ticktext"),
            showline=True,
            linewidth=config.get("axes_linewidth", 6),
            linecolor=config.get("axes_linecolor", "black"),
            tickfont=config.get("x_tickfont", dict(size=32)),
            tickangle=config.get("tickangle", 0),
            showgrid=config.get("x_showgrid", True),
            zeroline=config.get("x_zeroline", False),
        ),
        yaxis=dict(
            title=config.get("y_title"),
            title_font_size=config.get("y_title_font_size", 42),
            title_standoff=config.get("y_title_standoff", 25),
            title_font_color=config.get("y_title_font_color", "black"),
            range=config.get("y_range"),
            ticks="outside",
            tickwidth=config.get("y_tickwidth", 6),
            tickmode="array",
            tickcolor=config.get("tickcolor"),
            tickvals=config.get("y_tickvals"),
            ticktext=config.get("y_ticktext"),
            showline=True,
            linewidth=config.get("axes_linewidth", 6),
            linecolor=config.get("axes_linecolor", "black"),
            tickfont=config.get("y_tickfont", dict(size=42)),
            showgrid=config.get("y_showgrid", True),
            zeroline=config.get("y_zeroline", False),
        ),
        font_size=config.get("font_size", 15),
        font_color=config.get("font_color"),
        plot_bgcolor=config.get("bgcolor", "white"),
        paper_bgcolor=config.get("bgcolor", "white"),
        # scattermode="group",
    )
    # update marginal grids
    fig.update_yaxes(showgrid=config.get("y_marginal_y_showgrid", False), row=1, col=2)
    fig.update_xaxes(showgrid=config.get("y_marginal_x_showgrid", False), row=1, col=2)
    fig.update_yaxes(zeroline=config.get("y_marginal_y_zeroline", False), row=1, col=2)
    fig.update_xaxes(zeroline=config.get("y_marginal_x_zeroline", False), row=1, col=2)

    fig.update_yaxes(showgrid=config.get("x_marginal_y_showgrid", False), row=2, col=1)
    fig.update_xaxes(showgrid=config.get("x_marginal_x_showgrid", False), row=2, col=1)
    fig.update_yaxes(zeroline=config.get("x_marginal_y_zeroline", False), row=2, col=1)
    fig.update_xaxes(zeroline=config.get("x_marginal_x_zeroline", False), row=2, col=1)

    if config.get("regression", False):
        predict_df = plot_df.copy()
        nans = predict_df[y_measure].isna() | predict_df[x_measure].isna()  # type: ignore
        predict_df = predict_df.loc[~nans]
        predictor_vars_with_constant = sm.add_constant(predict_df[x_measure].to_numpy())
        model = sm.OLS(
            predict_df[y_measure].to_numpy(),
            predictor_vars_with_constant,
        )
        result = model.fit()

        # get summary
        summary = summary_str(x_measure, y_measure, result)
        print("Summary\n" + summary)

        # put r2 on plot
        if config.get("regression_on_plot", True):
            fig.add_annotation(
                x=0,
                y=0,
                xref="paper",
                yref="paper",
                text=f"R2: {result.rsquared:.2f}, p: {result.f_pvalue:.3f}",
                showarrow=False,
                font=dict(size=21),
            )

    if config.get("save", False):
        filename = f"{x_measure}.{y_measure}_"
        filename += config_to_descriptive_string(config)
        if config.get("filepostfix"):
            filename += f"_{config['filepostfix']}"
        output_path = os.path.join(
            config.get("study", ""),
            "measure.measure",
            f"{filename}.{config.get('filetype', 'png')}",
        )
        save_plot(config, fig, output_path)

    if config.get("show", False):
        fig.show(width=config["width"], height=config["height"])

    return fig


def plot_scatter_measures(config) -> List[Tuple[Dict[str, Any], Any]]:
    data = aggregator(
        config,
        load_func=load_questionnaire,
        call_func=func_plot_scatter_sr_srl,
        no_extra_columns=True,
    )
    return data


if __name__ == "__main__":
    n_plots = 1

    nofilter = (
        "position",
        {
            "post": (
                "filter",
                {},
            ),
        },
    )
    low_sr_load_spec = (
        "position",
        {
            "post": (
                "filter",
                {"exclude": ("gt", "mean_sr_post", 2.9)},
            ),
        },
    )
    suppress_load_spec = (
        "position",
        {
            "post": (
                "filter",
                {
                    "include": ("match", "wcg_group", "no_strategy"),
                },
            ),
        },
    )
    neutrualcue_load_spec = (
        "position",
        {
            "post": (
                "filter",
                {
                    # "exclude": [
                    #     ("gte", "timestamp", 180000),
                    # ],
                    "include": ("match", "wcg_group", "no_strategy"),
                },
            ),
        },
    )
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
                                # "suppress": suppress_load_spec,
                                # "neutralcue": neutrualcue_load_spec,
                                # "intact": nofilter,
                                # "sentence_scrambled": nofilter,
                                "button_press": nofilter,
                            },
                        ),
                        # "carver_replication": (
                        #     "condition",
                        #     {
                        #         "intact": nofilter,
                        #         "sentence_scrambled": nofilter,
                        #     },
                        # ),
                    },
                )
            },
        ),
        "x_measure": "linger_rating",
        "y_measure": "te_rate_before",
        "aggregate_on": "all",
        "x_title": "Self-reported Lingering",
        "y_title": "Number Intrusions",
        "x_range": [0.5, 7.5],
        "y_range": [-0.1, 1.1],
        "width": 900,
        "height": 900,
        "scale": 3,
        "color": [
            # "#ffc000",  # yellow
            # "#44546A",  # dark blue
            # "#4472c4",  # blue
            # "#70ad47",  # green
            # "#ed7d31",  # orange
            "purple",
        ],
        "save": True,
        "show": False,
        "regression": True,
    }
    plot_scatter_measures(config)
