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
            raise ValueError(f"Require newline for file {path}")
    return lines


def string_to_dict(string: str) -> str:
    string = string.replace(" true,", " True,")
    string = string.replace(" false,", " False,")
    return literal_eval(string.replace("null", "None"))


def load_trialdata(path: str) -> pd.DataFrame:
    print(f"Loading {path}")
    trialdata = pd.read_csv(
        path,
        names=["participantID:studyID", "dataID", "timestamp", "data"],
    )
    # split participant ID from study ID
    trialdata[["participantID", "studyID"]] = trialdata.loc[
        :, "participantID:studyID"
    ].str.split(pat=":", n=1, expand=True)
    # convert data to dicts
    trialdata.loc[:, "data"] = trialdata.loc[:, "data"].apply(string_to_dict)
    # reorder
    trialdata = trialdata[["participantID", "studyID", "dataID", "timestamp", "data"]]
    # extract all fields in the data dicts
    trialdata = trialdata.join(pd.DataFrame(trialdata.pop("data").to_numpy().tolist()))

    return trialdata


def load_eventdata(path="data/eventdata.csv") -> pd.DataFrame:
    print(f"Loading {path}")
    eventdata = pd.read_csv(
        path,
        names=[
            "participantID:studyID",
            "event",
            "delta_time",
            "data",
            "timestamp",
        ],
    )
    # split participant ID from study ID
    eventdata[["participantID", "studyID"]] = eventdata.loc[
        :, "participantID:studyID"
    ].str.split(pat=":", n=1, expand=True)
    eventdata = eventdata.drop(columns="participantID:studyID")
    return eventdata


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
    finished = (trialdata["phase"] == "q_open") & (trialdata["status"] == "end")
    print(
        f"Finished participants: {len(trialdata[finished]['participantID'].unique())}"
    )
    return trialdata["participantID"][finished].unique().tolist()


def filter_by_pID(data: pd.DataFrame, pIDs) -> pd.DataFrame:
    return data[data["participantID"].isin(pIDs)]


def filter_duplicate_entries(trialdata: pd.DataFrame) -> pd.DataFrame:
    q_open_count = (
        trialdata.loc[trialdata["phase"] == "q_open"]
        .groupby(["participantID"])["participantID"]
        .count()
    )
    pID_duplicates = q_open_count[q_open_count != 7].index.tolist()

    duplicates = trialdata[
        (trialdata["participantID"].isin(pID_duplicates))
        & (trialdata["phase"] == "q_open")
    ]

    # find first "end" in duplicates
    indices_to_drop = []
    for _, pID_df in duplicates.groupby("participantID"):
        end_idx = pID_df[pID_df["status"] == "end"].sort_index().index[0]
        indices_to_drop.extend(pID_df.loc[end_idx:].iloc[1:].index.tolist())
    trialdata = trialdata.drop(index=indices_to_drop)

    return trialdata


def load_data(
    study_dir: str = "data",
    filter_condition: Optional[str] = None,
    filter_condition_ocd: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """From study dir Returns (trialdata (pd.df), eventdata (pd.df), story/condition id
    (str))."""
    config_dir = "config"

    print(f"> Loading study in {study_dir}:")

    # get config paths
    trialdatafiles_path = os.path.join(study_dir, config_dir, "trialdatafiles.txt")
    eventdatafiles_path = os.path.join(study_dir, config_dir, "eventdatafiles.txt")
    studyIDs_path = os.path.join(study_dir, config_dir, "studyIDs.txt")
    story_condition_id_path = os.path.join(
        study_dir, config_dir, "story_condition_id.txt"
    )

    # Check if they exist
    if not os.path.exists(trialdatafiles_path):
        raise ValueError(f"Require config file: {trialdatafiles_path}")
    if not os.path.exists(eventdatafiles_path):
        raise ValueError(f"Require config file: {eventdatafiles_path}")
    if not os.path.exists(studyIDs_path):
        raise ValueError(f"Require config file: {studyIDs_path}")

    # Get config values
    trialdata_paths = load_config(trialdatafiles_path)
    eventdata_paths = load_config(eventdatafiles_path)
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

    # load trialdata
    print(os.getcwd())
    trialdata_pds: List[pd.DataFrame] = list()
    for trialdata_path in trialdata_paths:
        trialdata_pds.append(load_trialdata(os.path.join(study_dir, trialdata_path)))
    trialdata = pd.concat(trialdata_pds)

    # load eventdata
    eventdata_pds: List[pd.DataFrame] = list()
    for eventdata_path in eventdata_paths:
        eventdata_pds.append(load_eventdata(os.path.join(study_dir, eventdata_path)))
    eventdata = pd.concat(eventdata_pds)

    # filter studyIDs
    trialdata = filter_by_studyID(trialdata, studyIDs)
    eventdata = filter_by_studyID(eventdata, studyIDs)

    # filter finished
    finished_ids = participants_finished(trialdata)
    trialdata = filter_by_pID(trialdata, finished_ids)
    eventdata = filter_by_pID(eventdata, finished_ids)

    # filter condition
    if filter_condition and filter_condition_ocd:
        raise ValueError(
            "Only filter_condition or filter_condition_ocd can be active, not both."
        )

    if filter_condition is not None:
        all_conditions = trialdata["condition"].unique()
        print(f"Filtering for condition: {filter_condition} out of {all_conditions}")
        p_with_condition = trialdata["condition"] == filter_condition
        pIDs_condition = (
            trialdata.loc[p_with_condition, "participantID"].unique().tolist()
        )
        trialdata = filter_by_pID(trialdata, pIDs_condition)
        eventdata = filter_by_pID(eventdata, pIDs_condition)
        condition = filter_condition

    if filter_condition_ocd is not None:
        print(
            "Filtering ocd condition:"
            f" {filter_condition_ocd} out of ['ocd_first', 'ocd_last']"
        )
        q_personality_start_df = trialdata.loc[
            (trialdata["phase"] == "q_personality") & (trialdata["status"] == "begin"),
            ["participantID", "timestamp"],
        ]
        wcg_start_df = trialdata.loc[
            (trialdata["phase"] == "wcg")
            & (trialdata["status"] == "begin")
            & (trialdata["pre_or_post"] == "pre"),
            ["participantID", "timestamp"],
        ]
        starts_df = q_personality_start_df.merge(wcg_start_df, "inner", "participantID")
        ocd_first_df = starts_df["timestamp_x"] < starts_df["timestamp_y"]
        if filter_condition_ocd == "ocd_first":
            pIDs_condition = starts_df.loc[ocd_first_df, "participantID"].to_list()
        elif filter_condition_ocd == "ocd_last":
            pIDs_condition = starts_df.loc[~ocd_first_df, "participantID"].to_list()
        else:
            raise ValueError(
                "filter_condition_ocd has to be one of ['ocd_first', 'ocd_last']"
            )
        # filter
        trialdata = filter_by_pID(trialdata, pIDs_condition)
        eventdata = filter_by_pID(eventdata, pIDs_condition)
        condition = filter_condition_ocd

    # Need to remove doubled q_open data if present
    trialdata = filter_duplicate_entries(trialdata)

    return trialdata, eventdata, story, condition


#
# Buddhika Study Loading Code
#


def load_trialdata_buddhika(path: str) -> pd.DataFrame:
    trialdata = pd.read_csv(path)
    # convert data to dicts
    trialdata.loc[:, "Datastring"] = trialdata.loc[:, "Datastring"].apply(
        string_to_dict
    )
    # rename
    trialdata = trialdata.rename(
        columns={
            "ID": "participantID",
            "Trial": "dataID",
            "Timestamp": "timestamp",
            "Datastring": "data",
        }
    )
    # reorder
    trialdata = trialdata[
        ["participantID", "dataID", "timestamp", "counterbalance", "data"]
    ]
    # extract all fields in the data dicts
    trialdata = trialdata.join(pd.DataFrame(trialdata.pop("data").to_numpy().tolist()))

    return trialdata


def load_eventdata_buddhika(path: str) -> pd.DataFrame:
    eventdata = pd.read_csv(path)
    # rename
    eventdata = eventdata.rename(
        columns={
            "ID": "participantID",
            "Event": "event",
            "Duration": "delta_time",
            "Details": "data",
            "Timestamp": "timestamp",
        }
    )
    # reorder
    eventdata = eventdata[
        ["participantID", "event", "delta_time", "data", "timestamp", "condition"]
    ]

    return eventdata


def load_questiondata_buddhika(path: str) -> pd.DataFrame:
    questiondata = pd.read_csv(path)
    # rename
    questiondata = questiondata.rename(columns={"ID": "participantID"})
    return questiondata


def participants_finished_buddhika(trialdata: pd.DataFrame) -> List[str]:
    finished = (trialdata["phase"] == "postquestionnaire_2") & (
        trialdata["status"] == "submit"
    )
    print(
        f"Finished participants: {len(trialdata[finished]['participantID'].unique())}"
    )
    return trialdata["participantID"][finished].unique().tolist()


def load_data_buddhika(
    path_trialdata: str,
    path_eventdata: str,
    path_questiondata: str,
    filter_condition: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print("> Loading study from:")
    print(f">> {path_trialdata}")
    print(f">> {path_eventdata}")
    print(f">> {path_questiondata}")

    # load trialdata
    trialdata = load_trialdata_buddhika(path_trialdata)

    # load eventdata
    eventdata = load_eventdata_buddhika(path_eventdata)

    # load questiondata
    questiondata = load_questiondata_buddhika(path_questiondata)

    # filter finished
    finished_ids = participants_finished_buddhika(trialdata)
    trialdata = filter_by_pID(trialdata, finished_ids)
    eventdata = filter_by_pID(eventdata, finished_ids)
    questiondata = filter_by_pID(questiondata, finished_ids)

    # filter condition
    if filter_condition is not None:
        all_conditions = trialdata["condition"].unique()
        print(f"Filtering for condition: {filter_condition} out of {all_conditions}")
        p_with_condition = trialdata["condition"] == filter_condition
        pIDs_condition = (
            trialdata.loc[p_with_condition, "participantID"].unique().tolist()
        )
        trialdata = filter_by_pID(trialdata, pIDs_condition)
        eventdata = filter_by_pID(eventdata, pIDs_condition)
        questiondata = filter_by_pID(questiondata, pIDs_condition)

    return trialdata, eventdata, questiondata
