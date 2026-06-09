import os
from typing import Dict, List, Tuple

from oc_pmc import DATA_DIR, console
from oc_pmc.exclusions import exclude_linger_multi_day
from oc_pmc.import_data.import_data_json import (
    import_data_dfs_from_json,
)
from oc_pmc.utils import check_make_dirs

q_keys_1 = {
    "questionnaire_transportation": [
        ("tran_Q1", "tran_Q1", "num"),
        ("tran_Q2", "tran_Q2", "num"),
        ("tran_Q3", "tran_Q3", "num"),
        ("tran_Q4", "tran_Q4", "num"),
        ("tran_Q5", "tran_Q5", "num"),
        ("tran_Q6", "tran_Q6", "num"),
        ("tran_Q7", "tran_Q7", "num"),
        ("tran_Q8", "tran_Q8", "num"),
        ("tran_Q9", "tran_Q9", "num"),
        ("tran_Q10", "tran_Q10", "num"),
        ("tran_Q11", "tran_Q11", "num"),
        ("tran_Q12", "tran_Q12", "num"),
        ("tran_Q13", "tran_Q13", "num"),
    ],
    "questionnaire_experience": [
        # 1
        ("read_story", "read_story", "str"),
        ("read_enjoy", "read_enjoy", "num"),
        ("wcg_strategy", "wcg_strategy", "str"),
        ("wcg1_sound_meaning", "wcg1_sound_meaning", "str"),
        ("wcg2_sound_meaning", "wcg2_sound_meaning", "str"),
        ("guess_experiment", "guess_experiment", "str"),
        # 2
        ("wcg_diff_general", "wcg_diff_general", "str"),
        ("linger_rating", "linger_rating", "num"),
        # 3
        ("volition", "volition", "str"),
        ("volition_explanation", "volition_explanation", "str"),
        # 4
        ("wcg_diff_emotion", "wcg_diff_emotion", "num"),
        ("wcg_diff_topics", "wcg_diff_topics", "num"),
        ("wcg_diff_ease", "wcg_diff_ease", "num"),
        ("wcg_diff_tired", "wcg_diff_tired", "num"),
        ("wcg_diff_bored", "wcg_diff_bored", "num"),
        ("wcg_diff_thoughts", "wcg_diff_thoughts", "num"),
        ("wcg_diff_explanation", "wcg_diff_explanation", "str"),
    ],
    "questionnaire_demographics": [
        ("demographics_country", "demographics_country", "str"),
        ("demographics_currenttime", "demographics_currenttime", "str"),
        ("demographics_age", "demographics_age", "str"),
        ("demographics_gender", "demographics_gender", "str"),
        ("demographics_hand", "demographics_hand", "str"),
        ("demographics_nativelang", "demographics_nativelang", "str"),
        ("demographics_nativelang_text", "demographics_nativelang_text", "str"),
        ("demographics_fluency", "demographics_fluency", "str"),
        ("demographics_fluency_text", "demographics_fluency_text", "str"),
        ("demographics_race", "demographics_race", "str"),
        ("demographics_attncheck", "demographics_attncheck", "str"),
        ("demographics_hispanic", "demographics_hispanic", "str"),
        ("demographics_education", "demographics_education", "str"),
        ("demographics_reading", "demographics_reading", "str"),
    ],
    "questionnaire_open": [
        ("content_attention", "content_attention", "str"),
        ("content_attention_text", "content_attention_text", "str"),
        ("clarity_rating", "clarity_rating", "num"),
        ("clarity_explanation", "clarity_explanation", "str"),
        ("open_box", "open_box", "str"),
    ],
}

q_keys_2 = {
    "questionnaire_transportation": [
        ("tran_Q1", "tran_Q1", "num"),
        ("tran_Q2", "tran_Q2", "num"),
        ("tran_Q3", "tran_Q3", "num"),
        ("tran_Q4", "tran_Q4", "num"),
        ("tran_Q5", "tran_Q5", "num"),
        ("tran_Q6", "tran_Q6", "num"),
        ("tran_Q7", "tran_Q7", "num"),
        ("tran_Q8", "tran_Q8", "num"),
        ("tran_Q9", "tran_Q9", "num"),
        ("tran_Q10", "tran_Q10", "num"),
        ("tran_Q11", "tran_Q11", "num"),
        ("tran_Q12", "tran_Q12", "num"),
        ("tran_Q13", "tran_Q13", "num"),
    ],
    "questionnaire_experience": [
        # 1
        ("read_story", "read_story", "str"),
        ("read_enjoy", "read_enjoy", "num"),
        ("wcg_strategy", "wcg_strategy", "str"),
        ("wcg1_sound_meaning", "wcg1_sound_meaning", "str"),
        ("wcg2_sound_meaning", "wcg2_sound_meaning", "str"),
        ("check_suppress_topic", "check_suppress_topic", "str"),
        ("guess_experiment", "guess_experiment", "str"),
        # 2
        ("wcg_diff_general", "wcg_diff_general", "str"),
        ("linger_rating", "linger_rating", "num"),
        ("success_suppress_story", "success_suppress_story", "num"),
        # 3
        ("volition", "volition", "str"),
        ("volition_explanation", "volition_explanation", "str"),
        # 4
        ("wcg_diff_emotion", "wcg_diff_emotion", "num"),
        ("wcg_diff_topics", "wcg_diff_topics", "num"),
        ("wcg_diff_ease", "wcg_diff_ease", "num"),
        ("wcg_diff_tired", "wcg_diff_tired", "num"),
        ("wcg_diff_bored", "wcg_diff_bored", "num"),
        ("wcg_diff_thoughts", "wcg_diff_thoughts", "num"),
        ("wcg_diff_explanation", "wcg_diff_explanation", "str"),
    ],
    "questionnaire_lingering_24h": [
        ("linger_24h_rating", "linger_24h_rating", "num"),
        ("linger_24h_emotion", "linger_24h_emotion", "num"),
        ("linger_24h_intentional", "linger_24h_intentional", "num"),
        ("linger_24h_unintentional", "linger_24h_unintentional", "num"),
    ],
    "questionnaire_rii": [
        ("rii_1", "rii_1", "num"),
        ("rii_2", "rii_2", "num"),
        ("rii_3", "rii_3", "num"),
        ("rii_4", "rii_4", "num"),
        ("rii_5", "rii_5", "num"),
        ("rii_6", "rii_6", "num"),
        ("rii_7", "rii_7", "num"),
        ("rii_8", "rii_8", "num"),
        ("rii_9", "rii_9", "num"),
        ("rii_10", "rii_10", "num"),
        ("rii_11", "rii_11", "num"),
        ("rii_12", "rii_12", "num"),
        ("rii_13", "rii_13", "num"),
        ("rii_14", "rii_14", "num"),
        ("rii_15", "rii_15", "num"),
        ("rii_16", "rii_16", "num"),
    ],
    "questionnaire_demographics": [
        ("demographics_country", "demographics_country", "str"),
        ("demographics_currenttime", "demographics_currenttime", "str"),
        ("demographics_age", "demographics_age", "str"),
        ("demographics_gender", "demographics_gender", "str"),
        ("demographics_hand", "demographics_hand", "str"),
        ("demographics_nativelang", "demographics_nativelang", "str"),
        ("demographics_nativelang_text", "demographics_nativelang_text", "str"),
        ("demographics_fluency", "demographics_fluency", "str"),
        ("demographics_fluency_text", "demographics_fluency_text", "str"),
        ("demographics_race", "demographics_race", "str"),
        ("demographics_attncheck", "demographics_attncheck", "str"),
        ("demographics_hispanic", "demographics_hispanic", "str"),
        ("demographics_education", "demographics_education", "str"),
        ("demographics_reading", "demographics_reading", "str"),
    ],
    "questionnaire_open": [
        ("content_attention", "content_attention", "str"),
        ("content_attention_text", "content_attention_text", "str"),
        ("clarity_rating", "clarity_rating", "num"),
        ("clarity_explanation", "clarity_explanation", "str"),
        ("open_box", "open_box", "str"),
    ],
}


q_keys_carver = {}
# the stages across to which an extra measure of time away
main_experiment_stages = [
    "free_association_pre",
    "reading",
    "free_association_post",
    "questionnaire_comprehension",
    "questionnaire_transportation",
    "questionnaire_experience",
]

ratings_carver = {
    "approach": "incontext",
    "model": "gpt-5-mini-2025-08-07",
    "story": "carver_original",
    "file": "ratings.csv",
}

ratings_july = {
    "approach": "incontext",
    "model": "gpt-5-mini-2025-08-07",
    "story": "july_original",
    "file": "ratings.csv",
}


def import_data_json_multi_day(
    story_1: str,
    story_2: str,
    q_keys_1: Dict[str, List[Tuple[str, str, str]]],
    q_keys_2: Dict[str, List[Tuple[str, str, str]]],
    filter_condition: tuple[str, str],
    ratings_1: Dict[str, str],
    ratings_2: Dict[str, str],
):
    data_dir = DATA_DIR
    try:
        (
            story_1,
            condition_1,
            _,
            _,
            pID_summary_1,
            pID_timing_pre_df_1,
            pID_timing_post_df_1,
            pID_sentence_time_spr_1,
        ) = import_data_dfs_from_json(
            study_name_or_data_dir="linger-multi-day-1",
            q_keys=q_keys_1,
            data_dir=data_dir,
            main_experiment_stages=main_experiment_stages,
            filter_condition=filter_condition,
            ratings=ratings_1,
            story_override=story_1,
        )
    except ValueError as err:
        print("Import failed for linger-multi-day-1")
        raise err
    print("")

    day_2_success = False
    try:
        (
            story_2,
            condition_2,
            _,
            _,
            pID_summary_2,
            pID_timing_pre_df_2,
            pID_timing_post_df_2,
            pID_sentence_time_spr_2,
        ) = import_data_dfs_from_json(
            study_name_or_data_dir="linger-multi-day-2",
            q_keys=q_keys_2,
            data_dir=data_dir,
            main_experiment_stages=main_experiment_stages,
            filter_condition=filter_condition,
            ratings=ratings_2,
            story_override=story_2,
        )
        day_2_success = True
    except ValueError as err:
        print(f"Import failed for linger-multi-day-2:\n{err}\nContinuing...")
        # ---
        # just for the type checker
        condition_2 = None
        pID_summary_2 = None
        pID_timing_pre_df_2 = None
        pID_timing_post_df_2 = None
        pID_sentence_time_spr_2 = None
        # ---

    console.print("\nSaving to ldata", style="yellow")

    pID_summary_1["day1"] = True

    if day_2_success:
        assert condition_1 == condition_2, "conditions must be the same"  # type: ignore
        assert story_1 != story_2, "day 1 and day 2 stories must be different"  # type: ignore

        pID_summary_2["day2"] = True  # type: ignore

        # pID_summary = pID_summary_1.join(pID_summary_2, lsuffix="_1", rsuffix="_2")
        # # type: ignore

        pID_summary_1_renamed = pID_summary_1.add_suffix("_1")
        pID_summary_2_renamed = pID_summary_2.add_suffix("_2")  # type: ignore
        pID_summary = pID_summary_1_renamed.join(pID_summary_2_renamed)
    else:
        # add day1 suffix
        new_colnames = {
            colname: f"{colname}_1" for colname in pID_summary_1.columns.tolist()
        }
        pID_summary_1.rename(columns=new_colnames, inplace=True)

        pID_summary = pID_summary_1
        pID_summary["day2"] = False

    # (skip old wordchains data format)
    # (A) questionnaire data
    questionnaires_path_1 = os.path.join(
        data_dir, "questionnaires", story_1, condition_1, "summary.csv"
    )
    check_make_dirs(questionnaires_path_1)

    pID_summary.to_csv(
        questionnaires_path_1,
        header=True,
        index=True,
    )

    # (B) timing data
    timing_dir_1 = os.path.join(data_dir, "time_words", story_1, condition_1)
    timing_post_dir_1 = os.path.join(timing_dir_1, "post.csv")
    timing_pre_dir_1 = os.path.join(timing_dir_1, "pre.csv")
    check_make_dirs([timing_post_dir_1, timing_pre_dir_1])
    pID_timing_pre_df_1.to_csv(
        timing_pre_dir_1,
        header=True,
        index=True,
    )
    pID_timing_post_df_1.to_csv(
        timing_post_dir_1,
        header=True,
        index=True,
    )

    # (C) self-paced reading times
    time_spr_path_1 = os.path.join(
        data_dir, "time_spr", story_1, condition_1, "spr.csv"
    )
    check_make_dirs(time_spr_path_1)
    pID_sentence_time_spr_1.to_csv(
        time_spr_path_1,
        header=True,
        index=True,
    )

    if day_2_success:
        # ---
        # just to satisfy the type checker
        assert story_2 is not None
        assert condition_2 is not None
        assert pID_timing_pre_df_2 is not None
        assert pID_timing_post_df_2 is not None
        assert pID_sentence_time_spr_2 is not None
        # ---

        questionnaires_path_2 = os.path.join(
            data_dir, "questionnaires", story_2, condition_2, "summary.csv"
        )
        check_make_dirs(questionnaires_path_2)
        pID_summary.to_csv(
            questionnaires_path_2,
            header=True,
            index=True,
        )

        # (B) timing data
        timing_dir_2 = os.path.join(data_dir, "time_words", story_2, condition_2)
        timing_post_dir_2 = os.path.join(timing_dir_2, "post.csv")
        timing_pre_dir_2 = os.path.join(timing_dir_2, "pre.csv")
        check_make_dirs([timing_post_dir_2, timing_pre_dir_2])
        pID_timing_pre_df_2.to_csv(
            timing_pre_dir_2,
            header=True,
            index=True,
        )
        pID_timing_post_df_2.to_csv(
            timing_post_dir_2,
            header=True,
            index=True,
        )

        # (C) self-paced reading times
        time_spr_path_2 = os.path.join(
            data_dir, "time_spr", story_2, condition_2, "spr.csv"
        )
        check_make_dirs(time_spr_path_2)
        pID_sentence_time_spr_2.to_csv(
            time_spr_path_2,
            header=True,
            index=True,
        )

    print("Done\n")

    return True


def do_import_linger_multi_day():
    console.print("\n# Importing (multi_day_carver_july)", style="red bold")
    success = import_data_json_multi_day(
        story_1="carver_original",
        story_2="july_original",
        q_keys_1=q_keys_1,
        q_keys_2=q_keys_2,
        filter_condition=("carver_july", "multi_day_carver_july"),
        ratings_1=ratings_carver,
        ratings_2=ratings_july,
    )
    if success:
        console.print("# Excluding (multi_day_carver_july)", style="red bold")
        exclude_linger_multi_day(condition="multi_day_carver_july")

    console.print("\n# Importing (multi_day_july_carver)", style="red bold")
    success = import_data_json_multi_day(
        story_1="july_original",
        story_2="carver_original",
        q_keys_1=q_keys_1,
        q_keys_2=q_keys_2,
        filter_condition=("july_carver", "multi_day_july_carver"),
        ratings_1=ratings_july,
        ratings_2=ratings_carver,
    )
    if success:
        console.print("# Excluding (multi_day_july_carver)", style="red bold")
        exclude_linger_multi_day(condition="multi_day_july_carver")


if __name__ == "__main__":
    do_import_linger_multi_day()
