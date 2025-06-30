import os
from pathlib import Path
from typing import Any, Dict

from oc_pmc import CORRECTIONS_DIR, DATA_DIR
from oc_pmc.load import load_corrections, load_rated_words, load_word_list_txt


def export_words_to_rate(config: Dict[str, Any]):
    # load new word list
    all_words = set(load_word_list_txt(config["path_word_list"]))

    print(f"Initial amount of words: {len(all_words)}")

    # load corrections & correct
    correction_dict = load_corrections()
    corrected_words = {
        correction_dict[w] if w in correction_dict.keys() else w for w in all_words
    }

    # load discarded words and remove them
    path_discarded = os.path.join(DATA_DIR, CORRECTIONS_DIR, "discarded.csv")
    if os.path.isfile(path_discarded):
        discarded = set(load_word_list_txt(path_discarded))

        filtered_words = corrected_words.difference(discarded)
    else:
        filtered_words = corrected_words

    # load already rated words
    rated_words = load_rated_words(config["ratings"])
    words_to_rate = filtered_words.difference(set(rated_words.keys()))

    # load words which already where supposed to be rated
    if config.get("path_other_words_to_rate") is not None:
        other_words_to_rate = set(
            load_word_list_txt(config["path_other_words_to_rate"])
        )
        extra_words_to_rate = words_to_rate.difference(other_words_to_rate)
        print(f"Extra words to rate: {len(extra_words_to_rate)}")
        words_to_rate = words_to_rate.union(other_words_to_rate)

    print(f"Final words to rate: {len(words_to_rate)}")

    final_words_to_rate = sorted(list(words_to_rate))

    with open(config["path_output"], "w") as f_out:
        f_out.writelines("\n".join(final_words_to_rate) + "\n")


if __name__ == "__main__":
    config = {
        "path_word_list": Path(
            DATA_DIR,
            "words_to_rate/carver_original/2024-04-22-additional_words-toronto.txt",
        ),
        "ratings": {
            "approach": "human",
            "model": "moment",
            "story": "carver_original",
            "file": "all.csv",
        },
        "path_other_words_to_rate": Path(
            DATA_DIR, "words_to_rate/carver_original/2024-04-07-final_words_to_rate.txt"
        ),
        "path_output": Path(
            DATA_DIR,
            "words_to_rate/carver_original/2024-04-22-final_words_to_rate-suppress_and_chris.txt",
        ),
    }
    export_words_to_rate(config)
