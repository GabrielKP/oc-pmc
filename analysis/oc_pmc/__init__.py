import logging
from typing import Optional

from dotenv import dotenv_values
from rich.console import Console

config = dotenv_values(".env")

CACHE_DIR = ".cache"
DATA_DIR: str = config.get("DATA_DIR", "data")  # type: ignore
EXTERNAL_DIR = "external"
EMBEDDINGS_DIR = "embeddings"
QUESTIONNAIRE_DIR = "questionnaires"
EXCLUSION_DATA_DIR = "exclusion_data"
WORDS_DIR = "words_to_rate"
WORDCHAINS_DIR = "wordchains"
PLOTS_DIR = "plots"
EVENTS_THEMES_DIR = "event_theme"
OUTPUTS_DIR: str = config.get("OUTPUTS_DIR", "data")  # type: ignore
STUDYPLOTS_DIR = config.get("STUDYPLOTS_DIR", "plots")
EXPORT_DIR = "export"
RATEDWORDS_DIR = "rated_words"
RATEDWORDCHAINS_DIR = "rated_wordchains"
POSITIONS_DIR = "positions"
CORRECTIONS_DIR = "corrections"
TIME_SPR_DIR = "time_spr"
STUDYDATA_DIR: str = config.get("STUDYDATA_DIR", "conditions/psyserver-based/data")  # type: ignore
STUDYDATA_LEGACY_DIR: str = config.get(
    "STUDYDATA_LEGACY_DIR", "conditions/psiturk-based/linger-volition"
)  # type: ignore
BELLANA_DIR: Optional[str] = config.get("BELLANA_DIR")
FORMAT = "[%(levelname)s] %(name)s.%(funcName)s - %(message)s"
ALL = {
    "carver_original": [
        "intact",
        "sentence_scrambled",
        "word_scrambled",
        "neutralcue",
    ],
    "carver_rewrite": ["intact", "sentence_scrambled"],
    "carver_replication": ["intact", "sentence_scrambled"],
    "carver_error": ["emotion", "proofread"],
    "july_original": ["intact", "sentence_scrambled"],
}
CARVER = {
    "carver_original": [
        "intact",
        "sentence_scrambled",
        "word_scrambled",
        "neutralcue",
    ],
    "carver_rewrite": ["intact", "sentence_scrambled"],
    "carver_replication": ["intact", "sentence_scrambled"],
    "carver_error": ["emotion", "proofread"],
}

RATINGS_CARVER = {
    "approach": "human",
    "model": "moment",
    "story": "carver_original",
    "file": "all.csv",
}

RATINGS_LIGHTBULB = {
    "approach": "themesim",
    "model": "glove",
    "story": "dark_bedroom",
    "file": "19.csv",
}


logging.basicConfig(format=FORMAT)


console = Console()


def get_logger(
    name=__name__,
    log_level=logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Initializes multi-GPU-friendly python command line logger."""

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # create formatter
    formatter = logging.Formatter(FORMAT)

    if log_file is not None:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
