from oc_pmc import console
from oc_pmc.exclusions import exclude_linger_interference_story_spr_end
from oc_pmc.import_data.import_data_json import import_data_json

q_keys = {
    "questionnaire_manipulation_check": [
        # ("integration_difficulty", "integration_difficulty", "num"), < 1.0.0-dev9
        ("integration_attempt", "integration_attempt", "num"),
        ("integration_success", "integration_success", "num"),
        ("manipulation_believed", "manipulation_believed", "str"),
    ],
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
        ("wcg_diff_general", "wcg_diff_general", "str"),
        ("wcg_strategy", "wcg_strategy", "str"),
        ("wcg1_sound_meaning", "wcg1_sound_meaning", "str"),
        ("wcg2_sound_meaning", "wcg2_sound_meaning", "str"),
        ("guess_experiment", "guess_experiment", "str"),
        ("read_story", "read_story", "str"),
        ("read_enjoy", "read_enjoy", "num"),
        ("linger_rating", "linger_rating", "num"),
        ("volition", "volition", "str"),
        ("volition_explanation", "volition_explanation", "str"),
        ("wcg_diff_emotion", "wcg_diff_emotion", "num"),
        ("wcg_diff_topics", "wcg_diff_topics", "num"),
        ("wcg_diff_ease", "wcg_diff_ease", "num"),
        ("wcg_diff_tired", "wcg_diff_tired", "num"),
        ("wcg_diff_bored", "wcg_diff_bored", "num"),
        ("wcg_diff_thoughts", "wcg_diff_thoughts", "num"),
        ("wcg_diff_explanation", "wcg_diff_explanation", "str"),
    ],
    "questionnaire_transportation_interference": [
        ("tran_interference_Q1", "tran_interference_Q1", "num"),
        ("tran_interference_Q2", "tran_interference_Q2", "num"),
        ("tran_interference_Q3", "tran_interference_Q3", "num"),
        ("tran_interference_Q4", "tran_interference_Q4", "num"),
        ("tran_interference_Q5", "tran_interference_Q5", "num"),
        ("tran_interference_Q6", "tran_interference_Q6", "num"),
        ("tran_interference_Q7", "tran_interference_Q7", "num"),
        ("tran_interference_Q8", "tran_interference_Q8", "num"),
        ("tran_interference_Q9", "tran_interference_Q9", "num"),
        ("tran_interference_Q10", "tran_interference_Q10", "num"),
        ("tran_interference_Q11", "tran_interference_Q11", "num"),
        ("tran_interference_Q12", "tran_interference_Q12", "num"),
        ("tran_interference_Q13", "tran_interference_Q13", "num"),
    ],
    "questionnaire_experience_interference": [
        ("interference_explanation", "interference_explanation", "str"),
        ("read_story_interference", "read_story_interference", "str"),
        ("read_enjoy_interference", "read_enjoy_interference", "str"),
        ("linger_rating_interference", "linger_rating_interference", "num"),
        ("stories_distinct", "stories_distinct", "str"),
        ("volition_interference", "volition_interference", "str"),
        (
            "volition_interference_explanation",
            "volition_interference_explanation",
            "str",
        ),
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
    "server": [("h_captcha_verification", "h_captcha_verification", "str")],
}

# the stages across to which an extra measure of time away
main_experiment_stages = [
    "free_association_pre",
    "reading",
    "manipulation",
    "interference_reading_testing",
    "free_association_post",
    "questionnaire_manipulation_check",
    "questionnaire_explanation_stories_black",
    "questionnaire_transportation",
    "questionnaire_comprehension",
    "questionnaire_experience",
    "questionnaire_explanation_stories_purple",
    "questionnaire_transportation_interference",
    "questionnaire_comprehension_interference",
    "questionnaire_experience_interference",
]

ratings = {
    "approach": "human",
    "model": "moment",
    "story": "carver_original",
    "file": "all.csv",
}


def do_import_linger_interference_story_spr_end():
    console.print("\nContinued", style="red bold")
    success = import_data_json(
        "linger-interference-story-spr-end",
        q_keys=q_keys,
        main_experiment_stages=main_experiment_stages,
        filter_condition=("continued", "interference_story_spr_end_continued"),
        ratings=ratings,
    )

    if success:
        console.print("\n# Excluding - continued", style="green")
        exclude_linger_interference_story_spr_end("continued")

    console.print("\nSeparated", style="red bold")
    success = import_data_json(
        "linger-interference-story-spr-end",
        q_keys=q_keys,
        main_experiment_stages=main_experiment_stages,
        filter_condition=("separated", "interference_story_spr_end_separated"),
        ratings=ratings,
    )

    if success:
        console.print("\n# Excluding - separated", style="green")
        exclude_linger_interference_story_spr_end("separated")

    console.print("\nDelayed-continued", style="red bold")
    success = import_data_json(
        "linger-interference-story-spr-end",
        q_keys=q_keys,
        main_experiment_stages=main_experiment_stages,
        filter_condition=(
            "delayed-continued",
            "interference_story_spr_end_delayed_continued",
        ),
        ratings=ratings,
    )

    if success:
        console.print("\n# Excluding - delayed-continued", style="green")
        exclude_linger_interference_story_spr_end("delayed_continued")

    # Use original pre-registration exclusion criteria to
    # make sure adaptations to pre-reg do not change interpretations

    # console.print("\nContinued - original prereg", style="red bold")
    # success = import_data_json(
    #     "linger-interference-story-spr-end",
    #     q_keys=q_keys,
    #     main_experiment_stages=main_experiment_stages,
    #     filter_condition=("continued", "interference_story_spr_end_continued_opr"),
    #     ratings=ratings,
    # )

    # if success:
    #     console.print("\n# Excluding - continued", style="green")
    #     exclude_linger_interference_story_spr_end(
    #         "continued_opr", pre_reg_exclusions=True
    #     )

    # console.print("\nSeparated", style="red bold")
    # success = import_data_json(
    #     "linger-interference-story-spr-end",
    #     q_keys=q_keys,
    #     main_experiment_stages=main_experiment_stages,
    #     filter_condition=("separated", "interference_story_spr_end_separated_opr"),
    #     ratings=ratings,
    # )

    # if success:
    #     console.print("\n# Excluding - separated", style="green")
    #     exclude_linger_interference_story_spr_end(
    #         "separated_opr", pre_reg_exclusions=True
    #     )

    # console.print("\nDelayed-continued", style="red bold")
    # success = import_data_json(
    #     "linger-interference-story-spr-end",
    #     q_keys=q_keys,
    #     main_experiment_stages=main_experiment_stages,
    #     filter_condition=(
    #         "delayed-continued",
    #         "interference_story_spr_end_delayed_continued_opr",
    #     ),
    #     ratings=ratings,
    # )

    # if success:
    #     console.print("\n# Excluding - delayed-continued", style="green")
    #     exclude_linger_interference_story_spr_end(
    #         "delayed_continued_opr", pre_reg_exclusions=True
    #     )


if __name__ == "__main__":
    do_import_linger_interference_story_spr_end()
