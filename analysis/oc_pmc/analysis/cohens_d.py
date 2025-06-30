import os
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
from tqdm import tqdm

from oc_pmc import get_logger
from oc_pmc.load import df_to_np, load_rated_wordchains

log = get_logger(__name__)


def bin(
    config: Dict,
    wordchains_1: np.ndarray,
    wordchains_2: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    bin_size = config.get("bin_size", 1)
    if bin_size == 1:
        return wordchains_1, wordchains_2

    # require array to be divisible by bin_size, trim it accordingly
    n_smaller_words = min(wordchains_1.shape[1], wordchains_2.shape[1])
    cutoff = n_smaller_words - (n_smaller_words % bin_size)
    wordchains_1 = wordchains_1[:, :cutoff]
    wordchains_2 = wordchains_2[:, :cutoff]

    n_bins = cutoff // bin_size

    # rearrange wordchains such that all word ratings in the same bin
    # are "below" each-other
    # split into the bins
    splitted_1 = np.split(wordchains_1, n_bins, axis=1)
    splitted_2 = np.split(wordchains_2, n_bins, axis=1)

    # join bins together
    binned_1 = np.stack(splitted_1, axis=1)
    binned_2 = np.stack(splitted_2, axis=1)
    # shape = (n_wordchains, n_bins, bin_size)
    #       = (n_wordchains, n_words // bin_size, bin_size)

    # average bins
    bin_means_1 = np.nanmean(binned_1, axis=2)
    bin_means_2 = np.nanmean(binned_2, axis=2)
    # shape = (n_wordchains, n_bins)

    return bin_means_1, bin_means_2


def cohens_d_per_word_independent(
    binned_wordchains_1: np.ndarray,
    binned_wordchains_2: np.ndarray,
) -> np.ndarray:
    # binned_wordchains_1.shape = (n_wordchains, n_bins)

    nan_mask_1 = np.isnan(binned_wordchains_1)
    nan_mask_2 = np.isnan(binned_wordchains_2)
    # there could be bins with no value value, need to handle that case
    n_means_per_bin_pos_1 = np.sum(~nan_mask_1, axis=0)
    n_means_per_bin_pos_2 = np.sum(~nan_mask_2, axis=0)
    dfs_1 = n_means_per_bin_pos_1 - 1
    dfs_2 = n_means_per_bin_pos_2 - 1

    # get first position where no bin mean exists
    max_position_1 = dfs_1.shape[0]
    if 0 in dfs_1:
        max_position_1 = np.min(np.nonzero(dfs_1 == 0)[0][0])
    max_position_2 = dfs_2.shape[0]
    if 0 in dfs_2:
        max_position_2 = np.min(np.nonzero(dfs_2 == 0)[0][0])
    max_position = min(max_position_1, max_position_2)

    # limit length to positions with at least 2 bin means
    binned_wordchains_1 = binned_wordchains_1[:, :max_position]
    binned_wordchains_2 = binned_wordchains_2[:, :max_position]
    dfs_1 = dfs_1[:max_position]
    dfs_2 = dfs_2[:max_position]

    # get variance
    var_1 = np.nanvar(binned_wordchains_1, axis=0, ddof=1)
    var_2 = np.nanvar(binned_wordchains_2, axis=0, ddof=1)

    # compute pooled variance
    pooled_var = (var_1 * dfs_1 + var_2 * dfs_2) / (dfs_1 + dfs_2)

    # average
    avg_1 = np.nanmean(binned_wordchains_1, axis=0)
    avg_2 = np.nanmean(binned_wordchains_2, axis=0)

    # cohen's d
    cohens_ds = (avg_1 - avg_2) / np.sqrt(pooled_var)
    # cohens_ds.shape = (max_positition)
    return cohens_ds


def cohens_d_per_word_dependent(
    binned_wordchains_1: np.ndarray,
    binned_wordchains_2: np.ndarray,
) -> np.ndarray:
    # binned_wordchains_1.shape = (n_wordchains, n_bins)

    nan_mask_1 = np.isnan(binned_wordchains_1)
    nan_mask_2 = np.isnan(binned_wordchains_2)
    # there could be bins with no value value, need to handle that case
    n_means_per_bin_pos_1 = np.sum(~nan_mask_1, axis=0)
    n_means_per_bin_pos_2 = np.sum(~nan_mask_2, axis=0)
    dfs_1 = n_means_per_bin_pos_1 - 1
    dfs_2 = n_means_per_bin_pos_2 - 1

    # get position in which not enough words exist
    max_position_1 = dfs_1.shape[0]
    if 0 in dfs_1:
        max_position_1 = np.min(np.nonzero(dfs_1 == 0)[0][0])
    max_position_2 = dfs_2.shape[0]
    if 0 in dfs_2:
        max_position_2 = np.min(np.nonzero(dfs_2 == 0)[0][0])
    max_position = min(max_position_1, max_position_2)

    # limit length to positions with enough words
    binned_wordchains_1 = binned_wordchains_1[:, :max_position]
    binned_wordchains_2 = binned_wordchains_2[:, :max_position]

    # subtract bin means
    diffs = binned_wordchains_1 - binned_wordchains_2
    d_mean = np.nanmean(diffs, axis=0)
    d_sd = np.nanstd(diffs, axis=0, ddof=1)

    cohens_ds = d_mean / d_sd
    # cohens_ds.shape = (max_positition)
    return cohens_ds


def cohens_d_per_word_independent_individual(
    wordchains_1: np.ndarray,
    wordchains_2: np.ndarray,
) -> np.ndarray:
    # binned_wordchains_1.shape = (n_wordchains, max_wordchain_length)

    nan_mask_1 = np.isnan(wordchains_1)
    nan_mask_2 = np.isnan(wordchains_2)
    # there could be bins with no value value, need to handle that case
    n_means_per_wordchain_1 = np.sum(~nan_mask_1, axis=1)
    n_means_per_wordchain_2 = np.sum(~nan_mask_2, axis=1)
    dfs_1 = n_means_per_wordchain_1 - 1
    dfs_2 = n_means_per_wordchain_2 - 1

    # get variance
    var_1 = np.nanvar(wordchains_1, axis=1, ddof=1)
    var_2 = np.nanvar(wordchains_2, axis=1, ddof=1)

    # compute pooled variance
    pooled_var = (var_1 * dfs_1 + var_2 * dfs_2) / (dfs_1 + dfs_2)

    # average
    wordchain_means_1 = np.nanmean(wordchains_1, axis=1)
    wordchain_means_2 = np.nanmean(wordchains_2, axis=1)

    # cohen's d
    cohens_ds = (wordchain_means_1 - wordchain_means_2) / np.sqrt(pooled_var)

    return cohens_ds


def cohens_d_per_word(
    config: Dict,
    wordchains_1: np.ndarray,
    wordchains_2: np.ndarray,
) -> np.ndarray:
    if config["paired"]:
        return cohens_d_per_word_dependent(wordchains_1, wordchains_2)
    return cohens_d_per_word_independent(wordchains_1, wordchains_2)


def cohens_d_2d(
    config: Dict,
    samples_1: np.ndarray,
    samples_2: np.ndarray,
) -> np.ndarray:
    """Returns the cohen's D for multiple bins simultaneously.

    config : Dict
        'paired': True: runs dependent sample cohen's D
    samples_1: np.ndarray, shape==(n_samples, n_bins)
        Cohen's D is computed for each bin individually, taking all values within a
        sample.
    samples_2: np.ndarray, shape==((n_samples, n_bins)
        Must be same shape as data_1, can include nan values.

    Returns
    -------
    np.ndarray, shape==((n_bins)
        Cohen's D value for each bin
    """
    return cohens_d_per_word(config, samples_1, samples_2)


def cohens_d_1d(
    config: Dict,
    sample_1: np.ndarray,
    sample_2: np.ndarray,
) -> float:
    """Returns the cohen's D for two samples.

    config : Dict
        'paired': True: runs dependent sample cohen's D
    sample_1: np.ndarray, shape==((n_samples)
        Cohen's D is computed for each bin individually, taking all values within a
        sample.
    sample_2: np.ndarray, shape==((n_samples)
        Must be same shape as data_1, can include nan values.

    Returns
    -------
    float
        Cohen's D
    """
    return cohens_d_2d(config, sample_1[:, None], sample_2[:, None])[0]


def sample(
    wordchains_1: np.ndarray,
    wordchains_2: np.ndarray,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    n_wordchains = wordchains_1.shape[0]
    # get to randomly choose new bin means at bin position
    vals_chosen = rng.integers(0, n_wordchains, wordchains_1.shape)
    # choose bin means
    resampled_1 = wordchains_1[vals_chosen, np.arange(wordchains_1.shape[1])]
    resampled_2 = wordchains_2[vals_chosen, np.arange(wordchains_1.shape[1])]
    return resampled_1, resampled_2


def cohens_d_confidence_intervals(
    config: Dict[str, Any],
    binned_wordchains_1: np.ndarray,
    binned_wordchains_2: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    quant_lower = (1 - config["ci"]) / 2
    quant_higher = config["ci"] + quant_lower

    rng = np.random.default_rng()
    cohens_ds: List[np.ndarray] = list()
    for _ in tqdm(
        range(config["n_bootstrap"]),
        desc="bootstrapping",
        total=config["n_bootstrap"],
    ):
        # resample
        resampled_1, resampled_2 = sample(
            binned_wordchains_1.copy(), binned_wordchains_2.copy(), rng
        )

        cohens_ds.append(cohens_d_per_word(config, resampled_1, resampled_2))

    cohens_ds_nd = np.stack(cohens_ds, axis=0)
    lowers = np.quantile(cohens_ds_nd, q=quant_lower, axis=0)
    uppers = np.quantile(cohens_ds_nd, q=quant_higher, axis=0)
    return lowers, uppers


def cohens_d(
    config: Dict,
    rated_wordchains_1: Optional[np.ndarray] = None,
    rated_wordchains_2: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
    # load
    if rated_wordchains_1 is None:
        rated_wordchains_1 = df_to_np(
            load_rated_wordchains(config["path_rated_wordchains_1"])
        )
    if rated_wordchains_2 is None:
        rated_wordchains_2 = df_to_np(
            load_rated_wordchains(config["path_rated_wordchains_2"])
        )
    if config.get("max_position", None) is not None:
        rated_wordchains_1 = rated_wordchains_1[:, : config["max_position"]]
        rated_wordchains_2 = rated_wordchains_2[:, : config["max_position"]]

    # bin
    binned_wordchains_1, binned_wordchains_2 = bin(
        config,
        rated_wordchains_1,
        rated_wordchains_2,
    )  # shape = (n_wordchains, n_bins)

    # Confidence intervals
    if config.get("bootstrap", True):
        ci_upper, ci_lower = cohens_d_confidence_intervals(
            config,
            binned_wordchains_1,
            binned_wordchains_2,
        )
    else:
        ci_upper = None
        ci_lower = None

    # compute
    cd = cohens_d_per_word(
        config,
        binned_wordchains_1,
        binned_wordchains_2,
    )
    return (cd, ci_upper, ci_lower)


def cohens_d_sliding_window(
    config: Dict,
    rated_wordchains_1: Optional[np.ndarray] = None,
    rated_wordchains_2: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
    # load
    if rated_wordchains_1 is None:
        rated_wordchains_1 = df_to_np(
            load_rated_wordchains(config["path_rated_wordchains_1"])
        )
    if rated_wordchains_2 is None:
        rated_wordchains_2 = df_to_np(
            load_rated_wordchains(config["path_rated_wordchains_2"]),
        )
    if config.get("max_position", None) is not None:
        rated_wordchains_1 = rated_wordchains_1[:, : config["max_position"]]
        rated_wordchains_2 = rated_wordchains_2[:, : config["max_position"]]

    # sliding window view
    n_participants = rated_wordchains_1.shape[0]
    window_shape = (n_participants, config["bin_size"])
    rated_wordchains_1_windowed = np.lib.stride_tricks.sliding_window_view(
        rated_wordchains_1, window_shape
    )[0]
    rated_wordchains_2_windowed = np.lib.stride_tricks.sliding_window_view(
        rated_wordchains_2, window_shape
    )[0]
    # shape = (n_windows, n_participants, bin_size)

    rated_wordchains_1_concat = np.concatenate(rated_wordchains_1_windowed, 1)
    rated_wordchains_2_concat = np.concatenate(rated_wordchains_2_windowed, 1)
    # shape = (n_participants, n_windows * bin_size)

    # bin
    binned_wordchains_1, binned_wordchains_2 = bin(
        config,
        rated_wordchains_1_concat,
        rated_wordchains_2_concat,
    )  # shape = (n_wordchains, n_bins)

    # Confidence intervals
    if config.get("bootstrap", True):
        ci_upper, ci_lower = cohens_d_confidence_intervals(
            config,
            binned_wordchains_1,
            binned_wordchains_2,
        )
    else:
        ci_upper = None
        ci_lower = None

    # compute
    cd = cohens_d_per_word(
        config,
        binned_wordchains_1,
        binned_wordchains_2,
    )
    return (cd, ci_upper, ci_lower)
