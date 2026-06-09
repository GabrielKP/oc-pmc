from copy import deepcopy
from typing import Optional

import pandas as pd
import statsmodels.api as sm

from oc_pmc.load import load_per_participant_data
from oc_pmc.utils import cut_small_value, summary_str


def stat_latex_str_corr(
    config: dict,
    result,
    threshold: float,
    pvalue_exact: bool,
) -> str:
    pvalue = result.f_pvalue
    df = int(result.df_resid)
    r = result.rsquared**0.5
    if result.params[1] < 0:
        r = -r

    if pvalue_exact:
        pvalue_str = f"p = {f'{pvalue:f}'[1:]}"
    elif pvalue < (threshold - 0.2 * threshold):
        pvalue_str = f"p < {threshold}".replace("0.", ".")
    else:
        # find
        if pvalue < 0.09:
            pvalue_str = f"p = {cut_small_value(pvalue)}"
        else:
            pvalue_str = f"p = {str(round(pvalue, 2))[1:]}"

    corr_str = f"{round(r, 2):.2f}".replace("0.", ".")

    return f"$r({df}) = {corr_str}, {pvalue_str}$"


def correlate_two(
    config: dict,
    data1_df: Optional[pd.DataFrame] = None,
    data2_df: Optional[pd.DataFrame] = None,
):
    """Correlate two measures for a set of participants."""
    x_measure = config["x_measure"]
    y_measure = config["y_measure"]

    config1 = {**config, "measure": x_measure}
    config2 = {**config, "measure": y_measure}

    if "config1" in config:
        config1 = {**config1, **config["config1"]}
    if "config2" in config:
        config2 = {**config2, **config["config2"]}

    if data1_df is None:
        data1_df = load_per_participant_data(config1)
    if data2_df is None:
        data2_df = load_per_participant_data(config2)

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
        latex_str = stat_latex_str_corr(
            config=config, result=result, threshold=threshold, pvalue_exact=pvalue_exact
        )
        print(latex_str)

    return result
