# script to handle actual data import
import os

from oc_pmc import BELLANA_DIR
from oc_pmc.import_data.import_data_buddhika import import_data_buddhika

# applies to exp3 & 4
q_keys_exp3_exp4 = {
    "demographics": [
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
        ("demographics_hispanic", "demographics_hispanic", "str"),
        ("demographics_education", "demographics_education", "str"),
        ("demographics_reading", "demographics_reading", "str"),
    ],
    "content": [
        ("content_read", "read_story", "str"),
        ("content_enjoy", "read_enjoy", "num"),
        ("content_strategies", "wcg_strategy", "str"),
        ("content_strategies_fa1", "wcg1_sound_meaning", "str"),
        ("content_strategies_fa2", "wcg2_sound_meaning", "str"),
        ("content_purpose", "guess_experiment", "str"),
        ("content_difference", "wcg_diff_general", "str"),
        ("content_linger", "linger_rating", "num"),
        ("content_probe_describeintent", "volition_explanation", "str"),
        ("content_probe_rateintent", "volition", "str"),
        ("content_probe_describelinger", "wcg_diff_explanation", "str"),
        ("content_probe_ratediff", "wcg_diff_ease", "num"),
        ("content_probe_ratebored", "wcg_diff_bored", "num"),
        ("content_probe_ratetired", "wcg_diff_tired", "num"),
        ("content_probe_ratetop", "wcg_diff_topics", "num"),
        ("content_probe_rateemo", "wcg_diff_emotion", "num"),
        ("content_probe_rateother", "wcg_diff_thoughts", "num"),
        ("content_feedback", "open_box", "str"),
        ("content_attention", "content_attention", "str"),
        ("content_attention_text", "content_attention_text", "str"),
    ],
    "transportation": [
        ("5B_Q1", "tran_Q1", "num"),
        ("5B_Q2", "tran_Q2", "num"),
        ("5B_Q3", "tran_Q3", "num"),
        ("5B_Q4", "tran_Q4", "num"),
        ("5B_Q5", "tran_Q5", "num"),
        ("5B_Q6", "tran_Q6", "num"),
        ("5B_Q7", "tran_Q7", "num"),
        ("5B_Q8", "tran_Q8", "num"),
        ("5B_Q9", "tran_Q9", "num"),
        ("5B_Q10", "tran_Q10", "num"),
        ("5B_Q11", "tran_Q11", "num"),
        ("5B_Q12", "tran_Q12", "num"),
        ("5B_Q13", "tran_Q13", "num"),
    ],
}
# applies to exp3, exp4 & exp1 (replication)
comprehension_keys_exp3_exp4_exp1_2 = [
    ("5D_Q1", "3", "general"),
    ("5D_Q2", "2", "general"),
    ("5D_Q3", "4", "specific"),
    ("5D_Q4", "3", "specific"),
    ("5D_Q5", "3", "specific"),
    ("5D_Q6", "4", "specific"),
    ("5D_Q7", "2", "catch"),
    ("5D_Q8", "1", "general"),
    ("5D_Q9", "4", "general"),
    ("5D_Q10", "2", "specific"),
    ("5D_Q11", "4", "general"),
    ("5D_Q12", "2", "specific"),
    ("5D_Q13", "3", "general"),
    ("5D_Q14", "2", "specific"),
    ("5D_Q15", "1", "specific"),
    ("5D_Q16", "1", "general"),
    ("5D_Q17", "2", "general"),
    ("5D_Q18", "2", "general"),
    ("5D_Q19", "1", "general"),
    ("5D_Q20", "3", "specific"),
    ("5D_Q21", "1", "catch"),
    ("5D_Q22", "1", "specific"),
    ("5D_Q23", "4", "general"),
    ("5D_Q24", "1", "specific"),
    ("5D_Q25", "4", "general"),
    ("5D_Q26", "3", "specific"),
]
# applies to exp1 (original, rewrite, word_scrambled)
q_keys_exp1_1 = {
    "demographics": [
        ("demographics_age", "demographics_age", "str"),
        ("demographics_gender", "demographics_gender", "str"),
        ("demographics_hand", "demographics_hand", "str"),
        ("demographics_nativelang", "demographics_nativelang", "str"),
        ("demographics_nativelang_text", "demographics_nativelang_text", "str"),
        ("demographics_fluency", "demographics_fluency", "str"),
        ("demographics_fluency_text", "demographics_fluency_text", "str"),
        ("demographics_race", "demographics_race", "str"),
        ("demographics_hispanic", "demographics_hispanic", "str"),
        ("demographics_education", "demographics_education", "str"),
        ("demographics_reading", "demographics_reading", "str"),
    ],
    "content": [
        ("content_read", "read_story", "str"),
        ("content_strategies", "wcg_strategy", "str"),
        ("content_strategies_fa1", "wcg1_sound_meaning", "str"),
        ("content_strategies_fa2", "wcg2_sound_meaning", "str"),
        ("content_purpose", "guess_experiment", "str"),
        ("content_difference", "wcg_diff_general", "str"),
        ("content_linger", "linger_rating", "num"),
        ("content_feedback", "open_box", "str"),
        ("content_attention", "content_attention", "str"),
        ("content_attention_text", "content_attention_text", "str"),
    ],
    "transportation": [
        ("4B_Q1", "tran_Q1", "num"),
        ("4B_Q2", "tran_Q2", "num"),
        ("4B_Q3", "tran_Q3", "num"),
        ("4B_Q4", "tran_Q4", "num"),
        ("4B_Q5", "tran_Q5", "num"),
        ("4B_Q6", "tran_Q6", "num"),
        ("4B_Q7", "tran_Q7", "num"),
        ("4B_Q8", "tran_Q8", "num"),
        ("4B_Q9", "tran_Q9", "num"),
        ("4B_Q10", "tran_Q10", "num"),
        ("4B_Q11", "tran_Q11", "num"),
        ("4B_Q12", "tran_Q12", "num"),
        ("4B_Q13", "tran_Q13", "num"),
    ],
}
# applies to exp1 (original, rewrite, word_scrambled)
comprehension_keys_exp1_1 = [
    ("4C_Q1", "3", "general"),
    ("4C_Q2", "2", "general"),
    ("4C_Q3", "4", "specific"),
    ("4C_Q4", "3", "specific"),
    ("4C_Q5", "3", "specific"),
    ("4C_Q6", "4", "specific"),
    ("4C_Q7", "2", "catch"),
    ("4C_Q8", "1", "general"),
    ("4C_Q9", "4", "general"),
    ("4C_Q10", "2", "specific"),
    ("4C_Q11", "4", "general"),
    ("4C_Q12", "2", "specific"),
    ("4C_Q13", "3", "general"),
    ("4C_Q14", "2", "specific"),
    ("4C_Q15", "1", "specific"),
    ("4C_Q16", "1", "general"),
    ("4C_Q17", "2", "general"),
    ("4C_Q18", "2", "general"),
    ("4C_Q19", "1", "general"),
    ("4C_Q20", "3", "specific"),
    ("4C_Q21", "1", "catch"),
    ("4C_Q22", "1", "specific"),
    ("4C_Q23", "4", "general"),
    ("4C_Q24", "1", "specific"),
    ("4C_Q25", "4", "general"),
    ("4C_Q26", "3", "specific"),
]
# applies to exp1 (replication)
q_keys_exp1_2 = {
    "demographics": [
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
        ("demographics_hispanic", "demographics_hispanic", "str"),
        ("demographics_education", "demographics_education", "str"),
        ("demographics_reading", "demographics_reading", "str"),
    ],
    "content": [
        ("content_read", "read_story", "str"),
        ("content_enjoy", "read_enjoy", "num"),
        ("content_strategies", "wcg_strategy", "str"),
        ("content_strategies_fa1", "wcg1_sound_meaning", "str"),
        ("content_strategies_fa2", "wcg2_sound_meaning", "str"),
        ("content_purpose", "guess_experiment", "str"),
        ("content_difference", "wcg_diff_general", "str"),
        ("content_linger", "linger_rating", "num"),
        ("content_feedback", "open_box", "str"),
        ("content_attention", "content_attention", "str"),
        ("content_attention_text", "content_attention_text", "str"),
    ],
    "transportation": [
        ("5B_Q1", "tran_Q1", "num"),
        ("5B_Q2", "tran_Q2", "num"),
        ("5B_Q3", "tran_Q3", "num"),
        ("5B_Q4", "tran_Q4", "num"),
        ("5B_Q5", "tran_Q5", "num"),
        ("5B_Q6", "tran_Q6", "num"),
        ("5B_Q7", "tran_Q7", "num"),
        ("5B_Q8", "tran_Q8", "num"),
        ("5B_Q9", "tran_Q9", "num"),
        ("5B_Q10", "tran_Q10", "num"),
        ("5B_Q11", "tran_Q11", "num"),
        ("5B_Q12", "tran_Q12", "num"),
        ("5B_Q13", "tran_Q13", "num"),
    ],
}
stage_keys = {
    "fa1": "free_association_pre",
    "spr": "reading",
    "fa2": "free_association_post",
    "transportation": "questionnaire_transportation",
    "content": "questionnaire_comprehension",
}
ratings = {
    "approach": "human",
    "model": "moment",
    "story": "carver_original",
    "file": "all.csv",
}


def do_import_exclusion_data_buddhika():
    # How to import original data:
    # 1. Download https://osf.io/dmbx4/
    # 2. Unzip
    # 3. Add new line into .env: 'BELLANA_DIR="<path/to/unzipped/folder>"'

    if BELLANA_DIR is None:
        raise ValueError("BELLANA_DIR is not defined. Please add BELLANA_DIR in .env")

    # carver_original neutralcue
    base_path = os.path.join(BELLANA_DIR, "Experiment 3/Data/Raw/Final")
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_original",
        "neutralcue",
        q_keys=q_keys_exp3_exp4,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp3_exp4_exp1_2,
        ratings=ratings,
    )
    print("Done with carver_original neutralcue\n\n\n")
    # carver_original intact
    base_path = os.path.join(
        BELLANA_DIR, "Experiment 1/carver_original/Data/Raw/Final/"
    )
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_original",
        "intact",
        q_keys=q_keys_exp1_1,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp1_1,
        filter_condition="intact",
        ratings=ratings,
    )
    print("Done with carver_original intact\n\n\n")
    # carver_original sentence_scrambled
    base_path = os.path.join(
        BELLANA_DIR, "Experiment 1/carver_original/Data/Raw/Final/"
    )
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_original",
        "sentence_scrambled",
        q_keys=q_keys_exp1_1,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp1_1,
        filter_condition="full_scramble",
        ratings=ratings,
    )
    print("Done with carver_original sentence_scrambled\n\n\n")
    # carver_replication intact
    base_path = os.path.join(
        BELLANA_DIR, "Experiment 1/carver_replication/Data/Raw/Final/"
    )
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_replication",
        "intact",
        q_keys=q_keys_exp1_2,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp3_exp4_exp1_2,
        filter_condition="intact",
        ratings=ratings,
    )
    print("Done with carver_replication intact\n\n\n")
    # carver_replication sentence_scrambled
    base_path = os.path.join(
        BELLANA_DIR, "Experiment 1/carver_replication/Data/Raw/Final/"
    )
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_replication",
        "sentence_scrambled",
        q_keys=q_keys_exp1_2,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp3_exp4_exp1_2,
        filter_condition="full_scramble",
        ratings=ratings,
    )
    print("Done with carver_replication sentence_scrambled\n\n\n")
    # carver_rewrite intact
    base_path = os.path.join(BELLANA_DIR, "Experiment 1/carver_rewrite/Data/Raw/Final")
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final_sc.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_rewrite",
        "intact",
        q_keys=q_keys_exp1_1,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp1_1,
        filter_condition="intact",
        ratings=ratings,
    )
    print("Done with carver_rewrite intact\n\n\n")
    # carver_rewrite sentence_scrambled
    base_path = os.path.join(BELLANA_DIR, "Experiment 1/carver_rewrite/Data/Raw/Final")
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final_sc.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_rewrite",
        "sentence_scrambled",
        q_keys=q_keys_exp1_1,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp1_1,
        filter_condition="full_scramble",
        ratings=ratings,
    )
    print("Done with carver_original sentence_scrambled\n\n\n")
    # carver_original word_scrambled
    base_path = os.path.join(
        BELLANA_DIR, "Experiment 1/carver_wordscramble/Data/Raw/Final"
    )
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_original",
        "word_scrambled",
        q_keys=q_keys_exp1_1,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp1_1,
        filter_condition="full_word_scramble",
        ratings=ratings,
    )
    print("Done with carver_original word_scrambled\n\n\n")
    # carver_error emotion
    base_path = os.path.join(BELLANA_DIR, "Experiment 4/Data/Raw/Final")
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_error",
        "emotion",
        q_keys=q_keys_exp3_exp4,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp3_exp4_exp1_2,
        filter_condition="Emotion",
        ratings=ratings,
    )
    print("Done with carver_error emotion\n\n\n")
    # carver_error proofread
    base_path = os.path.join(BELLANA_DIR, "Experiment 4/Data/Raw/Final")
    import_data_buddhika(
        os.path.join(base_path, "trialdata_final.csv"),
        os.path.join(base_path, "eventdata_final.csv"),
        os.path.join(base_path, "questiondata_final.csv"),
        "carver_error",
        "proofread",
        q_keys=q_keys_exp3_exp4,
        stage_keys=stage_keys,
        comprehension_keys=comprehension_keys_exp3_exp4_exp1_2,
        filter_condition="Proofread",
        ratings=ratings,
    )
    print("Done with carver_error proofread\n\n\n")


if __name__ == "__main__":
    do_import_exclusion_data_buddhika()
