import os

from oc_pmc import DATA_DIR, RATEDWORDS_DIR
from oc_pmc.load import load_rated_words_from_path as load_rated_words
from oc_pmc.utils.rate_wordchains import rate_wordchains


def load_rated_words_and_rate_wordchains(config):
    # load ratings
    path_rated_words = os.path.join(
        DATA_DIR,
        RATEDWORDS_DIR,
        config["approach"],
        config["model"],
        config["story"],
        config["file"],
    )
    ratings_dict = load_rated_words(
        path_rated_words,
    )
    rated_wordchains_config = config["rate_wordchains_config"]
    rated_wordchains_config.update(
        {
            "approach": config["approach"],
            "model": config["model"],
            "story_model": config["story"],
        }
    )
    rate_wordchains(rated_wordchains_config, ratings_dict)


if __name__ == "__main__":
    config = {
        # Ratings dict
        "story": "carver_original",
        "approach": "human",
        "model": "moment",
        "file": "all.csv",
        # Which wordchains to rate
        "rate_wordchains_config": {
            "stories": {
                "carver_original": [
                    "neutralcue",
                    "suppress",
                    "intact",
                    "word_scrambled",
                    "sentence_scrambled",
                ]
            },
            "approach": "moment_all.carver",
            "corrections": True,
        },
    }
    load_rated_words_and_rate_wordchains(config)
