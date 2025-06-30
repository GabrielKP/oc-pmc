import argparse
import os
from typing import Dict, List

import pandas as pd

from oc_pmc import DATA_DIR, QUESTIONNAIRE_DIR, console
from oc_pmc.exclusions.analyze import print_exclusive_exclusions
from oc_pmc.exclusions.utils import (
    exclusion_catch_prop,
    exclusion_comp_prop,
    exclusion_exp_time_away_abs,
    exclusion_focusevents_abs,
    exclusion_reaction_time_abs,
    exclusion_reaction_time_max,
    exclusion_spr_char_abs,
    exclusion_spr_wcg_break_abs,
    exclusion_story_read,
    print_stage_times,
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


def func_exclude_linger_interference_story_spr_end(
    config: Dict,
    data_df: pd.DataFrame,
) -> pd.DataFrame:
    pre_reg_exclusions = config.get("pre_reg_exclusions", False)
    # load comparison data
    to_compare_df = data_df
    to_exclude_df = load_questionnaire(
        {
            "story": config["chosen_story"],
            "condition": config["chosen_condition"],
            "filter": False,
        }
    )

    # pre reg: https://aspredicted.org/see_one.php?a=NnNiNGZGbkplR1IvMWNwSE1Kd0VOdz09
    to_exclude_df["exclusion"] = "unprocessed"

    # 1. by char/time correlation ( < 0.37 )
    if pre_reg_exclusions:
        exclusions_spr_char = exclusion_spr_char_abs(
            config, to_exclude_df, to_compare_df, 0.37
        )
    else:
        # Adapted: decreased to 0.25 from 0.37
        exclusions_spr_char = exclusion_spr_char_abs(
            config, to_exclude_df, to_compare_df, 0.25
        )

    # 2. by mean reaction time during wcg ( > 6700ms )
    if pre_reg_exclusions:
        exclusions_rt_mean = exclusion_reaction_time_abs(
            config, to_exclude_df, to_compare_df, 6700
        )
    else:
        # Adapted: increased from 6700 to 10000
        exclusions_rt_mean = exclusion_reaction_time_abs(
            config, to_exclude_df, to_compare_df, 10000
        )

    # 3. by focusevents ( > 5 )
    exclusions_focusevents = exclusion_focusevents_abs(
        config, to_exclude_df, to_compare_df, 5
    )

    # 4. by maximum reaction time (30s)
    if pre_reg_exclusions:
        exclusions_rt_max = exclusion_reaction_time_max(
            config, to_exclude_df, to_compare_df, 30000
        )
    else:
        # changed: only on post!
        exclusions_rt_max = exclusion_reaction_time_max(
            config, to_exclude_df, to_compare_df, 30000, post_only=True
        )

    # 5. by time between reading phase and FA2 (70s)
    exclusions_spr_wcg_break = exclusion_spr_wcg_break_abs(
        config,
        to_exclude_df,
        to_compare_df,
        70000,
        colname="spr-wcg-break_interference",
        skip_to_compare=config["to_compare_name"] != "interference_story_spr",
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

    # 10. by char/time correlation for interference story ( < 0.37 )
    if pre_reg_exclusions:
        exclusions_spr_char_interference = exclusion_spr_char_abs(
            config, to_exclude_df, to_compare_df, 0.37, interference=True
        )
    else:
        # Do not use: criteria is computed on too little data values.
        pass

    # 11. Did not believe the instruction for continuation/separation of stories
    def exclusion_believed_instructions(config: dict, to_exclude_df: pd.DataFrame):
        """Returns bool Series marking all participants excluded because they did
        not believe the instruction of the manipulation."""
        print("Believed story threshold: No")
        believed_instruction_exclusion = to_exclude_df["manipulation_believed"] != "yes"
        believed_instruction_exclusion.name = "believed_instruction"
        print(f"Exclusions: {believed_instruction_exclusion.sum()}")
        print("---")
        return believed_instruction_exclusion

    exclusions_believed_instructions = exclusion_believed_instructions(
        config, to_exclude_df
    )

    def exclusion_h_captcha_verification(config: dict, to_exclude_df: pd.DataFrame):
        """Returns bool Series marking all participants excluded because they did
        not believe the instruction of the manipulation."""
        h_captcha_verification_exclusion = (
            to_exclude_df["h_captcha_verification"] != "verified"
        )
        h_captcha_verification_exclusion.name = "h_catpcha_verification"
        return h_captcha_verification_exclusion

    # 12. h_captcha verification failed.
    exclusions_h_captcha_verification = exclusion_h_captcha_verification(
        config, to_exclude_df
    )

    # Merge all exclusions together
    exclusions_df = to_exclude_df[["exclusion"]]
    if pre_reg_exclusions:
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
                exclusions_spr_char_interference,  # type: ignore
                exclusions_believed_instructions,
                exclusions_h_captcha_verification,
            ]
        )
    else:
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
                # exclusions_spr_char_interference,
                exclusions_believed_instructions,
                exclusions_h_captcha_verification,
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

    # Show
    print_stage_times(to_exclude_df.loc[exclusions_df["exclusion"] == "included"])

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


def exclude_linger_interference_story_spr_end(
    condition: str, pre_reg_exclusions: bool = False
):
    to_compare_name = "interference_story_spr"
    aggregator(
        {
            "chosen_story": "carver_original",
            "chosen_condition": f"interference_story_spr_end_{condition}",
            "load_spec": get_comparison_load_spec(to_compare_name),
            "load_func": load_questionnaire,
            "call_func": func_exclude_linger_interference_story_spr_end,
            "aggregate_on": "all",
            "filter": False,
            "to_exclude_name": f"interference_story_spr_end_{condition}",
            "to_compare_name": to_compare_name,
            "pre_reg_exclusions": pre_reg_exclusions,
        }
    )
    if pre_reg_exclusions:
        console.print(
            "\nEXLCUDING BASED ON ORIGINAL PRE-REGISTRATION!", style="red bold"
        )


if __name__ == "__main__":
    console.print("\nContinued", style="green")
    exclude_linger_interference_story_spr_end("continued")
    console.print("\nSeparated", style="green")
    exclude_linger_interference_story_spr_end("separated")
    console.print("\nDelayed-continued", style="green")
    exclude_linger_interference_story_spr_end("delayed_continued")
