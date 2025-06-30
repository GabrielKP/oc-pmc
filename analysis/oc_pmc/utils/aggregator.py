import copy
from numbers import Number
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, cast

import pandas as pd

from oc_pmc.utils.types import Loadspec


def ensure_not_none(config_arg: Any, arg: Any, arg_name: str) -> Any:
    if config_arg is not None:
        return config_arg
    if arg is None:
        raise ValueError(f"Argument {arg_name} not in config. Cannot be None.")
    return arg


def aggregator(
    config: Dict[str, Any],
    load_spec: Optional[Loadspec] = None,  # type: ignore
    load_func: Optional[Callable] = None,  # type: ignore
    call_func: Optional[Callable] = None,  # type: ignore
    aggregate_on: Optional[str] = None,  # type: ignore
    no_extra_columns: bool = False,  # type: ignore
    **kwargs,
) -> List[Tuple[Dict[str, Any], Any]]:
    """Aggregates data from load_spec and calls call_func on it.


    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dictionary with strings as keys.
        All following paremeters will be overridden if passed in the config file.
    load_spec: Loadspec
        A load_spec is a tuple with the group category, and a dict containing
        the group name and its load specification. It can also contain
        a Filter specification.
        A load_spec is resolved by converting `group_category` into a key,
        `group_name` into a value. These are values are passed as `config`
        into the load_func. Multiple `group_name` entries result in multiple
        calls to load_func.

        A load_spec is definded recursively, such that for each group you can
        specify different subgroups:
            ```
            load_spec = ("group_category", {"group_name": group_load_spec})`.
            # or
            load_spec = ("filter", filterspec)
            ```
        A filter specification determines which datapoints within a load_spec
        are loaded. It is a single tuple or a list of tuples, each specifying
        which filter category to use, on which column and the value applied:
            ```
            filterspec = {
                "exclude": ("filter_command", "filter_column", filter_value),
                "include": ("filter_command", "filter_column", filter_value),
            }
            # or
            filterspec = {}
            ```
        Multiple values for filter_command exist:
            * "match": match anything to filter_value.
            * "gt": include/exclude anything greater than filter_value
            * "gte": include/exclude anything greater or equal than filter_value
            * "lt": include/exclude anything lesser than filter_value
            * "lte": include/exclude anything lesser or equal than filter_value
            * "contains": include/exclude anything that contains filter_value which is
                          a case-sensitive regex (see here)

        Example:
            ```
            shared = (
                "position",
                {"post": ("filter", {"include": ("match", "volition", "intentional")})},
            )
            load_spec = (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "suppression": shared,
                            "neutralcue": shared,
                        },
                    ),
                    # ...
                },
            )
            ```

    load_func : Callable
        Function called with a fully resolved load_spec, which is passed in form of
        key value pairs in the `config` dict.
        `load_func` has to return a pd.DataFrame.
        Extra kwargs should be passed via the config, rather than as keywords.


    call_func : Callable
        Function which is called on sub load_spec of group_category which is
        given in "aggregate_on".
        with the following arguments:
            func(config, data_df)

        Whatever func returns as first argument is put into a nested dict:
        results[story][condition][position]

    no_extra_columns : bool, default=`False`
        Whether data_df passed to call_func should have the extra columns on which
        the data was aggregated on.

    Returns
    -------
    List[Tuple[Dict[str, Any], Any]]
        A list of tuples containing the config and the result of call_func.
        The config contains the resolved load_spec as key value pairs.
        The result of call_func is the result of the call_func.
    """

    # arguments
    config = copy.deepcopy(config)
    load_spec: Loadspec = ensure_not_none(
        config.pop("load_spec", None), load_spec, "load_spec"
    )
    load_func: Callable = ensure_not_none(
        config.pop("load_func", None), load_func, "load_func"
    )
    call_func: Callable = ensure_not_none(
        config.pop("call_func", None), call_func, "call_func"
    )
    aggregate_on = config.pop("aggregate_on", aggregate_on)
    no_extra_columns = config.get("no_extra_columns", no_extra_columns)

    if aggregate_on is None:
        aggregate_on = "<all>"
        load_spec = ("<all>", {"<all>": load_spec})

    results: List[Tuple[Dict[str, Any], Any]] = list()

    iteration = [0]

    # Because of `aggregate_on` need to call load_func and call_func
    # during resolving.
    def resolve_load_call(
        load_spec: Loadspec, resolved: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        group_category, group_specs = load_spec
        # special keyword: filter: end recursion

        if group_category == "filter":
            return [{**group_specs, **resolved}], [group_specs]

        resolved_load_specs: List[Dict[str, Any]] = list()
        bottom_up_resolved_load_specs: List[Dict[str, Any]] = list()
        for group_name, group_load_spec in group_specs.items():
            resolved_group = {group_category: group_name, **resolved}
            # resolve group_load_spec
            (
                resolved_sub_group_load_specs,  # combined load_specs
                isolated_resolved_sub_group_load_specs,  # "bottom-up" load_specs
            ) = resolve_load_call(cast(Loadspec, group_load_spec), resolved_group)
            resolved_load_specs.extend(resolved_sub_group_load_specs)
            isolated_resolved_sub_group_load_specs = [
                {
                    group_category: group_name,
                    **irsbgls,
                }
                for irsbgls in isolated_resolved_sub_group_load_specs
            ]
            bottom_up_resolved_load_specs.extend(isolated_resolved_sub_group_load_specs)

            # aggregate on here, -> call load_func and call_func
            if group_category == aggregate_on:
                # call load_func
                data_dfs: List[pd.DataFrame] = list()
                sub_group_categories: List[str] = list()
                for (
                    resolved_sub_group_load_spec,
                    isolated_resolved_sub_group_load_spec,
                ) in zip(
                    resolved_sub_group_load_specs,
                    isolated_resolved_sub_group_load_specs,
                ):
                    sub_group_load_config = {
                        **copy.deepcopy(config),
                        **resolved_sub_group_load_spec,
                    }
                    group_df: pd.DataFrame = load_func(config=sub_group_load_config)
                    # add resolved group_categories as columns

                    if not no_extra_columns:
                        for (
                            sub_group_category,
                            sub_group_name,
                        ) in resolved_sub_group_load_spec.items():
                            if (
                                sub_group_category == "include"
                                or sub_group_category == "exclude"
                                # or sub_group_category == aggregate_on
                            ):
                                continue
                            # if the loaded data has the selector as a column, skip this
                            if sub_group_category in group_df.columns:
                                continue
                            group_df.insert(0, sub_group_category, sub_group_name)

                    # keep track of columns over which was aggregated
                    for (
                        sub_group_category,
                        sub_group_name,
                    ) in isolated_resolved_sub_group_load_spec.items():
                        if (
                            sub_group_category == "include"
                            or sub_group_category == "exclude"
                            or sub_group_category == aggregate_on
                        ):
                            continue
                        if sub_group_category not in sub_group_categories:
                            sub_group_categories.append(sub_group_category)

                    # rename participant ID column
                    if group_df.index.name == "ID":
                        group_df.index.rename("participantID", inplace=True)
                    data_dfs.append(group_df)

                data_df = pd.concat(data_dfs, axis=0)

                # call call_func
                group_call_config = {**copy.deepcopy(config), **resolved_group}
                group_call_config["aggregate_over"] = sub_group_categories
                group_call_config["aggregate_on"] = aggregate_on
                group_call_config["iteration"] = iteration[0]
                result = call_func(config=group_call_config, data_df=data_df)
                results.append((group_call_config, result))
                iteration[0] += 1

        return resolved_load_specs, bottom_up_resolved_load_specs

    resolve_load_call(load_spec, {})

    return results
