from collections import defaultdict
from typing import Dict, List, Tuple, cast

import numpy as np
import pandas as pd


def get_comp_prop_carver_buddhika(
    pID_questiondata: pd.DataFrame,
    comprehension_keys: List[Tuple[str, str, str]],
    detailed: bool = False,
) -> pd.DataFrame:
    answers_dct: Dict[str, List[pd.DataFrame]] = defaultdict(list)
    for question, correct_answer, kind in comprehension_keys:
        answer_df = pID_questiondata[(pID_questiondata["Question"] == question)][
            ["Response"]
        ]
        # check for correctness
        answer_df[question] = answer_df["Response"] == correct_answer
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
        # return all data
        return pID_questionnaire
    # return overview columns
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


def get_time_away_buddhika(
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

    # time away in general
    pID_focusevents = pID_eventdata.loc[
        (pID_eventdata["event"] == "focus"), ["data", "timestamp"]
    ]
    pID_timeaway = pID_focusevents.groupby("participantID").apply(_time_away)

    # preparations for phase-specific time away
    pID_trialdata_eventdata = pd.concat([pID_trialdata, pID_eventdata])

    def _time_away_phase(group_df: pd.DataFrame) -> float:
        # cut off everything before and after phase
        phase_times = group_df.loc[group_df["phase"] == phase, ["timestamp"]]
        phase_start = phase_times.min().item()
        phase_end = phase_times.max().item()

        # all events within phase
        events_within_phase = group_df.loc[
            (group_df["timestamp"] >= phase_start)
            & (group_df["timestamp"] <= phase_end)
            & (group_df["event"] == "focus"),
            ["data", "timestamp"],
        ]

        if events_within_phase.empty:
            return 0.0
        return _time_away(events_within_phase).item()

    # time away for wcg
    phase = "fa1"
    pID_time_away_fa1 = pID_trialdata_eventdata.groupby("participantID").apply(
        _time_away_phase
    )
    phase = "fa2"
    pID_time_away_fa2 = pID_trialdata_eventdata.groupby("participantID").apply(
        _time_away_phase
    )
    pID_time_away_wcg = pID_time_away_fa1 + pID_time_away_fa2
    pID_time_away_wcg.name = "wcg time away (m)"

    # time away for spr
    phase = "spr"
    pID_time_away_spr = pID_trialdata_eventdata.groupby("participantID").apply(
        _time_away_phase
    )
    pID_time_away_spr.name = "spr time away (m)"

    # Join with base df
    pID_eventstats = pID_eventstats.join(
        [pID_timeaway, pID_off_events, pID_time_away_spr, pID_time_away_wcg]
    )
    pID_eventstats = pID_eventstats.drop(columns="event")

    # rename
    pID_eventstats = pID_eventstats.rename(
        columns={"data": "focusevents", "timestamp": "time away (m)"}
    )

    # replace NaNs with 0
    pID_eventstats.loc[pID_eventstats["time away (m)"].isna(), ["time away (m)"]] = 0
    pID_eventstats.loc[pID_eventstats["focusevents"].isna(), ["focusevents"]] = 0

    return pID_eventstats


def get_reaction_time_buddhika(
    pID_trialdata: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    def _word_submit_time_to_relative(group_df: pd.DataFrame) -> pd.Series:
        sorted_times = group_df.sort_values("word_submit_time")
        sorted_times.loc[:, "prev_word_submit_time"] = sorted_times.loc[
            :, "word_submit_time"
        ].shift()
        sorted_times.iloc[0, 1] = 0

        # relative time
        sorted_times.loc[:, "relative_word_submit_time"] = (
            sorted_times.loc[:, "word_submit_time"]
            - sorted_times.loc[:, "prev_word_submit_time"]
        )

        return sorted_times["relative_word_submit_time"]

    # pre
    pID_word_times_pre = pID_trialdata.loc[
        (pID_trialdata["phase"] == "fa1"),
        ["word_submit_time"],
    ]
    pID_relative_word_times_pre = cast(
        pd.Series,
        (
            pID_word_times_pre.groupby("participantID")
            .apply(_word_submit_time_to_relative)
            .reset_index(level=1, drop=True)
        ),
    )

    # post
    pID_word_times_post = pID_trialdata.loc[
        (pID_trialdata["phase"] == "fa2"),
        ["word_submit_time"],
    ]
    pID_relative_word_times_post = cast(
        pd.Series,
        (
            pID_word_times_post.groupby("participantID")
            .apply(_word_submit_time_to_relative)
            .reset_index(level=1, drop=True)
        ),
    )

    pID_relative_word_times = pd.concat(
        [pID_relative_word_times_pre, pID_relative_word_times_post]
    )

    pID_rt_means = pID_relative_word_times.groupby("participantID").mean()
    pID_rt_means = pID_rt_means.to_frame("rt_mean")
    pID_rt_max = pID_relative_word_times.groupby("participantID").max()
    pID_rt_max = pID_rt_max.to_frame("rt_max")

    return pID_rt_means, pID_rt_max


def get_spr_wcg_break_buddhika(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    times_spr_wcg = list()
    pIDs = list()
    for group_name, group_df in pID_trialdata.groupby("participantID"):
        end_spr = group_df.loc[
            (group_df["phase"] == "spr"),
            "timestamp",
        ].max()
        start_wcg = group_df.loc[
            (group_df["phase"] == "fa2"),
            "timestamp",
        ].min()

        times_spr_wcg.append(start_wcg - end_spr)
        pIDs.append(group_name)
    pID_spr_wcg_break = pd.DataFrame(
        data=times_spr_wcg, index=pIDs, columns=["spr-wcg-break"]
    )
    pID_spr_wcg_break.index.name = "participantID"

    return pID_spr_wcg_break


def get_spr_correlations_buddhika(
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
        lower = group_df["sprt"].quantile(lower_trim)
        upper = group_df["sprt"].quantile(upper_trim)
        group_df = group_df.loc[(group_df["sprt"] > lower) & (group_df["sprt"] < upper)]

        # correlate
        return group_df.corr().iloc[0, 1]  # type: ignore

    # get relevant variables
    sel = pID_trialdata["phase"] == "spr"

    spr = pID_trialdata.loc[sel.tolist()]
    spr_nchars = spr.loc[:, ["sentence_numchar", "sprt"]]
    # convert rows to int
    spr_nchars["sentence_numchar"] = spr_nchars["sentence_numchar"].astype(int)

    # for word_scrambled, remove probe trials
    if spr.columns.str.contains("trial_type").any():
        spr_nchars = spr_nchars.loc[~(spr["trial_type"] == "probe")]

    # trim and correlate
    spr_char_corrs = spr_nchars.groupby("participantID").apply(_trim_and_correlate)
    spr_char_corrs.name = "spr/char"
    # join dfs for output
    return pd.DataFrame(spr_char_corrs)


def get_story_read_buddhika(pID_questiondata: pd.DataFrame) -> pd.DataFrame:
    pID_story_read = pID_questiondata.loc[
        (pID_questiondata["Question"] == "content_read"), ["Response"]
    ]
    pID_story_read.rename(columns={"Response": "read_story"}, inplace=True)
    return pID_story_read


def get_questionnaire_data_buddhika(
    pID_questiondata: pd.DataFrame,
    q_keys: Dict[str, List[Tuple[str, str, str]]],
) -> pd.DataFrame:
    q_results_all: List[pd.DataFrame] = list()
    colnames: List[str] = list()
    for phase, questions in q_keys.items():
        q_answers: List[pd.DataFrame] = list()
        for question, q_colname, num_or_str in questions:
            answer_df = pID_questiondata[(pID_questiondata["Question"] == question)][
                ["Response"]
            ]
            if answer_df.empty:
                print(
                    f"No entry for question; {question}, q_colname: {q_colname};"
                    f" {num_or_str}"
                )
                continue
            if num_or_str == "num":
                answer_df[q_colname] = pd.to_numeric(answer_df["Response"])
            elif num_or_str == "str":
                answer_df[q_colname] = answer_df["Response"]
            answer_df = answer_df.drop(columns="Response")

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
        if phase == "transportation":
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
            pID_answers["tran_raw"] = pID_answers_no_Q5.sum(axis=1)
            pID_answers["tran_raw_all"] = pID_answers_all.sum(axis=1)
            pID_answers["tran_raw_10"] = pID_answers_no_Q5_Q12_Q13.sum(axis=1)

            # add proportion score to output df
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
