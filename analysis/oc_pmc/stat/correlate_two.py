from copy import deepcopy

import pandas as pd
import statsmodels.api as sm

from oc_pmc.load import load_per_participant_data
from oc_pmc.utils import summary_str


def correlate_two(config: dict):
    """Correlate two measures for a set of participants."""
    x_measure = config["x_measure"]
    y_measure = config["y_measure"]

    data1_df = load_per_participant_data({**config, "measure": x_measure})
    data2_df = load_per_participant_data({**config, "measure": y_measure})

    data_df = data1_df.join(data2_df)

    # remove nans
    nans = data_df[y_measure].isna() | data_df[x_measure].isna()
    data_df = data_df.loc[~nans]

    # run regression
    predictor_vars_with_constant = sm.add_constant(data_df[x_measure].to_numpy())
    model = sm.OLS(
        data_df[y_measure].to_numpy(),
        predictor_vars_with_constant,
    )
    result = model.fit()

    # get summary
    if config.get("verbose", True):
        threshold = config.get("threshold", 0.05)
        pvalue_exact = config.get("pvalue_exact", False)
        summary = summary_str(x_measure, y_measure, result, threshold, pvalue_exact)
        print("Summary\n" + summary)

    return result
