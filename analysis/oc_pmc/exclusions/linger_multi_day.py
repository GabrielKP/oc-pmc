import os

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
    exclusion_screen_recording,
    exclusion_spr_char_abs,
    exclusion_spr_wcg_break_abs,
    exclusion_story_read,
    exclusion_suppress_probe,
)
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import check_make_dirs

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
                            "neutralcue2": unconstrained,
                        },
                    ),
                },
            )
        },
    )


def get_load_spec_2():
    unconstrained = ("filter", {})
    return (
        "all",
        {
            "all": (
                "story",
                {
                    "july_original": (
                        "condition",
                        {
                            "intact": unconstrained,
                        },
                    ),
                },
            )
        },
    )


def exclude_linger_multi_day(
    condition: str,
) -> pd.DataFrame:
    if condition == "multi_day_carver_july":
        config_1 = {
            "story": "carver_original",
            "condition": "multi_day_carver_july",
            "filter": False,
        }
        config_2 = {
            "story": "july_original",
            "condition": "multi_day_carver_july",
            "filter": False,
        }
    elif condition == "multi_day_july_carver":
        config_1 = {
            "story": "july_original",
            "condition": "multi_day_july_carver",
            "filter": False,
        }
        config_2 = {
            "story": "carver_original",
            "condition": "multi_day_july_carver",
            "filter": False,
        }
    else:
        raise ValueError(f"Invalid condition: {condition}")

    # pre-reg: TODO

    # questionnaire data contains both days.
    exclusion_dfs = list()
    data_day_2_exists = False
    for desc, config, suffix in zip(
        ["day 1", "day 2"], [config_1, config_2], ["_1", "_2"]
    ):
        if suffix == "_2":
            try:
                to_exclude_df = load_questionnaire(config)
                to_exclude_df = to_exclude_df.loc[~to_exclude_df["day2_2"].isna()]
            except FileNotFoundError:
                print(
                    f"Cannot load questionnaire for {desc}:"
                    f" {config['story']} {config['condition']} (day 2)"
                )
                break
            data_day_2_exists = True
        else:
            to_exclude_df = load_questionnaire(config)

        to_exclude_df[f"exclusion{suffix}"] = "unprocessed"
        to_compare_df = None

        # 1. by char/time correlation ( < 0.25 )
        exclusions_spr_char = exclusion_spr_char_abs(
            config, to_exclude_df, to_compare_df, 0.25, colname=f"spr/char{suffix}"
        )

        # 2. by focusevents
        exclusions_focusevents = exclusion_focusevents_abs(
            config, to_exclude_df, to_compare_df, 5, colname=f"focusevents{suffix}"
        )

        # 3. by the reaction time during wcg
        exclusions_rt_mean = exclusion_reaction_time_abs(
            config, to_exclude_df, to_compare_df, 10000, colname=f"rt_mean{suffix}"
        )

        # 4. by maximum reaction time (30s)
        exclusions_rt_max = exclusion_reaction_time_max(
            config, to_exclude_df, to_compare_df, 30000, colname=f"rt_max{suffix}"
        )

        # 5. by time between spr and wcg (70s)
        exclusions_spr_wcg_break = exclusion_spr_wcg_break_abs(
            config,
            to_exclude_df,
            to_compare_df,
            70000,
            colname=f"spr-wcg-break{suffix}",
            skip_to_compare=True,
        )

        # 6. by comprehension (0.25)
        exclusions_comp = exclusion_comp_prop(
            config, to_exclude_df, to_compare_df, 0.25, colname=f"comp_prop{suffix}"
        )

        # 7. by catch (0.5)
        exclusions_catch = exclusion_catch_prop(
            config, to_exclude_df, to_compare_df, 0.5, colname=f"catch_prop{suffix}"
        )

        # 8. by story read
        exclusions_story_read = exclusion_story_read(
            config, to_exclude_df, to_compare_df, colname=f"read_story{suffix}"
        )

        # 9. by time away between wcg-start and demographics-start (45s)
        exclusions_time_exp = exclusion_exp_time_away_abs(
            config,
            to_exclude_df,
            to_compare_df,
            45000,
            colname=f"exp_time_away{suffix}",
        )

        # 10. issues with the recording
        print("---\nScreen recording exclusions:")
        exclusions_screen_recording = exclusion_screen_recording(config, suffix=suffix)

        exclusions_df = to_exclude_df[[f"exclusion{suffix}"]]
        exclusions_df = exclusions_df.join(
            [
                exclusions_spr_char,
                exclusions_focusevents,
                exclusions_rt_mean,
                exclusions_rt_max,
                exclusions_spr_wcg_break,
                exclusions_comp,
                exclusions_catch,
                exclusions_story_read,
                exclusions_time_exp,
                exclusions_screen_recording,
            ]
        )

        if suffix == "_2":
            # 13. by suppression probe
            exclusions_suppress_probe = exclusion_suppress_probe(
                config,
                to_exclude_df,
                to_compare_df,
                check_for_food=False,
                colname_story="check_suppress_topic_2",
            )
            exclusions_suppress_probe.name = "suppress_probe_2"
            exclusions_df = exclusions_df.join(exclusions_suppress_probe)

        sel_excluded = exclusions_df.iloc[:, 1:].sum(axis=1) > 0
        exclusions_df.loc[sel_excluded, f"exclusion{suffix}"] = "excluded"
        exclusions_df.loc[~sel_excluded, f"exclusion{suffix}"] = "included"

        # Rename columns
        new_colnames = {
            colname: f"{colname}_excl"
            for colname in exclusions_df.columns.tolist()
            if (colname != f"exclusion{suffix}")
        }
        exclusions_df.rename(columns=new_colnames, inplace=True)

        # Print Stats
        console.print(f"\n{condition} | {desc} | exclusion overview", style="yellow")
        print(f"Total Participants: {len(exclusions_df)}")
        print(f"Excluded Participants: {sel_excluded.sum()}")
        print(f"Included Participants: {(~sel_excluded).sum()}")
        print("---\n Exclusion reasons (do not sum to total)")
        print(exclusions_df.iloc[:, 1:].sum(axis=0).astype(int))
        print("---")

        # Output exclusive exclusions
        print_exclusive_exclusions(exclusions_df)
        print("---")

        exclusion_dfs.append(exclusions_df)

    if data_day_2_exists:
        combined_exclusions_df = pd.concat(exclusion_dfs, axis=1)
        combined_exclusions_df["exclusion"] = "unprocessed"

        cols_to_exclude = [
            "exclusion_1",
            "exclusion_2",
            combined_exclusions_df.columns[-1],
        ]
        cols_to_sum = combined_exclusions_df.columns.difference(cols_to_exclude)
        sel_excluded = combined_exclusions_df[cols_to_sum].sum(axis=1) > 0
        combined_exclusions_df.loc[sel_excluded, "exclusion"] = "excluded"
        combined_exclusions_df.loc[~sel_excluded, "exclusion"] = "included"

        # exclude people with no day 2 data
        no_day_2_data = combined_exclusions_df["exclusion_2"].isna()
        combined_exclusions_df.loc[no_day_2_data, "exclusion"] = "excluded"

        console.print("\n\nCombined exclusion stats", style="yellow bold")
        print(
            "Excluded on day 1: ",
            len(
                combined_exclusions_df.loc[
                    combined_exclusions_df["exclusion_1"] == "excluded", "exclusion_1"
                ]
            ),
        )
        print(
            "Excluded on day 2: ",
            len(
                combined_exclusions_df.loc[
                    combined_exclusions_df["exclusion_2"] == "excluded", "exclusion_2"
                ]
            ),
        )
        print(
            "Excluded on both days: ",
            len(
                combined_exclusions_df.loc[
                    combined_exclusions_df["exclusion"] == "excluded", "exclusion"
                ]
            ),
        )

        console.print("\n\nCombined inclusion stats", style="yellow bold")
        print(
            "Included on day 1: ",
            len(
                combined_exclusions_df.loc[
                    combined_exclusions_df["exclusion_1"] == "included", "exclusion_1"
                ]
            ),
        )
        print(
            "Included on day 2: ",
            len(
                combined_exclusions_df.loc[
                    combined_exclusions_df["exclusion_2"] == "included", "exclusion_2"
                ]
            ),
        )
        print(
            "Included on both days: ",
            len(
                combined_exclusions_df.loc[
                    combined_exclusions_df["exclusion"] == "included", "exclusion"
                ]
            ),
            "\n",
        )
    else:
        combined_exclusions_df = exclusion_dfs[0]
        combined_exclusions_df["exclusion"] = "excluded"  # no day 2 -> all excluded
        print(
            "Excluded on day 1: ",
            len(
                combined_exclusions_df.loc[
                    combined_exclusions_df["exclusion_1"] == "excluded", "exclusion_1"
                ]
            ),
        )

    # Save data
    output_path_1 = os.path.join(
        DATA_DIR,
        QUESTIONNAIRE_DIR,
        config_1["story"],
        config_1["condition"],
        "exclusions.csv",
    )
    check_make_dirs(output_path_1)
    combined_exclusions_df.to_csv(output_path_1)

    if data_day_2_exists:
        output_path_2 = os.path.join(
            DATA_DIR,
            QUESTIONNAIRE_DIR,
            config_2["story"],
            config_2["condition"],
            "exclusions.csv",
        )
        combined_exclusions_df.to_csv(output_path_2)

    return combined_exclusions_df


if __name__ == "__main__":
    exclude_linger_multi_day(condition="multi_day_carver_july")
    exclude_linger_multi_day(condition="multi_day_july_carver")
