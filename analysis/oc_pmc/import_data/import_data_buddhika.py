"""
This script imports data from an experiment folder into the ldata folder.
It assigns participants to exclusion groups, saves the results in the ldata folder,
and saves the results in the base folder.
"""

import os
from ast import literal_eval
from typing import Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
from oc_pmc import DATA_DIR, get_logger
from oc_pmc.import_data.load_study_data import load_data_buddhika
from oc_pmc.import_data.utils import get_mean_sr_rt
from oc_pmc.import_data.utils_buddhika import (
    get_comp_prop_carver_buddhika,
    get_questionnaire_data_buddhika,
    get_reaction_time_buddhika,
    get_spr_correlations_buddhika,
    get_spr_wcg_break_buddhika,
    get_time_away_buddhika,
)
from oc_pmc.load import load_rated_words
from oc_pmc.utils import check_make_dirs

log = get_logger(__name__)


def get_stage_timestamps(pID_trialdata: pd.DataFrame, stage_keys) -> pd.DataFrame:
    # phase == stage
    phases = pID_trialdata["phase"].unique()
    phases = phases[phases != "INSTRUCTIONS"]
    phase_timestamps_long_ls: List[pd.DataFrame] = list()
    mentioned = set()
    for pID, pID_df in pID_trialdata.groupby("participantID"):
        for phase in phases:
            phase_df = pID_df[pID_df["phase"] == phase]
            phase_start = phase_df["timestamp"].min()
            phase_end = phase_df["timestamp"].max()
            if phase in stage_keys:
                phase_name = stage_keys[phase]
            else:
                if phase not in mentioned:
                    log.warning(f"Phase {phase} not in stage_keys")
                    mentioned.add(phase)
                phase_name = phase
            phase_timestamps_long_ls.append(
                pd.DataFrame(
                    {
                        "participantID": [pID],
                        "phase": [f"{phase_name}_stage_start"],
                        "timestamp": [phase_start],
                    }
                )
            )
            phase_timestamps_long_ls.append(
                pd.DataFrame(
                    {
                        "participantID": [pID],
                        "phase": [f"{phase_name}_stage_end"],
                        "timestamp": [phase_end],
                    }
                )
            )
    phase_timestamps_long = pd.concat(phase_timestamps_long_ls)
    phase_timestamps = pd.pivot(
        phase_timestamps_long,
        index="participantID",
        columns="phase",
        values="timestamp",
    )
    return phase_timestamps


def get_spr_task_time(pID_phase_timestamps: pd.DataFrame) -> pd.DataFrame:
    pID_start_end_time = pID_phase_timestamps[["reading_stage_start"]]
    pID_start_end_time["reading_stage_end"] = pID_phase_timestamps["reading_stage_end"]
    pID_start_end_time["spr_time"] = (
        pID_start_end_time["reading_stage_end"]
        - pID_start_end_time["reading_stage_start"]
    )

    return pID_start_end_time.loc[:, ["spr_time"]]


def import_data_buddhika(
    path_trialdata: str,
    path_eventdata: str,
    path_questiondata: str,
    story: str,
    condition: str,
    q_keys: Dict[str, List[Tuple[str, str, str]]],
    stage_keys: Dict[str, str],
    comprehension_keys: List[Tuple[str, str, str]],
    data_dir: Optional[str] = None,
    filter_condition: Optional[str] = None,
    ratings: Optional[Dict[str, str]] = None,
):
    """Imports data from an experiment folder into the data folder.

    Parameters
    ----------
    path_*: str
        Path to respective datafile
    story: str
        Identifier for story
    condition: str
        Identifier for condition
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
    ratings: Dict, default=None
        Dict specifying, approach, model, story and file of ratings.
        e.g. dict(
            approach="human", model="moment",story="carver_original",file="all.csv"
        ),
    """
    if data_dir is None:
        data_dir = DATA_DIR

    # Load data
    # do not use trialdata/eventdata, b
    trialdata, eventdata, questiondata = load_data_buddhika(
        path_trialdata, path_eventdata, path_questiondata, filter_condition
    )

    # set index
    pID_trialdata = trialdata.set_index("participantID")
    pID_eventdata = eventdata.set_index("participantID")
    pID_questiondata = questiondata.set_index("participantID")

    print("\nImporting questionnaire & exclusion data.")

    questionnaires_path = os.path.join(
        data_dir, "questionnaires", story, condition, "questionnaire_data.csv"
    )
    check_make_dirs(questionnaires_path)

    # 1. Get comprehension data
    if "carver" in story:
        pID_comp_data = get_comp_prop_carver_buddhika(
            pID_questiondata, comprehension_keys, detailed=True
        )
    else:
        raise ValueError("No comprehension solutions implemented for story.")

    # 2. Get rest of the questionnaires
    pID_questionnaire_rest = get_questionnaire_data_buddhika(
        pID_questiondata, q_keys=q_keys
    )

    # 3. Get the phase timestamps
    pID_stage_timestamps = get_stage_timestamps(pID_trialdata, stage_keys)

    # 4. Time away
    pID_time_away = get_time_away_buddhika(pID_eventdata, pID_trialdata)

    # 5. Average/Max reaction time
    pID_rt_mean, pID_rt_max = get_reaction_time_buddhika(pID_trialdata)

    # 6. Break between spr & FA2
    pID_spr_wcg_break = get_spr_wcg_break_buddhika(pID_trialdata)

    # 7. Correlation reading time and characters
    pID_spr_char_corr = get_spr_correlations_buddhika(pID_trialdata)

    # 8. Get spr task time (for consistency)
    pID_spr_time = get_spr_task_time(pID_stage_timestamps)

    # focusevents?
    # attention check?

    # Combine all data
    pID_questionnaire_data = pID_spr_char_corr.join(
        [
            pID_questionnaire_rest,
            pID_stage_timestamps,
            pID_spr_time,
            pID_spr_wcg_break,
            pID_rt_max,
            pID_rt_mean,
            pID_time_away,
            pID_comp_data,
        ]
    )

    print("Importing word (chain) data")
    for position in ["pre", "post"]:
        timing_df_path = os.path.join(
            DATA_DIR,
            "time_words",
            story,
            condition,
            f"{position}.csv",
        )
        check_make_dirs(timing_df_path)

        # Load Buddhikas word data
        path_time_words = os.path.join(
            DATA_DIR,
            "time_words_legacy",
            story,
            condition,
            f"{position}.csv",
        )
        if not os.path.exists(path_time_words):
            log.warning(f"Cannot find word data in {path_time_words}, skipping.")
            continue

        legacy_timing_df = pd.read_csv(path_time_words)

        working_timing_df = legacy_timing_df.loc[
            :,
            [
                "ID",
                "word_count",
                "submit_time",
                "key_onsets",
                "key_ids",
                "key_codes",
                "word",
            ],
        ]
        working_timing_df.loc[:, "timestamp_absolute"] = legacy_timing_df.loc[
            :, "Timestamp"
        ]
        # use submit_time as a timestamp
        working_timing_df.loc[:, "timestamp"] = legacy_timing_df.loc[:, "submit_time"]
        working_timing_df = working_timing_df.rename(
            columns={
                "key_onsets": "word_key_onsets",
                "key_ids": "word_key_chars",
                "submit_time": "word_time",
                "key_codes": "word_key_codes",
                "word": "word_text",
            }
        )

        timing_df_list = list()
        for group_name, group_df in working_timing_df.groupby("ID", sort=True):
            group_df = group_df.sort_values("word_count", ascending=True)
            # remove empty submission at end
            if (
                len(
                    literal_eval(
                        cast(str, group_df.loc[group_df.index[-1], "word_key_codes"])
                    )
                )
                == 0
            ):  # type: ignore
                group_df = group_df.iloc[:-1]
            # convert key_onsets to list
            group_df["word_key_onsets"] = group_df["word_key_onsets"].apply(
                literal_eval
            )

            # compute relative onset nd submission times.
            group_df.loc[:, "prev_word_time"] = group_df.loc[:, "word_time"].shift()
            group_df.loc[group_df.index[0], "prev_word_time"] = 0
            group_df["prev_word_time"] = group_df["prev_word_time"].astype(int)

            def key_onset_times_relative(row: pd.Series) -> List[int]:
                word_key_onsets_ls: List[int] = row["word_key_onsets"]
                prev_word_time: int = row["prev_word_time"]
                if len(word_key_onsets_ls) == 0:
                    return []
                word_key_onsets: np.ndarray = np.array(word_key_onsets_ls)  # type: ignore
                relative_onsets = word_key_onsets[1:] - word_key_onsets[:-1]
                # concat and return
                return [
                    word_key_onsets[0] - prev_word_time,
                    *relative_onsets.tolist(),
                ]

            # make times in key_onsets relative to previous keystroke
            group_df.loc[:, "word_key_onsets"] = group_df.loc[
                :, ["word_key_onsets", "prev_word_time"]
            ].apply(key_onset_times_relative, axis=1)

            group_df.loc[:, "word_time"] = (
                group_df.loc[:, "word_time"] - group_df.loc[:, "prev_word_time"]
            )
            group_df = group_df.drop(columns="prev_word_time")

            # make timestamp relative to start of word chain game
            wcg_start = (
                group_df.loc[group_df.index[0], "timestamp"].item()  # type: ignore
                - group_df.loc[group_df.index[0], "word_time"].item()  # type: ignore
            )
            group_df["timestamp"] = group_df.loc[:, "timestamp"] - wcg_start

            timing_df_list.append(group_df)

        timing_df = pd.concat(timing_df_list, axis=0)

        # save to file
        timing_df.rename(columns={"ID": "participantID"}, inplace=True)
        pID_timing_df = timing_df.set_index("participantID")
        pID_timing_df.to_csv(timing_df_path, index=True)

        # add ratings to questionnaire
        if ratings is not None:
            ratings_dict = load_rated_words(ratings)
            mean_sr, mean_rt = get_mean_sr_rt(pID_timing_df, ratings_dict)
            mean_sr_30s, mean_rt_30s = get_mean_sr_rt(
                pID_timing_df, ratings_dict, max_time=30000
            )
            pID_questionnaire_data[f"mean_sr_{position}"] = mean_sr
            pID_questionnaire_data[f"mean_rt_{position}"] = mean_rt
            pID_questionnaire_data[f"mean_sr_{position}_30s"] = mean_sr_30s
            pID_questionnaire_data[f"mean_rt_{position}_30s"] = mean_rt_30s

    # Save Questionnaire & Exclusion data
    pID_questionnaire_data.to_csv(
        questionnaires_path,
        header=True,
        index=True,
    )
    print(f"Saved {questionnaires_path}")
