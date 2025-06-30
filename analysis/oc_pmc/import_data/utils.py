from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def carver_solutions() -> List[Tuple[str, str, str]]:
    return [
        ("comp_Q1", "3", "general"),
        ("comp_Q2", "2", "general"),
        ("comp_Q3", "4", "specific"),
        ("comp_Q4", "3", "specific"),
        ("comp_Q5", "3", "specific"),
        ("comp_Q6", "4", "specific"),
        ("comp_Q7", "2", "catch"),
        ("comp_Q8", "1", "general"),
        ("comp_Q9", "4", "general"),
        ("comp_Q10", "2", "specific"),
        ("comp_Q11", "4", "general"),
        ("comp_Q12", "2", "specific"),
        ("comp_Q13", "3", "general"),
        ("comp_Q14", "2", "specific"),
        ("comp_Q15", "1", "specific"),
        ("comp_Q16", "1", "general"),
        ("comp_Q17", "2", "general"),
        ("comp_Q18", "2", "general"),
        ("comp_Q19", "1", "general"),
        ("comp_Q20", "3", "specific"),
        ("comp_Q21", "1", "catch"),
        ("comp_Q22", "1", "specific"),
        ("comp_Q23", "4", "general"),
        ("comp_Q24", "1", "specific"),
        ("comp_Q25", "4", "general"),
        ("comp_Q26", "3", "specific"),
    ]


def get_comp_prop_carver(
    pID_trialdata: pd.DataFrame, detailed: bool = True
) -> pd.DataFrame:
    solutions = carver_solutions()

    answers_dct: Dict[str, List[pd.DataFrame]] = defaultdict(list)
    for question, correct_answer, kind in solutions:
        answer_df = pID_trialdata[(pID_trialdata["question"] == question)][["answer"]]
        # check for correctness
        answer_df[question] = answer_df["answer"] == correct_answer
        # remove duplicate indices
        answer_df = answer_df[~answer_df.index.duplicated(keep="last")]

        answers_dct[kind].append(answer_df[[question]])

    pID_catch = answers_dct["catch"][0].join(answers_dct["catch"][1:])  # type: ignore
    pID_general = answers_dct["general"][0].join(answers_dct["general"][1:])  # type: ignore
    pID_specific = answers_dct["specific"][0].join(answers_dct["specific"][1:])  # type: ignore
    pID_questionnaire = pID_general.join(pID_specific)

    correct_responses = pID_questionnaire.sum(axis=1)
    correct_responses.name = "comp_raw"

    # merge into one df
    pID_questionnaire = pID_questionnaire.join(correct_responses)
    pID_questionnaire["comp_prop"] = pID_questionnaire["comp_raw"] / 24
    pID_questionnaire["specific_prop"] = pID_general.sum(axis=1) / 12
    pID_questionnaire["general_prop"] = pID_specific.sum(axis=1) / 12
    pID_questionnaire["catch_prop"] = pID_catch.sum(axis=1) / 2

    if detailed:
        return pID_questionnaire

    # only return overview columns
    return pID_questionnaire.loc[
        :,
        [
            "catch_prop",
            "general_prop",
            "specific_prop",
            "comp_prop",
            "comp_raw",
        ],
    ]


def compute_comp_prop(
    pID_trialdata: pd.DataFrame,
    detailed: bool,
    solutions: List[Tuple[str, str, str]],
) -> pd.DataFrame:
    answers_dct: Dict[str, List[pd.DataFrame]] = defaultdict(list)
    for question, correct_answer, kind in solutions:
        answer_df = pID_trialdata[(pID_trialdata["question"] == question)][["answer"]]
        # check for correctness
        answer_df[question] = answer_df["answer"] == correct_answer
        # remove duplicate indices
        answer_df = answer_df[~answer_df.index.duplicated(keep="last")]

        answers_dct[kind].append(answer_df[[question]])

    pID_questionnaire = answers_dct["general"][0].join(answers_dct["general"][1:])  # type: ignore

    correct_responses = pID_questionnaire.sum(axis=1)
    correct_responses.name = "comp_raw"

    # merge into one df
    pID_questionnaire = pID_questionnaire.join(correct_responses)
    pID_questionnaire["comp_prop"] = pID_questionnaire["comp_raw"] / len(
        answers_dct["general"]
    )

    overview_columns = ["comp_prop", "comp_raw"]
    if answers_dct.get("catch") is not None:
        pID_catch = answers_dct["catch"][0].join(answers_dct["catch"][1:])  # type: ignore
        pID_questionnaire["catch_prop"] = pID_catch.sum(axis=1)
        overview_columns.insert(0, "catch_prop")

    if detailed:
        return pID_questionnaire

    # only return overview columns
    return pID_questionnaire.loc[:, overview_columns]


def davis_solutions() -> List[Tuple[str, str, str]]:
    return [
        ("2B_Q1", "4", "general"),
        ("2B_Q2", "2", "general"),
        ("2B_Q3", "1", "general"),
        ("2B_Q4", "2", "general"),
        ("2B_Q5", "1", "catch"),
        ("2B_Q6", "4", "general"),
        ("2B_Q7", "2", "general"),
    ]


def get_comp_prop_davis(
    pID_trialdata: pd.DataFrame, detailed: bool = True
) -> pd.DataFrame:
    solutions = davis_solutions()
    return compute_comp_prop(pID_trialdata, detailed, solutions)


def interference_story_solutions() -> List[Tuple[str, str, str]]:
    return [
        ("comp_Q1_interference", "2", "general"),
        ("comp_Q2_interference", "3", "general"),
        ("comp_Q3_interference", "2", "general"),
        ("comp_Q4_interference", "4", "general"),
    ]


def get_comp_prop_interference_story(
    pID_trialdata: pd.DataFrame, detailed: bool = True
) -> pd.DataFrame:
    solutions = interference_story_solutions()
    return compute_comp_prop(pID_trialdata, detailed, solutions)


def dark_bedroom_story_solutions(
    interference: bool = False,
) -> List[Tuple[str, str, str]]:
    if interference:
        return [
            ("comp_Q1_interference", "3", "general"),
            ("comp_Q2_interference", "1", "general"),
            ("comp_Q3_interference", "2", "general"),
            ("comp_Q4_interference", "4", "catch"),
            ("comp_Q5_interference", "2", "general"),
        ]

    return [
        ("comp_Q1", "3", "general"),
        ("comp_Q2", "1", "general"),
        ("comp_Q3", "2", "general"),
        ("comp_Q4", "4", "catch"),
        ("comp_Q5", "2", "general"),
    ]


def get_comp_prop_dark_bedroom(
    pIDtrialdata: pd.DataFrame,
    detailed: bool = True,
    interference: bool = False,
) -> pd.DataFrame:
    solutions = dark_bedroom_story_solutions(interference)
    return compute_comp_prop(pIDtrialdata, detailed, solutions)


def get_attention_check(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_attention_check = pID_trialdata.loc[
        (pID_trialdata["question"] == "demographics_attncheck"), ["answer"]
    ]
    pID_attention_check.rename(columns={"answer": "attncheck"}, inplace=True)
    pID_attention_check = pID_attention_check[
        ~pID_attention_check.index.duplicated(keep="last")
    ]
    return pID_attention_check


def _fix_on_off_mismatch(group_df: pd.DataFrame) -> pd.DataFrame:
    """Removes doubled/quadrupled "on" and "off" events.
    Also removes "on" events at the beginning and "off" events at the end.
    """
    # iterate over rows and remove doubled events
    new_rows = list()
    mode = "begin"
    removed_events = 0
    for i, row in group_df.iterrows():
        # remove any "on" events at the beginning
        if mode == "begin":
            if row["data"] == "on":
                continue
            mode = "off"
            new_rows.append(row)
        else:
            if row["data"] == mode:
                # remove duplicate entries
                # count to remove off events at end
                removed_events += 1
            else:
                removed_events = 0
                mode = "on" if mode == "off" else "off"
                new_rows.append(row)

    if mode == "off":
        # remove off events at end
        new_rows = new_rows[:-removed_events]

    return pd.DataFrame(new_rows)


def _time_away(group_df: pd.DataFrame) -> pd.Series:
    group_df = group_df.sort_values("timestamp")

    # make sure if "on" and "off" events match:
    # make sure that list starts with "off" events, ends with "on" events
    group_df = _fix_on_off_mismatch(group_df)
    if group_df.empty:
        return pd.Series({"timestamp": 0})

    time_away_ms = (
        group_df.loc[(group_df["data"] == "on"), ["timestamp"]]
        - group_df.loc[(group_df["data"] == "off"), ["timestamp"]]
    ).sum()

    return time_away_ms / 1000 / 60


def get_time_away(
    pID_eventdata: pd.DataFrame, pID_trialdata: pd.DataFrame
) -> pd.DataFrame:
    # base df for joining things in
    pID_eventstats = pID_eventdata.loc[
        pID_eventdata["event"] == "initialized", ["event"]
    ]

    # Special case, nobody focussed out of the window
    if not any(pID_eventdata["data"] == "off"):
        # get index, colnames and 0 data
        index = pID_eventdata.index.unique()
        colnames = [
            "time away (m)",
            "focusevents",
            "spr time away (m)",
            "rating time away (m)",
        ]
        zero_data = np.zeros((len(index), len(colnames)))
        return pd.DataFrame(
            data=zero_data,
            index=index,
            columns=colnames,
        )

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
        within_phase["phase"] == "story_reading",
        ["participantID", "data", "timestamp"],
    ].set_index("participantID")
    pID_timeaway_spr = pID_events_within_spr.groupby("participantID").apply(_time_away)
    pID_timeaway_spr = pID_timeaway_spr.rename(
        columns={"timestamp": "spr time away (m)"}
    )  # type: ignore
    # if there are no off-events
    if "data" in pID_timeaway_spr.columns.to_list():
        pID_timeaway_spr = pID_timeaway_spr.drop(columns="data")
    # time away within wcg
    pID_events_within_rating = within_phase.loc[
        within_phase["phase"] == "wcg",
        ["participantID", "data", "timestamp"],
    ].set_index("participantID")
    pID_timeaway_rating = pID_events_within_rating.groupby(
        "participantID",
        group_keys=False,
    ).apply(_time_away)
    pID_timeaway_rating = pID_timeaway_rating.rename(
        columns={"timestamp": "wcg time away (m)"}
    )  # type: ignore
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
        pID_eventstats["wcg time away (m)"].isna(), ["wcg time away (m)"]
    ] = 0
    pID_eventstats = pID_eventstats.drop(columns="event")

    # rename columns
    pID_eventstats = pID_eventstats.rename(
        columns={"data": "focusevents", "timestamp": "time away (m)"}
    )
    return pID_eventstats


def get_reaction_time(pID_trialdata: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    pID_word_times = pID_trialdata.loc[
        (pID_trialdata["phase"] == "wcg") & (pID_trialdata["status"] == "ongoing"),
        ["word_time"],
    ]

    pID_rt_means = pID_word_times.groupby("participantID").mean()
    pID_rt_means.rename(columns={"word_time": "rt_mean"}, inplace=True)
    pID_rt_max = pID_word_times.groupby("participantID").max()
    pID_rt_max.rename(columns={"word_time": "rt_max"}, inplace=True)

    return pID_rt_means, pID_rt_max


def get_spr_wcg_break(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    times_spr_wcg = list()
    pIDs = list()
    for group_name, group_df in pID_trialdata.groupby("participantID"):
        end_spr = group_df.loc[
            (group_df["phase"] == "story_reading") & (group_df["status"] == "end"),
            "timestamp",
        ].iloc[0]
        start_wcg = group_df.loc[
            (group_df["phase"] == "wcg")
            & (group_df["status"] == "begin")
            & (group_df["pre_or_post"] == "post"),
            "timestamp",
        ].iloc[0]

        times_spr_wcg.append(start_wcg - end_spr)
        pIDs.append(group_name)
    pID_spr_wcg_break = pd.DataFrame(data=times_spr_wcg, index=pIDs, columns=["time"])
    pID_spr_wcg_break.index.name = "participantID"
    pID_spr_wcg_break.rename(columns={"time": "spr-wcg-break"}, inplace=True)

    return pID_spr_wcg_break


def get_exp_time_away(
    pID_eventdata: pd.DataFrame, pID_trialdata: pd.DataFrame
) -> pd.DataFrame:
    """Return time away between start of word chain game and start of demographics
    questionnaire."""
    exp_times = list()
    pIDs = list()

    # Merge to have all data
    pID_trial_eventdata = pd.concat([pID_trialdata, pID_eventdata], axis=0)

    for group_name, group_df in pID_trial_eventdata.groupby("participantID"):
        start_wcg = group_df.loc[
            (group_df["phase"] == "wcg")
            & (group_df["status"] == "begin")
            & (group_df["pre_or_post"] == "pre"),
            "timestamp",
        ].iloc[0]
        start_demographics = group_df.loc[
            (group_df["phase"] == "q_demographics") & (group_df["status"] == "begin"),
            "timestamp",
        ].iloc[0]

        # Disregard any information outside of range, only pick on off events
        group_df = group_df.loc[
            (group_df["timestamp"] > start_wcg)
            & (group_df["timestamp"] < start_demographics)
            & ((group_df["data"] == "off") | (group_df["data"] == "on"))
        ]

        if group_df.empty:
            exp_times.append(0)
        else:
            exp_times.append(_time_away(group_df).item())
        pIDs.append(group_name)
    pID_exp_time = pd.DataFrame(data=exp_times, index=pIDs, columns=["exp_time_away"])
    pID_exp_time.index.name = "participantID"

    return pID_exp_time


def get_spr_correlations(
    pID_trialdata: pd.DataFrame,
    lower_trim: float = 0.05,
    upper_trim: float = 0.95,
) -> pd.DataFrame:
    """
    lower/upper_trim trim the lower and upper ratio of sentence times
    before correlation (to get rid of outliers)
    """

    # helper function
    def _trim_and_correlate(group_df: pd.DataFrame) -> float:
        # trim
        lower = group_df["sentence_time"].quantile(lower_trim)
        upper = group_df["sentence_time"].quantile(upper_trim)
        group_df = group_df.loc[
            (group_df["sentence_time"] > lower) & (group_df["sentence_time"] < upper)
        ]

        # correlate
        return group_df.corr().iloc[0, 1]  # type: ignore

    # get relevant variables
    sel = (pID_trialdata["phase"] == "story_reading") & (
        pID_trialdata["status"] == "ongoing"
    )

    spr = pID_trialdata.loc[sel.tolist()]
    spr_nchars = spr.loc[:, ["sentence_length", "sentence_time"]]
    # convert rows to int
    spr_nchars["sentence_length"] = spr_nchars["sentence_length"].astype(int)

    # trim and correlate
    spr_char_corrs = spr_nchars.groupby("participantID").apply(_trim_and_correlate)
    spr_char_corrs.name = "spr/char"
    # join dfs for output
    return pd.DataFrame(spr_char_corrs)


def get_story_read(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_story_read = pID_trialdata.loc[
        (pID_trialdata["question"] == "read_story"), ["answer"]
    ]
    pID_story_read.rename(columns={"answer": "read_story"}, inplace=True)
    return pID_story_read


def get_questionnaire_data(
    pID_trialdata: pd.DataFrame,
    q_keys: Dict[str, List[Tuple[str, str, str]]],
    condition: str,
) -> pd.DataFrame:
    q_results_all: List[pd.DataFrame] = list()
    colnames: List[str] = list()
    for phase, questions in q_keys.items():
        q_answers: List[pd.DataFrame] = list()
        for question, q_colname, num_or_str in questions:
            answer_df = pID_trialdata[
                (pID_trialdata["question"] == question)
                & (pID_trialdata["phase"] == phase)
            ][["answer"]]
            if answer_df.empty:
                print(
                    f"No entry for question; {question},"
                    f" q_colname: {q_colname}; {num_or_str}"
                )
                continue
            if num_or_str == "num":
                answer_df[q_colname] = pd.to_numeric(answer_df["answer"])
            elif num_or_str == "str":
                answer_df[q_colname] = answer_df["answer"]
            answer_df = answer_df.drop(columns="answer")

            colnames.append(question)
            q_answers.append(answer_df)

        if len(q_answers) == 0:
            # if everybody rated 1 for linger_rating, this would be true.
            continue
        # join into dataframe with pIDs
        pID_answers = q_answers[0].join(q_answers[1:])  # type: ignore

        # remove linebreaks
        pID_answers = pID_answers.map(
            lambda x: x.replace("\n", " ") if isinstance(x, str) else x
        )  # type: ignore

        # for transportation, compute summary stats
        if phase == "q_transportation":
            # compute transportation score without item Q5
            # (to distinguish lingering & transportation)
            pID_answers_no_Q5 = pID_answers.copy().drop(columns="tran_Q5")
            # compute transportation on all answers
            # (just to have it)
            pID_answers_all = pID_answers.copy()
            # compute the transportation score without Q5 and last two items
            # (because of bug in suppress condition)
            pID_answers_no_Q5_Q12_Q13 = pID_answers.copy().drop(
                columns=["tran_Q5", "tran_Q12", "tran_Q13"]
            )

            # add raw score column to output df
            if condition != "suppress":
                pID_answers["tran_raw"] = pID_answers_no_Q5.sum(axis=1)
                pID_answers["tran_raw_all"] = pID_answers_all.sum(axis=1)
            pID_answers["tran_raw_10"] = pID_answers_no_Q5_Q12_Q13.sum(axis=1)

            # add proportion score to output df
            if condition != "suppress":
                pID_answers["tran_prop"] = pID_answers["tran_raw"] / (
                    pID_answers_no_Q5.shape[-1] * 7
                )
                pID_answers["tran_prop_all"] = pID_answers["tran_raw_all"] / (
                    pID_answers_all.shape[-1] * 7
                )
            pID_answers["tran_prop_10"] = pID_answers["tran_raw_10"] / (
                pID_answers_no_Q5_Q12_Q13.shape[-1] * 7
            )

        q_results_all.append(pID_answers)

    # Merge the dfs
    pID_questionnaire = q_results_all[0].join(q_results_all[1:])  # type: ignore

    return pID_questionnaire


def get_mean_sr_rt(
    pID_timing_df: pd.DataFrame,
    ratings_dict: Dict[str, float],
    max_time: Optional[int] = None,
) -> Tuple[pd.Series, pd.Series]:
    def _rate_word(row: pd.Series) -> float:
        word = row["word_text"]
        if not isinstance(word, str):
            return np.nan
        word = word.lower().strip()
        try:
            rating = ratings_dict[word]
        except KeyError:
            rating = np.nan
        return rating

    if max_time is not None:
        pID_timing_df = pID_timing_df.loc[pID_timing_df["timestamp"] < max_time]
    pID_timing_df.loc[:, "story_relatedness"] = pID_timing_df.apply(_rate_word, axis=1)

    mean_sr = pID_timing_df["story_relatedness"].groupby("participantID").mean()
    mean_rt = pID_timing_df["word_time"].groupby("participantID").mean()

    return mean_sr, mean_rt
