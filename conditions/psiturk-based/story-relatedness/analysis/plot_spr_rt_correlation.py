import argparse
from typing import Optional

import pandas as pd
import plotly.express as px

from overview import load_data, get_spr_correlations


def plot_spr_rt_correlation(study_dir: str, study_dir2: Optional[str] = None):

    trialdata, _, _ = load_data(study_dir, exclude=False)
    pID_trialdata = trialdata.set_index("participantID")
    plot_df = get_spr_correlations(pID_trialdata)
    plot_df["source"] = study_dir

    if study_dir2 is not None:
        trialdata2, _, _ = load_data(study_dir2, exclude=False)
        pID_trialdata2 = trialdata2.set_index("participantID")
        spr_corrs2 = get_spr_correlations(pID_trialdata2)
        spr_corrs2["source"] = study_dir2
        plot_df = pd.concat([plot_df, spr_corrs2])

    fig = px.histogram(plot_df, x="spr/char", color="source", histnorm="percent")
    fig.update_layout(barmode="overlay")
    fig.update_traces(opacity=0.75)
    fig.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="extract data")
    parser.add_argument(
        "-s",
        "--study_dir",
        type=str,
        default="data",
        help="Directory for study",
    )
    parser.add_argument(
        "-s2",
        "--study_dir2",
        type=str,
        default="data",
        help="Directory for second study (to compare)",
    )
    args = parser.parse_known_args()[0]
    plot_spr_rt_correlation(study_dir=args.study_dir, study_dir2=args.study_dir2)
