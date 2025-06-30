import os
from copy import deepcopy
from numbers import Number
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from numpy.random import Generator, default_rng
from plotly.subplots import make_subplots

from oc_pmc import OUTPUTS_DIR, PLOTS_DIR, STUDYPLOTS_DIR, get_logger

log = get_logger(__name__)


def permute_theme_words(
    theme_words: str,
    rng: Optional[Generator] = None,
) -> str:
    if rng is None:
        rng = default_rng()

    if theme_words.endswith("."):
        ending = "."
        theme_words = theme_words[:-1]
    elif theme_words.endswith(","):
        ending = ","
        theme_words = theme_words[:-1]
    else:
        ending = ""
    splitted = theme_words.split(",")
    permuted = rng.permutation(splitted).tolist()
    joint = ",".join(permuted)
    return f"{joint}{ending}"


def check_make_dirs(
    paths: Union[str, list[str]],
    verbose: bool = True,
    isdir: bool = False,
) -> None:
    """Create base directories for given paths if they do not exist.

    Parameters
    ----------
    paths: list[str] | str
        A path or list of paths for which to check the basedirectories
    verbose: bool, default=True
        Whether to log the output path
    isdir: bool, default=False
        Treats given path(s) as diretory instead of only checking the basedir.
    """

    if not isinstance(paths, list):
        paths = [paths]
    for path in paths:
        if isdir and path != "" and not os.path.exists(path):
            os.makedirs(path)
        elif os.path.dirname(path) != "" and not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if verbose:
            log.info(f"Output path: {path}")


def dct_replace(dct: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    for key, value in dct.items():
        if isinstance(value, dict):
            dct[key] = dct_replace(value, old, new)
        if not isinstance(value, str):
            continue
        if old not in value:
            continue
        dct[key] = value.replace(old, new)
    return dct


def pad_with_val(
    wordchain: list[Any],
    max_len: int,
    pad_val: Any = np.nan,
    dtype: Optional[type] = None,
) -> np.ndarray:
    n_pad = max_len - len(wordchain)
    if n_pad < 0:
        raise ValueError(
            f"Rated wordchain to pad longer"
            f" ({len(wordchain)}) than max_len ({max_len})."
        )
    if dtype is None:
        dtype = type(wordchain[1])
    paddings = np.empty(n_pad, dtype=dtype)
    paddings.fill(pad_val)
    return np.concatenate((wordchain, paddings), axis=0)


def pad_with_nan(wordchain: list[float], max_len: int) -> np.ndarray:
    return pad_with_val(wordchain, max_len, pad_val=np.nan)


def wordchains_to_ndarray(
    wcs: list[list[Any]],
    pad_val: Any = np.nan,
    dtype: Optional[type] = None,
) -> np.ndarray:
    if isinstance(wcs, np.ndarray):
        return wcs

    # get max length of a wordchain
    max_len = max([len(wc) for wc in wcs])

    # pad rated wordchains to max_len
    padded_wcs = [pad_with_val(wc, max_len, pad_val, dtype=dtype) for wc in wcs]

    # shape = (n_wordchains, max_len)
    return np.array(padded_wcs)


def wordchains_to_df(
    wcs: list[list[float]],
    colname_base: Optional[str] = None,
) -> pd.DataFrame:
    wcs_np = wordchains_to_ndarray(wcs)
    if colname_base is not None:
        colnames = [f"{colname_base}_{idx}" for idx in range(wcs_np.shape[1])]
    else:
        colnames = None
    return pd.DataFrame(wcs_np, columns=colnames)


def trim_wordchain(wordchain: list[str]) -> list[str]:
    """trims the last few empty values off of wordchains"""
    reversed_clean = []
    wc_started = False
    for word in reversed(wordchain):
        if isinstance(word, str) and word.strip() != "":
            wc_started = True
        if wc_started:
            if not isinstance(word, str):
                if np.isnan(word):
                    word = ""
            reversed_clean.append(word)
    return list(reversed(reversed_clean))


def trim_wordchain_num(wordchain: list[Number]) -> list[Number]:
    """trims the last few empty values off of wordchains"""
    reversed_clean = []
    wc_started = False
    for num in reversed(wordchain):
        if not np.isnan(num):  # type: ignore
            wc_started = True
        if wc_started:
            reversed_clean.append(num)
    return list(reversed(reversed_clean))


def wordchain_df_to_list(
    wordchain_df: pd.DataFrame,
    numeric: bool = False,
) -> Sequence[Sequence[Union[str, Number]]]:
    """Converts a wordchain dataframe to a list of wordchains."""
    wordchains = wordchain_df.values.tolist()
    if numeric:
        wordchains = [trim_wordchain_num(wordchain) for wordchain in wordchains]
    else:
        wordchains = [trim_wordchain(wordchain) for wordchain in wordchains]
    return wordchains


def config_to_descriptive_string(
    config: dict,
    relevant_fields: Sequence[str] = ("story", "condition", "position"),
) -> str:
    descr = "_".join([value for key, value in config.items() if key in relevant_fields])
    if len(descr) > 0:
        return descr
    return "plot"


def save_plot(
    config: dict[str, Any],
    fig: go.Figure,
    path: Union[str, Path],
    verbose: bool = True,
):
    if "verbose" in config.keys():
        verbose = config["verbose"]
    if STUDYPLOTS_DIR:
        base = STUDYPLOTS_DIR
    else:
        base = os.path.join(OUTPUTS_DIR, PLOTS_DIR)
    output_path = os.path.join(base, path)
    check_make_dirs(output_path, verbose=False)
    fig.write_image(
        file=output_path,
        width=config.get("width"),
        height=config.get("height"),
        scale=config.get("scale"),
    )
    if verbose:
        log.info(f"Save plot to {output_path}")


def short_coefs(coefs: list) -> str:
    if len(coefs) == 0:
        return ""
    if len(coefs) == 1:
        return round(coefs[0], 2)
    return ", ".join([f"{coef:.2f}" for coef in coefs[1:]])


def cut_small_value(value: float) -> str:
    """Rounds value to first non-zero position after comma, if it is small."""
    value_str = f"{value:f}"

    if value >= abs(0.09):
        return str(round(value, 2))

    idx = 3
    # offset start if negative value is found
    if value_str[0] == "-":
        idx += 1

    while value_str[idx] == "0":
        idx += 1

    cut_value = f"{round(value, idx - 1):f}"[: idx + 1]

    # remove leading 0
    if value_str[0] == "-":
        return f"-{cut_value[2:]}"
    return cut_value[1:]


def summary_str(
    predictor_names: str,
    outcome_names: str,
    result,
    threshold: float = 0.05,
    pvalue_exact: bool = False,
) -> str:
    pvalue = result.f_pvalue
    if pvalue_exact:
        pvalue_str = f"p = {f'{pvalue:f}'[1:]}"
    elif pvalue < (threshold - 0.2 * threshold):
        # if close to threshold show exact value
        pvalue_str = f"p < {threshold}".replace("0.", ".")
    else:
        # cut off after first nonzero position
        if pvalue < 0.09:
            pvalue_str = f"p = {cut_small_value(pvalue)}"
        else:
            pvalue_str = f"p = {str(round(pvalue, 2))[1:]}"

    return (
        f"Predictor(s): {predictor_names} -> "
        f"Outcome: {outcome_names}"
        "\n"
        f"coeffs: {short_coefs(result.params)},"
        f" r(+/-) {result.rsquared**0.5:.3f},"
        f" r2: {result.rsquared:.3f},"
        f" f({result.df_model}, {result.df_resid}) = {result.fvalue:.2f},"
        f" {pvalue_str}"
    )


def percentile_of(
    samples: Union[pd.DataFrame, np.ndarray, list], value: float
) -> np.ndarray:
    if isinstance(samples, list):
        samples = np.array(samples)[None, :]
    return np.count_nonzero(samples < value, axis=1) / samples.shape[-1]


def get_summary_func(config: dict) -> Union[str, Callable]:
    summary_func_name = config.get("within_participants_summary_func")
    if summary_func_name is None:
        summary_func_name = config.get("within_participant_summary_func")

    within_participant_summary_func = "mean"
    if summary_func_name is not None:
        if summary_func_name == "count_high_sr":

            def _count_high_sr(group_sr: pd.DataFrame) -> int:
                return (group_sr > config["high_sr"]).sum().item()

            within_participant_summary_func = _count_high_sr

            # log.info(
            #     f"Setting within_participant_summary_func to"
            #     f" custom function: {summary_func_name}"
            # )

        else:
            within_participant_summary_func = summary_func_name

            # log.info(
            #     f"Setting within_participant_summary_func to pandas function:"
            #     f" {within_participant_summary_func}"
            # )
    # else:
    #     log.info(
    #         f"Setting within_participant_summary_func to pandas function:"
    #         f" {within_participant_summary_func}"
    # )

    return within_participant_summary_func


def remove_or_keep_filter_args(
    config: dict, filter_args: list[str], keep_or_remove: str
) -> dict:
    """Returns a copy of config with or without filter_args"""

    assert keep_or_remove in ["keep", "remove"]

    if keep_or_remove == "remove":
        config = deepcopy(config)
        if "include" in config:
            if not isinstance(config["include"], list):
                config["include"] = [config["include"]]
            config["include"] = [
                filter_spec
                for filter_spec in config["include"]
                if filter_spec[1] not in filter_args
            ]
        if "exclude" in config:
            if not isinstance(config["exclude"], list):
                config["exclude"] = [config["exclude"]]
            config["exclude"] = [
                filter_spec
                for filter_spec in config["exclude"]
                if filter_spec[1] not in filter_args
            ]

    if keep_or_remove == "keep":
        config = deepcopy(config)
        if "include" in config:
            if not isinstance(config["include"], list):
                config["include"] = [config["include"]]
            config["include"] = [
                filter_spec
                for filter_spec in config["include"]
                if filter_spec[1] in filter_args
            ]
        if "exclude" in config:
            if not isinstance(config["exclude"], list):
                config["exclude"] = [config["exclude"]]
            config["exclude"] = [
                filter_spec
                for filter_spec in config["exclude"]
                if filter_spec[1] in filter_args
            ]

    return config


def remove_filter_args(config: dict, filter_args: list[str]) -> dict:
    return remove_or_keep_filter_args(config, filter_args, keep_or_remove="remove")


def keep_filter_args(config: dict, filter_args: list[str]) -> dict:
    return remove_or_keep_filter_args(config, filter_args, keep_or_remove="keep")


def add_dummy_thought_entries(
    thought_entry_df: pd.DataFrame, questionnaire_df: pd.DataFrame
) -> pd.DataFrame:
    """Returns copy of thought_entry_df with dummy rows for participants who did
    not submit a thought entry.

    The dummy row is identical to the last row in thought_entry_df
    except for the 'double_press' and 'pID' field.

    If not existing, adds a column 'double_press' which is
        1 for real thought entries
        0 otherwise
    """

    if "double_press" not in thought_entry_df.columns:
        thought_entry_df["double_press"] = 1

    # get pIDs without data
    pIDs_no_te = set(questionnaire_df.index.unique()).difference(
        thought_entry_df.index.unique()
    )
    dummy_rows_ls: list[pd.Series] = list()
    for pID_no_te in pIDs_no_te:
        dummy_row = thought_entry_df.iloc[-1].copy()
        dummy_row.loc["double_press"] = 0
        dummy_row.name = pID_no_te
        dummy_rows_ls.append(dummy_row)

    thought_entry_with_dummy_df = pd.concat(
        [thought_entry_df, pd.DataFrame(dummy_rows_ls)]
    )
    thought_entry_with_dummy_df.index.name = "participantID"
    return thought_entry_with_dummy_df


def add_config_columns(
    config: dict,
    data_df: pd.DataFrame,
    config_columns: list[str],
) -> pd.DataFrame:
    """Returns copy of dataframe with specifified config columns added"""
    for column in config_columns:
        data_df[column] = config[column]
    return data_df
