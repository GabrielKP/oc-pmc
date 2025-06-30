import os
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd

from oc_pmc import (
    DATA_DIR,
    OUTPUTS_DIR,
    POSITIONS_DIR,
    RATEDWORDCHAINS_DIR,
    WORDCHAINS_DIR,
    get_logger,
)
from oc_pmc.load import load_wordchains
from oc_pmc.utils import check_make_dirs, wordchain_df_to_list
from oc_pmc.utils.conditions_iterator import conditions_iterator

log = get_logger(__name__)


def rate(word, ratings_dict: Dict[str, float]) -> float:
    try:
        word = ratings_dict[word]
    except KeyError:
        word = np.nan
    return word


def ismissing(word, ratings_dict: Dict[str, float]) -> int:
    try:
        ratings_dict[word]
        miss = 0
    except KeyError:
        miss = 1
    return miss


def rate_wordchain_df(
    wordchains_df: pd.DataFrame,
    ratings_dict: Dict[str, float],
) -> pd.DataFrame:
    return wordchains_df.map(lambda word: rate(word, ratings_dict))


def func_rate_wordchains(
    config: Dict,
    wcs: pd.DataFrame,
    story: str,
    condition: str,
    position: str,
    ratings_dict: Dict[str, Union[int, float]],
):
    wordchains_df = wcs
    rated_wordchains_df = rate_wordchain_df(wordchains_df, ratings_dict)
    missing_df = wordchains_df.map(lambda word: ismissing(word, ratings_dict))
    # calculate missing words
    wc_lens = [len(wc) for wc in wordchain_df_to_list(wordchains_df)]
    for idx_wc in range(missing_df.shape[0]):
        missing_df.iloc[idx_wc, wc_lens[idx_wc] :] = 0
    n_words_missing_mean = missing_df.sum(axis=1).mean()

    # calculate mean wordchain length
    wc_lens_mean = np.mean(wc_lens)

    log.info(f"Mean length of wordchains       : {wc_lens_mean:.2f}")
    log.info(f"Mean words missing per wordchain: {n_words_missing_mean:.2f}")

    # save
    path_output = os.path.join(
        OUTPUTS_DIR,
        RATEDWORDCHAINS_DIR,
        config["approach"],
        config["model"],
        config["story_model"],
        story,
        condition,
        f"{position}.csv",
    )
    check_make_dirs(path_output)
    rated_wordchains_df.to_csv(path_output, index=True)


def rate_wordchains(
    config: Dict,
    ratings_dict: Dict[str, Union[int, float]],
):
    """Rates wordchains for all given stories and conditions

    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dictionary with strings as keys.
        It is expected to have at least the key "stories":
            "stories": {
                story1: [condition1, condition2, ...],
                story2: [condition1, condition2, ...],
                ...
            }
    """
    conditions_iterator(
        config=config,
        func=func_rate_wordchains,
        load_func=load_wordchains,
        ratings_dict=ratings_dict,
    )
