import os
from typing import Any, Dict, List, Optional, Sequence, cast

import numpy as np
import pandas as pd
import plotly.express as px
from tqdm import tqdm

from oc_pmc import DATA_DIR
from oc_pmc.load import load_rated_wordchains, load_thought_entries
from oc_pmc.utils import config_to_descriptive_string, save_plot
from oc_pmc.utils.aggregator import aggregator


def func_plot_example(
    config: Dict[str, Any],
    data_df: Optional[pd.DataFrame] = None,
):
    thought_entries = config["condition"] in ["button_press", "button_press_suppress"]
    clusters = config.get("clusters") is not None

    rated_wc_df = load_rated_wordchains(config)
    rated_wc_df["story"] = config["story"]
    rated_wc_df["condition"] = config["condition"]
    rated_wc_df["position"] = config["position"]

    # set participants
    if config.get("pID") is not None:
        if isinstance(config["pID"], list):
            pIDs = config["pID"]
        else:
            pIDs = [config["pID"]]
    else:
        pIDs = rated_wc_df.index.unique()

    if thought_entries:
        # some participant did not report a thought entry
        thought_entries_df = load_thought_entries(config)

    if clusters:
        cluster_config: Dict = config["clusters"]
        cluster_filename = f"{cluster_config['n_consecutive_words']}"
        cluster_filename += f"_{cluster_config['high_sr_threshold']}"
        if cluster_config.get("strict"):
            cluster_filename += "_strict"
        pID_clusters_df = pd.read_csv(
            os.path.join(
                DATA_DIR,
                "clusters",
                config["story"],
                config["condition"],
                f"{config['position']}_{cluster_filename}.csv",
            ),
            index_col=0,
        )

    message_sent = False
    for pID in tqdm(pIDs, desc="(plotting participant wcs)", disable=(len(pIDs) < 10)):
        pID_wc_df = rated_wc_df.loc[[pID]]

        # cutoff

        fig = px.line(
            pID_wc_df,
            x="timestamp",
            y="story_relatedness",
            text=config.get("text", "word_text"),
            color_discrete_sequence=cast(List, config.get("color_sequence")),
            symbol=config.get("symbol"),
            symbol_map=config.get("symbol_map"),
            line_dash=config.get("line_dash"),
            line_dash_map=config.get("line_dash_map"),
            markers=True,
            title=config.get("title", pID),
        )
        x_tickvals = list(range(0, config.get("max_timestamp", 180001), 10000))
        x_ticktext = [f"{x // 1000}s" for x in x_tickvals]
        fig.update_layout(
            xaxis=dict(
                title=config.get("x_title", "Time past since start"),
                range=config.get("x_range"),
                title_font_size=config.get("x_title_font_size", 32),
                title_font_color="black",
                title_standoff=config.get("x_title_standoff", 25),
                ticks=config.get("x_ticks", "outside"),
                tickwidth=config.get("x_tickwidth", 6),
                tickmode="array",
                tickvals=x_tickvals,
                ticktext=x_ticktext,
                tickcolor=config.get("axes_tickcolor"),
                showline=True,
                linewidth=config.get("axes_linewidth", 6),
                linecolor=config.get("axes_linecolor", "black"),
                tickfont=config.get("x_tickfont", dict(size=32)),
                tickangle=config.get("tickangle", 0),
                showgrid=config.get("x_showgrid", False),
                rangemode=config.get("x_rangemode"),
            ),
            yaxis=dict(
                title=config.get("y_title"),
                title_font_size=config.get("y_title_font_size", 42),
                title_standoff=config.get("y_title_standoff", 25),
                title_font_color="black",
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
                tickfont=config.get("y_tickfont", dict(size=42)),
                showgrid=config.get("y_showgrid", False),
                rangemode=config.get("y_rangemode"),
            ),
            showlegend=config.get("showlegend", False),
            plot_bgcolor="rgba(0, 0, 0, 0)",
            # font_size=18,
        )
        fig.update_traces(
            marker=dict(size=config.get("marker_size", 20)),
            line=dict(width=config.get("line_width", 4)),
            textposition=config.get("textposition", "top left"),
            textfont=config.get(
                "textfont"
            ),  # https://plotly.com/python/text-and-annotations/#font-color-size-and-familiy
        )
        # add thought entries
        if thought_entries:
            if pID in thought_entries_df.index:  # type: ignore
                participant_thought_entries_df = thought_entries_df.loc[[pID]]  # type: ignore
                for _, thought_entry in participant_thought_entries_df.iterrows():
                    fig.add_vline(
                        x=thought_entry["timestamp"],
                        line_width=config.get("thougth_entry_line_width", 2),
                        line_color=config.get("thought_entry_color", "red"),
                        line_dash=config.get("thought_entry_line_dash", "solid"),
                        # https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html?highlight=add_shape#plotly.graph_objects.Figure.add_shape
                        layer=config.get(
                            "thought_entry_layer", "above"
                        ),  # below | between | above
                        # between seems to be bugged when saving.
                    )

        if clusters:
            if pID in pID_clusters_df.index:  # type: ignore
                participant_clusters_df = pID_clusters_df.loc[[pID]]  # type: ignore
                for _, cluster in participant_clusters_df.iterrows():
                    fig.add_vrect(
                        x0=cluster["start_timestamp"],
                        x1=cluster["end_timestamp"],
                        fillcolor="blue",
                        opacity=0.12,
                        line_width=0,
                    )
                    fig.add_vrect(
                        x0=cluster["start_timestamp"],
                        x1=cluster["end_timestamp"],
                        line_width=1,
                        line_color="black",
                    )

        if config.get("show", False):
            fig.show(width=config["width"], height=config["height"])

        if config.get("save", False):
            filename = config_to_descriptive_string(config)
            if config.get("filepostfix"):
                filename += f"_{config['filepostfix']}"
            filename += f"_{pID}"
            filetype = config.get("filetype", "png")
            if clusters:
                wcs_folder = f"example_wcs_with_clusters_{cluster_filename}"  # type: ignore
            else:
                wcs_folder = "example_wcs"
            output_path = os.path.join(
                config.get("study", ""),
                wcs_folder,
                f"{filename}.{filetype}",
            )
            save_plot(config, fig, output_path, not message_sent)
            message_sent = True


def func_load_dummy(config):
    return pd.DataFrame(np.zeros(4))


def plot_example_wcs(config: Dict[str, Any]):
    aggregator(
        config,
        load_func=func_load_dummy,
        call_func=func_plot_example,
        no_extra_columns=True,
    )


if __name__ == "__main__":
    config = {
        "ratings": {
            "approach": "human",
            "model": "moment",
            "story": "carver_original",
            "file": "all.csv",
        },
        "story": "carver_original",
        "condition": "button_press",
        "position": "post",
        "column": "story_relatedness",
        # "pID": [1268, 1269, 1271, 1257],
        # cluster config
        "clusters": {
            "n_consecutive_words": 1,
            "high_sr_threshold": 3.5,
            "strict": True,
        },
        # plot
        "color_sequence": ["#4472c4"],
        "y_title": "Story Relatedness",
        # "x_range": [0, 100000],
        "y_range": [0.8, 7.2],
        # saving
        "save": True,
        "width": 1500,
        "height": 600,
        "scale": 2,
        "filetype": "png",
    }
    func_plot_example(config)
