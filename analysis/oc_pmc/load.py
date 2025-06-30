import csv
import glob
import os
import pickle
from copy import deepcopy
from functools import partial, wraps
from numbers import Number
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union, cast

import numpy as np
import pandas as pd

from oc_pmc import (
    CORRECTIONS_DIR,
    DATA_DIR,
    EMBEDDINGS_DIR,
    OUTPUTS_DIR,
    QUESTIONNAIRE_DIR,
    RATEDWORDS_DIR,
    TIME_SPR_DIR,
    WORDCHAINS_DIR,
    get_logger,
)
from oc_pmc.utils import (
    get_summary_func,
    keep_filter_args,
    remove_filter_args,
    wordchain_df_to_list,
    wordchains_to_ndarray,
)
from oc_pmc.utils.types import Filterspec

log = get_logger(__name__)


def map_keys_wrapper(func: Callable) -> Callable:
    """Decorator to map custom keys in config, and remap output columns in dataframe.

    Only works for functions outputting dataframes.
    Will turn a config such as this:
    config = {
        ...
        "key_map": {
            "key_name": {"old_value": "new_value"}
        }
        ...
        "key_name": "old_value",
        ...
    }
    to
    config_passed_into_function = {
        ...
        "key_map": {
            "key_name": {"old_value": "new_value"}
        }
        ...
        "key_name": "new_value",
        ...
    }

    The dataframe output of the function will have all instances of 'new_value' with
    'old_value' in the column with 'key_name' replaced, as long as such a column exists.
    """

    @wraps(func)
    def mapped_keys(config, *args, **kwargs):
        key_maps = config.get("key_maps")
        active_swaps = list()  # track which keys have been mapped
        if key_maps is not None:
            config = deepcopy(config)
            for key, val_map in key_maps.items():
                if config[key] in val_map:
                    # (key, old, new)
                    active_swaps.append((key, config[key], val_map[config[key]]))
                    config[key] = val_map[config[key]]

        output_df = func(config, *args, **kwargs)

        # need to put old name back for accurate grouping if it is in there
        for key, old_name, new_name in active_swaps:
            if key in output_df.columns:
                output_df.loc[output_df[key] == new_name, key] = old_name

        return output_df

    return mapped_keys


def map_keys(func: Callable) -> Callable[..., pd.DataFrame]:
    """See map_keys_wrapper"""
    # shenanigans because of typing
    return map_keys_wrapper(func)


def map_keys_ls(func: Callable) -> Callable[..., list[str]]:
    """Same as map_keys but returns a list"""
    # shenanigans because of typing
    return map_keys_wrapper(func)


def load_questionnaire_from_path(path: str) -> pd.DataFrame:
    """Returns questionnaire data for config.

    Parameters
    ----------
    path : str
        Path to questionnaire data. Has to indclude participantID as first column.

    Returns
    -------
    questionnaire_df : pd.DataFrame
        Data containing questionnaire data.
    """
    return pd.read_csv(path, index_col=0)


def load_rated_fields(config: Dict[str, Any]) -> pd.DataFrame:
    """Returns rated fields for config.

    Paramaters
    ----------
    config : dict
        Needs following keys:
        - "story" : story
        - "condition" : experimental condition
        - "fields" : list of fields to load
        - "method"
    """
    method: str = config["method"]  # just conceptual method skeleton

    rated_fields_ls: list[pd.DataFrame] = list()
    for field in config["fields"]:
        temp_rated_fields_df = load_manual_field_ratings({**config, "field": field})

        # Get data into format with right method
        if "rater:" in method:
            # chooses ratings from one rater only
            rater_name = method.replace("rater:", "")
            field_name = f"{field}_category"
            temp_rated_fields_df = temp_rated_fields_df[[rater_name]].rename(
                columns={rater_name: field_name}
            )

            # handle multiple categories
            multiple_categories_strategy = config["multiple_category_strategy"]
            if multiple_categories_strategy == "first":
                temp_rated_fields_df[field_name] = temp_rated_fields_df[field].apply(
                    lambda cat: cat.split(",")[0] if isinstance(cat, str) else "none"
                )
            elif multiple_categories_strategy == "last":
                temp_rated_fields_df[field_name] = temp_rated_fields_df[field].apply(
                    lambda cat: cat.split(",")[-1] if isinstance(cat, str) else "none"
                )
            elif multiple_categories_strategy == "exclude":
                with pd.option_context("future.no_silent_downcasting", True):
                    temp_rated_fields_df = temp_rated_fields_df.loc[
                        ~temp_rated_fields_df[field_name]
                        .str.contains(",")
                        .fillna(False)
                        .infer_objects(copy=False)  # type: ignore
                    ]
            elif multiple_categories_strategy == "keep":
                # just keep the rows unchanged
                pass
            elif multiple_categories_strategy == "expand":
                # filter out the ones with multiple ratings
                with pd.option_context("future.no_silent_downcasting", True):
                    multi_rating = (
                        temp_rated_fields_df[field_name]
                        .str.contains(",")
                        .fillna(False)
                        .infer_objects(copy=False)  # type: ignore
                    )
                single_rated_fields_df = temp_rated_fields_df.loc[~multi_rating]
                multi_rated_fileds_df = temp_rated_fields_df.loc[multi_rating]

                # efficiency blah blah blah
                additional_single_rated_field_ls = list()
                for pID, row in multi_rated_fileds_df.iterrows():
                    for idx, category in enumerate(row[field_name].split(",")):
                        new_row_df = pd.DataFrame(
                            {field_name: [category]},
                            index=[f"{pID}-{idx}"],
                        )
                        new_row_df.index.name = "participantID"
                        additional_single_rated_field_ls.append(new_row_df)

                additional_single_rated_field_df = pd.concat(
                    additional_single_rated_field_ls
                )
                temp_rated_fields_df = pd.concat(
                    (single_rated_fields_df, additional_single_rated_field_df)
                )
            else:
                raise ValueError(
                    "config['mulitple_categories_strategy']"
                    f" = {multiple_categories_strategy} is not vlaid."
                )
        elif method == "strategy_no_strategy_strict":
            # groups participants into no_strategy group if all raters rated the
            # participant as no_strategy
            if len(temp_rated_fields_df.columns) < 2:
                raise ValueError(
                    f"Need at least two columns for config['method'] = {method}"
                )

            def strat_no_strat_strict(row) -> str:
                return "no_strategy" if all(row[1:] == "no_strategy") else "strategy"

            temp_rated_fields_df = temp_rated_fields_df.apply(
                strat_no_strat_strict, axis=1
            ).to_frame(f"{field}_category")

        elif method == "strategy_no_strategy_single":
            # groups participants into no_strategy group if one rater rated the
            # participant as no_strategy

            def strat_no_strat_single(row) -> str:
                return "no_strategy" if any(row == "no_strategy") else "strategy"

            temp_rated_fields_df = temp_rated_fields_df.apply(
                strat_no_strat_single, axis=1
            ).to_frame(f"{field}_category")

        else:
            raise ValueError(f"config['method'] == {method} is not a valid method.")
        rated_fields_ls.append(temp_rated_fields_df)

    rated_fields_df = rated_fields_ls[0].join(rated_fields_ls[1:])  # type: ignore

    return rated_fields_df


@map_keys
def load_questionnaire(config: Dict[str, Any]) -> pd.DataFrame:
    """Returns questionnaire data for config.

    Parameters
    ----------
    config : Dict[str, Any]
        Has to include fields `story` and `condition`.
        E.g. `{"story": "carver_original", "condition": "neutralcue"}`

    Returns
    -------
    questionnaire_df : pd.DataFrame
        Data containing questionnaire data.
    """
    if config.get("volition", False):
        raise DeprecationWarning(
            "`volition` in config is deprecated, use `filename` instead."
        )
    filename = config.get("filename", "summary.csv")
    dir_questionnaire = os.path.join(
        DATA_DIR,
        QUESTIONNAIRE_DIR,
        config["story"],
        config["condition"],
    )
    # path to questionnaire files
    path_questionnaire = os.path.join(dir_questionnaire, filename)
    path_questionnaire_volitionfile = os.path.join(dir_questionnaire, "volition.csv")
    path_questionnaire_groups = os.path.join(dir_questionnaire, "groups.csv")
    path_questionnaire_exclusions = os.path.join(dir_questionnaire, "exclusions.csv")
    path_questionnaire_additional = os.path.join(
        dir_questionnaire, "questionnaire_data.csv"
    )

    # load files if they exist
    questionnaire_df = load_questionnaire_from_path(path_questionnaire)
    if os.path.exists(path_questionnaire_volitionfile):
        questionnaire_volition_df = load_questionnaire_from_path(
            path_questionnaire_volitionfile
        )
        questionnaire_df = questionnaire_df.join(
            questionnaire_volition_df, rsuffix="_volition"
        )
    if os.path.exists(path_questionnaire_groups):
        questionnaire_groups_df = load_questionnaire_from_path(
            path_questionnaire_groups
        )
        questionnaire_df = questionnaire_df.join(
            questionnaire_groups_df, rsuffix="_groups"
        )
    if os.path.exists(path_questionnaire_exclusions):
        questionnaire_exclusions_df = load_questionnaire_from_path(
            path_questionnaire_exclusions
        )
        questionnaire_df = questionnaire_df.join(
            questionnaire_exclusions_df, rsuffix="_exclusions"
        )
    if os.path.exists(path_questionnaire_additional):
        questionnaire_additional_df = load_questionnaire_from_path(
            path_questionnaire_additional
        )
        questionnaire_df = questionnaire_df.join(
            questionnaire_additional_df, rsuffix="_additional"
        )
    if config.get("fields"):
        questionnaire_additional_df = load_rated_fields(config)
        questionnaire_df = questionnaire_df.join(
            questionnaire_additional_df,
            rsuffix="_category",  # move to loead_rated_fields
        )

    if config.get("filter", True):
        questionnaire_df = filter_participants(
            config,
            questionnaire_df,
            load_questionnaire_df=False,
        )
    return questionnaire_df


def check_for_type(
    filter_command: str,
    filter_column: str,
    filter_value: Union[str, Number],
    type_str: str,
):
    _type = str if type_str == "str" else Number
    if not isinstance(filter_value, _type):
        raise ValueError(
            f"filter_command {filter_command} requires {type_str} as filter_value:"
            "\n"
            f"Offending Filterspec: ({filter_command}, {filter_column}, {filter_value})"
        )


def select(
    pID_df: pd.DataFrame,
    filter_specs: List[Filterspec],
    exclude: bool = False,
) -> Tuple[pd.DataFrame, List[str]]:
    if len(filter_specs) == 0:
        return pID_df, []

    selector = None
    filtered_columns = list()
    for filter_command, filter_column, filter_value in filter_specs:
        filtered_columns.append(filter_column)
        if filter_command == "match" or filter_command == "eq":
            current_selector = pID_df[filter_column] == filter_value
        elif filter_command == "gt":
            check_for_type(filter_command, filter_column, filter_value, "num")
            current_selector = pID_df[filter_column] > filter_value
        elif filter_command == "gte":
            check_for_type(filter_command, filter_column, filter_value, "num")
            current_selector = pID_df[filter_column] >= filter_value
        elif filter_command == "lt":
            check_for_type(filter_command, filter_column, filter_value, "num")
            current_selector = pID_df[filter_column] < filter_value
        elif filter_command == "lte":
            check_for_type(filter_command, filter_column, filter_value, "num")
            current_selector = pID_df[filter_column] <= filter_value
        elif filter_command == "contains":
            check_for_type(filter_command, filter_column, filter_value, "str")
            current_selector = pID_df[filter_column].str.contains(
                cast(str, filter_value)
            )
        else:
            raise ValueError(f"Unknown filter_command: {filter_command}")

        if selector is not None:
            selector = selector | current_selector
        else:
            selector = current_selector

    if exclude:
        selector = ~cast(pd.Series, selector)

    return pID_df.loc[cast(np.ndarray, selector), :], filtered_columns


def filter_participants(
    config: Dict[str, Any],
    pID_df: pd.DataFrame,
    include: Optional[Union[Filterspec, List[Filterspec]]] = None,
    exclude: Optional[Union[Filterspec, List[Filterspec]]] = None,
    auto_exclude: bool = True,
    load_questionnaire_df: bool = True,
) -> pd.DataFrame:
    """Excludes or includes participants given conditions.

    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dict, can also pass `include` and `exclude` directly.

    pID_df : pd.DataFrame
        Dataframe containing data to filter.

    include : Optional[Union[Filterspec, List[Filterspec]]], optional
        A filter specification determines which datapoints within a load_spec
        are included. Multiple inclusion parameters are conjoined as `or`.
        Will be overriden by `config['include']`.
        The Filterspec is a single tuple or a list of tuples, each specifying
        which filter category to use, on which column and the value applied:
            ```
            filterspec = [
                ("filter_command", "filter_column", filter_value),
                ("filter_command", "filter_column", filter_value),
            ]
            # or
            filterspec = []
            ```
        Multiple values for filter_command exist:
            * "match": match anything to filter_value.
            * "gt": include/exclude anything greater than filter_value
            * "gte": include/exclude anything greater or equal than filter_value
            * "lt": include/exclude anything lesser than filter_value
            * "lte": include/exclude anything lesser or equal than filter_value
            * "contains": include/exclude anything that contains filter_value which is
              a case-sensitive regex (see here)
    exclude : Optional[Union[Filterspec, List[Filterspec]]], optional
        Same as include, but for exclusion parameters. Will be overriden by
        `config['exclude']`.
        Multiple exclusion parameters are conjoined as `or`.
    auto_exclude : bool, default = True
        If True, will automatically exclude participants which have been marked
        as excluded by the exclusions.csv data.

    Returns
    -------
    pd.DataFrame
        Dataframe with filtered data.
    """
    include = config.get("include", include)
    exclude = config.get("exclude", exclude)
    auto_exclude = config.get("auto_exclude", auto_exclude)

    if auto_exclude:
        if exclude is None:
            exclude = []
        if not isinstance(exclude, List):
            exclude = [exclude]
        exclude.insert(0, ("match", "exclusion", "excluded"))
    if include is None and exclude is None:
        return pID_df

    if load_questionnaire_df:
        q_config = config.copy()
        q_config["filter"] = False
        pID_questionnaire_df = load_questionnaire(q_config)
        questionnaire_df_cols = pID_questionnaire_df.columns.to_list()

        pID_df = pID_df.join(
            pID_questionnaire_df, on="participantID", how="left", rsuffix="right"
        )
    else:
        questionnaire_df_cols = []

    filtered_cols = list()
    try:
        # 1. include first
        if include is not None:
            if not isinstance(include, List):
                include = [include]
            pID_df, filtered_cols_include = select(pID_df, include, exclude=False)
            filtered_cols.extend(filtered_cols_include)

        # 2. exclude second
        if exclude is not None:
            if not isinstance(exclude, List):
                exclude = [cast(Filterspec, exclude)]
            pID_df, filtered_cols_exclude = select(pID_df, exclude, exclude=True)
            filtered_cols.extend(filtered_cols_exclude)
    except KeyError as err:
        log.critical(f"Data does not contain column {err}.")
        log.critical(f"Data config: {config}")
        raise KeyError(err)

    remove_df_cols = set(questionnaire_df_cols).difference(set(filtered_cols))
    if auto_exclude:
        remove_df_cols.add("exclusion")

    # 3. remove questionnaire columns, but not the ones to be kept.
    keep_columns = config.get("keep_columns")
    if keep_columns is not None:
        if not isinstance(keep_columns, List):
            keep_columns = [keep_columns]
        remove_df_cols = remove_df_cols.difference(set(keep_columns))
    remove_df_cols = list(remove_df_cols)
    pID_df = pID_df.drop(columns=remove_df_cols)

    return pID_df


def df_to_form(
    pID_df: pd.DataFrame, form: str, numeric: bool = False
) -> Union[
    Sequence[Sequence[Union[str, Number]]],
    np.ndarray,
    pd.DataFrame,
    Tuple[Sequence[Sequence[Union[str, Number]]], List[str]],
]:
    """Convert dataframe to correct form."""

    if form == "pandas":
        return pID_df
    elif form == "list":
        return wordchain_df_to_list(pID_df, numeric)
    elif form == "numpy":
        # [:, 1:] to remove cue column
        return pID_df.to_numpy()
    elif form == "list-ids":
        return (
            wordchain_df_to_list(pID_df, numeric),
            pID_df.index.to_list(),
        )
    raise ValueError(f"Incorrect form specified: {form}")


def df_to_np(pID_df: pd.DataFrame) -> np.ndarray:
    return pID_df.to_numpy()


def df_to_list(
    pID_df: pd.DataFrame, numeric: bool = False
) -> Sequence[Sequence[Union[str, Number]]]:
    return wordchain_df_to_list(pID_df, numeric)


def df_to_list_ids(
    pID_df: pd.DataFrame, numeric: bool = False
) -> Tuple[Sequence[Sequence[Union[str, Number]]], List[str]]:
    return (
        wordchain_df_to_list(pID_df, numeric),
        pID_df.index.to_list(),
    )


def load_cues_from_path(path: str, form: str = "pandas") -> pd.DataFrame:
    """Returns cues as dataframe, given path."""
    if form not in ["list", "pandas"]:
        raise ValueError(f"Incorrect form specified: {form}")

    pID_cues_df = pd.read_csv(path, index_col=0)
    pID_cues_df = pID_cues_df.iloc[:, [0]]
    return pID_cues_df


def load_cues(config: Dict, **filter_kwargs) -> pd.DataFrame:
    """Returns cues as dataframe, given config."""
    cues_path = os.path.join(
        DATA_DIR,
        WORDCHAINS_DIR,
        config["story"],
        config["condition"],
        config["position"] + ".csv",
    )  # type: ignore
    pID_cues_df = load_cues_from_path(cues_path)
    pID_cues_df = filter_participants(config, pID_cues_df, **filter_kwargs)
    return pID_cues_df


def load_corrections_from_path(
    path_corrections: str, path_discarded: Optional[str] = None
) -> Dict[str, str]:
    """Returns a dict with corrected words for given path."""
    corrections = dict()
    if os.path.isfile(path_corrections):
        corrections = load_dict(path_corrections)
    else:
        log.info(f"Corrections words file not found: {path_corrections}")
    if path_discarded is not None and os.path.isfile(path_discarded):
        discarded_words = load_word_list_txt(path_discarded)
        for discarded_word in discarded_words:
            corrections[discarded_word] = ""
    return corrections


def load_corrections() -> Dict[str, str]:
    """Returns a dict with corrected words from default location.

    The dict maps to the corrected string or an empty string if the word
    was discarded.
    """
    path_corrections = os.path.join(DATA_DIR, CORRECTIONS_DIR, "corrections.csv")  # type: ignore
    path_discarded = os.path.join(DATA_DIR, CORRECTIONS_DIR, "discarded.csv")  # type: ignore
    return load_corrections_from_path(path_corrections, path_discarded)


def load_rated_words_from_path(
    path: str,
    no_corrections: bool = False,
) -> Dict[str, float]:
    """Returns word-to-rating dict for given path.

    Lowercases words and checks for duplicates.

    Parameters
    ----------
    path : str
        Path to rated_words file.

    Returns
    -------
    rated_words_dct : Dict[str, float]
        Dictionary mapping words to ratings
    """
    ratings_dict = dict()  # saves ratings
    tracking_set = set()  # tracks which words in ratings dict (no lowercase)
    with open(path, "r") as f_in:
        csv_file = csv.reader(f_in, delimiter=",")

        # iterate through lines
        for idx, (word, rating) in enumerate(csv_file):
            if idx == 0:
                # assumes file header
                continue

            try:
                word_orig = word
                word = word.lower()

                # print error for duplicates
                if word_orig in tracking_set:
                    print(f"Error, duplicate entry: row {idx}, word {word_orig}")
                    continue
                tracking_set.add(word_orig)

                # if a lowercase/uppercase difference, choose the one which
                # is lowercase, if both have uppercase, choose first
                if word in ratings_dict and word_orig != word:
                    continue

                # add to ratings
                ratings_dict[word] = float(rating)
            except ValueError as e:
                print(f"ValueError: row {idx}, word {word}, rating {rating}")
                raise ValueError(e)

    if not no_corrections:
        corrections = load_corrections()
        for incorrect_spelling, correct_spelling in corrections.items():
            try:
                ratings_dict[incorrect_spelling] = ratings_dict[correct_spelling]
            except KeyError:
                continue

    return ratings_dict


def load_rated_words(config: Dict) -> Dict[str, float]:
    """Returns word-to-rating dict for given config.

    Lowercases words and checks for duplicates.

    Parameters
    ----------
    config : Dict
        Hast to include fields `approach`, `model`, `story`, `file`.
        E.g:
        ```py
        {
            "approach": "human",
            "model": "moment",
            "story": "carver_original",
            "file": "all.csv",
        }
        ```

    Returns
    -------
    rated_words_dct : Dict[str, float]
        Dictionary mapping words to ratings
    """
    rated_words_path = os.path.join(
        DATA_DIR,
        RATEDWORDS_DIR,
        config["approach"],
        config["model"],
        config["story"],
        config["file"],
    )
    return load_rated_words_from_path(
        rated_words_path, config.get("no_corrections", False)
    )


def load_word_list_txt(path: str) -> List[str]:
    """Loads file.txt in which each line is treated as a new word."""
    with open(path, "r") as f_in:
        lines = f_in.readlines()

    if lines[-1][-1] != "\n":
        raise ValueError("Only accept files with newline at the end.")

    return [line[:-1] for line in lines]


def load_exp(path) -> Dict:
    """Loads .pkl output file from rate_word.py"""
    with open(path, "rb") as f_in:
        return pickle.load(f_in)


def load_dict(path: str) -> Dict:
    data = pd.read_csv(path)
    dct = dict(list(data.itertuples(index=False, name=None)))
    return dct


def load_norm(path: str, lowercase: bool = True) -> pd.DataFrame:
    norm_df = pd.read_csv(
        path,
        sep="\t",
        index_col=0,
    )
    log.info(f"Loaded norm from: {path}")
    if lowercase:
        norm_df["cue"] = norm_df.index.str.lower()
        norm_df = norm_df.set_index("cue")
        norm_df.loc[:, "response"] = norm_df.loc[:, "response"].str.lower()
    return norm_df


def load_embeddings(path_or_config: Union[str, Dict]) -> List[np.ndarray]:
    if isinstance(path_or_config, dict):
        path = os.path.join(
            OUTPUTS_DIR,
            EMBEDDINGS_DIR,
            path_or_config["approach"].replace(
                "<story_base>",
                path_or_config.get("story_base", "<story_base_not_in_config>"),
            ),
            path_or_config["story"],
            path_or_config["condition"],
            f"{path_or_config['position']}.pkl",
        )
    else:
        path = path_or_config

    import pickle

    with open(path, "rb") as f_in:
        embeddings: List[np.ndarray] = pickle.load(f_in)

    return embeddings


def load_time_words_word_time(
    timing_data: pd.DataFrame,
) -> Tuple[List, List]:
    timing_data = timing_data.sort_values("word_count", ascending=True)
    timing_data = timing_data.loc[:, ["word_time"]]
    timing_data.rename(columns={"word_time": "time"}, inplace=True)

    # group by subject, and extract as list
    wcs_word_times: List[List[int]] = []
    wcs_id: List[str] = []
    for group_name, group_df in timing_data.groupby("ID", sort=True):
        # make sure the time is not cumulative
        wcs_word_times.append(group_df.loc[:, "time"].tolist())
        wcs_id.append(str(group_name))

    return wcs_word_times, wcs_id


# def load_time_words_key_onset(
#     timing_data: pd.DataFrame,
# ) -> Tuple[List, List]:
#     def choose_onset(ls_str: str) -> Optional[int]:
#         ls = literal_eval(ls_str)
#         return ls[0] if len(ls) > 0 else None

#     # when participants submit empty strings, key_onset is empty
#     # need to replace those with submission times
#     word_times = timing_data.loc[:, ["ID", "word_time"]]

#     timing_data = timing_data.loc[:, ["ID", "key_onsets"]]
#     timing_data["key_onsets"] = timing_data["key_onsets"].apply(
#         lambda ls_str: choose_onset(ls_str)
#     )
#     timing_data.rename(columns={"key_onsets": "time"}, inplace=True)

#     indcs_empty_str = pd.isna(timing_data["time"])
#     timing_data.loc[indcs_empty_str, "time"] = word_times.loc[
#         indcs_empty_str, "word_time"
#     ]

#     # sort by word number
#     timing_data = timing_data.sort_values("time", ascending=True)
#     word_times = word_times.sort_values("word_time", ascending=True)

#     # group by subject: subtract previous submit_time from key_onset
#     wcs_word_times: List[List[int]] = []
#     wcs_id: List[int] = []
#     for (group_name_onset, group_df_onset), (
#         group_name_submit,
#         group_df_submit,
#     ) in zip(
#         timing_data.groupby("ID", sort=True),
#         word_times.groupby("ID", sort=True),
#     ):
#         # make sure the time is not cumulative
#         group_df_onset.iloc[1:, 1] = (
#             group_df_onset.iloc[1:, 1].to_numpy()
#             - group_df_submit.iloc[:-1, 1].to_numpy()
#         )
#         wcs_word_times.append(group_df_onset.loc[:, "time"].tolist())
#         wcs_id.append(group_name_onset)

#     return wcs_word_times, wcs_id


def load_time_words_from_path(
    path: str,
    timing_mode: str,
) -> pd.DataFrame:
    """Return word timing data saved in path"""

    timing_data = pd.read_csv(path, index_col=0)

    # depending on mode extract correct columns
    if timing_mode == "word_time":
        wcs_word_times, wcs_id = load_time_words_word_time(timing_data)
    elif timing_mode == "key_onset":
        raise NotImplementedError("key_onset not implemented yet")
        # wcs_word_times, wcs_id = load_time_words_key_onset(timing_data)
    else:
        raise ValueError(f"Unknown timing_mode: {timing_mode}")

    wcs_word_times_padded = wordchains_to_ndarray(wcs_word_times, dtype=float)

    colnames = [f"time {x}" for x in range(len(wcs_word_times_padded[0]))]
    word_times_df = pd.DataFrame(
        data=np.array(wcs_word_times_padded), columns=colnames, index=wcs_id
    )
    word_times_df.index.name = "participantID"
    return word_times_df


def load_time_words(config: Dict[str, Any], **filter_kwargs) -> pd.DataFrame:
    path_time_words = os.path.join(
        OUTPUTS_DIR,
        "time_words",
        config["story"],
        config["condition"],
        f"{config['position']}.csv",
    )  # type: ignore
    timing_mode = config.get("timing_mode")
    if timing_mode is None:
        timing_mode = "word_time"
        log.debug("Setting timing_mode to `word_time`")
    pID_timing_df = load_time_words_from_path(path_time_words, timing_mode=timing_mode)
    pID_timing_df = filter_participants(config, pID_timing_df, **filter_kwargs)

    return pID_timing_df


@map_keys_ls
def load_words(config: Optional[dict] = None, corrections: bool = False) -> List[str]:
    """Returns a list of unique words for words in specified story/condition/position.

    Parameters
    ----------
    config : dict | None
        If nothing is specified, then words for all stories/conditions/positions are
        returned. If `story` is specified, words for all conditions/positions in the
        story are returned. If `story` and `condition` is specified, words for all
        positions in the story/condition combination are returned. If story/
        conditions/position is specified, all words for that combination are returned.
    corrections : bool, default = False
        Whether to apply corrections to the words.
    """

    if config is None:
        config = dict()

    if "story" in config and "condition" in config and "post" in config:
        base_dir = os.path.join(
            DATA_DIR,
            "time_words",
            config["story"],
            config["condition"],
            config["position"],
        )
        paths_words = glob.glob(f"{base_dir}.csv", recursive=True)
    if "story" in config and "condition" in config:
        base_dir = os.path.join(
            DATA_DIR, "time_words", config["story"], config["condition"]
        )
        paths_words = glob.glob(f"{base_dir}/*.csv", recursive=True)
    elif "story" in config:
        base_dir = os.path.join(DATA_DIR, "time_words", config["story"])
        paths_words = glob.glob(f"{base_dir}/*/*.csv", recursive=True)
    else:
        base_dir = os.path.join(DATA_DIR, "time_words")
        paths_words = glob.glob(f"{base_dir}/*/*/*.csv", recursive=True)

    words: List[str] = list()
    for path in paths_words:
        pID_words_df = pd.read_csv(path, index_col=0)
        words.extend(pID_words_df["word_text"])
    words = [
        str(word)
        for word in words
        if (word is not None and word != "" and word != np.nan)
    ]
    words = sorted(list(set(words)))
    log.info(f"Loaded {len(words)} words from {len(paths_words)} files")

    if corrections:
        corrections_dct = load_corrections()
        normalized_words = set()
        n_corrected = 0
        for word in words:
            word = str(word).lower().strip()
            if word in corrections_dct:
                word = corrections_dct[word]
                n_corrected += 1
            normalized_words.add(word)
        words = list(normalized_words)
        log.info(f"Corrected {n_corrected} words.")

    log.info(f"Loaded {len(words)} words from {len(paths_words)} files in {base_dir}")
    return words


def add_questionnaire_columns(
    config: Dict, data_df: pd.DataFrame, columns_to_add: Optional[Union[str, List]]
) -> pd.DataFrame:
    """Adds unfiltered questionnaire data columns to data_df"""
    if columns_to_add is None:
        return data_df

    pID_questionnaire_df = load_questionnaire({**config, "filter": False})
    remove_df_cols = set(pID_questionnaire_df.columns.to_list())
    data_df = data_df.join(pID_questionnaire_df, how="left")

    # need to handle columns which are not kept
    if columns_to_add is not None:
        if not isinstance(columns_to_add, List):
            columns_to_add = [columns_to_add]
        remove_df_cols = remove_df_cols.difference(set(columns_to_add))
    remove_df_cols = list(remove_df_cols)
    data_df = data_df.drop(columns=remove_df_cols)

    return data_df


@map_keys
def load_wordchains(config: Dict[str, Any]) -> pd.DataFrame:
    """Returns words or wordchains for config keys: story, condition, position.
    Can apply a function before loading.
    The DATA_DIR in .env has to be set appropriatly.

    Parameters
    ----------
    config: Dict[str, Any]
        Needs to contain 'story', 'condition' and 'position'.

    Returns
    -------
    words_or_wordchains : pd.Dataframe
        A dataframe with participantID as index, containing either
            A row for each word and it's data if 'return_' is in
                ["raw", "filter", "func"]
            A row for each participant with all the words, if 'return_' is "merged".
    """
    path_words = os.path.join(
        OUTPUTS_DIR,
        "time_words",
        config["story"],
        config["condition"],
        f"{config['position']}.csv",
    )  # type: ignore

    pID_words_df = pd.read_csv(path_words, index_col=0)

    if config.get("corrections", True):
        corrections = load_corrections()

        def _do_corrections(word: str) -> str:
            try:
                return corrections[str(word).lower().strip()]
            except KeyError:
                return str(word).lower()

        pID_words_df["word_text"] = pID_words_df["word_text"].apply(_do_corrections)

    if config.get("align_timestamp", False):
        # only works for post free association phase!
        pID_questionnaire_df = load_questionnaire({**config, "filter": False})
        alignment = (
            pID_questionnaire_df[config["align_timestamp"]]
            - pID_questionnaire_df["free_association_post_task_start"]
        )
        alignment.name = "timestamp_offset"
        pID_words_df = pID_words_df.join(alignment, how="left")
        pID_words_df["timestamp"] = (
            pID_words_df["timestamp"] - pID_words_df["timestamp_offset"]
        )

    if config.get("filter", True):
        pID_words_df = filter_participants(config, pID_words_df)

    return pID_words_df


def load_wordchains_dct_ls(config: dict) -> dict[str, list[list[str]]]:
    """Returns wordchains in dictionary and as lists (for backwards compatibility)."""
    wordchains_dct = dict()
    wordchains_dct["post"] = list()
    wordchains_dct["pre"] = list()
    post_df = load_wordchains({**config, "position": "post"})
    for _, p_df in post_df.groupby("participantID"):
        wordchains_dct["post"].append(p_df["word_text"].to_list())

    pre_df = load_wordchains({**config, "position": "pre"})
    for _, p_df in pre_df.groupby("participantID"):
        wordchains_dct["pre"].append(p_df["word_text"].to_list())

    return wordchains_dct


def load_wordchains_dct_np(config: dict) -> dict[str, np.ndarray]:
    """This is convoluted and slow but it works (for backwards compatibility)."""
    wordchains_dct = load_wordchains_dct_ls(config)
    wordchains_dct_np = dict()
    wordchains_dct_np["post"] = wordchains_to_ndarray(wordchains_dct["post"])
    wordchains_dct_np["pre"] = wordchains_to_ndarray(wordchains_dct["pre"])
    return wordchains_dct_np


def load_event_theme_rated_wordchains_np(config: dict) -> dict[str, np.ndarray]:
    """For legacy reasons"""

    ratings_carver_moment = {
        "approach": "human",
        "model": "moment",
        "story": "carver_original",
        "file": "all.csv",
    }
    ratings_carver_theme = {
        "approach": "human",
        "model": "theme",
        "story": "carver_original",
        "file": "all.csv",
    }
    r_wc_dct = dict()
    r_wc_dct["moment_pre"] = df_to_np(
        load_rated_wordchains(
            {**config, "position": "pre", "ratings": ratings_carver_moment}
        )
    )
    r_wc_dct["moment_post"] = df_to_np(
        load_rated_wordchains(
            {**config, "position": "post", "ratings": ratings_carver_moment}
        )
    )
    r_wc_dct["theme_pre"] = df_to_np(
        load_rated_wordchains(
            {**config, "position": "pre", "ratings": ratings_carver_theme}
        )
    )
    r_wc_dct["theme_post"] = df_to_np(
        load_rated_wordchains(
            {**config, "position": "post", "ratings": ratings_carver_theme}
        )
    )
    return r_wc_dct


@map_keys
def load_rated_wordchains(config: Dict) -> pd.DataFrame:
    """Returns rated words or word chains.

    Parameters
    ----------
    config: Dict[str, Any]
        Needs to contain 'story', 'condition', 'position', 'ratings' and 'column':
        'story': str
        'conditon': str
        'position': str
        'ratings': Dict
            A dict with keys 'approach', 'model', 'story', 'file' (all strings)
            describing which ratings to use.
        'simulated': bool
            If true, will simulate the wordchains.

    Returns
    -------
    words_or_wordchains : pd.Dataframe
        A dataframe with participantID as index, containing either
            A row for each word and it's data (e.g. timestamp, word_text,
            story_relatedness).
    """
    ratings_dict = load_rated_words(config["ratings"])

    pID_words_df = load_wordchains(config)

    def _rate_word(row: pd.Series) -> float:
        word = row["word_text"]
        word = str(word).lower().strip()

        try:
            rating = ratings_dict[word]
        except KeyError:
            rating = np.nan
        return rating

    # rate words
    pID_words_df["story_relatedness"] = pID_words_df.apply(_rate_word, axis=1)

    if config.get("verbose", False):
        n_nans = pID_words_df["story_relatedness"].isna().sum()
        n_participants = len(pID_words_df.index.unique())
        log.info(
            (
                f"{config['story']} | {config['condition']} | {config['position']}"
                f" | words: {len(pID_words_df)} | nans: {n_nans}"
                f" | proportion: {(n_nans / len(pID_words_df)):.2f}"
                f" | N: {n_participants}"
            )
        )

    return pID_words_df


@map_keys
def load_thought_entries(config: Dict[str, Any]) -> pd.DataFrame:
    path_double_presses = os.path.join(
        OUTPUTS_DIR,
        "double_press",
        config["story"],
        config["condition"],
        f"{config['position']}.csv",
    )

    pID_thought_entries_df = pd.read_csv(path_double_presses, index_col=0)

    if config.get("align_timestamp", False):
        # only works for post free association phase!
        pID_questionnaire_df = load_questionnaire({**config, "filter": False})
        alignment = (
            pID_questionnaire_df[config["align_timestamp"]]
            - pID_questionnaire_df["free_association_post_task_start"]
        )
        alignment.name = "timestamp_offset"
        pID_thought_entries_df = pID_thought_entries_df.join(alignment, how="left")
        pID_thought_entries_df["timestamp"] = (
            pID_thought_entries_df["timestamp"]
            - pID_thought_entries_df["timestamp_offset"]
        )

    if config.get("filter", True):
        pID_thought_entries_df = filter_participants(config, pID_thought_entries_df)

    return pID_thought_entries_df


@map_keys
def load_n_thought_entries(
    config: Dict[str, Any],
    te_filter: Dict[str, Any],
    questionnaire_filter: Dict[str, Any],
) -> pd.DataFrame:
    """Returns the number of thought entries, taking into account participants who
    did not report any thought entry.

    Parameters
    ----------
    config: dict
        Needs to have following keys: "story", "condition", "position".
        Optional keys:
            "filter": can filter by timestamp to get a count of thought entries
                      in a timeframe.
    te_filter: dict
        The filter for thought entries may be conflicting with the questionnaire filter
        arguments, thus you need to give both separately.
    questionnaire_filter: dict
        The filter for thought entries may be conflicting with the questionnaire filter
        arguments, thus you need to give both separately.
    """
    te_filter = te_filter or dict()
    questionnaire_filter = questionnaire_filter or dict()

    pID_thought_entries_df = load_thought_entries({**config, **te_filter})
    questionnaire_df = load_questionnaire({**config, **questionnaire_filter})

    nonzero_count_sr = pID_thought_entries_df.groupby("participantID")[
        "timestamp"
    ].count()

    pID_te_count_df = pd.DataFrame(
        data=np.zeros(len(questionnaire_df.index)),
        index=questionnaire_df.index,
        columns=["thought_entries"],
    )
    pID_te_count_df.loc[nonzero_count_sr.index.to_list(), "thought_entries"] = (
        nonzero_count_sr
    )

    pID_te_count_df = pID_te_count_df.join(questionnaire_df)

    return pID_te_count_df


def load_thought_entries_and_questionnaire(
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns thought_entry_df and questionnaire_df, both with appropriate
    exclusions.

    The thought_entry_df alone is not sufficient if data is to be binned later,
    as it does not contain participants who did not produce a thought entry within
    a bin or over the entire timeframe.
    Thus you need to get the questionnaire_df as well.
    """
    # as questionnaire data & te data need to be kept separate, filter them
    # separately.

    # double press columns are the only potential filter args for te_df
    # this also means that you cannot filter for any of these
    # for questionnaire data.
    double_press_columns = [
        "timestamp",
        "current_double_press_count",
        "time_since_last_word_start",
        "word_count",
        "word_text",
        "word_key_onsets",
        "word_key_chars",
        "word_key_codes",
        "word_double_press_count",
        "double_press",
    ]

    te_config = keep_filter_args(config, filter_args=double_press_columns)
    te_df = load_thought_entries(te_config)
    te_df["double_press"] = 1

    # need to append a list of all included participants
    quest_config = remove_filter_args(config, filter_args=double_press_columns)
    quest_df = load_questionnaire(quest_config)

    # need to filter participants given filter args
    pID_filtered = set(quest_df.index).intersection(te_df.index)
    te_df = te_df.loc[list(pID_filtered)]

    return te_df, quest_df


def load_per_participant_data(config: dict) -> pd.DataFrame:
    measure = config.get("measure_name")
    if measure is None:
        measure = config["measure"]

    old_measure = measure
    if config.get("custom_measure"):
        measure = config["custom_measure"]

    if measure == "story_relatedness":
        data_df = load_rated_wordchains(config)[["story_relatedness"]]
    elif measure == "word_time":
        data_df = load_wordchains(config)[["word_time"]]
    elif measure == "thought_entries":
        # hi :)
        # you will need a 'te_filter' and 'te_questionnaire' entry in your config
        data_df = load_n_thought_entries(
            config,
            # prioritize custom te/questionnaire filter
            te_filter=config.get("te_filter"),
            questionnaire_filter=config.get("questionnaire_filter"),
        )[["thought_entries"]]
    else:
        config = deepcopy(config)
        if config.get("exclude"):
            config["exclude"] = [
                rule for rule in config["exclude"] if rule[1] not in ["timestamp"]
            ]
        try:
            data_df = load_questionnaire(config)[[measure]]
        except KeyError as err:
            raise ValueError(
                f"Invalid key '{measure}' or measure not implemented: {err}"
            )

    # within participant mean
    if measure in ["story_relatedness", "word_time"]:
        data_df = data_df.groupby("participantID").aggregate(
            {measure: get_summary_func(config)}
        )

    if data_df.dtypes.iloc[0] == bool:  # noqa:E721
        data_df = data_df.astype(int)

    if config.get("custom_measure"):
        data_df[old_measure] = data_df[measure]

    data_df = data_df.sort_values("participantID")

    return data_df


def load_cluster(config: Dict[str, Any]) -> pd.DataFrame:
    filename = config["position"]
    filename += f"_{config['n_consecutive_words']}_{config['high_sr_threshold']}"
    if config.get("strict"):
        filename += "_strict"
    if config.get("filepostfix"):
        filename += "_" + cast(str, config["filepostfix"])
    cluster_path = os.path.join(
        DATA_DIR,
        "clusters",
        config["story"],
        config["condition"],
        f"{filename}.csv",
    )

    cluster_df = pd.read_csv(cluster_path, index_col=0)
    return cluster_df


def load_time_spr(config: Dict[str, Any]) -> pd.DataFrame:
    time_spr_path = os.path.join(
        DATA_DIR,
        TIME_SPR_DIR,
        config["story"],
        config["condition"],
        "spr.csv",
    )

    time_spr_df = pd.read_csv(time_spr_path, index_col=0)

    if config.get("filter", True):
        time_spr_df = filter_participants(
            config,
            time_spr_df,
            load_questionnaire_df=True,
        )
    return time_spr_df


def load_theme_words(
    config: Dict[str, Any], raw: bool = False
) -> Union[pd.DataFrame, List[str]]:
    """Returns theme words.

    Parameters
    ----------
    config : Dict
        Has to contain 'story' and can contain
        'extended' or 'filter'.
    raw : bool, default = False
        Whether to return the raw keywords each participant returns as
        pd.Dataframe. If set to False (default) then a list of the top 10
        theme words is returned or, all theme words in order of occurrence
        ('extended': True in config)
    """
    if raw:
        theme_words_path = os.path.join(
            DATA_DIR,
            "theme_words",
            config["story"],
            "theme_words_raw.csv",
        )

        theme_words_df = pd.read_csv(theme_words_path, index_col=0)
        if config.get("filter", True):
            theme_words_df = filter_participants(
                config,
                theme_words_df,
                load_questionnaire_df=True,
            )
        return theme_words_df

    extended = "_extended" if config.get("extended") else ""
    theme_words_path = os.path.join(
        DATA_DIR,
        "theme_words",
        config["story"],
        f"theme_words{extended}.txt",
    )
    theme_words = load_word_list_txt(theme_words_path)
    return theme_words


def load_manual_field_ratings(config: dict) -> pd.DataFrame:
    manual_ratings_dir = os.path.join(
        DATA_DIR, "manual", "fields", config["story"], config["condition"]
    )
    field = config["field"]
    field_colname = f"{field}_group"
    ratings_base_filename = f"{field}_{config['condition']}"
    filename_template = f"{ratings_base_filename}_*.csv"

    # load basefile
    field_ratings_pd = pd.read_csv(
        os.path.join(manual_ratings_dir, f"{ratings_base_filename}.csv"), index_col=0
    )
    field_ratings_pd.drop(columns=[field_colname], inplace=True)

    # load, process and combine ratings
    category_map: Optional[dict[str, int]] = config.get("category_map")

    if category_map is not None:  # just to get rid of the typing warnings

        def cat_to_int(rater_name: str, category: Union[str, float]) -> int:
            if isinstance(category, float):
                # rater_name such that nan categories never can match
                category = f"nan_{rater_name}"

            # Handle multiple categories
            category_ints = []
            for category in category.split(","):  # type: ignore
                if category not in category_map:
                    category_map[category] = len(category_map)
                category_ints.append(category_map[category])
            category_number = sum(
                [
                    10**exponent * number
                    for exponent, number in enumerate(
                        sorted(category_ints, reverse=True)
                    )
                ]
            )
            return category_number

    seletected_raters = config.get("raters")
    paths = glob.glob(os.path.join(manual_ratings_dir, filename_template))
    for path in paths:
        rater_name = (
            os.path.basename(path)
            .split(".")[-2]
            .replace(f"{ratings_base_filename}_", "")
        )

        if "for" in rater_name:
            # empty rate file
            continue
        if seletected_raters is not None and rater_name not in seletected_raters:
            continue

        rater_ratings_pd = pd.read_csv(path, index_col=0).rename(
            columns={field_colname: rater_name}
        )

        # remove all no_strategy tags that are together with other categories
        rater_ratings_pd[rater_name] = rater_ratings_pd[rater_name].apply(
            lambda rater_label: ",".join(
                [
                    category
                    for category in rater_label.split(",")
                    if category != "no_strategy" or len(rater_label.split(",")) < 2
                ]
            )
            if isinstance(rater_label, str)
            else rater_label
        )

        # raise error for nan values
        nan_ids = (
            np.arange(len(rater_ratings_pd))[rater_ratings_pd[rater_name].isna()] + 2
        )
        if len(nan_ids) > 0:
            print(
                "WARNING"
                f" | {config['story']} | {config['condition']} | {config['field']}"
                f" | {rater_name} | Rows without rating: {nan_ids}"
            )

        # replace categories with integers
        if category_map is not None:
            rater_ratings_pd[rater_name] = rater_ratings_pd[rater_name].apply(
                partial(cat_to_int, rater_name)  # type: ignore
            )

        field_ratings_pd = field_ratings_pd.join(rater_ratings_pd[rater_name])

    if category_map is not None:
        print(f"Category map: {category_map}")

    return field_ratings_pd
