import logging
import os
import pickle
from typing import Any, Dict, List, Tuple, Union

import numpy as np
from oc_pmc import OUTPUTS_DIR, RATEDWORDS_DIR, get_logger
from oc_pmc.convert.exp_to_csv import loaded_ratings_to_df
from oc_pmc.load import load_word_list_txt, load_words
from oc_pmc.model_objects.model_glove import Glove
from oc_pmc.model_objects.model_object import ModelObject
from oc_pmc.utils import check_make_dirs
from tqdm import tqdm

EXP_DIR = "exp"
APPROACH = "themesim"
PERMUTATION_SEED = 999


log = get_logger(__name__)


def cos_similarity(x1: np.ndarray, x2: np.ndarray) -> float:
    return np.dot(x1, x2) / (np.linalg.norm(x1, axis=1) * np.linalg.norm(x2))


class Experiment(object):
    """
    Exp() class contains wrapper methods to run experiments with transformer models.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        model_object: ModelObject,
    ):
        self.model_object = model_object

    def _compute_similarity(
        self,
        config: Dict[str, Any],
        word: str,
    ) -> Union[float, None]:
        # get embedding
        word_embedding = self.model_object.embedding(config, word)

        if word_embedding is None:
            return None

        # compute similarity score
        similarities = cos_similarity(self.theme_embeddings, word_embedding)

        return np.max(similarities).item()

    def get_theme_embeddings(
        self,
        config: Dict[str, Any],
        theme_words: List[str],
    ) -> np.ndarray:
        theme_embeddings: List[np.ndarray] = list()
        for theme_word in theme_words:
            theme_embedding = self.model_object.embedding(config, theme_word)
            if theme_embedding is None:
                raise RuntimeError(f"Theme word not in embedding file: {theme_word}")
            theme_embeddings.append(theme_embedding)

        return np.stack(theme_embeddings)

    def run(
        self,
        config: Dict,
    ) -> List[Dict[str, Union[float, str, None]]]:
        """Runs experiment."""

        # ---- get words to rate
        words_to_rate = load_words(dict(), corrections=config["corrections"])

        # ---- theme words
        theme_words = load_word_list_txt(config["path_theme_words"])
        if config.get("n_theme_words", None) is not None:
            theme_words = theme_words[: config["n_theme_words"]]
        log.info(f"Loaded {len(theme_words)} theme words")

        # ---- theme word embeddings
        self.theme_embeddings = self.get_theme_embeddings(config, theme_words)

        # ---- compute similarities
        desc = "(theme similarity)"
        rating_dicts: List[Dict[str, Union[float, str, None]]] = list()
        for word in tqdm(
            words_to_rate,
            desc=desc,
            total=len(words_to_rate),
        ):
            rating_dicts.append(
                {
                    "word": word,
                    "rating": self._compute_similarity(config, word),
                }
            )

        return rating_dicts


def get_output_paths(config: Dict) -> Tuple[str, str]:
    """Returns exp and csv output path."""
    normalized_model_name = config["model_name"].split("/")[-1]
    marker = (
        f"{config['n_theme_words']}"
        if config.get("n_theme_words", None) is not None
        else "10"
    )
    output_path = os.path.join(
        OUTPUTS_DIR,
        EXP_DIR,
        APPROACH,
        normalized_model_name,
        config["story"],
        f"{marker}.pkl",
    )
    output_path_csv = os.path.join(
        OUTPUTS_DIR,
        RATEDWORDS_DIR,
        APPROACH,
        normalized_model_name,
        config["story"],
        f"{marker}.csv",
    )
    return output_path, output_path_csv


def rate_theme_similarity(
    config: Dict,
    model_object: ModelObject,
) -> int:
    """Compute surprisal values for input with model and save them to output.

    Parameters
    ----------
    """

    # paste story into params
    config["path_theme_words"] = os.path.join(
        OUTPUTS_DIR,
        "theme_words",
        config["story"],
        config.get("theme_word_file", "theme_words.txt"),
    )

    # Prepare output
    output_path, output_path_csv = get_output_paths(config)
    check_make_dirs([output_path, output_path_csv])

    # Run actual Rating
    experiment = Experiment(
        config=config,
        model_object=model_object,
    )
    log.info("Rating")
    rating_dicts = experiment.run(config)

    # Merge input config with output data
    config["output_ratings"] = rating_dicts

    # Save csv
    rating_df = loaded_ratings_to_df(rating_dicts)
    log.info(f"Saving csv to {output_path_csv}")
    rating_df.to_csv(output_path_csv, index=False)

    # Save exp file
    log.info(f"Saving exp to: {output_path}")
    with open(output_path, "wb") as f_out:
        pickle.dump(config, f_out)

    return 0


def main():
    config = {
        "debug": False,
        "story": "dark_bedroom",  # story identifier to know which theme words
        "corrections": True,
        "theme_word_file": "theme_words_extended.txt",  # alternative: theme_words.txt
        "n_theme_words": 19,  # int : how many theme words to use
        "model_class": Glove,
        "model_name": "glove",
    }

    # Init Logger
    log_level = logging.DEBUG if config.get("debug", False) else logging.INFO
    log.setLevel(log_level)

    # Create model object
    log.info(f"Loading Model Class {str(config['model_class'])}")
    if config.get("model_name", None) is not None:
        log.info(f"Model name: {config['model_name']}")
    model_class = config.pop("model_class")
    model_object = model_class(config)

    rate_theme_similarity(config=config, model_object=model_object)


if __name__ == "__main__":
    main()
