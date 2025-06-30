import os
from collections import defaultdict
from functools import partial
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from oc_pmc import OUTPUTS_DIR
from oc_pmc.load import load_wordchains
from oc_pmc.utils import check_make_dirs


def save_dataframe(
    df: pd.DataFrame,
    path: str,
    **kwargs,
) -> None:
    df.to_csv(path, index=False, **kwargs)


def conditions_iterator(
    config,
    func: Callable,
    load_func: Callable = load_wordchains,
    form: str = "pandas",
    save_second_return_to: Optional[str] = None,
    save_func: Callable = save_dataframe,
    save_file_ending: str = "csv",
    **kwargs,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Iterates through all given conditions/stories.

    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dictionary with strings as keys.
        It is expected to have at least the key "stories":
            "stories": {
                story1: [condition1, condition2, ...],
                story2: [condition1, condition2, ...],
                ...
            }
    func : Callable
        Function which is called on every condition of every story
        with the following arguments:
            func(config, wordchains, story, condition, position, **kwargs)

        Whatever func returns as first argument is put into a nested dict:
        results[story][condition][position]
    load_func : Callable
    """
    dict_defaultdict = partial(defaultdict, dict)
    results = defaultdict(dict_defaultdict)
    for story, conditions in config["stories"].items():
        for condition in conditions:
            for position in ["post", "pre"]:
                wcs = load_func(
                    {
                        "story": story,
                        "condition": condition,
                        "position": position,
                        "story_base": story.split("_")[0],
                        **config,
                    },
                    form=form,
                )

                output = func(
                    config=config,
                    wcs=wcs,
                    story=story,
                    condition=condition,
                    position=position,
                    **kwargs,
                )

                if save_second_return_to:
                    output, data_to_save = output
                    path_output = os.path.join(
                        OUTPUTS_DIR,
                        save_second_return_to,
                        story,
                        condition,
                        f"{position}.{save_file_ending}",
                    )
                    check_make_dirs(path_output)
                    save_func(data_to_save, path_output)

                results[story][condition][position] = output

    return results  # type: ignore
