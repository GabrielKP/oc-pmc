from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from tqdm import tqdm

from oc_pmc import get_logger

log = get_logger(__name__)


def bootstrap_1d(
    config: Dict, sample: Union[List, np.ndarray], func: Callable
) -> Tuple[float, float]:
    """Bootstrap over a 1 dimensional sample.

    Parameters
    ----------
    config : Dict
        Config dict with fields:
            n_bootstrap : int
                amount of iterations
            ci : float
                confidence interval
            bootstrap_seed : int
                seed for random number generator used to resample
    sample : List or np.ndarray
        1 dimensional sample of observations
    func : Callable
        Function to compute summary statistic of interest
    """
    # setup
    rng = np.random.default_rng(config.get("bootstrap_seed"))
    if "n_bootstrap" not in config:
        log.info("Setting n_bootstrap to 5000")
    n_bootstrap = config.get("n_bootstrap", 5000)

    # bootstrapping
    estimate_population = list()
    for _ in tqdm(range(n_bootstrap), desc="bootstrapping", total=n_bootstrap):
        resampled = rng.choice(sample, size=len(sample), replace=True)
        estimate_population.append(func(resampled))

    ci = config.get("ci", 0.95)
    quant_lower = (1 - ci) / 2
    quant_higher = ci + quant_lower
    estimate_population = np.stack(estimate_population, axis=0)
    lowers = np.quantile(estimate_population, q=quant_lower, axis=0)
    uppers = np.quantile(estimate_population, q=quant_higher, axis=0)
    return lowers, uppers


def resample_2d(
    sample: np.ndarray,
    nums_per_col: np.ndarray,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    # for every position (across participants), choose a sample with replacement
    vals_chosen = np.empty(sample.shape, dtype=np.int64)
    for idx_position, nums_in_col in enumerate(nums_per_col):
        vals_chosen[:nums_in_col, idx_position] = rng.integers(
            0, nums_in_col, nums_in_col
        )
        vals_chosen[nums_in_col:, idx_position] = -1
    return sample[vals_chosen, np.arange(sample.shape[1])]  # type: ignore


def bootstrap_2d(config: Dict, sample: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng()

    # sample.shape = (n_wordchains, n_positions)
    # problem: for higher n_positions, there is a lot of nan's
    # solution: sort all nan's to the "bottom"

    nums_per_col = np.sum(~np.isnan(sample), axis=0)

    print(f"nans in each bin: {nums_per_col}")

    sorted_sample = sample[np.argsort(sample, axis=0), np.arange(sample.shape[1])]

    estimate_population_ls: List = list()

    for _ in tqdm(
        range(config["n_bootstrap"]),
        desc="bootstrapping",
        total=config["n_bootstrap"],
    ):
        # resample
        resampled = resample_2d(sorted_sample, nums_per_col, rng)

        estimate_population_ls.append(np.nanmean(resampled, axis=0))

    quant_lower = (1 - config["ci"]) / 2
    quant_higher = config["ci"] + quant_lower
    estimate_population = np.stack(estimate_population_ls, axis=0)
    lowers = np.quantile(estimate_population, q=quant_lower, axis=0)
    uppers = np.quantile(estimate_population, q=quant_higher, axis=0)
    return lowers, uppers


def bootstrap_with_groups_get_estimates(
    config: Dict[str, Any],
    data_df: pd.DataFrame,
    sample_agg_func: Callable,
    aggregation_args: Optional[Dict] = None,
) -> pd.DataFrame:
    estimates: List[pd.DataFrame] = []
    for _ in tqdm(
        range(config["n_bootstrap"]),
        desc="bootstrapping",
        total=config["n_bootstrap"],
        position=config.get("bootstrap_tqdm_position"),
        leave=config.get("bootstrap_tqdm_leave", True),
    ):
        if aggregation_args is not None:
            estimates.append(sample_agg_func(data_df, **aggregation_args))
        else:
            estimates.append(sample_agg_func(data_df))

    if not isinstance(estimates[0], (pd.DataFrame, pd.Series)):
        return pd.DataFrame(np.array(estimates)[None, :])

    return pd.concat(estimates, axis=1)


def get_confidence_intervals(
    config: dict, estimates_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    quant_lower = (1 - config["ci"]) / 2
    quant_higher = config["ci"] + quant_lower

    lowers = np.nanquantile(estimates_df, q=quant_lower, axis=1)
    uppers = np.nanquantile(estimates_df, q=quant_higher, axis=1)
    lowers_df = pd.DataFrame(lowers, index=estimates_df.index, columns=["ci_lower"])
    uppers_df = pd.DataFrame(uppers, index=estimates_df.index, columns=["ci_upper"])
    return lowers_df, uppers_df


def bootstrap_with_groups(
    config: Dict[str, Any],
    data_df: pd.DataFrame,
    sample_agg_func: Callable,
    aggregation_args: Optional[Dict] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    estimates_df = bootstrap_with_groups_get_estimates(
        config, data_df, sample_agg_func, aggregation_args
    )
    return get_confidence_intervals(config, estimates_df)
