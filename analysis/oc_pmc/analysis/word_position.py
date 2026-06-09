import re

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from oc_pmc.load import (
    load_questionnaire,
    load_rated_wordchains,
    load_story_sentences,
    load_story_sentences_grouped,
    load_word_position,
)
from oc_pmc.stat import test_two
from oc_pmc.utils import get_n_sections


def compute_cumulative_match_score(
    config: dict, pIDs: list[str], data_df: pd.DataFrame, only_high_sr: bool = False
):
    word_position_dct = load_word_position(config=config["word_position"])

    # prep for normalization
    any_word_re = re.compile(r"\b\w+\b", flags=re.IGNORECASE)
    if config["word_position"]["mode"] == "exact_match_sentences":
        section_lengths = np.array(
            [
                len(any_word_re.findall(sent))
                for sent in load_story_sentences(
                    story=config["story"], story_file="sectioned.txt"
                )
            ]
        )
    else:
        section_sentences = load_story_sentences_grouped(
            story=config["story"], story_file="sectioned.txt"
        )
        section_lengths = np.array(
            [
                len(any_word_re.findall("\n".join(section_sentences_)))
                for section_sentences_ in section_sentences
            ]
        )

    n_sections = get_n_sections(
        story=config["word_position"]["story"],
        word_position_mode=config["word_position"]["mode"],
    )

    n_participants = len(pIDs)
    match_score = np.zeros((n_participants, n_sections))
    for idx_participant, pID in enumerate(pIDs):
        participant_df = data_df.loc[data_df.index == pID]
        for idx_word, word in enumerate(participant_df["word_text"].unique()):
            if word not in word_position_dct:
                continue

            if not only_high_sr:
                match_score[idx_participant] += word_position_dct[word]
            else:
                # high SR words
                word_sr = participant_df.iloc[idx_word]["story_relatedness"]
                if not (np.isnan(word_sr)) and word_sr > config["high_sr_threshold"]:
                    match_score[idx_participant] += word_position_dct[word]

    if not config.get("not_normalize", False):
        match_score = match_score * (
            (sum(section_lengths) / (section_lengths)[None, :]) / n_sections
        )

    return match_score


def get_rho_diff_match_score_with_monotonic_increase_from_matchscores(
    diff_match_score: np.ndarray,
) -> pd.Series:
    """To avoid reloading/recomputing cumulative match scores."""
    # diff_match_score.shape = (n_participants, n_sections)

    n_participants = diff_match_score.shape[0]
    n_sections = diff_match_score.shape[1]

    rho_ls = list()
    for idx_participant in range(n_participants):
        if (
            diff_match_score[idx_participant][0] == diff_match_score[idx_participant]
        ).all():
            rho = 0
        else:
            rho, _ = spearmanr(np.arange(n_sections), diff_match_score[idx_participant])
        rho_ls.append(rho)
    rho_series = pd.Series(rho_ls)
    rho_series.name = "rho"
    return rho_series


def get_rho_diff_match_score_with_monotonic_increase(config: dict) -> pd.Series:
    pre_df = load_rated_wordchains(config={**config, "position": "pre"})
    post_df = load_rated_wordchains(config={**config, "position": "post"})

    # pre/post_df may are missing participants if they did not generate word during
    # timeframe
    pIDs = list(
        load_questionnaire(
            config={"story": config["story"], "condition": config["condition"]}
        ).index.unique()
    )

    pre_match_score = compute_cumulative_match_score(
        config=config, pIDs=pIDs, data_df=pre_df
    )
    post_match_score = compute_cumulative_match_score(
        config=config, pIDs=pIDs, data_df=post_df
    )
    diff_match_score = post_match_score - pre_match_score
    # diff_match_score.shape = (n_participants, n_sections)
    return get_rho_diff_match_score_with_monotonic_increase_from_matchscores(
        diff_match_score
    )


def compute_rank_spearman_correlation(
    config: dict,
    verbose: bool = True,
) -> tuple[float, float, float, float, float, int, float, float, int]:
    if "config1" in config:
        assert "config2" in config, "config2 must be provided if config1 is provided"

        rho_series_1 = get_rho_diff_match_score_with_monotonic_increase(
            config={**config, **config["config1"]}
        )
        rho_name_1 = config["name1"]
        rho_series_2 = get_rho_diff_match_score_with_monotonic_increase(
            config={**config, **config["config2"]}
        )
        rho_name_2 = config["name2"]
        test_type = "mwu"
    else:
        rho_series_1 = get_rho_diff_match_score_with_monotonic_increase(config=config)
        rho_series_2 = pd.Series(np.zeros(len(rho_series_1)))
        rho_series_2.name = "rho"

        rho_name_1 = config.get("name1", "post - pre correlation with increasing order")
        rho_name_2 = "zero"
        test_type = "wilcoxon"

    return test_two(
        {
            **config,
            "name1": rho_name_1,
            "name2": rho_name_2,
            "measure": "rho",
            "test_type": test_type,
            "return_all": True,
        },
        data1_sr=rho_series_1,
        data2_sr=rho_series_2,
        verbose=verbose,
    )  # type: ignore
