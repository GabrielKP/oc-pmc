import argparse
import os
from typing import List

from overview import (
    get_demographic_answers,
    get_focus_stats,
    get_questionnaire_answers,
    get_spr_correlations,
    load_config,
    load_data,
    remove_participantIDs,
)


def make_reason_list(n: int, reason: str) -> List[str]:
    return [f" # {reason}" for _ in range(n)]


def exclude_participants(study_dir: str):
    # load trialdata
    trialdata, eventdata, is_july = load_data(study_dir=study_dir)

    path_output = os.path.join(
        study_dir, "config", "excluded_participantIDs_proposal.txt"
    )
    path_sql_out = os.path.join(study_dir, "config", "sql_exclusion.txt")

    # pID version
    pID_trialdata = trialdata.set_index("participantID")
    pID_eventdata = eventdata.set_index("participantID")

    excluded_ids: List[str] = list()
    reasons: List[str] = list()

    # by spr correlation time
    spr_correlations = get_spr_correlations(pID_trialdata).reset_index()
    excluded_corr = spr_correlations[spr_correlations["spr/char"] < 0.5][
        "participantID"
    ].tolist()
    excluded_ids.extend(excluded_corr)
    reasons.extend(make_reason_list(len(excluded_corr), "spr/char corr < 0.5"))
    trialdata = remove_participantIDs(trialdata, excluded_corr)
    pID_trialdata = trialdata.set_index("participantID")

    # by percentage quiz correct stat
    questionnaire = get_questionnaire_answers(pID_trialdata, july=is_july).reset_index()
    excluded_quest = questionnaire[questionnaire["total (%)"] < 0.7][
        "participantID"
    ].tolist()
    excluded_ids.extend(excluded_quest)
    reasons.extend(make_reason_list(len(excluded_quest), "quiz percentage < .7"))
    trialdata = remove_participantIDs(trialdata, excluded_quest)
    pID_trialdata = trialdata.set_index("participantID")

    # catch question
    demographics = get_demographic_answers(pID_trialdata).reset_index()
    excluded_attn = demographics[demographics["attncheck"] == 1][
        "participantID"
    ].tolist()
    excluded_ids.extend(excluded_attn)
    reasons.extend(make_reason_list(len(excluded_attn), "failed attention check"))
    trialdata = remove_participantIDs(trialdata, excluded_attn)
    pID_trialdata = trialdata.set_index("participantID")

    # time away
    time_away = get_focus_stats(pID_eventdata, pID_trialdata).reset_index()
    away_spr = time_away["spr time away (m)"] > 1
    away_rating = time_away["rating time away (m)"] > 5
    # away_total = time_away["time away (m)"] > 10
    excluded_time = time_away[(away_spr | away_rating)]["participantID"].tolist()
    excluded_ids.extend(excluded_time)
    reasons.extend(
        make_reason_list(len(excluded_time), "too long away (>=1 spr; >=5 rating;")
    )

    print(f"Filtered {len(excluded_ids)} participants, suggestions in {path_output}")

    with open(path_output, "w") as f_out:
        for excluded_id, reason in zip(excluded_ids, reasons):
            f_out.write(excluded_id + reason + "\n")

    # write sql statement to easily mark participants as 0
    print(f"SQL exclusion statement in {path_sql_out}")

    excluded_participantIDs_path = os.path.join(
        study_dir, "config", "excluded_participantIDs.txt"
    )
    all_excluded_participantIDs = load_config(excluded_participantIDs_path)
    all_excluded_participantIDs.extend(excluded_ids)

    with open(path_sql_out, "w") as f_out:
        ids_formatted = ", ".join(
            [f"'{ex_id}'" for ex_id in all_excluded_participantIDs]
        )
        command_str = "UPDATE public.assignments"
        control_str = "SET status = 0"
        condition_str = f"WHERE workerid IN ({ids_formatted});"
        f_out.writelines("\n".join((command_str, control_str, condition_str)) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="exclude participants")
    parser.add_argument(
        "-s",
        "--study_dir",
        type=str,
        default="data",
        help="Directory for study",
    )
    args = parser.parse_known_args()[0]
    exclude_participants(study_dir=args.study_dir)
