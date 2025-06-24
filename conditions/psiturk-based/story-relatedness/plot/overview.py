import argparse
import os
from typing import Dict, Optional, cast

import numpy as np
import pandas as pd
import plotly.express as px

PLOT_DIR = "plots"


def load_df(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def load_experiment(study_dir: str) -> Dict[str, pd.DataFrame]:
    outputs_dir = "outputs"
    suffixes = ["count", "", "median", "variance"]
    kinds = ["moment", "theme"]

    output: Dict[str, pd.DataFrame] = dict()
    for kind in kinds:
        temp_df: Optional[pd.DataFrame] = None
        for suffix in suffixes:
            if len(suffix) != 0:
                suffix = f"_{suffix}"
            if temp_df is None:
                temp_df = load_df(
                    os.path.join(study_dir, outputs_dir, f"{kind}{suffix}.csv")
                )
            else:
                temp_df = pd.merge(
                    temp_df,
                    load_df(
                        os.path.join(study_dir, outputs_dir, f"{kind}{suffix}.csv")
                    ),
                )
        output[kind] = cast(pd.DataFrame, temp_df)

    return output


def plot_moment_v_theme(exp_dict: Dict[str, pd.DataFrame]):
    joint_df = pd.merge(
        exp_dict["theme"],
        exp_dict["moment"],
        on="word",
        suffixes=("_theme", "_moment"),
    )
    noise1 = np.random.normal(0, 0.01, joint_df.shape[0])
    noise2 = np.random.normal(0, 0.01, joint_df.shape[0])
    joint_df["mean_rating_moment"] = joint_df["mean_rating_moment"] + noise1
    joint_df["mean_rating_theme"] = joint_df["mean_rating_theme"] + noise2
    fig = px.scatter(
        joint_df,
        x="mean_rating_moment",
        y="mean_rating_theme",
        text="word",
        # color="cf4520",
        labels={
            "mean_rating_theme": "Mean Human Theme-Relatedness Rating",
            "mean_rating_moment": "Mean Human Event-Relatedness Rating",
            "count_theme": "n ratings",
        },
        # trendline="ols",
        # trendline_color_override="black",
        color_discrete_sequence=["#cf4520"],
        template="simple_white",
    )
    fig.add_scatter(
        x=[1, 7], y=[1, 7], mode="lines", showlegend=False, marker_color="grey"
    )
    fig.update_traces(textposition="top left")
    fig.update_layout(
        autosize=False,
        width=2000,
        height=2000,
        font_size=18,
        xaxis=dict(
            range=[1, 7.01],
            showgrid=True,
            gridwidth=3,
            title_font_size=40,
        ),
        yaxis=dict(
            range=[1, 7.011],
            showgrid=True,
            gridwidth=3,
            title_font_size=40,
        ),
    )
    return fig


def plot_overview_graphs(study_dir: str):
    exp_dict = load_experiment(study_dir)

    output_dir = os.path.join(study_dir, PLOT_DIR, "overview")

    print(f"Output directory: {output_dir}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    fig_count = px.histogram(
        exp_dict["moment"],
        "count",
    )
    fig_hist_moment = px.histogram(
        exp_dict["moment"],
        "mean_rating",
        labels={
            "count": "number of ratings",
            "mean_rating": "Mean Human Event-Relatedness Rating",
        },
    )
    fig_hist_theme = px.histogram(
        exp_dict["theme"],
        "mean_rating",
        labels={
            "count": "number of ratings",
            "mean_rating": "Mean Human Theme-Relatedness Rating",
        },
    )
    fig_scatter_theme_moment = plot_moment_v_theme(exp_dict)
    figs_and_filenames = [
        (fig_count, "hist_count.png", "default"),
        (fig_hist_moment, "hist_rating_moment.png", "default"),
        (fig_hist_theme, "hist_rating_theme.png", "default"),
        (fig_scatter_theme_moment, "scatter_theme_moment.svg", "custom"),
    ]

    for fig, filename, setting in figs_and_filenames:
        if "custom" in setting:
            fig.write_image(os.path.join(output_dir, filename))
        else:
            fig.write_image(os.path.join(output_dir, filename), scale=4.0, width=1400)
        if "html" in setting:
            if "custom" in setting:
                fig.write_html(
                    os.path.join(output_dir, filename.replace("png", "html"))
                )
            else:
                fig.write_html(
                    os.path.join(output_dir, filename), scale=4.0, width=1400
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="extract data")
    parser.add_argument(
        "-s",
        "--study_dir",
        type=str,
        default="data",
        help="Directory for study",
    )
    args = parser.parse_known_args()[0]
    plot_overview_graphs(study_dir=args.study_dir)
