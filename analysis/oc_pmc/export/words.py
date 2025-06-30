import os
from typing import Dict, List, Tuple

from oc_pmc import DATA_DIR, WORDS_DIR
from oc_pmc.load import load_words
from oc_pmc.utils import check_make_dirs


def get_words(config: Dict):
    """Saves all words for given story."""

    path_output = os.path.join(DATA_DIR, WORDS_DIR, config["story"], "words.txt")
    check_make_dirs(path_output)

    words_to_rate = load_words(config)

    with open(path_output, "w") as f_out:
        f_out.writelines([w + "\n" for w in words_to_rate])


if __name__ == "__main__":
    config = {
        "story": "dark_bedroom",
        "corrections": True,
    }
    get_words(config)
