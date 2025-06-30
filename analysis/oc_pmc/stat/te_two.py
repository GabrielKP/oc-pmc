from typing import Any, Dict

import numpy as np
import pandas as pd

from oc_pmc.load import filter_participants, load_questionnaire, load_thought_entries

from .utils import test_two


def te_two(config: Dict[str, Any]):
    data1_df = load_thought_entries({**config, **config["config1"]})
    data2_df = load_thought_entries({**config, **config["config2"]})

    # need to account for the participants not reporting thought entries at all.
    quest1_df = load_questionnaire({**config, **config["config1"]})
    quest2_df = load_questionnaire({**config, **config["config2"]})

    filtered1_df = filter_participants({**config, **config["config1"]}, quest1_df)
    filtered2_df = filter_participants({**config, **config["config2"]}, quest2_df)

    data1_with_missing_sr = data1_df["timestamp"].groupby("participantID").count()
    data2_with_missing_sr = data2_df["timestamp"].groupby("participantID").count()

    indcs1 = filtered1_df.index.unique().to_list()
    indcs2 = filtered2_df.index.unique().to_list()

    data1_sr = pd.Series(data=np.zeros(len(indcs1)), index=indcs1, dtype=int)
    data2_sr = pd.Series(data=np.zeros(len(indcs2)), index=indcs2, dtype=int)

    data1_sr[data1_with_missing_sr.index] = data1_with_missing_sr
    data2_sr[data2_with_missing_sr.index] = data2_with_missing_sr

    test_two(config, data1_sr, data2_sr)
