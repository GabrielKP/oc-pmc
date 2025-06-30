from oc_pmc.exclusions import exclude_linger_neutralcue2
from oc_pmc.import_data.import_data_json import import_data_json

q_keys = {
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
        ("read_story", "read_story", "str"),
        ("read_enjoy", "read_enjoy", "num"),
        ("wcg_strategy", "wcg_strategy", "str"),
        ("wcg1_sound_meaning", "wcg1_sound_meaning", "str"),
        ("wcg2_sound_meaning", "wcg2_sound_meaning", "str"),
        ("guess_experiment", "guess_experiment", "str"),
        ("wcg_diff_general", "wcg_diff_general", "str"),
        ("linger_rating", "linger_rating", "num"),
        ("volition", "volition", "str"),
        ("volition_explanation", "volition_explanation", "str"),
        ("linger_rating_start", "linger_rating_start", "num"),
        ("linger_rating_end", "linger_rating_end", "num"),
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

# the stages across to which an extra measure of time away
main_experiment_stages = [
    "free_association_pre",
    "reading",
    "free_association_post",
    "questionnaire_transportation",
    "questionnaire_comprehension",
    "questionnaire_experience",
]

ratings = {
    "approach": "human",
    "model": "moment",
    "story": "carver_original",
    "file": "all.csv",
}


def do_import_linger_neutralcue2():
    success = import_data_json(
        "linger-neutralcue2",
        q_keys=q_keys,
        main_experiment_stages=main_experiment_stages,
        ratings=ratings,
    )
    if success:
        print("# Excluding #")
        exclude_linger_neutralcue2()


if __name__ == "__main__":
    do_import_linger_neutralcue2()
