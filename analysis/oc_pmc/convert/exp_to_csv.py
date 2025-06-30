import argparse
import os
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from oc_pmc import get_logger
from oc_pmc.load import load_exp

log = get_logger(__name__)

BASE_DIR = "outputs/rated_words"


def get_output_path(path: str) -> str:
    # path = outputs/exp/approach/story/nexamples[_matched][_marker].txt
    splitted_exp_path = path.split("/")
    story = splitted_exp_path[-2]
    model = splitted_exp_path[-3]
    approach = splitted_exp_path[-4]
    # nexamples[_matched][_marker].txt
    filename = splitted_exp_path[-1].split(".")[0]

    # output_path = outputs/rated_words/approach/story/nexamples[_matched][_marker].csv
    return os.path.join(
        BASE_DIR,
        approach,
        model,
        story,
        f"{filename}.csv",
    )


def loaded_ratings_to_df(rating_dicts: List[Dict[str, Any]]) -> pd.DataFrame:
    words: List[str] = list()
    ratings: List[Union[int, float]] = list()
    n_non_rated_words = 0
    for rating_dict in rating_dicts:
        if not isinstance(rating_dict["rating"], int) and not isinstance(
            rating_dict["rating"],
            float,
        ):
            if "raw" in rating_dict:
                log.info(
                    f"ERROR: Word: {rating_dict['word']}"
                    f" | Rating {rating_dict['rating']}"
                    f" | Raw {rating_dict['raw']} | excluded"
                )
            else:
                log.info(
                    f"ERROR: Word: {rating_dict['word']}"
                    f" | Rating {rating_dict['rating']} | excluded"
                )
            n_non_rated_words += 1
            continue

        words.append(rating_dict["word"])
        ratings.append(rating_dict["rating"])

    rating_df = pd.DataFrame(
        {
            "word": words,
            "rating": ratings,
        }
    )
    log.info(f"N words | rated: {len(rating_df)} | not rated: {n_non_rated_words}")
    return rating_df


def ratings_to_csv(path: str, output_path: Optional[str]) -> str:
    if output_path is None:
        output_path = get_output_path(path)
    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))
    log.info(f"Saving into: {output_path}")

    experiment_data = load_exp(path)

    rating_dicts = experiment_data["output_ratings"]

    rating_df = loaded_ratings_to_df(rating_dicts)

    log.info(f"Saving to {output_path}")
    rating_df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="path of .pkl file with word ratings.")
    parser.add_argument(
        "-o",
        "--output_path",
        default=None,
        help="path for output.csv file.",
    )
    args = parser.parse_args()

    ratings_to_csv(args.path, args.output_path)
