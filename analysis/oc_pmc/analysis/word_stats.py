import os

import pandas as pd

from oc_pmc import OUTPUTS_DIR, PLOTS_DIR, STUDYPLOTS_DIR
from oc_pmc.load import load_corrections, load_rated_wordchains, load_rated_words
from oc_pmc.utils import check_make_dirs
from oc_pmc.utils.aggregator import aggregator

NOFILTER = ("filter", {})
TIMEFILTER = ("filter", {"exclude": [("gte", "timestamp", 180000)]})

POST_NOFILTER = ("position", {"post": NOFILTER})
POST_TIMEFILTER = ("position", {"post": TIMEFILTER})
PRE_POST_NOFILTER = ("position", {"post": NOFILTER, "pre": NOFILTER})
PRE_POST_TIMEFILTER = ("position", {"post": TIMEFILTER, "pre": TIMEFILTER})


def func_load(config: dict):
    return load_rated_wordchains(config)


def func_compute_word_stats(config: dict, data_df: pd.DataFrame):
    # Handle paths
    if STUDYPLOTS_DIR:
        base = STUDYPLOTS_DIR
    else:
        base = os.path.join(OUTPUTS_DIR, PLOTS_DIR)
    study = config.get("STUDY", "")
    dirs = [base, study, "word_stats"]
    for path_key in {"story", "condition"}.difference(
        set(config.get("aggregate_over", []))
    ):
        dirs.append(config[path_key])
    base_path = os.path.join(*dirs)

    highest_ratings_path = os.path.join(base_path, "highest_ratings.csv")
    post_path = os.path.join(base_path, "post.csv")
    pre_path = os.path.join(base_path, "pre.csv")
    check_make_dirs([post_path, pre_path, highest_ratings_path])

    n_participants = len(data_df.index.unique())

    # round for readability
    data_df["story_relatedness"] = data_df["story_relatedness"].round(2)

    data_post_df = data_df.loc[data_df["position"] == "post"]
    data_pre_df = data_df.loc[data_df["position"] == "pre"]

    # 1. most common words
    words_post_sr = data_post_df["word_text"]
    words_pre_sr = data_pre_df["word_text"]

    word_count_post_df = words_post_sr.value_counts().to_frame().reset_index()
    word_count_pre_df = words_pre_sr.value_counts().to_frame().reset_index()

    word_count_post_merged_df = word_count_post_df.merge(
        data_post_df, how="inner", on="word_text"
    ).drop_duplicates("word_text")
    word_count_pre_merged_df = word_count_pre_df.merge(
        data_pre_df, how="inner", on="word_text"
    ).drop_duplicates("word_text")

    # compute proportion of wordchains the respective words appear in
    prop_in_wc_post_df = (
        (
            data_post_df.reset_index()
            .drop_duplicates(["participantID", "word_text"])["word_text"]
            .value_counts()
            / n_participants
        )
        .round(4)
        .to_frame("prop_in_wc")
    )
    prop_in_wc_pre_df = (
        (
            data_pre_df.reset_index()
            .drop_duplicates(["participantID", "word_text"])["word_text"]
            .value_counts()
            / n_participants
        )
        .round(4)
        .to_frame("prop_in_wc")
    )

    # merge to output df
    word_stats_post_df = word_count_post_merged_df.merge(
        prop_in_wc_post_df, on="word_text", how="inner"
    )
    word_stats_pre_df = word_count_pre_merged_df.merge(
        prop_in_wc_pre_df, on="word_text", how="inner"
    )

    word_stats_post_df[
        ["word_text", "count", "story_relatedness", "prop_in_wc"]
    ].to_csv(post_path, index=False)
    word_stats_pre_df[["word_text", "count", "story_relatedness", "prop_in_wc"]].to_csv(
        pre_path, index=False
    )

    # 2. highest rated words
    uncorrected_rated_words_dict = load_rated_words(config["ratings"])

    # (a) first need to correct spellings
    corrections = load_corrections()
    words_to_correct = {}
    rated_words_dict = {}
    # separate words that are correct and that need correction
    for word, rating in uncorrected_rated_words_dict.items():
        if word in corrections:
            words_to_correct[word] = rating
        else:
            rated_words_dict[word] = rating

    # only add words back in for which correct spelling is not in already
    for word, rating in words_to_correct.items():
        if corrections[word] not in rated_words_dict:
            rated_words_dict[word] = rating

    # (b) Now can sort and filter data
    rated_words_unfiltered_df = pd.DataFrame.from_records(
        list(rated_words_dict.items()), columns=["word_text", "rating"]
    )

    # only use words that were in data of current condition(s)
    rated_words_unsorted_df = rated_words_unfiltered_df.merge(
        pd.Series(data_df["word_text"].unique(), name="word_text"),
        on="word_text",
        how="inner",
    )

    rated_words_df = rated_words_unsorted_df.sort_values(
        "rating", axis=0, ascending=False
    )
    rated_words_df["rating"] = rated_words_df["rating"].round(2)

    rated_words_df.to_csv(highest_ratings_path, index=False)


def compute_word_stats(config: dict):
    aggregator(
        config=config,
        load_func=func_load,
        call_func=func_compute_word_stats,
    )


if __name__ == "__main__":
    config = {
        "load_spec": (
            "all",
            {
                "all": (
                    "story",
                    {
                        "carver_original": (
                            "condition",
                            {
                                "neutralcue2": PRE_POST_NOFILTER,
                                "suppress": PRE_POST_NOFILTER,
                                "button_press": PRE_POST_NOFILTER,
                                "button_press_suppress": PRE_POST_NOFILTER,
                                "interference_situation": PRE_POST_NOFILTER,
                                "interference_tom": PRE_POST_NOFILTER,
                                "interference_geometry": PRE_POST_NOFILTER,
                                "interference_story_spr": PRE_POST_NOFILTER,
                                "interference_pause": PRE_POST_NOFILTER,
                            },
                        ),
                    },
                )
            },
        ),
        "aggregate_on": "all",
        "column": "story_relatedness",
        "ratings": {
            "approach": "human",
            "model": "moment",
            "story": "carver_original",
            "file": "all.csv",
        },
    }
    compute_word_stats(config)
