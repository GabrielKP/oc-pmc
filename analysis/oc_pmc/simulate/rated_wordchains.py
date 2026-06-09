"""Generates chains of story relatedness given certain parameters."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import lognorm

from oc_pmc import console
from oc_pmc.plot.by_time_shifted import func_plot_by_time
from oc_pmc.utils.aggregator import aggregator

NOFILTER = ("filter", {})
TIMEFILTER = ("filter", {"exclude": [("gte", "timestamp", 180000)]})
POST_NOFILTER = ("position", {"post": NOFILTER})
POST_TIMEFILTER = ("position", {"post": TIMEFILTER})
SOME_STORIES_DCT = {
    "carver_original": (
        "condition",
        {
            "neutralcue2": POST_TIMEFILTER,
            "button_press": POST_TIMEFILTER,
        },
    )
}

RATINGS_CARVER = {
    "approach": "human",
    "model": "moment",
    "story": "carver_original",
    "file": "all.csv",
}


def get_stats_wordchains(plot_distributions=False):
    def func_print_stats(config: dict, data_df: pd.DataFrame):
        # transform word submission time to log
        data_df["word_time"] = np.log(data_df["word_time"])

        from distfit import distfit

        # estimate distribution that fits
        dfit = distfit(
            distr=[
                "norm",
                # "lognorm",
                # "t",
                # "uniform",
                # "expon",
                # "pareto",
            ]  # type: ignore
        )

        # wordchain length (also transform to log)
        wc_lens = data_df.groupby(["participantID", "condition"]).count()["all"]
        wc_lens = np.log(wc_lens)
        wc_len_description = wc_lens.describe()  # type: ignore
        console.print("Number of generated words", style="blue")
        print(wc_len_description)
        dfit.fit_transform(wc_lens)
        dfit.plot()

        # word submission time (mean and std)
        # > Describe the distribution of means
        word_time_means = data_df.groupby(["participantID", "condition"])[
            "word_time"
        ].mean()
        # > Describe the distribition of stds
        word_time_stds = data_df.groupby(["participantID", "condition"])[
            "word_time"
        ].std()

        word_time_mean_description = word_time_means.describe()
        word_time_std_description = word_time_stds.describe()  # type: ignore

        console.print("Submition time of words", style="blue")
        console.print("Description of mean within participants:", style="green")
        print(word_time_mean_description)
        dfit.fit_transform(word_time_means)
        dfit.plot()

        console.print("Description of std within participants:", style="green")
        print(word_time_std_description)
        dfit.fit_transform(word_time_stds)
        dfit.plot()

        # although not the best fit, the normal distribution captures all
        # log transformed data well enough:
        # n_words       : [norm   ] [0.00 sec] [RSS: 0.169295] [loc=3.929 scale=0.318]
        # n_words (best): [t      ] [0.05 sec] [RSS: 0.139306] [loc=3.931 scale=0.302]

        # word_time_mean: [norm   ] [0.00 sec] [RSS: 0.0964415] [loc=8.031 scale=0.319]

        # word_time_std: [norm   ] [0.00 sec] [RSS: 3.51511] [loc=0.483 scale=0.104]

        if plot_distributions:
            plt.show()

    from oc_pmc.load import load_rated_wordchains

    aggregator(
        {
            "load_spec": ("all", {"all": ("story", SOME_STORIES_DCT)}),
            "ratings": RATINGS_CARVER,
            "aggregate_on": "all",
            "load_func": load_rated_wordchains,
            "call_func": func_print_stats,
        }
    )


def simulate_rated_wordchains(config: dict):
    # mean of all p submission time means
    word_time_mean_mean = config.get("word_time_mean_mean", 8.031)
    # std of all p submission time means
    word_time_mean_std = config.get("word_time_mean_std", 0.319)
    # mean of all p submission time stds
    word_time_std_mean = config.get("word_time_std_mean", 0.483)
    # std of all p submission time stds
    word_time_std_std = config.get("word_time_std_std", 0.104)

    max_n_words = config.get("max_n_words", 150)
    max_timestamp = config.get("max_timestamp", 180000)

    n_participants = config["n_participants"]
    pID_basis = config.get("pID_prefix", -2000)
    story = config.get("story", "fake_story_1")
    condition = config.get("condition", "fake_condition_1")
    position = config.get("position", "fake_position_1")

    rng = np.random.default_rng(seed=config.get("seed", 42))

    # choose participants means
    p_word_time_means = rng.normal(
        word_time_mean_mean, word_time_mean_std, size=n_participants
    )
    # choose participants stds
    p_word_time_stds = rng.normal(
        word_time_std_mean, word_time_std_std, size=n_participants
    )
    p_word_time_stds[p_word_time_stds < 0] = 0

    # choose participants word submission times
    p_word_submission_times = rng.lognormal(
        np.repeat(p_word_time_means[:, None], max_n_words, 1),
        np.repeat(p_word_time_stds[:, None], max_n_words, 1),
        size=(n_participants, max_n_words),
    )

    # trim values above threshold
    p_word_timestamps = np.cumsum(p_word_submission_times, axis=1)
    p_word_submission_times[p_word_timestamps > max_timestamp] = np.nan
    p_word_timestamps[p_word_timestamps > max_timestamp] = np.nan

    # pivot into long format
    p_word_submission_times_flat = p_word_submission_times.reshape(-1)
    p_word_timestamps_flat = p_word_timestamps.reshape(-1)
    p_word_counts_flat = np.tile(np.arange(max_n_words), n_participants)

    # sample story relatedness

    NOISE = 0.5

    descriptor = f"{config['story']}/{config['condition']}/{config['position']}"
    if descriptor == "carver_original/button_press/post":

        def carver_original_button_press_post(x: np.ndarray) -> np.ndarray:
            """Mirrors button_press post with curve"""
            param_noise = 1
            a = rng.normal(5, param_noise, size=len(x))
            b = rng.normal(3.8, param_noise, size=len(x))
            c = rng.normal(2.4, param_noise, size=len(x))
            d = 0.01
            return np.minimum(
                7,
                np.maximum(
                    ((a / ((x / 10000) + b)) + c + d * (x / 10000))
                    + rng.normal(0, NOISE, size=len(x)),
                    1,
                ),
            )

        sr_function = carver_original_button_press_post

        # I am aware that the individual chain of story relatedness from real
        # participants looks very different.
        # (It is more clusters of high vs a constant drop!)
    elif descriptor == "carver_original/word_scrambled/post":
        """Mirrors word scrambled post -> flat line."""
        pID_basis = pID_basis - n_participants

        def carver_original_words_scrambled_post(x: np.ndarray) -> np.ndarray:
            return np.minimum(
                7,
                np.maximum(2.7 + rng.normal(0, NOISE, size=len(x)), 1),
            )

        sr_function = carver_original_words_scrambled_post

    elif descriptor == "carver_original/control/post":
        pID_basis = pID_basis - 2 * n_participants

        def carver_original_control_post(x: np.ndarray) -> np.ndarray:
            """A linear decrease in story relatedness"""
            param_noise = 1
            m = rng.normal(-5, param_noise, size=len(x))
            w = rng.normal(4, param_noise, size=len(x))
            return np.minimum(
                7,
                np.maximum(m * (x / 600000) + w + rng.normal(0, NOISE, size=len(x)), 1),
            )

        sr_function = carver_original_control_post

    elif descriptor == "carver_original/control_flat/post":
        pID_basis = pID_basis - 3 * n_participants

        def carver_original_control_flat_post(x: np.ndarray) -> np.ndarray:
            """A flat line of story relatedness, similar to word scrambled"""
            a = rng.normal(2.5, 1, size=len(x))
            return np.minimum(
                7,
                np.maximum(a + rng.normal(0, NOISE, size=len(x)), 1),
            )

        sr_function = carver_original_control_flat_post

    elif descriptor == "carver_original/control_flat_high/post":
        pID_basis = pID_basis - 3 * n_participants

        def carver_original_control_flat_high_post(x: np.ndarray) -> np.ndarray:
            """A flat line of story relatedness, but high"""
            a = rng.normal(5, 1, size=len(x))
            return np.minimum(
                7,
                np.maximum(a + rng.normal(0, NOISE, size=len(x)), 1),
            )

        sr_function = carver_original_control_flat_high_post

    elif descriptor == "carver_original/interference_tom/post":

        def carver_original_interference_tom_post(x: np.ndarray) -> np.ndarray:
            """Mirrors ToM post with shifted curve."""
            param_noise = 1
            a = rng.normal(5, param_noise, size=len(x))
            b = rng.normal(3.8, param_noise, size=len(x))
            c = rng.normal(2.4, param_noise, size=len(x))
            d = 0.01
            f = rng.normal(2.5, param_noise, size=len(x))
            return np.minimum(
                7,
                np.maximum(
                    ((a / ((x / 10000) + b + f)) + c + d * (x / 10000))
                    + rng.normal(0, NOISE, size=len(x)),
                    1,
                ),
            )

        sr_function = carver_original_interference_tom_post

        if config.get("simulate_shift"):
            p_word_timestamps += 30000

        # I am aware that the individual chain of story relatedness from real
        # participants looks very different.
        # (It is more clusters of high vs a constant drop!)
    else:
        raise ValueError(f"{descriptor} - cannot be simulated.")

    p_word_storyrelatedness_flat = sr_function(p_word_timestamps_flat)

    raw_data = np.stack(
        (
            p_word_counts_flat,
            p_word_submission_times_flat,
            p_word_timestamps_flat,
            p_word_storyrelatedness_flat,
        ),
        1,
    )
    pIDs_flat = np.repeat((np.arange(n_participants) + pID_basis), max_n_words)

    wordchain_df = pd.DataFrame(
        data=raw_data,
        index=pIDs_flat,
        columns=["word_count", "word_time", "timestamp", "story_relatedness"],  # type: ignore
    )
    wordchain_df.index.name = "participantID"
    wordchain_df = wordchain_df.sort_values(["participantID", "word_count"])
    wordchain_df = wordchain_df.dropna()
    wordchain_df["story"] = story
    wordchain_df["condition"] = condition
    wordchain_df["position"] = position
    wordchain_df["word_text"] = "simulated"

    return wordchain_df


def simulate_rated_wordchains_from_list(config: dict, words: list[str]):
    wordchain_df = simulate_rated_wordchains(config)
    rng = np.random.default_rng(seed=config.get("seed", 42))
    wordchain_df["word_text"] = rng.choice(words, size=len(wordchain_df), replace=True)
    return wordchain_df


if __name__ == "__main__":
    # get_stats_wordchains()

    config = {
        "n_participants": 160,
        "word_time_mean_mean": 8.031,
        "word_time_mean_std": 0.319,
        "word_time_std_mean": 0.483,
        "word_time_std_std": 0.104,
        "story": "carver_original",
        "condition": "button_press",
        "position": "post",
        # plotting
        "step": 30000,
        "color": "condition",
        "symbol": "position",
        "plotkind": "line",
        "min_bin_n": 1,
        "column": "story_relatedness",
        "show": True,
        "width": 1500,
        "height": 600,
        "bootstrap": True,
        "n_bootstrap": 100,
        "ci": 0.95,
        "y_range": [2.2, 3.9],
        "y_tickvals": ["2.5", "3.0", "3.5"],
        "y_ticktext": [2.5, 3.0, 3.5],
    }
    wordchain_df = simulate_rated_wordchains(config)

    func_plot_by_time(config, wordchain_df)
