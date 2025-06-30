"""
This script imports data from an experiment folder into the ldata folder.
It assigns participants to exclusion groups, saves the results in the ldata folder,
and saves the results in the base folder.
"""

import os
from typing import Dict, List, Optional, Tuple

import pandas as pd
from oc_pmc import DATA_DIR, STUDYDATA_LEGACY_DIR
from oc_pmc.import_data.load_study_data import load_data
from oc_pmc.import_data.map_ids import mapIds
from oc_pmc.import_data.utils import (
    get_comp_prop_carver,
    get_comp_prop_davis,
    get_mean_sr_rt,
    get_questionnaire_data,
)
from oc_pmc.load import load_rated_words
from oc_pmc.utils import check_make_dirs, wordchains_to_ndarray

from .utils import (
    get_attention_check,
    get_exp_time_away,
    get_reaction_time,
    get_spr_correlations,
    get_spr_wcg_break,
    get_time_away,
)


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


def get_timing_df(
    trialdata: pd.DataFrame,
    position: str,
    is_double_press=False,
) -> pd.DataFrame:
    wcs_df = trialdata[
        (trialdata["phase"] == "wcg") & (trialdata["pre_or_post"] == position)
    ]
    pID_wcs_df = wcs_df.set_index("participantID")

    group_timing_df_list: List[pd.DataFrame] = list()
    for group_ID, group_df in pID_wcs_df.groupby("participantID"):
        start_time = group_df.loc[(group_df["status"] == "begin"), "timestamp"].item()

        if is_double_press:
            group_wcs_df = group_df.loc[
                (group_df["status"] == "ongoing") & (group_df["mode"] == "word")
            ]
        else:
            group_wcs_df = group_df.loc[(group_df["status"] == "ongoing")]
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
        # button press experiments
        if is_double_press:
            columns_to_extract.append("word_double_press_count")

        group_timing_df = group_wcs_df.loc[
            :,
            columns_to_extract,
        ]
        group_timing_df_list.append(group_timing_df)

    pID_timing_df = pd.concat(group_timing_df_list, axis=0)
    pID_timing_df["word_count"] = pID_timing_df["word_count"].astype(int)
    pID_timing_df["word_time"] = pID_timing_df["word_time"].astype(int)
    if is_double_press:
        pID_timing_df["word_double_press_count"] = pID_timing_df[
            "word_double_press_count"
        ].astype(int)
    return pID_timing_df


def get_double_press_df(
    pID_trialdata: pd.DataFrame,
    position: str,
) -> pd.DataFrame:
    pID_wcs_df = pID_trialdata[
        (pID_trialdata["phase"] == "wcg") & (pID_trialdata["pre_or_post"] == position)
    ]

    group_double_press_df_list: List[pd.DataFrame] = list()
    for group_ID, group_df in pID_wcs_df.groupby("participantID"):
        start_time = group_df.loc[(group_df["status"] == "begin"), "timestamp"].item()

        group_dp_df = group_df.loc[
            (group_df["status"] == "ongoing")
            & (group_df["mode"] == "double_press")
            & (group_df["double_press"] == "occurrence")
        ]
        group_dp_df = group_dp_df.copy()

        group_dp_df.loc[:, "timestamp"] = group_dp_df.loc[:, "timestamp"] - start_time

        columns_to_extract = [
            "timestamp",
            "current_double_press_count",
            "time_since_last_word_start",
            "word_count",
            "word_text",
            "word_key_onsets",
            "word_key_chars",
            "word_key_codes",
            "word_double_press_count",
        ]

        group_dp_df = group_dp_df.loc[
            :,
            columns_to_extract,
        ]
        group_double_press_df_list.append(group_dp_df)

    group_double_press_df = pd.concat(group_double_press_df_list, axis=0)
    group_double_press_df["word_count"] = group_double_press_df["word_count"].astype(
        int
    )
    group_double_press_df["word_double_press_count"] = group_double_press_df[
        "word_double_press_count"
    ].astype(int)
    group_double_press_df["time_since_last_word_start"] = group_double_press_df[
        "time_since_last_word_start"
    ].astype(int)
    return group_double_press_df


def get_stage_timestamps(
    pID_trialdata: pd.DataFrame, stage_keys: Dict[str, str]
) -> pd.DataFrame:
    # avoid lasting changes
    pID_trialdata = pID_trialdata.copy()

    # disambiguate wcg to wcg_pre/wcg_post
    pID_trialdata.loc[
        (pID_trialdata["phase"] == "wcg") & (pID_trialdata["pre_or_post"] == "pre"),
        "phase",
    ] = "wcg_pre"
    pID_trialdata.loc[
        (pID_trialdata["phase"] == "wcg") & (pID_trialdata["pre_or_post"] == "post"),
        "phase",
    ] = "wcg_post"
    pID_trialdata.loc[
        (pID_trialdata["phase"] == "wcg")
        & (pID_trialdata["pre_or_post"] == "practice"),
        "phase",
    ] = "wcg_practice"

    # rename phases
    pID_trialdata["phase"] = pID_trialdata["phase"].replace(stage_keys)

    phase_timestamps_begin_long = pID_trialdata.loc[
        pID_trialdata["status"] == "begin", ["phase", "timestamp"]
    ].reset_index()
    phase_timestamps_end_long = pID_trialdata.loc[
        pID_trialdata["status"] == "end", ["phase", "timestamp"]
    ].reset_index()

    phase_timestamps_begin = pd.pivot(
        phase_timestamps_begin_long,
        index="participantID",
        columns="phase",
        values="timestamp",
    )
    phase_timestamps_end = pd.pivot(
        phase_timestamps_end_long,
        index="participantID",
        columns="phase",
        values="timestamp",
    )

    phase_timestamps = phase_timestamps_begin.join(
        phase_timestamps_end, lsuffix="_stage_start", rsuffix="_stage_end"
    )

    # also save FA & reading as tasks, because that is the correct alignment to
    # the data collection in import_data_json
    for phase_column in [
        "free_association_pre_stage_start",
        "free_association_pre_stage_end",
        "reading_stage_start",
        "reading_stage_end",
        "free_association_post_stage_start",
        "free_association_post_stage_end",
    ]:
        phase_timestamps[phase_column.replace("stage", "task")] = phase_timestamps[
            phase_column
        ]

    return phase_timestamps


def get_time_spr_data(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "dataID",
        "timestamp",
        "sentence_length",
        "sentence_text",
        "sentence_time",
    ]
    pID_time_spr = pID_trialdata.loc[
        (pID_trialdata["phase"] == "story_reading")
        & (pID_trialdata["status"] == "ongoing"),
        columns,
    ]
    pID_time_spr.rename(
        columns={
            "dataID": "Trial",
            "timestamp": "Timestamp",
            "sentence_length": "char_count",
            "sentence_text": "sentence",
            "sentence_time": "sprt",
        },
        inplace=True,
    )
    return pID_time_spr


def get_spr_task_time(pID_trialdata: pd.DataFrame) -> pd.DataFrame:
    pID_start_time = pID_trialdata.loc[
        (pID_trialdata["phase"] == "story_reading")
        & (pID_trialdata["status"] == "begin"),
        ["timestamp"],
    ]
    pID_end_time = pID_trialdata.loc[
        (pID_trialdata["phase"] == "story_reading")
        & (pID_trialdata["status"] == "end"),
        ["timestamp"],
    ]

    pID_start_end_time = pID_start_time.join(
        pID_end_time, lsuffix="_start", rsuffix="_end"
    )
    pID_start_end_time["spr_time"] = (
        pID_start_end_time["timestamp_end"] - pID_start_end_time["timestamp_start"]
    )

    return pID_start_end_time.loc[:, ["spr_time"]]


def import_data(
    study_name_or_data_dir: str,
    q_keys: Dict[str, List[Tuple[str, str, str]]],
    stage_keys: Dict[str, str],
    data_dir: Optional[str] = None,
    filter_condition: Optional[str] = None,
    filter_condition_ocd: Optional[str] = None,
    ratings: Optional[Dict[str, str]] = None,
):
    """Imports data from an experiment folder into the data folder.

    Parameters
    ----------
    study_name_or_data_dir: str
        Name for study or directory for study. If only name is given, will attempt to
        locate study name in directory given by STUDYDATA_LEGACY_DIR in the .env
    data_dir: str
        Root data dir to export files to. Also set in .env
    q_keys : Dict[str, List[Tuple[str, str, str]]]
        Dictionary mapping phase to (id_in_datafile, id_in_export, datatype),
        whereas datatype = "num" | "str".
    stage_keys Dict[str, str]
        Map experiment stage/phase name to common stage name used across studies.
    filter_condition: str
        Condition name which to filter for. For example, a data_dir may
        contain multiple experiments ["intact", "suppress"], then you can filter
        for "suppress".
    filter_condition_ocd: str
        Same as above, but special handling for ocd study [due to experimenter error].
        Has to be one of ['ocd_first', 'ocd_last']
    ratings: Dict, default=None
        Dict specifying, approach, model, story and file of ratings.
        e.g. dict(
            approach="human", model="moment",story="carver_original",file="all.csv"
        ),
    """
    if data_dir is None:
        data_dir = DATA_DIR

    if not os.path.exists(study_name_or_data_dir):
        study_data_dir = os.path.join(STUDYDATA_LEGACY_DIR, study_name_or_data_dir)
        if not os.path.exists(study_data_dir):
            raise ValueError(
                f"'{study_name_or_data_dir}' is neither an existing path nor can"
                f" be found in STUDYDATA_DIR: {study_data_dir}"
            )
    else:
        study_data_dir = study_name_or_data_dir

    trialdata, eventdata, story, condition = load_data(
        study_data_dir, filter_condition, filter_condition_ocd
    )

    # Map ids for anonymization
    pIDs = trialdata["participantID"].unique().tolist()
    mapped_pIDs, mapping = mapIds(study_data_dir=study_data_dir, ids=pIDs)
    trialdata["participantID"] = trialdata["participantID"].map(mapping)
    eventdata["participantID"] = eventdata["participantID"].map(mapping)

    # convert
    pID_trialdata = trialdata.set_index("participantID")
    pID_eventdata = eventdata.set_index("participantID")

    print(f"Importing {study_data_dir} to {data_dir} as {story}/{condition}")

    is_double_press = "double_press" in trialdata["mode"].unique()

    # A) word chains post/pre/practice
    if not is_double_press:
        wcs_post = trialdata[
            (trialdata["phase"] == "wcg")
            & (trialdata["status"] == "ongoing")
            & (trialdata["pre_or_post"] == "post")
        ]
        pID_wcs_post = wcs_post.set_index("participantID")
        wcs_pre = trialdata[
            (trialdata["phase"] == "wcg")
            & (trialdata["status"] == "ongoing")
            & (trialdata["pre_or_post"] == "pre")
        ]
        pID_wcs_pre = wcs_pre.set_index("participantID")
        wcs_practice = wcs_post = trialdata[
            (trialdata["phase"] == "wcg")
            & (trialdata["status"] == "ongoing")
            & (trialdata["pre_or_post"] == "practice")
        ]
    else:
        wcs_post = trialdata[
            (trialdata["phase"] == "wcg")
            & (trialdata["status"] == "ongoing")
            & (trialdata["pre_or_post"] == "post")
            & (trialdata["mode"] == "word")
        ]
        pID_wcs_post = wcs_post.set_index("participantID")
        wcs_pre = trialdata[
            (trialdata["phase"] == "wcg")
            & (trialdata["status"] == "ongoing")
            & (trialdata["pre_or_post"] == "pre")
            & (trialdata["mode"] == "word")
        ]
        pID_wcs_pre = wcs_pre.set_index("participantID")
        wcs_practice = wcs_post = trialdata[
            (trialdata["phase"] == "wcg")
            & (trialdata["status"] == "ongoing")
            & (trialdata["pre_or_post"] == "practice")
            & (trialdata["mode"] == "word")
        ]

    has_practice = not wcs_practice.empty
    wcs_df_practice = pd.DataFrame()  # get rid of the linter warning
    if has_practice:
        pID_wcs_practice = wcs_practice.set_index("participantID")
        wcs_df_practice = get_wcs_df(pID_wcs_practice)

    wcs_df_post = get_wcs_df(pID_wcs_post)
    wcs_df_pre = get_wcs_df(pID_wcs_pre)

    # B) comprehension data
    if story == "carver_original":
        pID_comprehension = get_comp_prop_carver(pID_trialdata, detailed=True)
    elif story == "davis_original":
        pID_comprehension = get_comp_prop_davis(pID_trialdata, detailed=True)
    else:
        raise ValueError(f"Comprehension extraction not impleented for: {story}")

    # C) Demographics/Experience/Transportation/Open questionnaires
    pID_questionnaire_part = get_questionnaire_data(
        pID_trialdata, q_keys=q_keys, condition=condition
    )
    pID_summary_part = pID_comprehension.join(pID_questionnaire_part)

    # D) Word-by-word format (timing data)
    pID_timing_post_df = get_timing_df(
        trialdata=trialdata, position="post", is_double_press=is_double_press
    )
    pID_timing_pre_df = get_timing_df(
        trialdata=trialdata, position="pre", is_double_press=is_double_press
    )
    pID_timing_practice_df = pd.DataFrame()  # get rid of the linter warning
    if has_practice:
        pID_timing_practice_df = get_timing_df(
            trialdata=trialdata, position="practice", is_double_press=is_double_press
        )

    # E) Double presses
    pID_total_double_presses_post = pd.DataFrame()
    pID_total_double_presses_pre = pd.DataFrame()
    pID_double_press_post = pd.DataFrame()
    pID_double_press_pre = pd.DataFrame()
    if is_double_press:
        pID_total_double_presses_post = get_total_double_press(pID_trialdata, "post")
        pID_total_double_presses_post.rename(
            columns={"total_double_press_count": "total_double_press_count_post"},
            inplace=True,
        )
        pID_total_double_presses_pre = get_total_double_press(pID_trialdata, "pre")
        pID_total_double_presses_pre.rename(
            columns={"total_double_press_count": "total_double_press_count_pre"},
            inplace=True,
        )
        pID_double_press_post = get_double_press_df(pID_trialdata, "post")
        pID_double_press_pre = get_double_press_df(pID_trialdata, "pre")

        pID_summary_part = pID_summary_part.join(
            [pID_total_double_presses_post, pID_total_double_presses_pre]
        )

    # F) Stage times
    # Note that these stage times are different from the stage times in the
    # import_json data, as they do not include instructions.
    stage_times = get_stage_timestamps(pID_trialdata, stage_keys)
    pID_summary_part = pID_summary_part.join(stage_times)

    # get spr_time in own column for consistency with json import
    pID_spr_time = get_spr_task_time(pID_trialdata)
    pID_summary = pID_summary_part.join(pID_spr_time)

    # G) add mean sr, mean rt questionnaire data
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

    # H) add mean button presses into questionnaire data
    if is_double_press:
        pIDs_post = pID_double_press_post.index.unique().to_list()
        pID_summary.loc[pIDs_post, "te_count_post"] = pID_double_press_post.groupby(
            "participantID",
            group_keys=False,
        )["timestamp"].count()
        pID_summary.loc[pID_summary["te_count_post"].isna(), "te_count_post"] = 0
        pID_summary["te_count_post"] = pID_summary["te_count_post"].astype(int)

        pIDs_pre = pID_double_press_pre.index.unique().to_list()
        pID_summary.loc[pIDs_pre, "te_count_pre"] = pID_double_press_pre.groupby(
            "participantID",
            group_keys=False,
        )["timestamp"].count()
        pID_summary.loc[pID_summary["te_count_pre"].isna(), "te_count_pre"] = 0
        pID_summary["te_count_pre"] = pID_summary["te_count_pre"].astype(int)

    # Additionally, get exclusion data
    # 1. Correlation reading time and characters
    pID_spr_char_corr = get_spr_correlations(pID_trialdata)

    # 2. Time away & Focusevents
    pID_time_away = get_time_away(pID_eventdata, pID_trialdata)

    # 3. Average/ 4. Max reaction time
    pID_rt_mean, pID_rt_max = get_reaction_time(pID_trialdata)

    # 4. Break between spr & FA2
    pID_spr_wcg_break = get_spr_wcg_break(pID_trialdata)

    # 5. Attention check
    pID_attention_check = get_attention_check(pID_trialdata)

    # 6. Experiment time away
    # (start of free association until submission before demographics questionnaire)
    pID_exp_time_away = get_exp_time_away(pID_eventdata, pID_trialdata)

    # Merge summary data
    pID_summary = pID_summary.join(
        [
            pID_exp_time_away,
            pID_spr_char_corr,
            pID_spr_wcg_break,
            pID_rt_max,
            pID_rt_mean,
            pID_time_away,
            pID_attention_check,
        ]
    )

    # 7. time spr data
    pID_time_spr = get_time_spr_data(pID_trialdata)

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
    if has_practice:
        wordchain_practice_path = os.path.join(wordchain_dir, "practice.csv")
        wcs_df_practice.to_csv(
            wordchain_practice_path,
            header=True,
            index=True,
        )
        print(f"Saved {wordchain_practice_path}")

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
    if has_practice:
        timing_practice_path = os.path.join(timing_dir, "practice.csv")
        pID_timing_practice_df.to_csv(
            timing_practice_path,
            header=True,
            index=True,
        )

    # E) Double presses
    if is_double_press:
        double_press_dir = os.path.join(data_dir, "double_press", story, condition)
        double_press_post_path = os.path.join(double_press_dir, "post.csv")
        check_make_dirs(double_press_post_path)
        pID_double_press_post.to_csv(
            double_press_post_path,
            header=True,
            index=True,
        )
        print(f"Saved {double_press_post_path}")
        double_press_pre_path = os.path.join(double_press_dir, "pre.csv")
        pID_double_press_pre.to_csv(
            double_press_pre_path,
            header=True,
            index=True,
        )
        print(f"Saved {double_press_pre_path}")

    # F) Self-paced reading times
    time_spr_path = os.path.join(data_dir, "time_spr", story, condition, "spr.csv")
    check_make_dirs(time_spr_path)
    pID_time_spr.to_csv(
        time_spr_path,
        header=True,
        index=True,
    )
    print(f"Saved {time_spr_path}")
