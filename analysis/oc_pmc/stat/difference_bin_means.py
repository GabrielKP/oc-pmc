from copy import deepcopy

import numpy as np
import pandas as pd

from oc_pmc import RATINGS_CARVER, console, get_logger
from oc_pmc.load import load_rated_wordchains, load_wordchains
from oc_pmc.stat.test_two import cut_small_value
from oc_pmc.utils import percentile_of
from oc_pmc.utils.aggregator import aggregator
from oc_pmc.utils.bootstrap import bootstrap_with_groups_get_estimates

log = get_logger(__name__)

"""
test statistic:
Mean across all time bins of the differences between group1-mean and group2-means

resampling approach:
    in each iteration, randomly assign participants to either the Integrated or
    Separated condition (I think this will be the same assignment for all bins,
    not separately for each bin);
    recompute the test statistic with the random aassignments;


statistical significance:

    compare the observed difference against the difstribution of null differences
"""


def func_load(config: dict) -> pd.DataFrame:
    # adaptive ratings
    if config.get("multiple_ratings"):
        # this allows specifications of following form:
        # "multiple_ratings": (
        #     "story",
        #     {
        #         "carver_original": {
        #             "approach": "human",
        #             "model": "moment",
        #             "story": "carver_original",
        #             "file": "all.csv",
        #         },
        #         "dark_bedroom": {
        #             "approach": "incontext_bulk",
        #             "model": "gpt-4o",
        #             "story": "dark_bedroom",
        #             "file": "0_.csv",
        #         },
        #     },
        # ),
        config = deepcopy(config)
        # match ratings file to current config
        level = config["multiple_ratings"][0]
        level_value = config[level]
        config["ratings"] = config["multiple_ratings"][1][level_value]
    return load_rated_wordchains(config)


def func_difference_bin_means(
    config: dict, data_df: pd.DataFrame
) -> tuple[float, float, float]:
    column = config["column"]  # need to specify what you want to bin
    step = config["step"]  # bin step
    # expects a dict with {column: {category1, category2}}
    comparison_dct: dict[str, list] = config["comparison_dct"]

    comparison_column, comparison_categories = list(comparison_dct.items())[0]

    if len(comparison_categories) != 2:
        raise ValueError(
            f"Can only compare two groups, but 'compare_categories'is {comparison_dct}"
        )

    # Need to determine min x value: take closest multiple to "step"
    min_x = config.get(
        "min_x",
        (min(data_df["timestamp"]) // step) * step,
    )
    max_x = config.get(
        "max_x",
        # accomodate largest value                            | don't remember
        int(np.ceil(max(data_df["timestamp"]) / step)) * step + step - 1,
    )

    # bin each datapoint
    bins = np.arange(min_x, max_x + 1, step)
    n_bins = len(bins) - 1
    bin_labels = [i for i in range(n_bins)]
    data_df["bins"] = pd.cut(data_df["timestamp"], bins=bins, labels=bin_labels)

    # count number of words in each bin
    counted_bins = data_df.groupby(["bins", comparison_column], observed=False).count()
    n_observations_per_bin = counted_bins[counted_bins.columns[0]]
    n_observations_per_bin.name = "n_bin"

    data_with_n_bins_df = pd.merge(
        data_df.reset_index(),
        n_observations_per_bin.reset_index(),
        on=["bins", comparison_column],
    )
    data_df = data_with_n_bins_df.loc[
        data_with_n_bins_df["n_bin"] > config.get("min_bin_n", 1)
    ].set_index("participantID")

    if config.get("within_participant_summary", True):
        sample_df = (
            data_df.groupby(["bins", comparison_column, "participantID"], observed=True)
            .agg({column: "mean"})
            .reset_index()
        )

        sample_wide_df = sample_df.pivot(
            columns="bins",
            index=["participantID", comparison_column],
            values=column,
        ).reset_index(1)

        # Mean across participants
        bin_mean_df = sample_wide_df.groupby(comparison_column).mean()

        # Sanity checks
        if len(bin_mean_df.index) != 2:
            raise ValueError("Something went wrong.")

        # Subtract means and compute mean
        diff_stat = (
            bin_mean_df.loc[comparison_categories[0]]
            - bin_mean_df.loc[comparison_categories[1]]
        ).mean()

        def sample_diff_stat_func_within_participants(
            sample_wide_df: pd.DataFrame,
            comparison_categories: list[str],
            comparison_column: str,
        ) -> float:
            sample_wide_df.loc[:, comparison_column] = (
                sample_wide_df[comparison_column].sample(frac=1).values
            )
            bin_mean_df = sample_wide_df.groupby(comparison_column).mean()
            return (
                bin_mean_df.loc[comparison_categories[0]]
                - bin_mean_df.loc[comparison_categories[1]]
            ).mean()  # type: ignore

        bootstrap_sample_df = sample_wide_df
        bootstrap_func = sample_diff_stat_func_within_participants
        bootstrap_args = dict(
            comparison_categories=comparison_categories,
            comparison_column=comparison_column,
        )
    else:
        raise NotImplementedError(
            "Did not implement procedure for `within_participant_summary==False`"
        )

    estimate_df = bootstrap_with_groups_get_estimates(
        config, bootstrap_sample_df.copy(), bootstrap_func, bootstrap_args
    )

    percentile = percentile_of(estimate_df, diff_stat).item()

    alternative = config.get("alternative", "two-sided")
    if alternative == "two-sided":
        pvalue = min(1 - percentile, percentile) * 2
    elif alternative == "greater":
        pvalue = 1 - percentile
    elif alternative == "less":
        pvalue = percentile
    else:
        raise ValueError(
            'config[\'alternative\'] has to be one of "two-sided", "greater", or "less"'
            f'not "{alternative}"'
        )

    if config.get("verbose", True):
        print(
            f"Data mean {diff_stat} lies in percentile: {percentile:.4f}"
            f", p = {pvalue:.4f} ({alternative})"
        )

    if config.get("plot"):
        from oc_pmc.plot.distribution import func_plot_distribution

        measure_name = config.get("measure", "statistic")

        plot_df = pd.DataFrame(estimate_df.to_numpy()[0], columns=[measure_name])
        plot_config = deepcopy(config)
        plot_config["measure"] = measure_name
        plot_config["custom_lines"] = [
            {
                "x": diff_stat,
                "annotation_text": (
                    f" {diff_stat:.2f} | {int(percentile * 100)}th percentile"
                ),
            },
        ]
        func_plot_distribution(plot_config, data_df=plot_df)
    return (diff_stat, percentile, pvalue)


def test_difference_bin_means(config: dict) -> tuple[float, float, float]:
    measure = config["measure"]
    if config.get("name1") and config.get("name2"):
        console_comment = config.get("console_comment", "")
        console.print(
            f"\n > Test_two: {measure}: {config['name1']} v"
            f" {config['name2']}{console_comment}",
            style="yellow",
        )

    # load appropriate data
    if measure == "story_relatedness":
        data1_df = load_rated_wordchains({**config, **config["config1"]})[
            ["story_relatedness", "timestamp"]
        ]
        data2_df = load_rated_wordchains({**config, **config["config2"]})[
            ["story_relatedness", "timestamp"]
        ]
    elif measure == "word_time":
        data1_df = load_wordchains({**config, **config["config1"]})[
            ["word_time", "timestamp"]
        ]
        data2_df = load_wordchains({**config, **config["config2"]})[
            ["word_time", "timestamp"]
        ]
    elif measure == "thought_entries":
        # For implementation look at difference_slope.py
        raise NotImplementedError("Function not implemented for thought_entries")
    else:
        raise ValueError(f"Invalid measure:'{measure}'")

    data1_df["comparison_column"] = "x"
    data2_df["comparison_column"] = "y"

    config = deepcopy(config)
    config["comparison_dct"] = {"comparison_column": ["x", "y"]}
    config["verbose"] = False
    config["column"] = config["measure"]

    data_df = pd.concat((data1_df, data2_df))
    difference, percentile, pvalue = func_difference_bin_means(config, data_df)

    alt = " (two-sided)"
    if config.get("alternative"):
        alt = f" ({config['alternative']})"
    print(
        f"Bootstrapped bin difference: diff = {difference:.5f},"
        f" percentile = {percentile:.5f}, p={pvalue:.5f}{alt}"
    )
    # latex string
    name1 = config.get("name1", "name1")
    name2 = config.get("name2", "name2")
    super_script = ""
    if config.get("super_script"):
        super_script = f"^{{\\text{{{config['super_script']}}}}}"

    pvalue_exact = config.get("pvalue_exact", False)
    threshold = config.get("threshold", 0.05)

    pvalue_exact = config.get("pvalue_exact", False)

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

    alt_str = ""
    if config.get("alternative") == "greater" or config.get("alternative") == "less":
        alt_str = "one-sided, "

    n_bootstrap = config["n_bootstrap"]
    print(
        f"$\\text{{diff}}{super_script}_{{\\text{{{name1} - {name2}}}}}"
        f"={round(difference, 2):.2f}, ${alt_str}permutation test,$"
        f" n = {n_bootstrap}, {pvalue_str}$"
    )

    return difference, percentile, pvalue


def difference_bin_means(config: dict):
    return aggregator(
        config=config,
        load_func=func_load,
        call_func=func_difference_bin_means,
    )


if __name__ == "__main__":
    SEPARATEDFILTER = (
        "filter",
        {"include": [("eq", "stories_distinct", "story-start")]},
    )
    INTEGRATEDFILTER = (
        "filter",
        {"exclude": [("eq", "stories_distinct", "story-start")]},
    )
    config = {
        # loading config
        "load_spec": (
            "condition",
            {
                "interference_story_spr_separated": SEPARATEDFILTER,
                "interference_story_spr_integrated": INTEGRATEDFILTER,
            },
        ),
        "story": "carver_original",
        "position": "post",
        "align_timestamp": "reading_task_end",
        "ratings": RATINGS_CARVER,
        "key_maps": {
            "condition": {
                "interference_story_spr_separated": "interference_story_spr",
                "interference_story_spr_integrated": "interference_story_spr",
            }
        },
        # script config
        "column": "story_relatedness",
        "step": 30000,
        "comparison_dct": {
            "condition": [
                "interference_story_spr_separated",
                "interference_story_spr_integrated",
            ]
        },
        # bootstrap
        "n_bootstrap": 5000,
        # plot
        "measure": "Mean Bin Difference",
        "plot": True,
        "save": True,
        "width": 1000,
        "height": 1000,
        "scale": 2.0,
    }
    difference_bin_means(config)
