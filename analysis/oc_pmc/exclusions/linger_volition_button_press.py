import os
from typing import Optional

import pandas as pd

from oc_pmc import DATA_DIR, QUESTIONNAIRE_DIR
from oc_pmc.exclusions.analyze import print_exclusive_exclusions
from oc_pmc.exclusions.utils import (
    exclusion_catch_prop,
    exclusion_comp_prop,
    exclusion_exp_time_away_abs,
    exclusion_focusevents,
    exclusion_focusevents_abs,
    exclusion_reaction_time,
    exclusion_reaction_time_abs,
    exclusion_reaction_time_max,
    exclusion_spr_char,
    exclusion_spr_char_abs,
    exclusion_spr_wcg_break_abs,
    exclusion_story_read,
)
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import check_make_dirs

BASEDIR = "outputs/plots/exclusions"


def exclude_carver_original_button_press_old_pre_reg(
    config: dict[str, str],
    to_exclude_df: pd.DataFrame,
    to_compare_df: pd.DataFrame,
) -> pd.DataFrame:
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

    # 5. by time between spr and wcg
    exclusions_spr_wcg_break = exclusion_spr_wcg_break_abs(
        config, to_exclude_df, to_compare_df, 60000
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
        config["story_exclusion"],
        config["condition_exclusion"],
        "exclusions.csv",
    )
    check_make_dirs(output_path)
    exclusions_df.to_csv(output_path)

    return exclusions_df


def exclude_carver_original_button_press_new_pre_reg(
    config: dict[str, str],
    to_exclude_df: pd.DataFrame,
    to_compare_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    The following exclusion parameters do not exactly match
    the pre-registration of the experiment.
    They exist only to apply the exclusion parameters of the
    newer set of experiments to ensure that results stay the
    same even if we use this set of exclusion criteria.
    Specifically, rule 1, 2, and 3, are set to fixed values instead
    of being computed as outliers from the neutralcue experiment.
    """
    to_exclude_df["exclusion"] = "unprocessed"

    # 1. by char/time correlation ( < 0.37 )     (old 1, changed)
    exclusions_spr_char = exclusion_spr_char_abs(
        config, to_exclude_df, to_compare_df, 0.37
    )

    # 2. by mean reaction time during wcg ( > 6700ms )   (old 3, changed)
    exclusions_rt_mean = exclusion_reaction_time_abs(
        config, to_exclude_df, to_compare_df, 6700
    )

    # Technically this criterium should not be adapted to the newer set of criteria
    # as the experiment code used for the experiment counted focusevents
    # differently than the new code.
    # 3. by focusevents ( > 5 )      (old 2, changed)
    exclusions_focusevents = exclusion_focusevents_abs(
        config, to_exclude_df, to_compare_df, 5
    )

    # 4. by maximum reaction time (30s)    (old 4)
    exclusions_rt_max = exclusion_reaction_time_max(
        config, to_exclude_df, to_compare_df, 30000
    )

    # 5. by time between reading phase and FA2 (60s)    (old 5)
    exclusions_spr_wcg_break = exclusion_spr_wcg_break_abs(
        config,
        to_exclude_df,
        to_compare_df,
        60000,
        colname="spr-wcg-break",
        skip_to_compare=True,
    )

    # 6. by comprehension (0.25)       (old 6)
    exclusions_comp = exclusion_comp_prop(config, to_exclude_df, to_compare_df, 0.25)

    # 7. by catch (0.5)      (old 7)
    exclusions_catch = exclusion_catch_prop(config, to_exclude_df, to_compare_df, 0.5)
    exclusions_catch.name = "catch"

    # 8. by story read     (old 8)
    exclusions_story_read = exclusion_story_read(config, to_exclude_df, to_compare_df)

    # 9. by time away between FA1 and demographics questionnaire (45s)   (old 9)
    exclusions_time_exp = exclusion_exp_time_away_abs(
        config, to_exclude_df, to_compare_df, 45000
    )

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
        config["story_exclusion"],
        config["condition_exclusion"],
        "exclusions.csv",
    )
    check_make_dirs(output_path)
    exclusions_df.to_csv(output_path)

    return exclusions_df


def exclude_carver_original_button_press(
    config: dict,
    to_exclude_df: pd.DataFrame,
    to_compare_df: pd.DataFrame,
) -> pd.DataFrame:
    if config["pre_reg"] == "old":
        return exclude_carver_original_button_press_old_pre_reg(
            config, to_exclude_df, to_compare_df
        )
    elif config["pre_reg"] == "new":
        return exclude_carver_original_button_press_new_pre_reg(
            config, to_exclude_df, to_compare_df
        )
    else:
        raise ValueError(
            "Set 'pre-reg' in config to 'old' or 'new'"
            f" (currently: {config['pre-reg']})"
        )


def exclude_linger_volition_button_press(config: Optional[dict] = None):
    """Creates exclusion csv for linger_volition_button_press.
    Keys passed in config argument override default config.
    'pre_reg' key is required. (set to 'old' or 'new')
    """
    config_default = {
        "story_exclusion": "carver_original",
        "condition_exclusion": "button_press",
        "story_comparison": "carver_original",
        "condition_comparison": "neutralcue",
        "pre_reg": None,
    }
    if config is not None:
        config_default.update(config)

    config = config_default

    to_exclude_df = load_questionnaire(
        {
            "story": config["story_exclusion"],
            "condition": config["condition_exclusion"],
            "filter": False,
        }
    )
    to_compare_df = load_questionnaire(
        {
            "story": config["story_comparison"],
            "condition": config["condition_comparison"],
            "filter": False,
        }
    )

    if config["pre_reg"] == "old":
        return exclude_carver_original_button_press_old_pre_reg(
            config, to_exclude_df, to_compare_df
        )
    elif config["pre_reg"] == "new":
        return exclude_carver_original_button_press_new_pre_reg(
            config, to_exclude_df, to_compare_df
        )
    else:
        raise ValueError(
            "Set 'pre_reg' in config to 'old' or 'new'"
            f" (currently: {config['pre_reg']})"
        )


if __name__ == "__main__":
    exclude_linger_volition_button_press({"pre_reg": "old"})
