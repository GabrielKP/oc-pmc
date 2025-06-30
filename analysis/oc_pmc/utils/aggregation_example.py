from typing import Dict, cast

import pandas as pd

from oc_pmc.load import load_wordchains
from oc_pmc.utils.aggregator import aggregator


def func_load_worchains(config: Dict) -> pd.DataFrame:
    print(config)
    return cast(pd.DataFrame, load_wordchains(config))


def func_print(config: Dict, data_df: pd.DataFrame) -> pd.DataFrame:
    print(f"CONFIG FOR CALL FUNC: {config}")
    print(data_df)
    return data_df


if __name__ == "__main__":
    shared = (
        "position",
        {
            "post": ("filter", {"include": ("match", "volition", "intentional")}),
            "pre": ("filter", {"exclude": ("match", "volition", "intentional")}),
        },
    )
    config = {
        "load_spec": (
            "story",
            {
                "carver_original": (
                    "condition",
                    {
                        "suppress": shared,
                        "neutralcue": shared,
                    },
                ),
                # "july_original": (
                #     "condition",
                #     {
                #         "intact": shared,
                #         "sentence_scrambled": shared,
                #     },
                # ),
            },
        ),
        "load_func": func_load_worchains,
        "call_func": func_print,
        "aggregate_on": "condition",
    }

    res = aggregator(config)
    # print(res)
