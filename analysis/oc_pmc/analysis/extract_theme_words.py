import os
from typing import Dict, cast

import pandas as pd

from oc_pmc import DATA_DIR
from oc_pmc.load import load_theme_words
from oc_pmc.utils import check_make_dirs


def func_extract_theme_words(config: Dict):
    theme_words_base_path = os.path.join(DATA_DIR, "theme_words", config["story"])
    theme_words_path = os.path.join(theme_words_base_path, "theme_words.txt")
    theme_words_extended_path = os.path.join(
        theme_words_base_path, "theme_words_extended.txt"
    )
    check_make_dirs(theme_words_path)

    theme_words_df = cast(pd.DataFrame, load_theme_words(config, raw=True))

    theme_words = theme_words_df["answer"].value_counts().index.to_list()
    with open(theme_words_path, "w") as f_out:
        f_out.writelines([word + "\n" for word in theme_words[:10]])
    with open(theme_words_extended_path, "w") as f_out:
        f_out.writelines([word + "\n" for word in theme_words])
