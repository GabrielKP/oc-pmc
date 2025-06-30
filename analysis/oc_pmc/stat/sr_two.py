from typing import Any, Dict

from oc_pmc.load import load_rated_wordchains

from .utils import test_two


def sr_two(config: Dict[str, Any]):
    data1_df = load_rated_wordchains({**config, **config["config1"]})
    data2_df = load_rated_wordchains({**config, **config["config2"]})

    column = config["column"]

    if config.get("within_participant_summary", True):
        data1_sr = data1_df[column].groupby("participantID").mean().dropna()
        data2_sr = data2_df[column].groupby("participantID").mean().dropna()
    else:
        data1_sr = data1_df[column].dropna()
        data2_sr = data2_df[column].dropna()

    test_two(config, data1_sr, data2_sr)
