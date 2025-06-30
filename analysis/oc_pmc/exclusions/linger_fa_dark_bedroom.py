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
    exclusion_focusevents_abs,
    exclusion_reaction_time_abs,
    exclusion_reaction_time_max,
    exclusion_spr_char_abs,
    exclusion_spr_max,
    exclusion_spr_time,
    exclusion_spr_wcg_break_abs,
    exclusion_story_read,
)
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import check_make_dirs
from oc_pmc.utils.aggregator import aggregator

BASEDIR = "outputs/plots/exclusions"


def get_comparison_load_spec(condition: str):
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
                            condition: unconstrained,
                        },
                    ),
                },
            )
        },
    )


def func_exclude_linger_fa_dark_bedroom(
    config: Dict,
    data_df: pd.DataFrame,
) -> pd.DataFrame:
    # load comparison data
    to_compare_df = data_df
    to_exclude_df = load_questionnaire(
        {
            "story": config["chosen_story"],
            "condition": config["chosen_condition"],
            "filter": False,
        }
    )

    # pre reg: https://aspredicted.org/see_one.php?a=TkxIdndnZW1zYTcwZ2VhaTJST05Ldz09

    to_exclude_df["exclusion"] = "unprocessed"

    # 1. by char/time correlation ( < 0.25 )
    exclusions_spr_char = exclusion_spr_char_abs(
        config, to_exclude_df, to_compare_df, 0.25
    )

    # 2. by mean reaction time during wcg ( > 6700ms )
    exclusions_rt_mean = exclusion_reaction_time_abs(
        config, to_exclude_df, to_compare_df, 6700
    )

    # 3. by focusevents ( > 5 )
    exclusions_focusevents = exclusion_focusevents_abs(
        config, to_exclude_df, to_compare_df, 5
    )

    # 4. by maximum reaction time (30s)
    exclusions_rt_max = exclusion_reaction_time_max(
        config, to_exclude_df, to_compare_df, 30000
    )

    # 5. by time between reading phase and FA2 (70s) (DIFFERS FROM PRE-REGISTRATION)
    exclusions_spr_wcg_break = exclusion_spr_wcg_break_abs(
        config, to_exclude_df, to_compare_df, 70000
    )

    # 6. by comprehension (0.25)
    exclusions_comp = exclusion_comp_prop(config, to_exclude_df, to_compare_df, 0.25)

    # 7. by catch (0.5)
    exclusions_catch = exclusion_catch_prop(config, to_exclude_df, to_compare_df, 0.5)
    exclusions_catch.name = "catch"

    # 8. by story read
    exclusions_story_read = exclusion_story_read(config, to_exclude_df, to_compare_df)

    # 9. by time away between FA1 and demographics questionnaire (45s)
    exclusions_time_exp = exclusion_exp_time_away_abs(
        config, to_exclude_df, to_compare_df, 45000
    )

    # 10. single sentence reading time >15s
    # TODO: check for bugs
    exclusions_spr_max = exclusion_spr_max(config, to_exclude_df, 15000)

    # 11. story reading time <20s
    exclusions_spr_time = exclusion_spr_time(config, to_exclude_df, 20000)

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
            exclusions_spr_max,
            exclusions_spr_time,
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


def exclude_linger_fa_dark_bedroom():
    to_compare_name = "neutralcue2"
    aggregator(
        {
            "chosen_story": "dark_bedroom",
            "chosen_condition": "neutralcue",
            "load_spec": get_comparison_load_spec(to_compare_name),
            "load_func": load_questionnaire,
            "call_func": func_exclude_linger_fa_dark_bedroom,
            "aggregate_on": "all",
            "to_exclude_name": "neutralcue",
            "to_compare_name": to_compare_name,
        }
    )


if __name__ == "__main__":
    exclude_linger_fa_dark_bedroom()
