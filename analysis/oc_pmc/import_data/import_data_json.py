"""
This script imports data from an experiment folder into the ldata folder.
It assigns participants to exclusion groups, saves the results in the ldata folder,
and saves the results in the base folder.
"""

import os
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from oc_pmc import DATA_DIR, STUDYDATA_DIR, console
from oc_pmc.import_data.load_study_data_json import load_data_json
from oc_pmc.import_data.map_ids import mapIds
from oc_pmc.import_data.utils import (
    get_comp_prop_carver,
    get_comp_prop_dark_bedroom,
    get_comp_prop_interference_story,
    get_mean_sr_rt,
)
from oc_pmc.load import load_rated_words
from oc_pmc.utils import check_make_dirs, wordchains_to_ndarray


def _get_wcs_list(wc_df: pd.DataFrame) -> List:
    return [wc_df.index[0]] + wc_df["word_text"].tolist()


def get_wcs_df(pID_wcs: pd.DataFrame) -> pd.DataFrame:
    wcs_list = (
        pID_wcs.groupby("participantID", group_keys=False)
        .apply(_get_wcs_list)
        .to_list()
    )

    wcs_ndarray = wordchains_to_ndarray(wcs_list, pad_val="")
    colnames = ["ID"] + [f"word {i}" for i in range(wcs_ndarray.shape[-1] - 1)]
    wcs_df = pd.DataFrame(wcs_ndarray, columns=colnames)

    wcs_df = wcs_df.copy()

    # add cue
    cue_df = pd.DataFrame(
        ["" for _ in range(wcs_df.shape[0])],
        columns=["cue"],
        index=wcs_df.index,
    )
    wcs_df = cue_df.join(wcs_df)
    return wcs_df


def get_total_double_press(pID_trialdata: pd.DataFrame, position: str) -> pd.DataFrame:
    return pID_trialdata.loc[
        (pID_trialdata["phase"] == "wcg")
        & (pID_trialdata["pre_or_post"] == position)
        & (pID_trialdata["status"] == "ongoing")
        & (pID_trialdata["mode"] == "double_press")
        & (pID_trialdata["double_press"] == "total"),
        ["total_double_press_count"],
    ].astype(int)


def get_timing_df_json(
    trialdata: pd.DataFrame,
    position: str,
) -> pd.DataFrame:
    wcs_df = trialdata[
        (trialdata["stage"] == f"free_association_{position}")
        & (trialdata["task"] == "free_association")
    ]
    pID_wcs_df = wcs_df.set_index("participantID")

    group_timing_df_list: List[pd.DataFrame] = list()
    for group_ID, group_df in pID_wcs_df.groupby("participantID"):
        start_time = group_df.loc[
            (group_df["status"] == "task_begin"), "timestamp"
        ].item()

        group_wcs_df = group_df.loc[(group_df["status"] == "data")]
        group_wcs_df = group_wcs_df.copy()

        group_wcs_df.loc[:, "timestamp_absolute"] = group_wcs_df.loc[:, "timestamp"]
        group_wcs_df.loc[:, "timestamp"] = group_wcs_df.loc[:, "timestamp"] - start_time

        columns_to_extract = [
            "word_text",
            "word_count",
            "word_time",
            "word_key_onsets",
            "word_key_chars",
            "word_key_codes",
            "timestamp",
            "timestamp_absolute",
        ]

        group_timing_df = group_wcs_df.loc[
            :,
            columns_to_extract,
        ]

        # time to first key onset
        group_timing_df["key_onset"] = group_wcs_df["word_key_onsets"].apply(
            lambda lst: lst[0] if len(lst) > 0 else None
        )
        # time to first key onset since start of experiment
        group_timing_df.loc[:, "key_onset_timestamp"] = 0
        group_timing_df.iloc[
            1:, group_timing_df.columns.get_indexer(["key_onset_timestamp"])
        ] = group_timing_df["timestamp"].iloc[:-1].astype(int)
        group_timing_df.loc[:, "key_onset_timestamp"] += group_timing_df["key_onset"]

        group_timing_df_list.append(group_timing_df)

    pID_timing_df = pd.concat(group_timing_df_list, axis=0)
    pID_timing_df["word_count"] = pID_timing_df["word_count"].astype(int)
    pID_timing_df["word_time"] = pID_timing_df["word_time"].astype(int)
    return pID_timing_df


def get_questionnaire_data_json(
    pID_trialdata: pd.DataFrame,
    q_keys: Dict[str, List[Tuple[str, str, str]]],
) -> pd.DataFrame:
    q_results_all: List[pd.DataFrame] = list()
    colnames: List[str] = list()
    for phase, questions in q_keys.items():
        q_answers: List[pd.DataFrame] = list()
        for question, q_colname, num_or_str in questions:
            answer_df = pID_trialdata[
                (pID_trialdata["question"] == question)
                & (pID_trialdata["stage"] == phase)
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
                answer_df[q_colname] = answer_df["answer"].map(
                    lambda x: x.replace("\n", " ") if isinstance(x, str) else x
                )
            answer_df = answer_df.drop(columns="answer")

            colnames.append(question)
            q_answers.append(answer_df)

        if len(q_answers) == 0:
            # if everybody rated 1 for linger_rating, this would be true.
            continue
        # join into dataframe with pIDs
        pID_answers = q_answers[0].join(q_answers[1:])  # type: ignore

        # for transportation, compute summary stats
        if phase == "questionnaire_transportation":
            # compute transportation score without item Q5
            # (to distinguish lingering & transportation)
            pID_answers_no_Q5 = pID_answers.copy().drop(columns="tran_Q5")
            # compute transportation on all answers
            # (just to have it)
            pID_answers_all = pID_answers.copy()
            # compute the transportation score without Q3 and last two items
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

        # same for interference transportation
        if phase == "questionnaire_transportation_interference":
            # compute transportation score without item Q5
            # (to distinguish lingering & transportation)
            pID_answers_no_Q5 = pID_answers.copy().drop(columns="tran_interference_Q5")
            # compute transportation on all answers
            # (just to have it)
            pID_answers_all = pID_answers.copy()
            # compute the transportation score without Q3 and last two items
            # (because of bug in suppress condition)
            pID_answers_no_Q5_Q12_Q13 = pID_answers.copy().drop(
                columns=[
                    "tran_interference_Q5",
                    "tran_interference_Q12",
                    "tran_interference_Q13",
                ]
            )

            # add raw score column to output df
            pID_answers["tran_interference_raw"] = pID_answers_no_Q5.sum(axis=1)
            pID_answers["tran_interference_raw_all"] = pID_answers_all.sum(axis=1)
            pID_answers["tran_interference_raw_10"] = pID_answers_no_Q5_Q12_Q13.sum(
                axis=1
            )

            # add proportion score to output df
            pID_answers["tran_interference_prop"] = pID_answers[
                "tran_interference_raw"
            ] / (pID_answers_no_Q5.shape[-1] * 7)
            pID_answers["tran_interference_prop_all"] = pID_answers[
                "tran_interference_raw_all"
            ] / (pID_answers_all.shape[-1] * 7)
            pID_answers["tran_interference_prop_10"] = pID_answers[
                "tran_interference_raw_10"
            ] / (pID_answers_no_Q5_Q12_Q13.shape[-1] * 7)

        q_results_all.append(pID_answers)

    # Merge the dfs
    pID_questionnaire = q_results_all[0].join(q_results_all[1:])  # type: ignore

    return pID_questionnaire


def get_stage_timestamps_and_time(
    pID_trialdata: pd.DataFrame, condition: str
) -> pd.DataFrame:
    # phase == "stage"
    phase_timestamps_begin_long = pID_trialdata.loc[
        pID_trialdata["status"] == "stage_begin", ["stage", "timestamp"]
    ].reset_index()
    phase_timestamps_end_long = pID_trialdata.loc[
        pID_trialdata["status"] == "stage_end", ["stage", "timestamp"]
    ].reset_index()

    # also get task starts and ends

    if "iteration" not in pID_trialdata.columns:
        task_timestamps_begin_long = pID_trialdata.loc[
            pID_trialdata["status"] == "task_begin", ["stage", "timestamp"]
        ].reset_index()
        task_timestamps_end_long = pID_trialdata.loc[
            pID_trialdata["status"] == "task_end", ["stage", "timestamp"]
        ].reset_index()
    else:
        # some tasks potentially were repeated (e.g. tom training)
        # need to make them unique to get their start/end times.
        task_timestamps_begin_long = pID_trialdata.loc[
            pID_trialdata["status"] == "task_begin", ["stage", "timestamp", "iteration"]
        ].reset_index()
        task_timestamps_end_long = pID_trialdata.loc[
            pID_trialdata["status"] == "task_end", ["stage", "timestamp", "iteration"]
        ].reset_index()

        # need to handle repeated tasks (e.g. tom_training)
        task_timestamps_begin_long["stage_amend"] = ""
        task_timestamps_end_long["stage_amend"] = ""

        task_timestamps_begin_long.loc[
            ~task_timestamps_begin_long["iteration"].isna(), "stage_amend"
        ] = (
            task_timestamps_begin_long.loc[
                ~task_timestamps_begin_long["iteration"].isna(), "iteration"
            ]
            .astype(int)
            .astype(str)
        )
        task_timestamps_end_long.loc[
            ~task_timestamps_end_long["iteration"].isna(), "stage_amend"
        ] = (
            task_timestamps_end_long.loc[
                ~task_timestamps_end_long["iteration"].isna(), "iteration"
            ]
            .astype(int)
            .astype(str)
        )

        task_timestamps_begin_long["stage"] = (
            task_timestamps_begin_long["stage"]
            + task_timestamps_begin_long["stage_amend"]
        )
        task_timestamps_end_long["stage"] = (
            task_timestamps_end_long["stage"] + task_timestamps_end_long["stage_amend"]
        )

        # Data collection for interference-pause-end contains identical
        # task, status, iteration pairs (because 5s, 10s iteration).
        # Need to handle it (by removing the tasks, other options are viable too)
        if condition in ["interference_end_pause", "interference_pause"]:
            task_timestamps_begin_long = task_timestamps_begin_long.drop_duplicates(
                ["participantID", "stage"]
            )
            task_timestamps_end_long = task_timestamps_end_long.drop_duplicates(
                ["participantID", "stage"]
            )

    phase_ends_beginnings_long = phase_timestamps_end_long.merge(
        phase_timestamps_begin_long,
        on=["participantID", "stage"],
        suffixes=("_end", "_begin"),
    )

    phase_ends_beginnings_long["time"] = (
        phase_ends_beginnings_long["timestamp_end"]
        - phase_ends_beginnings_long["timestamp_begin"]
    )

    phase_times_long = phase_ends_beginnings_long.loc[
        :, ["participantID", "stage", "time"]
    ]

    # convert to wide format
    phase_timestamps_begin = pd.pivot(
        phase_timestamps_begin_long,
        index="participantID",
        columns="stage",
        values="timestamp",
    )
    phase_timestamps_end = pd.pivot(
        phase_timestamps_end_long,
        index="participantID",
        columns="stage",
        values="timestamp",
    )
    phase_times = pd.pivot(
        phase_times_long,
        index="participantID",
        columns="stage",
        values="time",
    )

    task_timestamps_begin = pd.pivot(
        task_timestamps_begin_long,
        index="participantID",
        columns="stage",
        values="timestamp",
    )
    task_timestamps_end = pd.pivot(
        task_timestamps_end_long,
        index="participantID",
        columns="stage",
        values="timestamp",
    )

    # rename columns & join
    phase_times = phase_times.rename(
        columns={col: f"{col}_time" for col in phase_times.columns}
    )
    phase_timestamps = phase_timestamps_begin.join(
        phase_timestamps_end, lsuffix="_stage_start", rsuffix="_stage_end"
    )
    task_timestamps = task_timestamps_begin.join(
        task_timestamps_end, lsuffix="_task_start", rsuffix="_task_end"
    )
    phase_timestamps_and_time = phase_timestamps.join([phase_times, task_timestamps])

    return phase_timestamps_and_time


def get_spr_correlations(
    pID_trialdata: pd.DataFrame,
    lower_trim: float = 0.05,
    upper_trim: float = 0.95,
    stage_filter: Optional[str] = None,
    task_filter: Optional[str] = None,
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

    # get relevant rows
    if task_filter is None:
        task_filter = "reading"

    if stage_filter is not None:
        sel = (
            (pID_trialdata["stage"] == stage_filter)
            & (pID_trialdata["task"] == task_filter)
            & (pID_trialdata["status"] == "ongoing")
        )
    else:
        sel = (pID_trialdata["task"] == task_filter) & (
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


def get_time_away(
    pID_eventdata: pd.DataFrame,
    pID_trialdata: pd.DataFrame,
    main_experiment_stages: List[str],
) -> pd.DataFrame:
    # Special case, nobody focussed out of the window
    if not any(pID_eventdata["event_type"] == "window_focus_out"):
        # get index, colnames and 0 data
        index = pID_eventdata.index.unique()
        # TODO: should be there for all stage_names
        colnames = [f"time_away_{stage_name}" for stage_name in main_experiment_stages]
        zero_data = np.zeros((len(index), len(colnames)))
        return pd.DataFrame(
            data=zero_data,
            index=index,
            columns=colnames,
        )

    # get all phases
    pID_phase_time_away_base = (
        pID_trialdata.loc[:, ["stage", "timestamp"]]
        .groupby(["participantID", "stage"])
        .first()
    ).reset_index()

    # get the time away in each phase
    pID_time_away = pID_eventdata.loc[
        (pID_eventdata["event_type"] == "window_focus_on")
        & (~pd.isna(pID_eventdata["off_focus_time"])),
        ["stage", "off_focus_time"],
    ].reset_index()

    # merge time away with phases
    pID_phase_time_away = pID_phase_time_away_base.merge(
        pID_time_away, how="left", on=["participantID", "stage"]
    ).loc[:, ["participantID", "stage", "off_focus_time"]]

    # replace nans with 0
    pID_phase_time_away.loc[
        pID_phase_time_away["off_focus_time"].isna(), "off_focus_time"
    ] = 0

    # add potential multiple off_focus_events in one phase
    pID_phase_time_away = (
        pID_phase_time_away.groupby(["participantID", "stage"]).sum().reset_index()
    )

    # pivot to wide format
    pID_phase_time_away = pID_phase_time_away.pivot(
        index="participantID", columns="stage", values="off_focus_time"
    )

    # rename columns
    new_columns = {col: f"time_away_{col}" for col in pID_phase_time_away.columns}
    pID_phase_time_away.rename(columns=new_columns, inplace=True)

    return pID_phase_time_away


def get_reaction_time(
    pID_trialdata: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # TODO: need to deal with bug where participants have no pre or post data
    # -> separate pre and post

    pID_word_time_pre = pID_trialdata.loc[
        (pID_trialdata["task"] == "free_association")
        & (pID_trialdata["status"] == "data")
        & (pID_trialdata["stage"] == "free_association_pre"),
        ["word_time"],
    ]

    pID_word_time_post = pID_trialdata.loc[
        (pID_trialdata["task"] == "free_association")
        & (pID_trialdata["status"] == "data")
        & (pID_trialdata["stage"] == "free_association_post"),
        ["word_time"],
    ]

    pID_rt_means_pre = pID_word_time_pre.groupby("participantID").mean()
    pID_rt_means_post = pID_word_time_post.groupby("participantID").mean()
    pID_rt_max_pre = pID_word_time_pre.groupby("participantID").max()
    pID_rt_max_post = pID_word_time_post.groupby("participantID").max()

    pID_empty = pd.DataFrame(index=pID_trialdata.index.copy())

    pID_rt_means_pre_merged = pd.merge(
        pID_empty, pID_rt_means_pre, "left", left_index=True, right_index=True
    )
    pID_rt_means_post_merged = pd.merge(
        pID_empty, pID_rt_means_post, "left", left_index=True, right_index=True
    )
    pID_rt_max_pre_merged = pd.merge(
        pID_empty, pID_rt_max_pre, "left", left_index=True, right_index=True
    )
    pID_rt_max_post_merged = pd.merge(
        pID_empty, pID_rt_max_post, "left", left_index=True, right_index=True
    )

    # replace nans
    # really can only happen if a participant did not submit a single word during FA
    if pID_rt_means_pre_merged["word_time"].isna().any():
        console.print(
            "Import: word_time; Pre participant means, replacing"
            f"{pID_rt_means_pre_merged['word_time'].isna().sum()} nans",
            style="red",
        )
        pID_rt_means_pre_merged["word_time"].fillna(180000, inplace=True)
    if pID_rt_means_post_merged["word_time"].isna().any():
        console.print(
            "Import: word_time; Pre participant means, replacing"
            f"{pID_rt_means_post_merged['word_time'].isna().sum()} nans",
            style="red",
        )
        pID_rt_means_post_merged["word_time"].fillna(180000, inplace=True)
    if pID_rt_max_pre_merged["word_time"].isna().any():
        console.print(
            "Import: word_time; Pre participant means, replacing"
            f"{pID_rt_max_pre_merged['word_time'].isna().sum()} nans",
            style="red",
        )
        pID_rt_max_pre_merged["word_time"].fillna(180000, inplace=True)
    if pID_rt_max_post_merged["word_time"].isna().any():
        console.print(
            "Import: word_time; Pre participant means, replacing"
            f"{pID_rt_max_post_merged['word_time'].isna().sum()} nans",
            style="red",
        )
        pID_rt_max_post_merged["word_time"].fillna(180000, inplace=True)

    # not the technical accurate mean, the phase with less words will
    # be overweighted.
    pID_rt_means = (
        pd.concat([pID_rt_means_pre_merged, pID_rt_means_post_merged])
        .groupby("participantID")
        .mean()
    )
    pID_rt_max_post = pID_rt_max_post_merged.groupby("participantID").max()
    pID_rt_max = (
        pd.concat(
            [
                pID_rt_max_pre_merged,
                pID_rt_max_post_merged,
            ]
        )
        .groupby("participantID")
        .max()
    )
    pID_rt_means.rename(columns={"word_time": "rt_mean"}, inplace=True)
    pID_rt_max.rename(columns={"word_time": "rt_max"}, inplace=True)
    pID_rt_max_post.rename(columns={"word_time": "rt_max_post"}, inplace=True)

    return pID_rt_means, pID_rt_max, pID_rt_max_post


def get_spr_wcg_break(
    pID_trialdata: pd.DataFrame,
    start_stage_filter: Optional[str] = None,
    start_task_filter: Optional[str] = None,
) -> pd.DataFrame:
    times_spr_wcg = list()
    pIDs = list()

    if start_task_filter is None:
        start_task_filter = "reading"

    for group_name, group_df in pID_trialdata.groupby("participantID"):
        if start_stage_filter is not None:
            end_start_stage = group_df.loc[
                (group_df["stage"] == start_stage_filter)
                & (group_df["task"] == start_task_filter)
                & (group_df["status"] == "task_end"),
                "timestamp",
            ].iloc[0]
        else:
            end_start_stage = group_df.loc[
                (group_df["task"] == start_task_filter)
                & (group_df["status"] == "task_end"),
                "timestamp",
            ].iloc[0]
        # TODO
        start_wcg = group_df.loc[
            (group_df["stage"] == "free_association_post")
            & (group_df["task"] == "free_association")
            & (group_df["status"] == "task_begin"),
            "timestamp",
        ].iloc[0]

        times_spr_wcg.append(start_wcg - end_start_stage)
        pIDs.append(group_name)
    pID_spr_wcg_break = pd.DataFrame(data=times_spr_wcg, index=pIDs, columns=["time"])
    pID_spr_wcg_break.index.name = "participantID"
    pID_spr_wcg_break.rename(columns={"time": "spr-wcg-break"}, inplace=True)

    return pID_spr_wcg_break


def get_attention_check(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_attention_check = pID_trialdata.loc[
        (pID_trialdata["question"] == "demographics_attncheck"), ["answer"]
    ]
    pID_attention_check.rename(columns={"answer": "attncheck"}, inplace=True)
    pID_attention_check = pID_attention_check[
        ~pID_attention_check.index.duplicated(keep="last")
    ]
    return pID_attention_check


def get_story_read(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_story_read = pID_trialdata.loc[
        (pID_trialdata["question"] == "read_story"), ["answer"]
    ]
    pID_story_read.rename(columns={"answer": "read_story"}, inplace=True)
    return pID_story_read


def get_exp_time_away(
    pID_time_away: pd.DataFrame,
    main_experiment_stages: List[str],
) -> pd.DataFrame:
    """Return time away in the main phases of the experiment."""

    colnames = [f"time_away_{stage}" for stage in main_experiment_stages]

    # add columns together
    pID_exp_time_away = pID_time_away.loc[:, colnames].sum(axis=1)
    pID_exp_time_away.name = "exp_time_away"

    return pID_exp_time_away.to_frame()


def get_focusevents(
    pID_eventdata: pd.DataFrame,
    main_experiment_stages: List[str],
) -> pd.DataFrame:
    """Return the amount of focusevents during main experiment stages."""

    # baseframe
    pID_focusevents = pd.DataFrame(index=pID_eventdata.index.unique())

    selector = (pID_eventdata["stage"].isin(main_experiment_stages)) & (
        pID_eventdata["event_type"] == "window_focus_out"
    )
    pID_focusevents_se = (
        pID_eventdata.loc[selector, "timestamp"].groupby("participantID").count()
    )
    pID_focusevents["focusevents"] = pID_focusevents_se
    pID_focusevents.fillna({"focusevents": 0}, inplace=True)
    pID_focusevents = pID_focusevents.astype(int)

    return pID_focusevents


def get_spr_max(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_spr_max = pd.DataFrame(index=pID_trialdata.index.unique())
    selector = (pID_trialdata["stage"] == "reading") & (
        pID_trialdata["status"] == "ongoing"
    )
    pID_spr_max_se = (
        pID_trialdata.loc[selector, "sentence_time"].groupby("participantID").max()
    )
    pID_spr_max["spr_max"] = pID_spr_max_se
    return pID_spr_max


def get_time_unpressed(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    time_unpressed_df = pID_trialdata.loc[
        (pID_trialdata["stage"] == "interference_pause_testing")
        & (pID_trialdata["status"] == "task_end"),
        ["time_unpressed", "time_unpressed_start"],
    ].astype(int)
    time_unpressed_df["time_unpressed"] = (
        time_unpressed_df["time_unpressed"] + time_unpressed_df["time_unpressed_start"]
    )
    time_unpressed_df.drop(columns="time_unpressed_start", inplace=True)
    return time_unpressed_df


def get_interference_correct(
    pID_trialdata: pd.DataFrame,
    interference_answers: List[Tuple[str, int, str]],
) -> pd.DataFrame:
    # interference_answers: [(stage_name, question_index, correct_answer),...]
    interference_correct_df = pd.DataFrame(index=pID_trialdata.index.unique().copy())
    interference_correct_df["interference_correct"] = False
    interference_correct_df["question_index"] = np.nan

    for interference_answer in interference_answers:
        interference_correct_sr = (
            pID_trialdata.loc[
                (pID_trialdata["stage"] == interference_answer[0])
                & (pID_trialdata["status"] == "ongoing")
                & (pID_trialdata["question_index"] == interference_answer[1]),
                "answer",
            ]
            == interference_answer[2]
        )
        interference_correct_df.loc[
            interference_correct_sr.index.to_list(), "interference_correct"
        ] = interference_correct_sr
        interference_correct_df.loc[
            interference_correct_sr.index.to_list(), "question_index"
        ] = interference_answer[1]

    return interference_correct_df


def get_spr_task_time(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_start_time = pID_trialdata.loc[
        (pID_trialdata["task"] == "reading")
        & (pID_trialdata["status"] == "task_begin"),
        ["timestamp"],
    ]
    pID_end_time = pID_trialdata.loc[
        (pID_trialdata["task"] == "reading") & (pID_trialdata["status"] == "task_end"),
        ["timestamp"],
    ]

    pID_start_end_time = pID_start_time.join(
        pID_end_time, lsuffix="_start", rsuffix="_end"
    )
    pID_start_end_time["spr_time"] = (
        pID_start_end_time["timestamp_end"] - pID_start_end_time["timestamp_start"]
    )

    return pID_start_end_time.loc[:, ["spr_time"]]


def get_sentence_time_spr_data(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "trial_index",
        "timestamp",
        "sentence_length",
        "sentence_text",
        "sentence_time",
    ]
    pID_time_spr = pID_trialdata.loc[
        (pID_trialdata["stage"] == "reading") & (pID_trialdata["status"] == "ongoing"),
        columns,
    ]
    pID_time_spr.rename(
        columns={
            "trial_index": "Trial",
            "timestamp": "Timestamp",
            "sentence_length": "char_count",
            "sentence_text": "sentence",
            "sentence_time": "sprt",
        },
        inplace=True,
    )
    return pID_time_spr


def get_missing_sentence_pIDs(
    trialdata: pd.DataFrame, story: str, condition: Optional[str] = None
) -> list[str]:
    """Returns participants who were not shown all sentences for some reason."""

    n_sentences = 269
    if condition == "interference_end_pause":
        n_sentences = 270

    missing_sentences_pIDs = list()
    if story == "carver_original":
        pID_n_sentences = trialdata.groupby("participantID").apply(
            lambda row: (
                (row["stage"] == "reading") & (row["status"] == "ongoing")
            ).sum()
        )
        pID_missing_sentences = pID_n_sentences != n_sentences

        if pID_missing_sentences.any():
            missing_sentences_pIDs = pID_missing_sentences.index[
                pID_missing_sentences
            ].to_list()
            console.print(
                f"Removing participants missing sentences:  {missing_sentences_pIDs}",
                style="red",
            )

    return missing_sentences_pIDs


def get_missing_fa_pIDS(trialdata: pd.DataFrame) -> list[str]:
    fa_pre = trialdata.loc[
        (trialdata["stage"] == "free_association_pre") & (trialdata["status"] == "data")
    ]
    fa_post = trialdata.loc[
        (trialdata["stage"] == "free_association_post")
        & (trialdata["status"] == "data")
    ]
    pIDs_missing_fa_pre = set(trialdata["participantID"].unique()).difference(
        set(fa_pre["participantID"].unique())
    )
    pIDs_missing_fa_post = set(trialdata["participantID"].unique()).difference(
        set(fa_post["participantID"].unique())
    )

    if len(pIDs_missing_fa_pre) > 0:
        console.print(
            f"Removing participants missing FA pre:  {list(pIDs_missing_fa_pre)}",
            style="red",
        )
    if len(pIDs_missing_fa_post) > 0:
        console.print(
            f"Removing participants missing FA post:  {list(pIDs_missing_fa_post)}",
            style="red",
        )

    if fa_pre["word_time"].isna().any():
        pIDs_word_time_na_pre = fa_pre.loc[fa_pre["word_time"].isna()].index.unique()
        console.print(
            f"Warning: FA pre: NA values word submission time for"
            f" {pIDs_word_time_na_pre}",
            style="red",
        )
    if fa_post["word_time"].isna().any():
        pIDs_word_time_na_post = fa_post.loc[fa_post["word_time"].isna()].index.unique()
        console.print(
            f"Warning: FA pre: NA values word submission time for"
            f" {pIDs_word_time_na_post}",
            style="red",
        )

    return [*list(pIDs_missing_fa_post), *list(pIDs_missing_fa_pre)]


def print_stage_times(pID_stage_times: pd.DataFrame):
    stage_time_names = [
        name for name in pID_stage_times.columns if name.endswith("_time")
    ]
    max_len = max(map(len, stage_time_names))
    console.print("Stage Times (pre-excluded)", style="yellow")
    for stage_time_name in stage_time_names:
        stage_time_mean = (pID_stage_times[stage_time_name] / 1000).mean()
        stage_time_std = (pID_stage_times[stage_time_name] / 1000).std()
        stage_time_mean_min = stage_time_mean / 60

        whitespaces = " " * (max_len - len(stage_time_name))
        print(
            f"{stage_time_name}{whitespaces} | {round(stage_time_mean, 2):6.2f}s"
            f" ({round(stage_time_std, 2):6.2f})"
            f" | {round(stage_time_mean_min, 2):6.2f}m"
        )


def import_data_json(
    study_name_or_data_dir: str,
    q_keys: Dict[str, List[Tuple[str, str, str]]],
    main_experiment_stages: List[str],
    data_dir: Optional[str] = None,
    filter_condition: Optional[Union[str, Tuple[str, str]]] = None,
    ratings: Optional[Dict[str, str]] = None,
    interference_answers: Optional[Union[List[Tuple[str, int, str]], str]] = None,
):
    """Imports data in the json format (e.g. psyserver) into ldata.

    Parameters
    ----------
    study_name_or_data_dir: str
        Name for study or directory for study. If only name is given, will attempt to
        locate study name in directory given by STUDYDATA_DIR in the .env
    q_keys: Dict[str, List[Tuple[str, str, str]]]
        Dictionary with stagenames and respective questionnaire keys,
        their name in the output table and their type (num or str).
    main_experiment_stages: List[str]
        List of stages over which time_away and focusevenets are computed.
    data_dir: str, default=None
        Root data dir to export files to. Also set in .env
    filter_condition: str, default=None
        Condition name which to filter for. For example, a data_dir may
        contain multiple experiments ["intact", "suppress"], then you can filter
        for "suppress".
        If True,  rather than the standard
        csv data loader (psiturk format).
    ratings: Dict, default=None
        Dict specifying, approach, model, story and file of ratings.
        e.g. dict(
            approach="human", model="moment",story="carver_original",file="all.csv"
        ),
    interference_answers: List[Tuple[str, int, str]], default=None
        List with Tuples specifying (stage_name, question_index, correct_answer)
    """
    if data_dir is None:
        data_dir = DATA_DIR

    if not os.path.exists(study_name_or_data_dir):
        study_data_dir = os.path.join(STUDYDATA_DIR, study_name_or_data_dir)
        if not os.path.exists(study_data_dir):
            raise ValueError(
                f"'{study_name_or_data_dir}' is neither an existing path nor can"
                f" be found in STUDYDATA_DIR: {study_data_dir}"
            )
    else:
        study_data_dir = study_name_or_data_dir

    trialdata, eventdata, story, condition = load_data_json(
        study_data_dir, filter_condition
    )

    if trialdata.empty:
        print("No participant data. Aborting.")
        return False

    # Sanity checks
    missing_sentence_pIDs = get_missing_sentence_pIDs(trialdata, story, condition)
    missing_fa_pIDs = get_missing_fa_pIDS(trialdata)

    missing_something = [*missing_sentence_pIDs, *missing_fa_pIDs]
    if len(missing_something) > 0:
        trialdata = trialdata.loc[~trialdata["participantID"].isin(missing_something)]

    # Map ids for anonymization
    pIDs = trialdata["participantID"].unique().tolist()
    mapped_pIDs, mapping = mapIds(study_data_dir=study_data_dir, ids=pIDs)
    trialdata["participantID"] = trialdata["participantID"].map(mapping)
    eventdata["participantID"] = eventdata["participantID"].map(mapping)

    # convert
    pID_trialdata = trialdata.set_index("participantID")
    pID_eventdata = eventdata.set_index("participantID")

    print(f"Importing {study_data_dir} to {data_dir} as {story}/{condition}")

    # 8. Focus events
    pID_focusevents = get_focusevents(pID_eventdata, main_experiment_stages)

    # A) word chains post/pre/practice
    wcs_post = trialdata[
        (trialdata["stage"] == "free_association_post")
        & (trialdata["status"] == "data")
    ]
    pID_wcs_post = wcs_post.set_index("participantID")
    wcs_pre = trialdata[
        (trialdata["stage"] == "free_association_pre") & (trialdata["status"] == "data")
    ]
    pID_wcs_pre = wcs_pre.set_index("participantID")

    wcs_df_post = get_wcs_df(pID_wcs_post)
    wcs_df_pre = get_wcs_df(pID_wcs_pre)

    # B) comprehension data
    if story == "dark_bedroom":
        pID_comprehension = get_comp_prop_dark_bedroom(pID_trialdata, detailed=True)
    else:
        pID_comprehension = get_comp_prop_carver(pID_trialdata, detailed=True)

    # C) Demographics/Experience/Transportation/Open questionnaires
    pID_questionnaire = get_questionnaire_data_json(pID_trialdata, q_keys=q_keys)

    # D) Word-by-word format (timing data)
    pID_timing_post_df = get_timing_df_json(trialdata=trialdata, position="post")
    pID_timing_pre_df = get_timing_df_json(trialdata=trialdata, position="pre")

    # F) Stage times
    # do not require stage_keys
    pID_stage_times = get_stage_timestamps_and_time(pID_trialdata, condition)

    # spr time is different from the stage times: stage times include the instructions
    pID_spr_time = get_spr_task_time(pID_trialdata)

    # Additionally, get exclusion data
    # 1. Correlation reading time and characters
    pID_spr_char_corr = get_spr_correlations(pID_trialdata)

    # 2. Time away
    pID_time_away = get_time_away(pID_eventdata, pID_trialdata, main_experiment_stages)

    # 3. Average/ 4. Max reaction time
    pID_rt_mean, pID_rt_max, pID_rt_max_post = get_reaction_time(pID_trialdata)

    # 5. Break between spr & FA2
    pID_spr_wcg_break = get_spr_wcg_break(pID_trialdata)

    # 6. Attention check
    pID_attention_check = get_attention_check(pID_trialdata)

    # 7. Experiment time away
    # (start free association until submission before demographics questionnaire)
    pID_exp_time_away = get_exp_time_away(pID_time_away, main_experiment_stages)

    # 8. Focus events
    pID_focusevents = get_focusevents(pID_eventdata, main_experiment_stages)

    # 8.1 Max spr time
    pID_spr_max = get_spr_max(pID_trialdata)

    # Merge summary data
    pID_summary = pID_comprehension.join(
        [
            pID_questionnaire,
            pID_exp_time_away,
            pID_stage_times,
            pID_spr_time,
            pID_spr_char_corr,
            pID_spr_wcg_break,
            pID_rt_max,
            pID_rt_max_post,
            pID_rt_mean,
            pID_time_away,
            pID_attention_check,
            pID_focusevents,
            pID_spr_max,
        ]
    )

    # 9.1 (interference pause) button not held
    if condition in ["interference_pause", "interference_end_pause"]:
        pID_time_unpressed = get_time_unpressed(pID_trialdata)
        pID_summary = pID_summary.join(pID_time_unpressed)

    # 9.2 (interference_story) comprehension
    if condition in ["interference_story", "interference_story_control"]:
        pID_comprehension_interference_story = get_comp_prop_interference_story(
            pID_trialdata
        )
        pID_summary = pID_summary.join(
            pID_comprehension_interference_story, rsuffix="_interference"
        )

    # 9.3 (fa-dark-bedroom) keywords (theme words)
    if "questionnaire_keywords" in pID_trialdata["stage"].unique():
        theme_words_base_path = os.path.join(data_dir, "theme_words", story)
        theme_words_raw_path = os.path.join(
            theme_words_base_path, "theme_words_raw.csv"
        )
        selector = (pID_trialdata["stage"] == "questionnaire_keywords") & (
            pID_trialdata["status"] == "ongoing"
        )
        theme_words_df = pID_trialdata.loc[selector, ["answer"]]
        check_make_dirs(theme_words_raw_path)
        # cannot save theme words directly, have to take exclusions into account.
        theme_words_df.to_csv(theme_words_raw_path, header=True, index=True)

    # 9.4 (interference_story_spr -> interference=dark_bedroom)
    if condition in [
        "interference_story_spr",
        "interference_story_spr_end_continued",
        "interference_story_spr_end_separated",
        "interference_story_spr_end_delayed_continued",
        "interference_story_spr_end_continued_opr",
        "interference_story_spr_end_separated_opr",
        "interference_story_spr_end_delayed_continued_opr",
    ]:
        # get comprehension
        pID_comprehension_interference_story = get_comp_prop_dark_bedroom(
            pID_trialdata, interference=True
        )
        # get spr/char correlation
        pID_spr_char_corr_interference = get_spr_correlations(
            pID_trialdata,
            stage_filter="interference_reading_testing",
            task_filter="interference_reading",
        )
        # break between story 3 reading and FA2
        pID_spr_wcg_break = get_spr_wcg_break(
            pID_trialdata,
            start_stage_filter="interference_reading_testing",
            start_task_filter="interference_reading",
        )
        pID_summary = pID_summary.join(
            pID_comprehension_interference_story,
            rsuffix="_interference",
        )
        pID_summary = pID_summary.join(
            pID_spr_char_corr_interference,
            rsuffix="_interference",
        )
        pID_summary = pID_summary.join(pID_spr_wcg_break, rsuffix="_interference")

    # 10. add mean sr, mean rt questionnaire data
    if ratings is not None:
        ratings_dict = load_rated_words(ratings)
        mean_sr_post, mean_rt_post = get_mean_sr_rt(pID_timing_post_df, ratings_dict)
        mean_sr_pre, mean_rt_pre = get_mean_sr_rt(pID_timing_pre_df, ratings_dict)
        mean_sr_30s_post, mean_rt_30s_post = get_mean_sr_rt(
            pID_timing_post_df, ratings_dict, max_time=30000
        )
        mean_sr_30s_pre, mean_rt_30s_pre = get_mean_sr_rt(
            pID_timing_pre_df, ratings_dict, max_time=30000
        )
        pID_summary["mean_sr_post"] = mean_sr_post
        pID_summary["mean_sr_pre"] = mean_sr_pre
        pID_summary["mean_rt_post"] = mean_rt_post
        pID_summary["mean_rt_pre"] = mean_rt_pre
        pID_summary["mean_sr_30s_post"] = mean_sr_30s_post
        pID_summary["mean_sr_30s_pre"] = mean_sr_30s_pre
        pID_summary["mean_rt_30s_post"] = mean_rt_30s_post
        pID_summary["mean_rt_30s_pre"] = mean_rt_30s_pre

    if interference_answers is not None:
        if isinstance(interference_answers, list):
            # tom, situation
            pID_interference_correct = get_interference_correct(
                pID_trialdata, interference_answers
            )
        else:
            # geometry
            pID_interference_correct = pID_trialdata.loc[
                (pID_trialdata["stage"] == "interference_geometry_testing")
                & (pID_trialdata["mode"] == "question"),
                ["answer", "correct_answer", "answered_correct", "answer_time"],
            ]
        pID_summary = pID_summary.join(pID_interference_correct)

    # 12. time spr data (sentence by sentence data)
    pID_sentence_time_spr = get_sentence_time_spr_data(pID_trialdata)

    # Print time info on pre-excluded data
    print_stage_times(pID_stage_times)

    # Now save files
    # A) word chains pre/post
    wordchain_dir = os.path.join(data_dir, "wordchains", story, condition)
    wordchain_post_path = os.path.join(wordchain_dir, "post.csv")
    check_make_dirs(wordchain_post_path)
    wcs_df_post.to_csv(
        wordchain_post_path,
        header=True,
        index=True,
    )
    print(f"Saved {wordchain_post_path}")
    wordchain_pre_path = os.path.join(wordchain_dir, "pre.csv")
    wcs_df_pre.to_csv(
        wordchain_pre_path,
        header=True,
        index=True,
    )
    print(f"Saved {wordchain_pre_path}")

    # B & C) all questionnaire data
    questionnaires_path = os.path.join(
        data_dir, "questionnaires", story, condition, "summary.csv"
    )
    check_make_dirs(questionnaires_path)
    pID_summary.to_csv(
        questionnaires_path,
        header=True,
        index=True,
    )
    print(f"Saved {questionnaires_path}")

    # D) Word-by-word format (timing data)
    timing_dir = os.path.join(data_dir, "time_words", story, condition)
    timing_post_path = os.path.join(timing_dir, "post.csv")
    check_make_dirs(timing_post_path)
    pID_timing_post_df.to_csv(
        timing_post_path,
        header=True,
        index=True,
    )
    print(f"Saved {timing_post_path}")
    timing_pre_path = os.path.join(timing_dir, "pre.csv")
    pID_timing_pre_df.to_csv(
        timing_pre_path,
        header=True,
        index=True,
    )
    print(f"Saved {timing_pre_path}")

    # E) Self-paced reading times
    time_spr_path = os.path.join(data_dir, "time_spr", story, condition, "spr.csv")
    check_make_dirs(time_spr_path)
    pID_sentence_time_spr.to_csv(
        time_spr_path,
        header=True,
        index=True,
    )
    print(f"Saved {time_spr_path}")

    return True
