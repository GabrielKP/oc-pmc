import argparse
import os
from ast import literal_eval
from typing import List, Optional, Tuple, Union

import pandas as pd

LOWER_TRIM = 0.05
UPPER_TRIM = 0.95


def remove_participantIDs(
    data: pd.DataFrame,
    excluded_participantIDs: Optional[List[str]],
) -> pd.DataFrame:
    if excluded_participantIDs is None:
        excluded_participantIDs = []
    data = data[~data["participantID"].isin(excluded_participantIDs)]
    return data


def remove_debug(data: pd.DataFrame) -> pd.DataFrame:
    data = data.loc[~data["participantID"].str.contains("debug.*")]
    return data


def filter_by_finished(data: pd.DataFrame, finished_ids) -> pd.DataFrame:
    return data[data["participantID"].isin(finished_ids)]


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


def load_data(
    study_dir: str = "data",
    config_dir: str = "config",
    exclude: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Returns (trialdata (pd.df), eventdata (pd.df), july (bool))."""

    print(f"> Loading study in {os.path.join(study_dir, config_dir)}:")

    # get config paths
    trialdatafiles_path = os.path.join(study_dir, config_dir, "trialdatafiles.txt")
    eventdatafiles_path = os.path.join(study_dir, config_dir, "eventdatafiles.txt")
    studyIDs_path = os.path.join(study_dir, config_dir, "studyIDs.txt")
    excluded_participantIDs_path = os.path.join(
        study_dir, config_dir, "excluded_participantIDs.txt"
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
    excluded_participantIDs = load_config(excluded_participantIDs_path)

    # check if july
    is_july = os.path.isfile(os.path.join(study_dir, config_dir, "july"))

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

    # filter participants
    if exclude:
        print("\n" + f"Removing {len(excluded_participantIDs)} participants." + "\n")
        trialdata = remove_participantIDs(trialdata, excluded_participantIDs)
        eventdata = remove_participantIDs(eventdata, excluded_participantIDs)
    else:
        print("Skipping exclusions.")

    # filter debug
    trialdata = remove_debug(trialdata)
    eventdata = remove_debug(eventdata)

    # filter finished
    finished_ids = participants_finished(trialdata)
    trialdata = filter_by_finished(trialdata, finished_ids)
    eventdata = filter_by_finished(eventdata, finished_ids)

    return trialdata, eventdata, is_july


def load_trialdata(path="data/trialdata.csv") -> pd.DataFrame:
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
    trialdata.loc[:, "data"] = trialdata.loc[:, "data"].apply(literal_eval)
    # reorder
    trialdata = trialdata[["participantID", "studyID", "dataID", "timestamp", "data"]]
    # extract all fields in the data dicts
    trialdata = trialdata.join(pd.DataFrame(trialdata.pop("data").values.tolist()))
    # set word responses to int
    trialdata.loc[~trialdata["response"].isna(), "response"] = trialdata.loc[
        ~trialdata["response"].isna(), "response"
    ].astype(int)

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


def studies_total(trialdata: pd.DataFrame) -> int:
    n_studies = len(trialdata["studyID"].unique())
    print(f"Total studies: {n_studies}")
    return n_studies


def participants_total(trialdata: pd.DataFrame) -> int:
    n_participants = len(trialdata["participantID"].unique())
    print(f"Participants: {n_participants}")
    return n_participants


def participants_by_study(trialdata: pd.DataFrame) -> None:
    n_grouped = trialdata[["participantID", "studyID"]].groupby("studyID").nunique()
    print("Participants by study:")
    print(n_grouped)


def participants_finished(trialdata: pd.DataFrame) -> List[str]:
    finished = (trialdata["phase"] == "demographic_survey") & (
        trialdata["status"] == "end"
    )
    print(
        f"Finished participants: {len(trialdata[finished]['participantID'].unique())}"
    )
    return trialdata["participantID"][finished].unique().tolist()


def participants_finished_by_study(trialdata: pd.DataFrame) -> None:
    finished = (trialdata["phase"] == "demographic_survey") & (
        trialdata["status"] == "end"
    )
    n_grouped = (
        trialdata[["participantID", "studyID"]][finished].groupby("studyID").nunique()
    )
    print("Finished participants by study:")
    print(n_grouped)


def get_times(trialdata: pd.DataFrame) -> pd.DataFrame:
    # phase times
    phase_times = pd.merge(
        trialdata[trialdata["status"] == "end"],
        trialdata[trialdata["status"] == "begin"],
        on=["participantID", "phase"],
    )[["participantID", "phase", "timestamp_x", "timestamp_y"]]
    phase_times["time"] = phase_times["timestamp_x"] - phase_times["timestamp_y"]
    phase_times["minutes"] = phase_times["time"] / 60000
    phase_times = phase_times[["participantID", "phase", "time", "minutes"]]

    def extract_total_time(participant_data: pd.DataFrame):
        time = (
            participant_data.iloc[-1]["timestamp"]
            - participant_data.iloc[0]["timestamp"]
        )
        return pd.DataFrame(
            {
                "phase": ["total"],
                "time": [time],
                "minutes": [time / 60000],
            }
        )

    # add total times
    total_times = (
        trialdata.groupby("participantID")
        .apply(extract_total_time)
        .reset_index(level=0)
    )
    times = pd.concat([phase_times, total_times]).sort_values(
        ["participantID", "phase"], ignore_index=True
    )

    # drop duplicates
    times = times.drop_duplicates(subset=["participantID", "phase"])

    print("Average phase times:")
    print(times.groupby("phase")["minutes"].mean())
    print("")
    print("Median phase times:")
    print(times.groupby("phase")["minutes"].median())

    return times


def get_demographic_answers(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    # get answers for each question
    demographic_answers_list = []
    for condition in [
        "attncheck",
        "gender",
        "country",
        "nativelang",
        "fluency",
        "race",
        "education",
    ]:
        answer_df = pID_trialdata[
            (pID_trialdata["question"] == f"demographics_{condition}")
        ][["answer"]]
        answer_df = answer_df.rename(columns={"answer": condition})
        # remove duplicate indices
        answer_df = answer_df[~answer_df.index.duplicated(keep="last")]
        demographic_answers_list.append(answer_df)

    # extra handling for content_read...
    answer_df = pID_trialdata[(pID_trialdata["question"] == "content_read")][["answer"]]
    answer_df = answer_df.rename(columns={"answer": "content_read"})
    answer_df = answer_df[~answer_df.index.duplicated(keep="last")]
    demographic_answers_list.append(answer_df)

    # join into dataframe with pIDs
    return demographic_answers_list[0].join(demographic_answers_list[1:])


def get_questionnaire_answers(
    pID_trialdata: pd.DataFrame, july: bool = False
) -> pd.DataFrame:
    questions_answers_carver = [
        ("3_Q1", "3", "general"),
        ("3_Q2", "2", "general"),
        ("3_Q3", "4", "specific"),
        ("3_Q4", "3", "specific"),
        ("3_Q5", "3", "specific"),
        ("3_Q6", "4", "specific"),
        ("3_Q7", "2", "catch"),
        ("3_Q8", "1", "general"),
        ("3_Q9", "4", "general"),
        ("3_Q10", "2", "specific"),
        ("3_Q11", "4", "general"),
        ("3_Q12", "2", "specific"),
        ("3_Q13", "3", "general"),
        ("3_Q14", "2", "specific"),
        ("3_Q15", "1", "specific"),
        ("3_Q16", "1", "general"),
        ("3_Q17", "2", "general"),
        ("3_Q18", "2", "general"),
        ("3_Q19", "1", "general"),
        ("3_Q20", "3", "specific"),
        ("3_Q21", "1", "catch"),
        ("3_Q22", "1", "specific"),
        ("3_Q23", "4", "general"),
        ("3_Q24", "1", "specific"),
        ("3_Q25", "4", "general"),
        ("3_Q26", "3", "specific"),
    ]
    questions_answers_july = [
        ("3_Q1", "1", "general"),
        ("3_Q2", "1", "specific"),
        ("3_Q3", "3", "general"),
        ("3_Q4", "4", "specific"),
        ("3_Q5", "2", "general"),
        ("3_Q6", "1", "specific"),
        ("3_Q7", "1", "catch"),
        ("3_Q8", "3", "specific"),
        ("3_Q9", "4", "general"),
        ("3_Q10", "4", "general"),
        ("3_Q11", "2", "specific"),
        ("3_Q12", "1", "general"),
        ("3_Q13", "4", "general"),
        ("3_Q14", "4", "specific"),
        ("3_Q15", "2", "specific"),
        ("3_Q16", "1", "general"),
        ("3_Q17", "2", "general"),
        ("3_Q18", "2", "specific"),
        ("3_Q19", "3", "specific"),
        ("3_Q20", "3", "specific"),
        ("3_Q21", "4", "general"),
        ("3_Q22", "2", "general"),
        ("3_Q23", "3", "specific"),
        ("3_Q24", "2", "catch"),
        ("3_Q25", "3", "general"),
        ("3_Q26", "1", "specific"),
    ]
    question_answers = questions_answers_july if july else questions_answers_carver
    questionnaire_answers_list: List[pd.DataFrame] = list()
    specific_answers_list: List[pd.DataFrame] = list()
    general_answers_list: List[pd.DataFrame] = list()
    catch_answers_list: List[pd.DataFrame] = list()
    for question, correct_answer, kind in question_answers:
        answer_df = pID_trialdata[(pID_trialdata["question"] == question)][["answer"]]
        # check for correctness
        answer_df[question] = answer_df["answer"] == correct_answer
        # remove duplicate indices
        answer_df = answer_df[~answer_df.index.duplicated(keep="last")]
        questionnaire_answers_list.append(answer_df[[question]])
        if kind == "general":
            general_answers_list.append(answer_df[[question]])
        elif kind == "specific":
            specific_answers_list.append(answer_df[[question]])
        elif kind == "catch":
            catch_answers_list.append(answer_df[[question]])

    # join into dataframe with pIDs
    pID_questionnaire = questionnaire_answers_list[0].join(
        questionnaire_answers_list[1:]  # type: ignore
    )
    pID_general = general_answers_list[0].join(general_answers_list[1:])  # type: ignore
    pID_specific = specific_answers_list[0].join(specific_answers_list[1:])  # type: ignore
    pID_catch = catch_answers_list[0].join(catch_answers_list[1:])  # type: ignore
    # count correct responses
    correct_responses = pID_questionnaire.sum(axis=1)
    correct_responses.name = "n_correct"
    # merge back
    pID_questionnaire = pID_questionnaire.join(correct_responses)
    pID_questionnaire["total (%)"] = pID_questionnaire["n_correct"] / 26
    pID_questionnaire["shallow (%)"] = pID_general.sum(axis=1) / 12
    pID_questionnaire["deep (%)"] = pID_specific.sum(axis=1) / 12
    pID_questionnaire["catch (%)"] = pID_catch.sum(axis=1) / 2
    # move overview columns to beginning
    for colname in [
        "catch (%)",
        "deep (%)",
        "shallow (%)",
        "total (%)",
        "n_correct",
    ]:
        pID_questionnaire.insert(
            0,
            colname,
            pID_questionnaire.pop(colname),
        )
    return pID_questionnaire


def _trim_and_correlate(group_df: pd.DataFrame):
    lower_trim = LOWER_TRIM
    upper_trim = UPPER_TRIM

    # trim
    lower = group_df["rt"].quantile(lower_trim)
    upper = group_df["rt"].quantile(upper_trim)
    group_df = group_df.loc[(group_df["rt"] > lower) & (group_df["rt"] < upper)]

    # correlate
    return group_df.corr().iloc[0, 1]


def get_spr_correlations(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    # get relevant variables
    sel = (pID_trialdata["phase"] == "spr") & (pID_trialdata["status"] == "ongoing")
    spr = pID_trialdata.loc[sel.tolist()]
    spr_nwords = spr.loc[:, ["num_words", "rt"]]
    spr_nchars = spr.loc[:, ["num_char", "rt"]]
    # convert rows to int
    spr_nwords["num_words"] = spr_nwords["num_words"].astype(int)
    spr_nchars["num_char"] = spr_nchars["num_char"].astype(int)

    # trim and correlate
    spr_word_corrs = spr_nwords.groupby("participantID").apply(_trim_and_correlate)
    spr_word_corrs.name = "spr/word"
    spr_char_corrs = spr_nchars.groupby("participantID").apply(_trim_and_correlate)
    spr_char_corrs.name = "spr/char"
    # join dfs for output
    return pd.DataFrame(spr_word_corrs).join(pd.DataFrame(spr_char_corrs))


def _get_word_properties(word: pd.Series, word_ratings: pd.DataFrame) -> list:
    try:
        return word_ratings.loc[word.iloc[0]].to_list()
    except KeyError:
        # in case the word was not rated by others
        return [0, None, None]


def _correlate_words_with_others(curr_ratings: pd.DataFrame, all_ratings: pd.DataFrame):
    # get pID
    curr_id = curr_ratings.name

    # exclude pID from all ratings
    all_ratings = all_ratings.iloc[~(all_ratings.index == curr_id)]

    # get average word ratings for other words
    word_ratings = (
        all_ratings.set_index("word").groupby("word").agg(["count", "mean", "median"])
    )

    # compute average rating for all other words
    curr_ratings[["count", "mean", "median"]] = curr_ratings[["word"]].apply(
        _get_word_properties,
        axis=1,
        # raw=True,
        result_type="expand",
        word_ratings=word_ratings,
    )
    result = curr_ratings[["response", "mean", "median"]].corr()["response"][
        ["median", "mean"]
    ]
    result = pd.concat(
        [result, pd.Series({"mean_word_count": curr_ratings["count"].mean()})]
    )

    # rename columns
    # result = result.rename(columns={""})

    return result


def _get_rating_stats(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_ratings = pID_trialdata[
        (pID_trialdata["phase"] == "rating") & (pID_trialdata["status"] == "ongoing")
    ]
    pIDratings2 = pID_ratings.copy()
    pIDratings2["response"] = pIDratings2.loc[:, "response"].astype(int)

    # copy to avoid data corruption
    pID_ratings_copy = pID_ratings.copy().loc[:, ["word", "response"]]

    # get rating times per word
    pID_avg_rating_times = pID_ratings["rt"].groupby("participantID").mean() / 1000

    # get correlations
    pID_correlations = (
        pIDratings2[["word", "response"]]
        .groupby("participantID")
        .apply(
            _correlate_words_with_others,  # type: ignore
            all_ratings=pID_ratings_copy,
        )
    )
    pID_correlations = pID_correlations.join(pID_avg_rating_times)
    pID_correlations = pID_correlations.rename(columns={"rt": "mean_rate_time (s)"})
    return pID_correlations


def get_rating_stats(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    print("0 / 3")
    pID_correlations = _get_rating_stats(pID_trialdata)
    pID_correlations = pID_correlations.rename(
        columns={
            "median": "crr:medi [a]",
            "mean": "crr:mean [a]",
            "mean_word_count": "wc:mean [a]",
            "mean_rate_time (s)": "rating_t [a]",
        }
    )

    print("1 / 3")
    pID_trialdata_moment = pID_trialdata[
        (
            (pID_trialdata["phase"] == "rating")
            & (pID_trialdata["status"] == "ongoing")
            & (pID_trialdata["question_type"] == "moment")
        )
    ]
    pID_correlations_moment = _get_rating_stats(pID_trialdata_moment)
    pID_correlations_moment = pID_correlations_moment.rename(
        columns={
            "median": "crr:medi [m]",
            "mean": "crr:mean [m]",
            "mean_word_count": "wc:mean [m]",
            "mean_rate_time (s)": "rating_t [m]",
        }
    )

    print("2 / 3")
    pID_trialdata_theme = pID_trialdata[
        (
            (pID_trialdata["phase"] == "rating")
            & (pID_trialdata["status"] == "ongoing")
            & (pID_trialdata["question_type"] == "theme")
        )
    ]
    pID_correlations_theme = _get_rating_stats(pID_trialdata_theme)
    pID_correlations_theme = pID_correlations_theme.rename(
        columns={
            "median": "crr:medi [t]",
            "mean": "crr:mean [t]",
            "mean_word_count": "wc:mean [t]",
            "mean_rate_time (s)": "rating_t [t]",
        }
    )

    return pID_correlations.join([pID_correlations_moment, pID_correlations_theme])


def _time_away(group_df: pd.DataFrame) -> float:
    # sometimes after resizing there is an on event
    if group_df.iloc[0, 0] == "on":
        group_df = group_df.iloc[1:]
    return (
        (
            group_df.loc[(group_df["data"] == "on"), ["timestamp"]].sort_values(
                "timestamp"
            )
            - group_df.loc[(group_df["data"] == "off"), ["timestamp"]].sort_values(
                "timestamp"
            )
        ).sum()
        / 1000
        / 60
    )  # type: ignore


def get_focus_stats(
    pID_eventdata: pd.DataFrame, pID_trialdata: pd.DataFrame
) -> pd.DataFrame:
    # base df for joining things in
    pID_eventstats = pID_eventdata.loc[
        pID_eventdata["event"] == "initialized", ["event"]
    ]

    # get off events
    pID_off_events = (
        pID_eventdata.loc[(pID_eventdata["data"] == "off"), ["data"]]
        .groupby("participantID")
        .count()
    )

    # get phase times
    trialdata = pID_trialdata.reset_index()
    phase_times = pd.merge(
        trialdata[trialdata["status"] == "end"],
        trialdata[trialdata["status"] == "begin"],
        on=["participantID", "phase"],
    )[["participantID", "phase", "timestamp_x", "timestamp_y"]]
    # merge with off events
    offs = pID_eventdata.loc[
        (pID_eventdata["data"] == "off"), ["timestamp", "data"]
    ].reset_index()
    phase_times_offs = pd.merge(
        phase_times,
        offs,
        on="participantID",
    )
    # merge with on events
    ons = pID_eventdata.loc[
        (pID_eventdata["data"] == "on"), ["timestamp", "data"]
    ].reset_index()
    phase_times_ons = pd.merge(
        phase_times,
        ons,
        on="participantID",
    )
    # check if off/on events are within phases
    offs_before_end = phase_times_offs["timestamp_x"] > phase_times_offs["timestamp"]
    offs_after_start = phase_times_offs["timestamp_y"] < phase_times_offs["timestamp"]
    offs_within_phase = phase_times_offs[(offs_before_end & offs_after_start)]
    ons_before_end = phase_times_ons["timestamp_x"] > phase_times_ons["timestamp"]
    ons_after_start = phase_times_ons["timestamp_y"] < phase_times_ons["timestamp"]
    ons_within_phase = phase_times_ons[(ons_before_end & ons_after_start)]
    within_phase: pd.DataFrame = pd.concat((offs_within_phase, ons_within_phase))
    # time away within spr
    pID_events_within_spr = within_phase.loc[
        within_phase["phase"] == "spr", ["participantID", "data", "timestamp"]
    ].set_index("participantID")
    pID_timeaway_spr = pID_events_within_spr.groupby("participantID").apply(_time_away)
    pID_timeaway_spr = pID_timeaway_spr.rename(
        columns={"timestamp": "spr time away (m)"}  # type: ignore
    )
    # if there are no off-events
    if "data" in pID_timeaway_spr.columns.to_list():
        pID_timeaway_spr = pID_timeaway_spr.drop(columns="data")
    # time away within rating
    pID_events_within_rating = within_phase.loc[
        within_phase["phase"] == "rating",
        ["participantID", "data", "timestamp"],
    ].set_index("participantID")
    pID_timeaway_rating = pID_events_within_rating.groupby("participantID").apply(
        _time_away
    )
    pID_timeaway_rating = pID_timeaway_rating.rename(
        columns={"timestamp": "rating time away (m)"}  # type: ignore
    )
    if "data" in pID_timeaway_rating.columns.to_list():
        pID_timeaway_rating = pID_timeaway_rating.drop(columns="data")

    # time away in general
    pID_focusevents = pID_eventdata.loc[
        (pID_eventdata["event"] == "focus"), ["data", "timestamp"]
    ]
    pID_timeaway = pID_focusevents.groupby("participantID").apply(_time_away)

    # join both results with stats
    pID_eventstats = pID_eventstats.join(
        [pID_timeaway, pID_off_events, pID_timeaway_spr, pID_timeaway_rating]
    )

    # get rid of NaNs
    pID_eventstats.loc[pID_eventstats["data"].isna(), ["data", "timestamp"]] = 0
    pID_eventstats.loc[
        pID_eventstats["spr time away (m)"].isna(), ["spr time away (m)"]
    ] = 0
    pID_eventstats.loc[
        pID_eventstats["rating time away (m)"].isna(), ["rating time away (m)"]
    ] = 0
    pID_eventstats = pID_eventstats.drop(columns="event")

    # rename columns
    pID_eventstats = pID_eventstats.rename(
        columns={"data": "focusevents", "timestamp": "time away (m)"}
    )
    return pID_eventstats


def generate_overview(
    study_dir: str,
    all_data: bool = False,
):
    option_context = [
        "display.precision",
        4,
    ]
    if all_data:
        option_context.extend(
            [
                "display.max_columns",
                None,
                # "display.width",
                # None,
            ]
        )
    with pd.option_context(*option_context):
        print("\n------- STUDY OVERVIEW -------\n")
        # load data
        trialdata, eventdata, is_july = load_data(study_dir=study_dir)

        # make pID index
        pID_trialdata = trialdata.set_index("participantID")
        pID_eventdata = eventdata.set_index("participantID")

        # overview
        participants_finished_by_study(trialdata)

        # show average times
        print("")
        times = get_times(trialdata)
        pID_times = times.pivot(
            index="participantID", columns="phase", values="minutes"
        )
        print("")

        print("\n-- Times\n")
        print(pID_times)

        print("\n-- Demographics\n")
        pID_demographics = get_demographic_answers(pID_trialdata)
        print(pID_demographics)

        print("\n-- Focus stats\n")
        pID_focusstats = get_focus_stats(pID_eventdata, pID_trialdata)
        print(pID_focusstats)

        print("\n-- Questionnaire\n")
        pID_questionnaire = get_questionnaire_answers(pID_trialdata, july=is_july)
        print(
            pID_questionnaire[
                [
                    "n_correct",
                    "total (%)",
                    "shallow (%)",
                    "deep (%)",
                    "catch (%)",
                ]
            ]
        )
        cols = pID_questionnaire.columns.tolist()
        cols.remove("n_correct")
        cols.remove("total (%)")
        cols.remove("shallow (%)")
        cols.remove("deep (%)")
        cols.remove("catch (%)")
        print("raw")
        print(pID_questionnaire[cols])

        print("\n-- SPR correlations\n")
        pID_spr_correlations = get_spr_correlations(pID_trialdata)
        print(pID_spr_correlations)

        print("\n-- Rating stats\n")
        pID_rating_correlations = get_rating_stats(pID_trialdata)
        print("crr:medi   :=  correlation of median")
        print("crr:mean   :=  correlation of means")
        print("rating_t   :=  mean rating time (s)")
        print(
            "wc:mean    :=  mean count of words with which a word of"
            " a participant was compared with"
        )
        print("[a] := all ; [t] := theme ; [m] := moment")
        print("")
        print(pID_rating_correlations)
        print("-- Means:")
        print(pID_rating_correlations.mean())

        print("\n-- Joint stats\n")
        pID_stats = pID_spr_correlations.join(
            [
                pID_questionnaire[["total (%)"]],
                pID_rating_correlations,
                pID_focusstats,
            ]
        )
        print(pID_stats)
        print(pID_stats.mean())

        # Save anonymous rating stats into overview file
        n_participants = len(participants_finished(trialdata))
        n_ratings = len(
            trialdata[
                (trialdata["phase"] == "rating") & (trialdata["status"] == "ongoing")
            ]
        )
        n_ratings_moment = n_ratings // 2
        n_ratings_theme = n_ratings // 2

        with open(os.path.join(study_dir, "outputs", "overview.txt"), "w") as f_out:
            f_out.write(
                f"N participants: {n_participants}" + "\n"
                f"N ratings: {n_ratings}" + "\n"
                f"N ratings moment: {n_ratings_moment}" + "\n"
                f"N ratings theme: {n_ratings_theme}" + "\n\n"
                "              - Legend -\n"
                "crr:medi   :=  correlation of median\n"
                "crr:mean   :=  correlation of means\n"
                "rating_t   :=  mean rating time (s)\n"
                "wc:mean    :=  mean count of words with which a word of"
                " a participant was compared with\n"
                "[a] := all ; [t] := theme ; [m] := moment\n"
                "spr/word   := corr reading time and sentence words\n"
                "spr/char   := corr reading time and sentence characters\n"
                "total (%)  := percentage correct comprehension test\n"
                "time away  := time window was not on focus\n"
                "focusevents      := amount of times focus switched away\n"
                "spr time away    := amount of time away during reading\n"
                "rating time away := amount of time away during rating\n\n"
                "           - Average Stats -\n"
            )
            avg_stats = pID_stats.mean().to_string()
            f_out.write(avg_stats + "\n\n")
            f_out.write("        - Participant Stats (each row a participant) -\n")
            stats = pID_stats.to_string(index=False)
            f_out.write(stats + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="generate trialdata overview")
    parser.add_argument(
        "-s",
        "--study_dir",
        type=str,
        default="data",
        help="Directory for study",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="show all data expanded.",
    )
    args = parser.parse_args()
    generate_overview(study_dir=args.study_dir, all_data=args.all)
