import argparse
import os
from typing import Dict, List

import pandas as pd

from oc_pmc import DATA_DIR, QUESTIONNAIRE_DIR
from oc_pmc.exclusions.analyze import print_exclusive_exclusions
from oc_pmc.exclusions.utils import (
    exclusion_catch_prop,
    exclusion_comp_prop,
    exclusion_exp_time_away_abs,
    exclusion_focusevents,
    exclusion_reaction_time,
    exclusion_reaction_time_max,
    exclusion_spr_char,
    exclusion_spr_wcg_break_abs,
    exclusion_story_read,
    exclusion_suppress_probe,
)
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import check_make_dirs
from oc_pmc.utils.aggregator import aggregator

BASEDIR = "outputs/plots/exclusions"


def get_load_spec():
    unconstrained = ("filter", {})
    return (
        "all",
        {
            "all": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "neutralcue": unconstrained,
                        },
                    ),
                },
            )
        },
    )


def func_exclude_carver_original_button_press(
    config: Dict,
    data_df: pd.DataFrame,
) -> pd.DataFrame:
    to_compare_df = data_df
    to_exclude_df = load_questionnaire(
        {
            "story": config["chosen_story"],
            "condition": config["chosen_condition"],
            "filter": False,
        }
    )
    to_exclude_df["exclusion"] = "unprocessed"

    # 1. by char/time correlation (outlier based on neutralcue)
    exclusions_spr_char = exclusion_spr_char(config, to_exclude_df, to_compare_df)
    exclusions_spr_char.name = "spr_char"

    # 2. by focusevents (outlier based on neutralcue)
    exclusions_focusevents = exclusion_focusevents(config, to_exclude_df, to_compare_df)
    exclusions_focusevents.name = "focusevents"

    # 3. by the reaction time during wcg (outlier based on neutralcue)
    exclusions_rt_mean = exclusion_reaction_time(config, to_exclude_df, to_compare_df)
    exclusions_rt_mean.name = "rt_mean"

    # 4. by maximum reaction time (30s)
    exclusions_rt_max = exclusion_reaction_time_max(
        config, to_exclude_df, to_compare_df, 30000
    )
    exclusions_rt_max.name = "rt_max"

    # 5. by time between spr and wcg (outlier based on neutralcue)
    exclusions_spr_wcg_break = exclusion_spr_wcg_break_abs(
        config, to_exclude_df, to_compare_df, 75000
    )
    exclusions_spr_wcg_break.name = "spr-wcg-break"

    # 6. by comprehension (0.25)
    exclusions_comp = exclusion_comp_prop(config, to_exclude_df, to_compare_df, 0.25)
    exclusions_comp.name = "comp_prop"

    # 7. by catch (0.5)
    exclusions_catch = exclusion_catch_prop(config, to_exclude_df, to_compare_df, 0.5)
    exclusions_catch.name = "catch"

    # 8. by story read
    exclusions_story_read = exclusion_story_read(config, to_exclude_df, to_compare_df)
    exclusions_story_read.name = "read_story"

    # 9. by time away between wcg-start and demographics-start (45s)
    exclusions_time_exp = exclusion_exp_time_away_abs(
        config, to_exclude_df, to_compare_df, 0.75
    )
    exclusions_time_exp.name = "time_exp"

    # 10. by suppression probe
    exclusions_suppress_probe = exclusion_suppress_probe(
        config, to_exclude_df, to_compare_df
    )
    exclusions_suppress_probe.name = "suppress_probe"

    # Merge all exclusions together
    exclusions_df = to_exclude_df[["exclusion"]]
    exclusions_df = exclusions_df.join(
        [
            exclusions_spr_char,
            exclusions_spr_wcg_break,
            exclusions_rt_mean,
            exclusions_rt_max,
            exclusions_comp,
            exclusions_catch,
            exclusions_story_read,
            exclusions_time_exp,
            exclusions_focusevents,
            exclusions_suppress_probe,
        ]
    )
    sel_excluded = exclusions_df.iloc[:, 1:].sum(axis=1) > 0
    exclusions_df.loc[sel_excluded, "exclusion"] = "excluded"
    exclusions_df.loc[~sel_excluded, "exclusion"] = "included"

    # Rename columns
    new_colnames = {
        colname: f"{colname}_excl"
        for colname in exclusions_df.columns.tolist()
        if colname != "exclusion"
    }
    exclusions_df.rename(columns=new_colnames, inplace=True)

    # Print Stats
    print(f"Total Participants: {len(exclusions_df)}")
    print(f"Excluded Participants: {sel_excluded.sum()}")
    print(f"Included Participants: {(~sel_excluded).sum()}")
    print("---\n Exclusion reasons (do not sum to total)")
    print(exclusions_df.iloc[:, 1:].sum(axis=0))
    print("---")

    # Output exclusive exclusions
    print_exclusive_exclusions(exclusions_df)
    print("---")

    # Save data
    output_path = os.path.join(
        DATA_DIR,
        QUESTIONNAIRE_DIR,
        config["chosen_story"],
        config["chosen_condition"],
        "exclusions.csv",
    )
    check_make_dirs(output_path)
    exclusions_df.to_csv(output_path)

    return exclusions_df


def exclude_linger_volition_button_press_suppress():
    aggregator(
        {
            "chosen_story": "carver_original",
            "chosen_condition": "button_press_suppress",
            "load_spec": get_load_spec(),
            "load_func": load_questionnaire,
            "call_func": func_exclude_carver_original_button_press,
            "aggregate_on": "all",
        }
    )


if __name__ == "__main__":
    exclude_linger_volition_button_press_suppress()
