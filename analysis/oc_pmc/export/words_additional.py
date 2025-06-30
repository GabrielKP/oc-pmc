import os
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd

from oc_pmc import DATA_DIR, WORDS_DIR
from oc_pmc.load import load_rated_words, load_wordchains
from oc_pmc.utils import check_make_dirs
from oc_pmc.utils.aggregator import aggregator


def func_get_unrated_words(config: Dict, data_df: pd.DataFrame):
    """Saves all words for a given story, minus the ones given as ratings."""
    ratings_dict = load_rated_words(config["ratings"])

    non_words: Set[Any] = set()
    no_rating: Set[str] = set()

    def _rate_word(row: pd.Series) -> float:
        word = row["word_text"]
        if not isinstance(word, str):
            non_words.add(word)
            return np.nan
        word = word.lower().strip()
        try:
            rating = ratings_dict[word]
        except KeyError:
            no_rating.add(word)
            rating = np.nan
        return rating

    data_df["story_relatedness"] = data_df.apply(_rate_word, axis=1)

    print(f"Non words: {len(non_words)}")
    print(f"Unrated words: {len(no_rating)}")

    path_output = os.path.join(
        DATA_DIR, WORDS_DIR, config["story"], "additional_words.txt"
    )
    check_make_dirs(path_output)
    with open(path_output, "w") as f_out:
        f_out.writelines([w + "\n" for w in no_rating])


def get_unrated_words(config: Dict[str, Any]):
    aggregator(
        config,
        load_func=load_wordchains,
        call_func=func_get_unrated_words,
        no_extra_columns=True,
    )


if __name__ == "__main__":
    pre_post_nofilter = ("position", {"post": ("filter", {}), "pre": ("filter", {})})
    config = {
        "load_spec": (
            "all",
            {
                "all": (
                    "story",
                    {
                        "carver_original": (
                            "condition",
                            {
                                "neutralcue": pre_post_nofilter,
                                "neutralcue2": pre_post_nofilter,
                                "suppress": pre_post_nofilter,
                                "button_press": pre_post_nofilter,
                                "button_press_suppress": pre_post_nofilter,
                            },
                        ),
                    },
                )
            },
        ),
        "aggregate_on": "story",
        "ratings": {
            "approach": "human",
            "model": "moment",
            "story": "carver_original",
            "file": "all.csv",
        },
    }
    get_unrated_words(config)
