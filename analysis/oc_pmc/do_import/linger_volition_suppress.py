from oc_pmc import console
from oc_pmc.exclusions import exclude_linger_volition_suppress
from oc_pmc.import_data.import_data import import_data

q_keys = {
    "q_demographics": [
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
    "q_experience1": [
        ("read_story", "read_story", "str"),
        ("read_enjoy", "read_enjoy", "num"),
        ("wcg_strategy", "wcg_strategy", "str"),
        ("wcg1_sound_meaning", "wcg1_sound_meaning", "str"),
        ("wcg2_sound_meaning", "wcg2_sound_meaning", "str"),
        ("guess_suppress_1", "guess_suppress_1", "str"),
        ("guess_suppress_2", "guess_suppres_2", "str"),
        ("guess_experiment", "guess_experiment", "str"),
    ],
    "q_experience2": [
        ("wcg_diff_general", "wcg_diff_general", "str"),
        ("linger_rating", "linger_rating", "num"),
        ("success_suppress_1", "success_suppress_1", "num"),
        ("success_suppress_2", "success_suppress_2", "num"),
    ],
    "q_experience3": [
        ("volition", "volition", "str"),
        ("volition_explanation", "volition_explanation", "str"),
    ],
    "q_experience4": [
        ("wcg_diff_emotion", "wcg_diff_emotion", "num"),
        ("wcg_diff_topics", "wcg_diff_topics", "num"),
        ("wcg_diff_ease", "wcg_diff_ease", "num"),
        ("wcg_diff_tired", "wcg_diff_tired", "num"),
        ("wcg_diff_bored", "wcg_diff_bored", "num"),
        ("wcg_diff_thoughts", "wcg_diff_thoughts", "num"),
        ("wcg_diff_explanation", "wcg_diff_explanation", "str"),
    ],
    "q_open": [
        ("clarity_rating", "clarity_rating", "num"),
        ("clarity_explanation", "clarity_explanation", "str"),
        ("open_box", "open_box", "str"),
    ],
    "q_transportation": [
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
}
stage_keys = {
    "wcg_pre": "free_association_pre",
    "story_reading": "reading",
    "wcg_post": "free_association_post",
    "q_transportation": "questionnaire_transportation",
    "q_comprehension": "questionnaire_comprehension",
    "q_demographics": "questionnaire_demographics",
}
ratings = {
    "approach": "human",
    "model": "moment",
    "story": "carver_original",
    "file": "all.csv",
}


def do_import_linger_volition_suppress():
    console.print("\nIMPORTING: suppress", style="red bold")
    import_data(
        "data_suppress_0",
        q_keys=q_keys,
        stage_keys=stage_keys,
        ratings=ratings,
    )
    console.print("\nEXCLUDING suppress", style="red bold")
    exclude_linger_volition_suppress()


if __name__ == "__main__":
    do_import_linger_volition_suppress()
