import glob
import json
import os
from ast import literal_eval
from typing import List, Optional, Tuple, Union

import pandas as pd


def load_config(path: str) -> List[str]:
    print(f">> {path}")
    if not os.path.isfile(path):
        return list()
    lines: List[str] = []
    lastline = None
    with open(path, "r") as f_in:
        for line in f_in.readlines():
            lastline = line
            line = line[:-1]
            # handle comments
            if line.startswith("#"):
                continue
            elif "#" in line:
                line = line[: line.index("#") - 1]
            lines.append(line)
        if lastline is None:
            # empty config file
            return []
        if not lastline.endswith("\n"):
            raise ValueError(f"Require newline at end of file: {path}")
    return lines


def expand_data_column(data: pd.DataFrame) -> pd.DataFrame:
    data = data.join(pd.DataFrame(data.pop("data").to_numpy().tolist()))
    return data


def filter_by_studyID(
    data: pd.DataFrame, studyID: Union[str, List[str]]
) -> pd.DataFrame:
    if isinstance(studyID, str):
        data = data[data["studyID"] == studyID]
    else:
        assert isinstance(studyID, list)
        data = data[data["studyID"].isin(studyID)]
    data.drop(columns="studyID")
    return data


def participants_finished(trialdata: pd.DataFrame) -> List[str]:
    finished = (trialdata["stage"] == "questionnaire_open") & (
        trialdata["status"] == "stage_end"
    )
    print(
        f"Finished participants: {len(trialdata[finished]['participantID'].unique())}"
    )
    return trialdata["participantID"][finished].unique().tolist()


def filter_by_pID(data: pd.DataFrame, pIDs) -> pd.DataFrame:
    return data[data["participantID"].isin(pIDs)]


def load_json_data(
    json_dir: str,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # get all json files
    json_file_paths = glob.glob(os.path.join(json_dir, "*.json"))
    print(f"> Attempting to load {len(json_file_paths)} json files from {json_dir}")

    # load all json files
    trialdata_pds: List[pd.DataFrame] = list()
    eventdata_pds: List[pd.DataFrame] = list()
    for json_file_path in json_file_paths:
        if json_file_path.endswith(".debug.json") or json_file_path.endswith(
            ".excluded.json"
        ):
            continue
        with open(json_file_path, "r") as json_in:
            # 1. load & parse json
            json_file = json.load(json_in)
            # 2. separate information
            trialdata_dct = json_file["trialdata"]
            eventdata_dct = json_file["eventdata"]

            participant_df = expand_data_column(
                pd.DataFrame.from_records(trialdata_dct)
            )

            if "h_captcha_verification" in json_file:
                # insert new row by mirroring h_captcha_response row
                new_col_dct = (
                    participant_df.loc[
                        participant_df["question"] == "h_captcha_response"
                    ]
                    .iloc[[0]]
                    .to_dict("list")
                )

                new_col_dct["question"] = ["h_captcha_verification"]
                new_col_dct["answer"] = [json_file["h_captcha_verification"]]
                new_col_dct["stage"] = ["server"]
                new_col_dct["status"] = [None]
                new_col_dct["timestamp"] = [None]

                participant_df = pd.concat(
                    (participant_df, pd.DataFrame(new_col_dct)), ignore_index=True
                )

            # 3. convert to pd
            trialdata_pds.append(participant_df)
            eventdata_pds.append(
                expand_data_column(pd.DataFrame.from_records(eventdata_dct))
            )

    # concat
    trialdata = pd.concat(trialdata_pds, ignore_index=True)
    eventdata = pd.concat(eventdata_pds, ignore_index=True)

    # rename columns
    trialdata = trialdata.rename(columns={"study_id": "studyID"})
    eventdata = eventdata.rename(columns={"study_id": "studyID"})

    return trialdata, eventdata


def load_data_json(
    study_dir: str = "data",
    filter_condition: Optional[Union[str, Tuple[str, str]]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """From study dir returns trialdata, eventdata, story/condition id."""
    config_dir = "config"

    print(f">>> Loading study in {study_dir}:")

    # get config paths
    json_dir = os.path.join(study_dir, "json")
    studyIDs_path = os.path.join(study_dir, config_dir, "studyIDs.txt")
    story_condition_id_path = os.path.join(
        study_dir, config_dir, "story_condition_id.txt"
    )

    # Check if they exist
    if not os.path.exists(json_dir):
        raise ValueError(f"Require json dir: {json_dir}")
    if not os.path.exists(studyIDs_path):
        raise ValueError(f"Require config file: {studyIDs_path}")

    # Get config values
    studyIDs = load_config(studyIDs_path)
    try:
        story = str(load_config(story_condition_id_path)[0])
        condition = str(load_config(story_condition_id_path)[1])
    except (FileExistsError, IndexError):
        print(
            f"Require config file: {story_condition_id_path} to specify"
            " story (first line) and condition (second line)."
        )
        import sys

        sys.exit(1)

    # check studyIDs
    if len(studyIDs) == 0:
        raise ValueError(f"Require one or more studyIDs in file: {studyIDs_path}")

    # load trialdata/eventdata
    trialdata, eventdata = load_json_data(json_dir)

    # filter studyIDs
    trialdata = filter_by_studyID(trialdata, studyIDs)
    eventdata = filter_by_studyID(eventdata, studyIDs)

    # filter finished
    finished_ids = participants_finished(trialdata)
    trialdata = filter_by_pID(trialdata, finished_ids)
    eventdata = filter_by_pID(eventdata, finished_ids)

    # filter condition
    if filter_condition is not None:
        if isinstance(filter_condition, str):
            filter_condition = (filter_condition, filter_condition)
        filter_condition_name, condition = filter_condition
        all_conditions = trialdata["condition"].unique()
        print(
            f"Filtering for condition: {filter_condition_name} out of {all_conditions}"
        )
        print(f"Naming condition {condition}")
        p_with_condition = trialdata["condition"] == filter_condition_name
        pIDs_condition = (
            trialdata.loc[p_with_condition, "participantID"].unique().tolist()
        )
        trialdata = filter_by_pID(trialdata, pIDs_condition)
        eventdata = filter_by_pID(eventdata, pIDs_condition)

    return trialdata, eventdata, story, condition
