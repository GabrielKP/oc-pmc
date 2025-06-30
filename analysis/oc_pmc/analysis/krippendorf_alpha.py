from typing import cast

import numpy as np
import pandas as pd
from krippendorff import alpha

from oc_pmc.load import load_manual_field_ratings
from oc_pmc.utils.aggregator import aggregator

NOFILTER = ("filter", {})
NAN_STRING = "<!nan!nan!>"


def func_krippendorf_alpha(config: dict, data_df: pd.DataFrame):
    data_df = data_df.drop(columns=["wcg_strategy"])
    n_categories = config["n_categories"]
    n_participants = data_df.shape[0]
    raters = config["raters"]

    # loop through data to determine number of categories
    categories = set()
    data_df.map(
        lambda rating: categories.update(
            rating.split(",") if not pd.isna(rating) else [NAN_STRING]
        )
    )
    if len(categories) != n_categories:
        raise ValueError(
            f"{n_categories} != found categories: {len(categories)}, check args"
        )

    categories_dct = dict()
    for category in categories:
        categories_dct[category] = len(categories_dct)

    # need to put data in right format
    # compute value_counts (N, V)
    # N is number of units (participants)
    # V is the value count (category)
    # The entry is the number of raters for that category for that participant
    value_counts = np.zeros((n_participants, n_categories), dtype=int)
    for idx in range(n_participants):
        for idx_rater in range(len(raters)):
            raw = data_df.iloc[idx, idx_rater]
            ratings = cast(str, raw).split(",") if not pd.isna(raw) else [NAN_STRING]
            for rating in ratings:
                value_counts[idx, categories_dct[rating]] += 1

    krips = alpha(
        value_counts=value_counts,
        level_of_measurement="nominal",
    )
    print(f"{config['story']} | {config['condition']}")
    print(f"Krippendorfs alpha: {round(krips, 2)}")


def krippendorf_alpha(config: dict):
    aggregator(
        config=config,
        load_func=load_manual_field_ratings,
        call_func=func_krippendorf_alpha,
    )


if __name__ == "__main__":
    config = {
        "load_spec": (
            "all",
            {
                "all": (
                    "story",
                    {
                        "carver_original": (
                            "condition",
                            {
                                "button_press": NOFILTER,
                                "button_press_suppress": NOFILTER,
                            },
                        ),
                    },
                )
            },
        ),
        "aggregate_on": "condition",
        "no_extra_columns": True,
        "field": "wcg_strategy",
        "raters": ["rater2", "rater1"],
        "n_categories": 6,
    }
    krippendorf_alpha(config)
