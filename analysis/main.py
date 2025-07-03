import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.io as pio
from oc_pmc import DATA_DIR, RATEDWORDS_DIR, console
from oc_pmc.analysis.demographic_stats import demographic_stats
from oc_pmc.analysis.krippendorf_alpha import krippendorf_alpha
from oc_pmc.analysis.word_stats import compute_word_stats
from oc_pmc.load import (
    load_n_thought_entries,
    load_questionnaire,
    load_rated_wordchains,
    load_wordchains,
)
from oc_pmc.plot import (
    plot_by_time_shifted,
    plot_categorical_measure,
    plot_example_wcs,
    plot_numeric_measure,
)
from oc_pmc.plot.distribution import plot_distribution
from oc_pmc.stat import (
    correlate_two,
    sr_two,
    test_mlm,
    test_multiple,
    test_two,
)
from oc_pmc.stat.difference_bin_means import test_difference_bin_means
from oc_pmc.utils.aggregator import aggregator

# because: https://github.com/plotly/plotly.py/issues/3469
# adds unwanted text to first pdf plot made (e.g. in suppl. materials volition)
pio.kaleido.scope.mathjax = None

STUDY = "pmc_manuscript"
STUDY_SUPPL = "pmc_manuscript_suppl"

N_BOOTSTRAP = 5000
FILETYPE = "svg"
FILETYPE_SUPPL = "pdf"
COL_BG = "#FFFFFF"
COL1 = "#000000"
SUBJECTIVE_LINGERING_Y_RANGE = [1, 7]
STORY_RELATEDNESS_Y_RANGE = [2.2, 3.9]
STORY_RELATEDNESS_Y_TICKTEXT = ["2.5", "3.0", "3.5"]
STORY_RELATEDNESS_Y_TICKVALS = [2.5, 3.0, 3.5]
STORY_RELATEDNESS_Y_RANGE_SUPPL = [1.55, 4.3]
STORY_RELATEDNESS_Y_TICKTEXT_SUPPL = ["2.0", "2.5", "3.0", "3.5", "4.0"]
STORY_RELATEDNESS_Y_TICKVALS_SUPPL = [2.0, 2.5, 3.0, 3.5, 4.0]
STORY_RELATEDNESS_INTERFERENCE_X_RANGE = [0, 7.01]
STORY_THOUGHTS_Y_RANGE = [0, 4.5]
STORY_THOUGHTS_Y_VALS_TICKS = [0, 1, 2, 3, 4]
STORY_THOUGHTS_Y_RANGE_SUPPL = [-0.3, 5.5]
STORY_THOUGHTS_Y_VALS_TICKS_SUPPL = [0, 1, 2, 3, 4, 5, 6]
COUNT_HIGH_SR_Y_RANGE = [0, 3.9]
THEME_SIMILARITY_RANGE = [0.25, 0.47]
WORD_TIME_Y_RANGE = [2400, 6900]


SIGNIFICANCE_THRESHHOLD = 0.05
P_DISPLAY_THRESHOLD = 0.0001

AXES_COLOR = "#6c6c6c"
AXES_COLOR_SUPPL = "#000000"


LOAD_KEY_MAPS = {
    "condition": {
        "interference_story_spr_aware": "interference_story_spr",
        "interference_story_spr_unaware": "interference_story_spr",
    }
}

THRESHOLD_HIGH_SR = 5.5

NOFILTER = ("filter", {})
TIMEFILTER = ("filter", {"exclude": [("gte", "timestamp", 180000)]})

POST_NOFILTER = ("position", {"post": NOFILTER})
POST_TIMEFILTER = ("position", {"post": TIMEFILTER})
PRE_NOFILTER = ("position", {"pre": NOFILTER})
PRE_POST_NOFILTER = ("position", {"post": NOFILTER, "pre": NOFILTER})
PRE_POST_TIMEFILTER = ("position", {"post": TIMEFILTER, "pre": TIMEFILTER})
POST_STORY_AWARE_FILTER = (
    "position",
    {"post": ("filter", {"include": [("eq", "stories_distinct", "story-start")]})},
)
POST_STORY_UNAWARE_FILTER = (
    "position",
    {"post": ("filter", {"exclude": [("eq", "stories_distinct", "story-start")]})},
)


ALL_STORIES_CONDITIONS_DCT = {
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
            "interference_end_pause": PRE_POST_NOFILTER,
            "interference_story_spr_end_continued": PRE_POST_NOFILTER,
            "interference_story_spr_end_separated": PRE_POST_NOFILTER,
            "interference_story_spr_end_delayed_continued": PRE_POST_NOFILTER,
            "word_scrambled": PRE_POST_NOFILTER,
        },
    ),
    "dark_bedroom": (
        "condition",
        {
            "neutralcue": PRE_POST_NOFILTER,
        },
    ),
}


ALL_STORIES_CONDITIONS_DCT_POST = {
    "carver_original": (
        "condition",
        {
            "button_press": POST_NOFILTER,
            "word_scrambled": POST_NOFILTER,
            "button_press_suppress": POST_NOFILTER,
            "neutralcue2": POST_NOFILTER,
            "suppress": POST_NOFILTER,
            "interference_situation": POST_NOFILTER,
            "interference_tom": POST_NOFILTER,
            "interference_story_spr": POST_NOFILTER,
            "interference_geometry": POST_NOFILTER,
            "interference_story_spr_end_continued": POST_NOFILTER,
            "interference_story_spr_end_separated": POST_NOFILTER,
            "interference_story_spr_end_delayed_continued": POST_NOFILTER,
            "interference_pause": POST_NOFILTER,
            "interference_end_pause": POST_NOFILTER,
        },
    ),
    "dark_bedroom": (
        "condition",
        {
            "neutralcue": POST_NOFILTER,
        },
    ),
}

INTERFERENCE_STORY_SPR_END_CONDITIONS = {
    "neutralcue2": POST_NOFILTER,
    "interference_story_spr_end_continued": POST_NOFILTER,
    "interference_story_spr_end_separated": POST_NOFILTER,
}


RATINGS_CARVER = {
    "approach": "human",
    "model": "moment",
    "story": "carver_original",
    "file": "all.csv",
}


RATINGS_LIGHTBULB = {
    "approach": "themesim",
    "model": "glove",
    "story": "dark_bedroom",
    "file": "19.csv",
}


ORDER_CONDITIONS = {
    "condition": [
        "button_press",
        "neutralcue2",
        "word_scrambled",
        "interference_situation",
        "interference_tom",
        "interference_geometry",
        "interference_pause",
        "interference_end_pause",
        "interference_story_spr",
        "interference_story_spr_aware",
        "interference_story_spr_unaware",
        "suppress",
        "button_press_suppress",
        "neutralcue",  # dark_bedroom condition
        "interference_story_spr_end_continued",
        "interference_story_spr_end_separated",
        "interference_story_spr_end_delayed_continued",
    ],
    "volition": [
        "unintentional",
        "intentional-mixed",
        "other",
        # "both",
        # "neither",
        # "dontknow",
    ],
}

ORDER_CONDITIONS_VOLITION_ALL = {
    "volition": [
        "unintentional",
        "intentional",
        "both",
        "neither",
        "dontknow",
    ],
}
ORDER_CONDITIONS_VOLITION_MERGED = {
    "condition": [
        "all-button_press",
        "unintentional-button_press",
        "all-button_press_suppress",
        "unintentional-button_press_suppress",
    ],
    "merged_columns": [
        "all-button_press",
        "unintentional-button_press",
        "all-button_press_suppress",
        "unintentional-button_press_suppress",
    ],
}

NAME_MAPPING = {
    "neutralcue2": "Baseline",
    "word_scrambled": "Scrambled",
    "suppress": "Suppress No Button Press",
    "button_press": "Intact",
    "button_press_suppress": "Suppress",
    "interference_tom": "ToM",
    "interference_situation": "Situation",
    "interference_pause": "Pause",
    "interference_end_pause": "End Cue + Pause",
    "interference_geometry": "Geometry",
    "interference_story_spr": "New Story",
    "neutralcue": "New Story Alone",
    "interference_story_spr_end_continued": "Continued",
    "interference_story_spr_end_separated": "Separated",
    "interference_story_spr_end_delayed_continued": "Delayed Continued",
}

# https://plotly.com/python/marker-style/#custom-marker-symbols
SYMBOL_MAP_POSITION = {
    "post": "circle",
    "pre": "diamond",
}

LEGEND_TEMPORARY = dict(
    yanchor="bottom",
    y=1.02,
    xanchor="left",
    x=0,
    font_size=24,
    title=None,
)
LEGEND_NAME_MAPPING = {
    "all-button_press": "Intact - All",
    "unintentional-button_press": "Intact - Unintentional",
    "all-button_press_suppress": "Suppress - All",
    "unintentional-button_press_suppress": "Suppress - Unintentional",
    "button_press, post": "Intact - Post",
    "button_press, pre": "Intact - Pre",
    "word_scrambled, post": "Scrambled - Post",
    "word_scrambled, pre": "Scrambled - Pre",
    "interference_situation, post": "Situation - Post",
    "interference_tom, post": "ToM - Post",
    "interference_geometry, post": "Geometry - Post",
    "interference_story_spr, post": "New Story - Post",
    "interference_pause": "Pause",
    "interference_end_pause": "End Cue + Pause",
    "interference_story_spr": "New Story",
    "interference_story_spr_end_continued": "Continued",
    "interference_story_spr_end_separated": "Separated",
    "interference_story_spr_end_delayed_continued": "Delayed Continued",
    "neutralcue": "New Story Alone",
}
LEGEND_NAME_MAPPING_POSITION = {
    "button_press, post": "Intact",
    "neutralcue2, post": "Baseline",
    "interference_situation, post": "Situation",
    "interference_tom, post": "ToM",
    "interference_geometry, post": "Geometry",
    "interference_story_spr, post": "New Story",
    "interference_story_spr_end_continued, post": "Continued",
    "interference_story_spr_end_separated, post": "Separated",
    "interference_story_spr_end_delayed_continued, post": "Delayed Continued",
    "interference_pause, post": "Pause",
    "interference_end_pause, post": "End Cue + Pause",
    "neutralcue, post": "New Story Alone",
}
LEGEND_NAME_MAPPING_WITH_POSITION = {
    "button_press, post": "Intact - Post",
    "button_press, pre": "Intact - Pre",
    "word_scrambled, post": "Scrambled - Post",
    "word_scrambled, pre": "Scrambled - Pre",
    "neutralcue, post": "New Story Alone - Post",
    "neutralcue, pre": "New Story Alone - Pre",
    "neutralcue2, post": "Baseline - Post",
    "neutralcue2, pre": "Baseline - Pre",
    "suppress, post": "Suppress No Button Press - Post",
    "suppress, pre": "Suppress No Button Press - Pre",
    "button_press_suppress, post": "Suppress - Post",
    "button_press_suppress, pre": "Suppress - Pre",
    "interference_situation, post": "Situation - Post",
    "interference_situation, pre": "Situation - Pre",
    "interference_tom, post": "ToM - Post",
    "interference_tom, pre": "ToM - Pre",
    "interference_geometry, post": "Geometry - Post",
    "interference_geometry, pre": "Geometry - Pre",
    "interference_story_spr, post": "New Story - Post",
    "interference_story_spr, pre": "New Story - Pre",
    "interference_story_spr_end_continued, post": "Continued - Post",
    "interference_story_spr_end_continued, pre": "Continued - Pre",
    "interference_story_spr_end_separated, post": "Separated - Post",
    "interference_story_spr_end_separated, pre": "Separated - Pre",
    "interference_story_spr_end_delayed_continued, post": "Delayed Continued - Post",
    "interference_story_spr_end_delayed_continued, pre": "Delayed Continued - Pre",
    "interference_pause, post": "Pause - Post",
    "interference_pause, pre": "Pause - Pre",
    "interference_end_pause, post": "End Cue + Pause - Post",
    "interference_end_pause, pre": "End Cue + Pause - Pre",
}
LEGEND_TOP_RIGHT = dict(
    yanchor="top",
    y=1,
    xanchor="right",
    x=1,
    font_size=36,
    title=None,
)

LEGEND_TOP_RIGHT_SMALL = dict(
    yanchor="top",
    y=1,
    xanchor="right",
    x=1,
    font_size=15,
    title=None,
)

LEGEND_TOP_MID = dict(
    yanchor="top",
    y=1,
    xanchor="center",
    x=0.5,
    font_size=36,
    title=None,
)

LEGEND_TOP_MID_SMALL = dict(
    yanchor="top",
    y=1,
    xanchor="center",
    x=0.5,
    font_size=18,
    title=None,
)


LEGEND_TOP_LEFT_MEDIUM = dict(
    yanchor="top",
    y=1,
    xanchor="left",
    x=0.1,
    font_size=24,
    title=None,
)

LEGEND_ABOVE = dict(
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="left",
    x=0,
    font_size=32,
    title=None,
)


LEGEND_RIGHT_NEXT = dict(
    yanchor="top",
    y=1,
    xanchor="left",
    x=1.02,
    font_size=36,
    title=None,
)

COL_NEUTRALCUE2 = "#F74639"

COLOR_SEQUENCE_ORDERED = [
    "#F74639",  # button_press
    COL_NEUTRALCUE2,  # neutralcue2
    "#5CC8FF",  # word scrambled
    "#C701FF",  # situation #DE5CBE
    "#FFAE00",  # tom
    "#0173DB",  # geometry
    "#8399FF",  # pause
    "#F8AAD6",  # end_pause
    "#09A000",  # interference_story_spr
    "#07CC00",  # interference_story_spr_aware
    "#0A7300",  # interference_story_spr_unaware
    "#A12371",  # suppress
    "#09A000",  # button_press_suppress
    "#ffc000",  # neutralcue (dark_bedroom)
    "#356BEB",  # continued
    "#09E3AC",  # separated
    "#A12371",  # delayed_continued
]
COLOR_SEQUENCE_VOLITION = [
    "#D94E4E",  # unintentional
    "#F4A4A1",  # intentional & both
    "#BCA4A1",  # other
]
COLOR_SEQUENCE_VOLITION_SUPPRESS = [
    "#6AAE6A",  # unintentional
    "#A8D08D",  # intentional & both
    "#7C8B7C",  # other
]
COLOR_SEQUENCE_VOLITION_MERGED = [
    "#C41414",  # unintentional / all
    "#D94E4E",  # intentional-mixed / unintentional
    "#2F6B2F",  # unintentional / all
    "#6AAE6A",  # intentional-mixed / unintentional
]
COLOR_MAP_VOLITION_ALL = {
    "Unintentional": "#C41414",
    "Intentional": "#FF1414",
    "Neither": "#F4A4A1",
    "Both": "#914E4E",
    "Don't know": "#BCA4A1",
    "No Rating": "#454545",
}
COLOR_MAP_VOLITION_SUPPRESS_ALL = {
    "Unintentional": "#2F6B2F",
    "Intentional": "#0FD10F",
    "Neither": "#000000",
    "Both": "#70FF70",
    "Don't know": "#7C8B7C",
    "No Rating": "#454545",
}

REPLACE_COLUMNS_VOLITION = {
    "volition": {
        None: "No Rating",
        "dontknow": "Don't know",
        "unintentional": "Unintentional",
        "intentional": "Intentional",
        "both": "Both",
        "neither": "Neither",
    }
}

REPLACE_COLUMNS_STRATEGIES = {
    "wcg_strategy_category": {
        "no_strategy": "No Strategy",
        "categories": "Categories",
        "surroundings": "Surroundings",
        "concerns": "Concerns",
        "rhyming": "Rhyming",
        "other": "Other",
    }
}


def stats_experiment_1_button_press():
    console.print("\nResults 1: Intact vs Scrambled: Statistics", style="red bold")

    console.print("\n > Reading time", style="yellow")

    bp_df = load_questionnaire(
        {"story": "carver_original", "condition": "button_press", "position": "post"}
    )
    reading_time = (bp_df["spr_time"] / 1000 / 60).mean()
    reading_sd = (bp_df["spr_time"] / 1000 / 60).std()
    print(
        f"Intact (button_press) | Avg. reading time: {round(reading_time, 2)}"
        f" | SD: {round(reading_sd, 2)}"
    )

    console.print("\n > Median words produced", style="yellow")

    def print_n_words_wordchain(config: dict, data_df: pd.DataFrame):
        median_words_produced = (
            data_df.groupby(["participantID", "position"]).count().median()["word_text"]
        )
        mean_words_produced = (
            data_df.groupby(["participantID", "position"]).count().mean()["word_text"]
        )
        sd_words_produced = (
            data_df.groupby(["participantID", "position"]).count().std()["word_text"]
        )

        print(f"{config['story']} | {NAME_MAPPING[config['condition']]}")

        print((f" | median words (post & pre combined): {median_words_produced}"))
        print(
            (
                f" | mean words (post & pre combined)  : {mean_words_produced}"
                f" | SD: {round(sd_words_produced, 2)}"
            )
        )

        data_df_post = data_df.loc[data_df["position"] == "post"]
        data_df_pre = data_df.loc[data_df["position"] == "pre"]

        median_words_produced_post = (
            data_df_post.groupby("participantID").count().median()["word_text"]
        )
        median_words_produced_pre = (
            data_df_pre.groupby("participantID").count().median()["word_text"]
        )

        mean_words_produced_post = (
            data_df_post.groupby("participantID").count().mean()["word_text"]
        )
        mean_words_produced_pre = (
            data_df_pre.groupby("participantID").count().mean()["word_text"]
        )

        sd_words_produced_post = (
            data_df_post.groupby("participantID").count().std()["word_text"]
        )
        sd_words_produced_pre = (
            data_df_pre.groupby("participantID").count().std()["word_text"]
        )

        print((f" | median words (post): {median_words_produced_post}"))
        print(
            (
                f" | mean words (post)  : {mean_words_produced_post}"
                f" | SD: {round(sd_words_produced_post, 2)}"
            )
        )
        print((f" | median words (pre): {median_words_produced_pre}"))
        print(
            (
                f" | mean words (pre)  : {mean_words_produced_pre}"
                f" | SD: {round(sd_words_produced_pre, 2)}"
            )
        )

    aggregator(
        config={
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": PRE_POST_TIMEFILTER,
                                    "word_scrambled": PRE_POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
        },
        load_func=load_wordchains,
        call_func=print_n_words_wordchain,
    )

    console.print("\n > Number of words rated", style="yellow")

    # Manual loading, because load_rated_words preprodcesses data.
    rated_words_path = Path(
        DATA_DIR,
        RATEDWORDS_DIR,
        RATINGS_CARVER["approach"],
        RATINGS_CARVER["model"],
        RATINGS_CARVER["story"],
        RATINGS_CARVER["file"],
    )
    print(f"Number rated words: {len(pd.read_csv(rated_words_path))}")

    console.print("\n > Number of story thoughts", style="yellow")
    sts_post = load_n_thought_entries(
        {"story": "carver_original", "condition": "button_press", "position": "post"},
        te_filter=dict(),
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_post = sts_post.mean().item()
    median_sts_post = sts_post.median().item()
    std_sts_post = sts_post.std().item()
    print(
        f"Mean (post/story): {round(mean_sts_post, 2)}"
        f" | SD: {round(std_sts_post, 2)}"
        f" | Median: {round(median_sts_post, 2)}"
    )
    sts_pre = load_n_thought_entries(
        {"story": "carver_original", "condition": "button_press", "position": "pre"},
        te_filter=dict(),
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_pre = sts_pre.mean().item()
    median_sts_pre = sts_pre.median().item()
    std_sts_pre = sts_pre.std().item()
    print(
        f"Mean (pre/food): {round(mean_sts_pre, 2)}"
        f" | SD: {round(std_sts_pre, 2)}"
        f" | Median: {round(median_sts_pre, 2)}"
    )

    console.print("\n > Number of story thoughts first 30s", style="yellow")
    sts_post_first30 = load_n_thought_entries(
        {"story": "carver_original", "condition": "button_press", "position": "post"},
        te_filter={"exclude": ("gt", "timestamp", 30000)},
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_post_first30 = sts_post_first30[["thought_entries"]].mean().item()
    median_sts_post_first30 = sts_post_first30[["thought_entries"]].median().item()
    std_sts_post_first30 = sts_post_first30[["thought_entries"]].std().item()
    print(
        f"Mean (post/story): {round(mean_sts_post_first30, 2)}"
        f" | SD: {round(std_sts_post_first30, 2)}"
        f" | Median: {round(median_sts_post_first30, 2)}"
    )
    sts_pre_first30 = load_n_thought_entries(
        {"story": "carver_original", "condition": "button_press", "position": "pre"},
        te_filter={"exclude": ("gt", "timestamp", 30000)},
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_pre_first30 = sts_pre_first30[["thought_entries"]].mean().item()
    median_sts_pre_first30 = sts_pre_first30[["thought_entries"]].median().item()
    std_sts_pre_first30 = sts_pre_first30[["thought_entries"]].std().item()
    print(
        f"Mean (pre/food): {round(mean_sts_pre_first30, 2)}"
        f" | SD: {round(std_sts_pre_first30, 2)}"
        f" | Median: {round(median_sts_pre_first30, 2)}"
    )

    console.print("\n > Number of story thoughts last 30s", style="yellow")
    sts_post_last30 = load_n_thought_entries(
        {"story": "carver_original", "condition": "button_press", "position": "post"},
        te_filter={
            "exclude": [("lte", "timestamp", 150000), ("gt", "timestamp", 180000)]
        },
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_post_last30 = sts_post_last30[["thought_entries"]].mean().item()
    median_sts_post_last30 = sts_post_last30[["thought_entries"]].median().item()
    std_sts_post_last30 = sts_post_last30[["thought_entries"]].std().item()
    print(
        f"Mean (post/story): {round(mean_sts_post_last30, 2)}"
        f" | SD: {round(std_sts_post_last30, 2)}"
        f" | Median: {round(median_sts_post_last30, 2)}"
    )
    sts_pre_last30 = load_n_thought_entries(
        {"story": "carver_original", "condition": "button_press", "position": "pre"},
        te_filter={
            "exclude": [("lte", "timestamp", 150000), ("gt", "timestamp", 180000)]
        },
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_pre_last30 = sts_pre_last30[["thought_entries"]].mean().item()
    median_sts_pre_last30 = sts_pre_last30[["thought_entries"]].median().item()
    std_sts_pre_last30 = sts_pre_last30[["thought_entries"]].std().item()
    print(
        f"Mean (pre/food): {round(mean_sts_pre_last30, 2)}"
        f" | SD: {round(std_sts_pre_last30, 2)}"
        f" | Median: {round(median_sts_pre_last30, 2)}"
    )

    test_two(
        {
            "name1": "Intact post",
            "name2": "Intact pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},  # no normality
            "story": "carver_original",
            "condition": "button_press",  # no equality of variances
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": first 30s",
            "name1": "Intact post",
            "name2": "Intact pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "condition": "button_press",  # no equality of variances
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": last 30s",
            "name1": "Intact post",
            "name2": "Intact pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("lt", "timestamp", 150000)],
            "story": "carver_original",
            "condition": "button_press",  # no equality of variances
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Story thoughts",
            "name2": "Food thoughts",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "story": "carver_original",
            "condition": "button_press",  # no equality of variances
            "ratings": RATINGS_CARVER,
            "measure": "thought_entries",
            "te_filter": dict(),
            "questionnaire_filter": dict(),
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Story thoughts: beginning & end", style="yellow")
    sts_beginning = load_n_thought_entries(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
        },
        te_filter={"exclude": ("gte", "timestamp", 30000)},
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_beginnning = sts_beginning.mean().item()
    median_sts_beginnning = sts_beginning.median().item()
    std_sts_beginnning = sts_beginning.std().item()
    print(
        f"Mean (beginning): {mean_sts_beginnning} in first 30s ->"
        f" {round(mean_sts_beginnning / 3, 2)} / 10s"
    )
    print(f"SD (beginning): {std_sts_beginnning} in first 30s")
    print(
        f"Median (beginning): {median_sts_beginnning} in first 30s ->"
        f" {round(median_sts_beginnning / 3, 2)} / 10s"
    )

    sts_end = load_n_thought_entries(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
        },
        te_filter={"exclude": [("lt", "timestamp", 150000)]},
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_end = sts_end.mean().item()
    median_sts_end = sts_end.median().item()
    std_sts_end = sts_end.std().item()
    print(
        f"Mean (end): {mean_sts_end} in last 30s -> {round(mean_sts_end / 3, 2)} / 10s"
    )
    print(f"SD (end): {round(std_sts_end, 2)} in the last 30s")
    print(
        f"Median (end): {median_sts_end} in last 30s ->"
        f" {round(median_sts_end / 3, 2)} / 10s"
    )

    console.print(
        "\n > Intact: CORR: Story relatedness & story thoughts", style="yellow"
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "x_measure": "story_relatedness",
            "y_measure": "thought_entries",
            "ratings": RATINGS_CARVER,
        }
    )

    console.print("\n > Intact: CORR: Linger rating & story thoughts", style="yellow")
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "x_measure": "thought_entries",
            "y_measure": "linger_rating",
        }
    )

    test_two(
        {
            "name1": "Intact post",
            "name2": "Scrambled post",
            "config1": {"condition": "button_press"},  # no equal variances
            "config2": {"condition": "word_scrambled"},  # no equal variances
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Scrambled post",
            "name2": "Scrambled pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},  # no normality
            "story": "carver_original",
            "condition": "word_scrambled",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Mean/Meadian high SR words post", style="yellow")

    def show_n_high_sr_words(config: dict, data_df: pd.DataFrame):
        n_high_sr_words = data_df.groupby("participantID")[
            "story_relatedness"
        ].aggregate(lambda x: (x > THRESHOLD_HIGH_SR).sum())
        mean_high_sr_words = n_high_sr_words.mean()
        median_high_sr_words = n_high_sr_words.median()

        print(
            f"{config['story']} | {config['condition']} | {config['position']} |"
            f" Mean #words > {THRESHOLD_HIGH_SR}: {round(mean_high_sr_words, 2)}"
        )
        print(
            f"{config['story']} | {config['condition']} | {config['position']} |"
            f" Median #words > {THRESHOLD_HIGH_SR}: {round(median_high_sr_words, 2)}"
        )

    aggregator(
        {
            "load_spec": (
                "condition",
                {"button_press": NOFILTER, "word_scrambled": NOFILTER},
            ),
            "exclude": ("gte", "timestamp", 180000),  # wordscrambled is for 5 minutes
            "story": "carver_original",
            "position": "post",
            "aggregate_on": "condition",
            "ratings": RATINGS_CARVER,
        },
        load_func=load_rated_wordchains,
        call_func=show_n_high_sr_words,
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Scrambled",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "word_scrambled"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def plots_fig_1_paradigm_results1():
    """
    For final plot use ghostscript to avoid compatibility issues
    with Previous and Chrome.

    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/prepress -dNOPAUSE \
        -dQUIET -dBATCH -sOutputFile=paradigm-results1.gs.pdf paradigm-results1.pdf
    """
    console.print(
        "\n\n1. Paradigm & Button-press: Fig 1: fig-paradigm-results1", style="bold red"
    )

    button_press_color = COLOR_SEQUENCE_ORDERED[
        ORDER_CONDITIONS["condition"].index("button_press")
    ]

    # 1. wordchain plots
    plot_example_wcs(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {"button_press": POST_NOFILTER},
                    )
                },
            ),
            "aggregate_on": "position",
            "ratings": RATINGS_CARVER,
            # data
            "pID": [1254],  # also good: 1233
            # visuals
            "title": None,
            "marker_size": 15,
            "line_width": 5,
            "color_sequence": [button_press_color],
            "thought_entry_color": "#ffae00",
            "thougth_entry_line_width": 6,
            "thought_entry_layer": "below",
            "axes_linewidth": 5,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "y_tickfont": dict(size=24, color="#4d4d4d"),
            "x_tickfont": dict(size=24, color="#4d4d4d"),
            "y_title": None,
            "x_title": None,
            "y_tickvals": [1, 3, 5, 7],
            "y_ticktext": ["1", "3", "5", "7"],
            "y_range": [0.8, 7.2],
            "x_rangemode": "tozero",
            "x_range": (0, 110220),
            "text": None,
            "textfont": dict(color="black", size=18),
            "textposition": "top center",
            # saving
            "study": STUDY,
            "save": True,
            "width": 1550,
            "height": 330,
            "scale": 2,
            "filetype": "svg",
        }
    )

    plot_example_wcs(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {"button_press": PRE_NOFILTER},
                    )
                },
            ),
            "aggregate_on": "position",
            "ratings": RATINGS_CARVER,
            # data
            "pID": [1254],  # also good: 1233
            # visuals
            "title": None,
            "marker_size": 15,
            "line_width": 5,
            "color_sequence": [button_press_color],
            "thought_entry_color": "#36982C",
            "thougth_entry_line_width": 6,
            "thought_entry_line_dash": "solid",
            "thought_entry_layer": "below",
            "axes_linewidth": 5,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "y_tickfont": dict(size=24, color="#4d4d4d"),
            "x_tickfont": dict(size=24, color="#4d4d4d"),
            "y_title": None,
            "x_title": None,
            "y_tickvals": [1, 3, 5, 7],
            "y_ticktext": ["1", "3", "5", "7"],
            "y_range": [0.8, 7.2],
            "x_rangemode": "tozero",
            "x_range": (0, 110220),
            "text": None,
            "textfont": dict(color="black", size=18),
            "textposition": "top center",
            "symbol": "position",
            "symbol_map": {"pre": "diamond"},
            "line_dash": "position",
            "line_dash_map": {"pre": "dot"},
            # saving
            "study": STUDY,
            "save": True,
            "width": 1550,
            "height": 330,
            "scale": 2,
            "filetype": "svg",
        }
    )

    # 2. story relatedness plot
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": PRE_POST_TIMEFILTER,
                                    "word_scrambled": PRE_POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "color": "condition",
            "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": LEGEND_NAME_MAPPING,
            "show": False,
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 1050,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_ws_f1",
        }
    )

    # 3. button presses
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {"button_press": PRE_POST_TIMEFILTER},
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "mode": "double_press",
            # plot data config
            "column": "double_press",
            "color": "condition",
            "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story thoughts",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_THOUGHTS_Y_VALS_TICKS,
            "y_ticktext": STORY_THOUGHTS_Y_VALS_TICKS,
            "y_range": STORY_THOUGHTS_Y_RANGE,
            "x_range": [0, 6.05],
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": {
                "button_press, post": "Story thoughts - Post",
                "button_press, pre": "Food thoughts - Pre",
            },
            "show": False,
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 1050,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_f1",
        }
    )

    # 4. Self reported lingering
    plot_distribution(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_NOFILTER,
                                    "word_scrambled": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "all",
            # plot data config
            "measure": "linger_rating",
            "summary_func": np.nanmean,
            # plot config
            "color": "condition",
            "title": None,
            "nbins": 7,
            "barmode": "group",
            "histnorm": "percent",
            "bargap": 0.12,
            "x_range": [0.5, 7.5],
            "y_range": [0, 41],
            "marker": dict(line_width=1, line_color="black"),
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "showlegend": False,
            "x_ticktext": [1, 2, 3, 4, 5, 6, 7],
            "x_tickvals": [1, 2, 3, 4, 5, 6, 7],
            "y_ticktext": [0, 10, 20, 30, 40],
            "y_tickvals": [0, 10, 20, 30, 40],
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_title": "Self-reported lingering",
            "y_title": "Proportion Participants",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "mean_lines": [
                {
                    "condition": "button_press",
                    "line": {"dash": "dot", "width": 6},
                    "layer": "above",
                },
                {
                    "condition": "word_scrambled",
                    "line": {"dash": "dot", "width": 6},
                    "layer": "above",
                },
            ],
            # save config
            "save": True,
            "width": 660,
            "height": 660,
            "scale": 2.0,
            "filepostfix": "bp_ws_f1",
            "study": STUDY,
            "filetype": FILETYPE,
            # kruskal
            "kruskal": False,
        }
    )

    return


def stats_experiment_2_button_press_suppress():
    console.print("\n\n2. Volition: stats", style="red bold")
    print("\n\n## Narrative content persists without and against volition.")

    # percentages
    n_total = len(
        load_questionnaire({"story": "carver_original", "condition": "button_press"})
    )
    n_unintentional = len(
        load_questionnaire(
            {
                "story": "carver_original",
                "condition": "button_press",
                "include": ("eq", "volition", "unintentional"),
            }
        )
    )
    n_intentional = len(
        load_questionnaire(
            {
                "story": "carver_original",
                "condition": "button_press",
                "include": ("eq", "volition", "intentional"),
            }
        )
    )
    n_both = len(
        load_questionnaire(
            {
                "story": "carver_original",
                "condition": "button_press",
                "include": ("eq", "volition", "both"),
            }
        )
    )
    console.print("\nPercentages", style="yellow")
    print(f"Percentage unintentional: {round(n_unintentional / n_total * 100, 1):.1f}")
    perc_int_both = (n_intentional + n_both) / n_total * 100
    print(f"Percentage intentional + both: {round(perc_int_both, 1):.1f}")

    test_two(
        {
            "name1": "Suppress Post",
            "name2": "Suppress Pre",
            "config1": {"position": "post"},  # not normal
            "config2": {"position": "pre"},  # not normal
            "story": "carver_original",
            "condition": "button_press_suppress",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": first 30s",
            "name1": "<30s Suppress Post",
            "name2": "<30s Suppress Pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},  # not normal
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "condition": "button_press_suppress",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Story thoughts",
            "name2": "Food thoughts",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "story": "carver_original",
            "condition": "button_press_suppress",
            "ratings": RATINGS_CARVER,
            "measure": "thought_entries",
            "te_filter": dict(),
            "questionnaire_filter": dict(),
            "test_type": "wilcoxon",  # to be consistent
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Intact story thoughts",
            "name2": "Suppress story thoughts",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},  # not equal variances
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "thought_entries",
            "te_filter": dict(),
            "questionnaire_filter": dict(),
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Suppress: story shoughts beginning & end", style="yellow")
    sts_beginning = load_n_thought_entries(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
        },
        te_filter={"exclude": ("gte", "timestamp", 30000)},
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_beginnning = sts_beginning.mean().item()
    median_sts_beginnning = sts_beginning.median().item()
    print(
        f"Mean: {round(mean_sts_beginnning, 2)} in first 30s ->"
        f" {round(mean_sts_beginnning / 3, 2)} / 10s"
    )
    print(
        f"Median: {median_sts_beginnning} in first 30s ->"
        f" {round(median_sts_beginnning / 3, 2)} / 10s"
    )

    sts_end = load_n_thought_entries(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
        },
        te_filter={"exclude": [("lt", "timestamp", 150000)]},
        questionnaire_filter=dict(),
    )[["thought_entries"]]
    mean_sts_end = sts_end.mean().item()
    median_sts_end = sts_end.median().item()
    print(
        f"Mean: {round(mean_sts_end, 2)} in last 30s -> {round(mean_sts_end / 3, 2)}"
        " / 10s"
    )
    print(
        f"Median: {median_sts_end} in last 30s -> {round(median_sts_end / 3, 2)} / 10s"
    )

    console.print(
        "\n > Suppress: CORR: Story relatedness & story thoughts", style="yellow"
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "x_measure": "story_relatedness",
            "y_measure": "thought_entries",
            "ratings": RATINGS_CARVER,
        }
    )

    console.print(
        "\n > Supprsss: CORR: CONTROL Story relatedness (pre) & story thoughts (post)",
        style="yellow",
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "pre",
            "x_measure": "story_relatedness",
            "y_measure": "total_double_press_count_post",
            "ratings": RATINGS_CARVER,
        }
    )

    console.print(
        "\n > Suppress: CORR: Linger rating & story thoughts.", style="yellow"
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "x_measure": "thought_entries",
            "y_measure": "linger_rating",
        }
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # # control by correlation pre -> linger rating
    # console.print("\n > Control: Linger rating & food thoughts.", style="yellow")
    # correlate_two(
    #     {
    #         "story": "carver_original",
    #         "condition": "button_press_suppress",
    #         "x_measure": "linger_rating",
    #         "y_measure": "total_double_press_count_pre",
    #     }
    # )

    # # control by correlation:
    # # "If story thoughts are generally driven by the instruction to report them, then
    # # number of food thoughts and story thoughts should be correlated"
    # console.print(
    #     "\n > Control: Story thoughts & Food thoughts: button_press_suppress",
    #     style="yellow",
    # )
    # correlate_two(
    #     {
    #         "story": "carver_original",
    #         "condition": "button_press_suppress",
    #         "x_measure": "total_double_press_count_post",
    #         "y_measure": "total_double_press_count_pre",
    #     }
    # )


def plots_fig_2_results2():
    """
    For final plot use ghostscript to avoid compatibility issues
    with Previous and Chrome.

    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/prepress -dNOPAUSE \
        -dQUIET -dBATCH -sOutputFile=results2.gs.pdf results2.pdf
    """
    console.print("\n\n2. Volition: fig-result2 plots", style="red bold")

    VOLITION_GROUPS = {
        "intentional": "intentional-mixed",
        "both": "intentional-mixed",
        "neither": "other",
        "dontknow": "other",
    }

    # 0. Volition distribution
    console.print("> Bar plot", style="yellow")
    plot_categorical_measure(
        {
            # data
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {"button_press": POST_NOFILTER},
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "normalize": True,
            "measure_name": "volition",
            "replace_measure": VOLITION_GROUPS,
            "x": "condition",
            "text": "proportion",
            # plot
            "textposition": "inside",
            "texttemplate": "%{x:.1%}",
            "textfont": dict(size=42, color="white"),
            "bargap": None,
            "barmode": "relative",
            "orientation": "h",
            "x_showline": False,
            "y_showline": False,
            "x_showticklabels": False,
            "y_showticklabels": False,
            "y_tickfont": dict(color=COL1, size=42),
            "y_title": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_ticks": "",
            "y_ticks": "",
            "y_range": [0, 1],
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "title": None,
            "showlegend": False,
            "color_sequence": COLOR_SEQUENCE_VOLITION,
            "category_orders": ORDER_CONDITIONS,
            # save config
            "save": True,
            "width": 1350,
            "height": 300,
            "scale": 2.0,
            "filepostfix": "bp_f2",
            "study": STUDY,
            "filetype": "svg",
        }
    )
    plot_categorical_measure(
        {
            # data
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press_suppress": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "normalize": True,
            "measure_name": "volition",
            "replace_measure": VOLITION_GROUPS,
            "x": "condition",
            "text": "proportion",
            # plot
            "textposition": "inside",
            "texttemplate": "%{x:.1%}",
            "textfont": dict(size=42, color="white"),
            "bargap": None,
            "barmode": "relative",
            "orientation": "h",
            "x_showline": False,
            "y_showline": False,
            "x_showticklabels": False,
            "y_showticklabels": False,
            "y_tickfont": dict(color=COL1, size=42),
            "y_title": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_ticks": "",
            "y_ticks": "",
            "y_range": [0, 1],
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "title": None,
            "showlegend": False,
            "color_sequence": COLOR_SEQUENCE_VOLITION_SUPPRESS,
            "category_orders": ORDER_CONDITIONS,
            # save config
            "save": True,
            "width": 1350,
            "height": 300,
            "scale": 2.0,
            "filepostfix": "bps_f2",
            "study": STUDY,
            "filetype": "svg",
        }
    )

    # 1. Story relatedness
    console.print("\n> Story relatedness plot", style="yellow")
    # Need to do data loading & plotting manually
    bp_all_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "keep_columns": ["linger_rating"],
        }
    )
    bps_all_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "keep_columns": ["linger_rating"],
        }
    )
    bp_unintentional_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "include": [("eq", "volition", "unintentional")],
            "keep_columns": ["linger_rating"],
        }
    )
    bps_unintentional_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "include": [("eq", "volition", "unintentional")],
            "keep_columns": ["linger_rating"],
        }
    )

    bp_all_df["condition"] = "all-button_press"
    bps_all_df["condition"] = "all-button_press_suppress"
    bp_unintentional_df["condition"] = "unintentional-button_press"
    bps_unintentional_df["condition"] = "unintentional-button_press_suppress"

    data_df = pd.concat(
        (bp_all_df, bps_all_df, bp_unintentional_df, bps_unintentional_df)
    )
    # to add the grouping columns, easier than custumizable grouping columns
    data_df["story"] = "carver_original"
    data_df["position"] = "post"

    from oc_pmc.plot.by_time_shifted import func_plot_by_time

    func_plot_by_time(
        config={
            "column": "story_relatedness",
            "mode": "relatedness",
            "step": 30000,
            "min_bin_n": 1,
            "plotkind": "line",
            "color": "condition",
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_VOLITION_MERGED,
            "category_orders": ORDER_CONDITIONS_VOLITION_MERGED,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": LEGEND_NAME_MAPPING,
            "show": False,
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 1140,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_bps_volition_f2",
        },
        data_df=data_df,
    )
    # use same data for linger_rating
    from oc_pmc.plot.numeric_measure import func_plot_numeric_measure

    console.print("\n> Self-reported lingering plot", style="yellow")
    func_plot_numeric_measure(
        config={
            "measure_name": "linger_rating",
            "x": "condition",
            "title": "",
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_VOLITION_MERGED,
            "category_orders": ORDER_CONDITIONS_VOLITION_MERGED,
            "orientation": "h",
            "x_ticktext": [],
            "x_tickvals": [],
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_title": "Condition",
            "y_title": "Self-reported lingering",
            "x_title_standoff": 50,
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "showlegend": False,
            "hlines": [
                {
                    "y": 2.62,
                    "line": {
                        "dash": "dash",
                        "color": COLOR_SEQUENCE_ORDERED[
                            ORDER_CONDITIONS["condition"].index("word_scrambled")
                        ],
                        "width": 9,
                    },
                },
            ],
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # save config
            "save": True,
            "width": 660,
            "height": 660,
            "scale": 2.0,
            "filepostfix": "bp_bps_volition_f2",
            "study": STUDY,
            "filetype": FILETYPE,
            # kruskal
            "kruskal": False,
        },
        data_df=data_df,
    )

    # 4. Button_press
    console.print("\n> Story thoughts plot", style="yellow")
    # I should have done this with the previous ones..
    ALL_UNINTENTIONAL_GROUPING = (
        "group",
        {
            "all": TIMEFILTER,
            "unintentional": (
                "filter",
                {
                    "exclude": [("gte", "timestamp", 180000)],
                    "include": [("eq", "volition", "unintentional")],
                },
            ),
        },
    )
    plot_by_time_shifted(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "position",
                        {
                            "post": (
                                "condition",
                                {
                                    "button_press": ALL_UNINTENTIONAL_GROUPING,
                                    "button_press_suppress": ALL_UNINTENTIONAL_GROUPING,  # noqa
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "double_press",
            "column": "double_press",
            # "keep_columns": ["volition"],
            # "additional_grouping_columns": ["volition"],
            "merged_columns": ["group", "condition"],
            "color": "merged_columns",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "x_title": "Time from start of free association",
            "y_title": "Story thoughts",
            "x_range": [0, 6.05],
            "y_range": STORY_THOUGHTS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_THOUGHTS_Y_VALS_TICKS,
            "y_ticktext": STORY_THOUGHTS_Y_VALS_TICKS,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_VOLITION_MERGED,
            "category_orders": ORDER_CONDITIONS_VOLITION_MERGED,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": LEGEND_NAME_MAPPING,
            "show": False,
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 1140,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_bps_volition_f2",
        }
    )


def stats_experiment_3_interference():
    console.print("\n3. Stats Interference", style="bold red")

    console.print("\nAligned by free association start", style="green")
    test_two(
        {
            "console_comment": ": 0s-30s",
            "name1": "Baseline",
            "name2": "Situation",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "interference_situation"},
            "include": [("lte", "timestamp", 30000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": 0s-30s",
            "name1": "Baseline",
            "name2": "ToM",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "interference_tom"},
            "include": [("lt", "timestamp", 30000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nAligned by story end", style="green")

    BIN_START = 30000
    BIN_END = 60000
    test_two(
        {
            "console_comment": ": 30s-60s",
            "name1": "Baseline",
            "name2": "Situation",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "interference_situation"},
            "exclude": [
                ("lt", "timestamp", BIN_START),
                ("gte", "timestamp", BIN_END),
            ],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "measure": "story_relatedness",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": 30s-60s",
            "name1": "Baseline",
            "name2": "ToM",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "interference_tom"},
            "exclude": [
                ("lt", "timestamp", BIN_START),
                ("gte", "timestamp", BIN_END),
            ],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "measure": "story_relatedness",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline",
            "name2": "Situation",
            "config1": {"condition": "neutralcue2"},  # normality not given
            "config2": {"condition": "interference_situation"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline",
            "name2": "ToM",
            "config1": {"condition": "neutralcue2"},  # normality not given
            "config2": {"condition": "interference_tom"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nNew Story Alone / New Story section", style="green")

    console.print("\n > Time to read new story length", style="yellow")
    new_story_df = load_questionnaire(
        {"story": "carver_original", "condition": "interference_story_spr"}
    )
    lightbulb_new_story_reading_time = (
        new_story_df["interference_reading_testing_time"].mean() / 1000
    )
    print(
        f"Time to read lightbulb in New Story: {lightbulb_new_story_reading_time:.2f}s"
    )

    test_two(
        {
            "console_comment": ": 0s-30s",
            "name1": "Baseline",
            "name2": "New Story",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "interference_story_spr"},
            "include": [("lt", "timestamp", 30000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": aligned-by story-end: 60s-90s",
            "name1": "Baseline",
            "name2": "New Story",
            "config1": {"condition": "neutralcue2"},
            "config2": {
                "condition": "interference_story_spr"
            },  # levene test is significant for this sample, normality not given
            "exclude": [
                ("lt", "timestamp", 60000),
                ("gte", "timestamp", 90000),
            ],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "measure": "story_relatedness",
            "test_type": "mwu",  # need to use nonparametric test
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline",
            "name2": "New Story",
            "config1": {"condition": "neutralcue2"},  # normality not given
            "config2": {"condition": "interference_story_spr"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nGeometry section", style="green")

    test_two(
        {
            "console_comment": ": aligned-by FA-start: 0s-30s",
            "name1": "Baseline",
            "name2": "Geometry",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "interference_geometry"},
            "include": [("lte", "timestamp", 30000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": aligned-by story-end: 30s-60s",
            "name1": "Baseline",
            "name2": "Geometry",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "interference_geometry"},
            "exclude": [("lt", "timestamp", 30000), ("gte", "timestamp", 60000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "measure": "story_relatedness",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline",
            "name2": "Geometry",
            "config1": {"condition": "neutralcue2"},  # normality not given
            "config2": {"condition": "interference_geometry"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    return


def plots_fig_3_results3():
    """
    For final plot use ghostscript to prevent compatibility issues with
    Preview and Chrome.

    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/prepress -dNOPAUSE \
        -dQUIET -dBATCH -sOutputFile=results3.gs.pdf results3.pdf
    """
    console.print("\nFig 3: plots fig-results3\n", style="red bold")

    # 1. interference conditions (aligned by FA start)
    console.print("\nInterference aligned FA start.", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_geometry": POST_NOFILTER,
                                    "interference_situation": POST_NOFILTER,
                                    "interference_tom": POST_NOFILTER,
                                    "interference_story_spr": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "aligend_fa_start_f3",
        }
    )

    # 1. interference conditions (aligned by reading end)
    console.print("\nInterference aligned reading end.", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_geometry": POST_NOFILTER,
                                    "interference_situation": POST_NOFILTER,
                                    "interference_tom": POST_NOFILTER,
                                    "interference_story_spr": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": False,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 1200,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "aligned_reading_end_f3",
        }
    )

    # 3. self-reported lingering
    console.print("\nLinger rating interference data.", style="yellow")
    plot_numeric_measure(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_geometry": POST_NOFILTER,
                                    "interference_situation": POST_NOFILTER,
                                    "interference_tom": POST_NOFILTER,
                                    "interference_story_spr": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "all",
            # plot data config
            "measure_name": "linger_rating",
            "summary_func": np.nanmean,
            # plot config
            "title": "",
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "orientation": "h",
            "showlegend": False,
            "x_ticktext": [],
            "x_tickvals": [],
            "y_tickfont": dict(color=COL1, size=42),
            "x_title": "Condition",
            "y_title": "Self-reported lingering",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "hlines": [
                {
                    "y": 2.62,
                    "line": {
                        "dash": "dash",
                        "color": COLOR_SEQUENCE_ORDERED[
                            ORDER_CONDITIONS["condition"].index("word_scrambled")
                        ],
                        "width": 9,
                    },
                },
            ],
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # save config
            "save": True,
            "width": 720,
            "height": 660,
            "scale": 2.0,
            "filepostfix": "f3",
            "study": STUDY,
            "filetype": FILETYPE,
            # kruskal
            "kruskal": False,
        }
    )


def stats_experiment_4_continued_separated():
    console.print("\nStats Exp4 continued v separated", style="red bold")
    # correlation attempt integrate and story relatedness first bin
    correlate_two(
        {
            "story": "carver_original",
            "condition": "interference_story_spr_end_continued",
            "position": "post",
            "x_measure": "story_relatedness",
            "y_measure": "integration_attempt",
            "align_timestamp": "reading_task_end",
            "exclude": [("gte", "timestamp", 90000), ("lt", "timestamp", 60000)],
            "ratings": RATINGS_CARVER,
        }
    )

    console.print("\n1) Manipulation check", style="green")
    test_two(
        {
            "name1": "Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            # equality of variances almost is not given > nonparametric
            "story": "carver_original",
            "measure": "integration_attempt",
            "test_type": "mwu",
            "alternative": "greater",
            "measure_letter": "M",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nEffect of PMC", style="green")
    test_two(
        {
            "name1": "Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            # equality of variances almost is not given > nonparametric
            "story": "carver_original",
            "measure": "integration_success",
            "test_type": "mwu",
            "alternative": "two-sided",
            "measure_letter": "M",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nStats: Continued v Separated", style="red bold")

    test_difference_bin_means(
        {
            "console_comment": ": aligned-by main-story: < 150s",
            "name1": "Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            "position": "post",
            "story": "carver_original",
            "exclude": ("gte", "timestamp", 150000),
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "greater",
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": aligned-by main-story: 60s - 90s",
            "name1": "Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            "exclude": [
                ("lt", "timestamp", 60000),
                ("gte", "timestamp", 90000),
            ],
            "position": "post",
            "story": "carver_original",
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "alternative": "greater",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": aligned-by new-story: 0 - 30s",
            "name1": "Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            "exclude": [
                ("gte", "timestamp", 30000),
            ],
            "position": "post",
            "story": "carver_original",
            "align_timestamp": "interference_reading_testing_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "alternative": "greater",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # 1) Neutralcue2 vs continued
    test_difference_bin_means(
        {
            "console_comment": ": aligned-by main-story: all",
            "name1": "Continued",
            "name2": "Baseline",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "neutralcue2"},
            "position": "post",
            "story": "carver_original",
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "greater",
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # 1) Neutralcue2 vs separated
    test_difference_bin_means(
        {
            "console_comment": ": aligned-by main-story: all",
            "name1": "Separated",
            "name2": "Baseline",
            "config1": {"condition": "interference_story_spr_end_separated"},
            "config2": {"condition": "neutralcue2"},
            "position": "post",
            "story": "carver_original",
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "greater",
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nTheme similarity to New Story", style="green")

    test_two(
        {
            "console_comment": ": aligned-by fa-start: 0s - 30s",
            "name1": "New Story Alone",
            "name2": "Continued",
            "config1": {
                "story": "dark_bedroom",
                "condition": "neutralcue",
            },
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_continued",
            },
            "exclude": [
                ("gte", "timestamp", 30000),
            ],
            "position": "post",
            "ratings": RATINGS_LIGHTBULB,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "alternative": "two-sided",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": aligned-by fa-start: 0s - 30s",
            "name1": "New Story Alone",
            "name2": "Separated",
            "config1": {
                "story": "dark_bedroom",
                "condition": "neutralcue",
            },
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_separated",
            },
            "exclude": [
                ("gte", "timestamp", 30000),
            ],
            "position": "post",
            "ratings": RATINGS_LIGHTBULB,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "alternative": "two-sided",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nLinger Rating to New Story", style="green")

    test_two(
        {
            "name1": "New Story Alone",
            "name2": "Continued",
            "config1": {
                "story": "dark_bedroom",
                "condition": "neutralcue",
            },
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_continued",
                "custom_measure": "linger_rating_interference",
            },
            "measure": "linger_rating",
            "story": "carver_original",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "New Story Alone",
            "name2": "Separated",
            "config1": {
                "story": "dark_bedroom",
                "condition": "neutralcue",
            },
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_separated",
                "custom_measure": "linger_rating_interference",
            },
            "measure": "linger_rating",
            "story": "carver_original",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def plots_fig_4_results():
    """
    For final plot use ghostscript to avoid compatibility issues
    with Preview and Chrome.

    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/prepress -dNOPAUSE \
        -dQUIET -dBATCH -sOutputFile=results4.gs.pdf results4.pdf
    """
    console.print("\nPlots: Continued v Separated", style="red bold")

    console.print("\nStory relatedness aligned by story 1", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "neutralcue2": POST_NOFILTER,
                            "interference_story_spr_end_continued": POST_NOFILTER,
                            "interference_story_spr_end_separated": POST_NOFILTER,
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "<b>Original story</b> relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": COL1,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "min_bin_n": 300,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": False,
            "legend": LEGEND_TOP_MID_SMALL,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 1200,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "continued_separated_aligned_reading_end_f4",
        }
    )

    console.print("\n Theme Similarity aligned by FA start", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "neutralcue2": POST_NOFILTER,
                            "interference_story_spr_end_continued": POST_NOFILTER,
                            "interference_story_spr_end_separated": POST_NOFILTER,
                            # "interference_story_spr": POST_NOFILTER,
                        },
                    ),
                    "dark_bedroom": ("condition", {"neutralcue": POST_NOFILTER}),
                },
            ),
            "ratings": RATINGS_LIGHTBULB,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "<b>New story</b> relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": THEME_SIMILARITY_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": COL1,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "min_bin_n": 300,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": False,
            "legend": LEGEND_TOP_MID_SMALL,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "condition",
            "symbol_map": {
                "neutralcue2": "circle",
                "interference_story_spr_end_continued": "circle",
                "interference_story_spr_end_separated": "circle",
                "neutralcue": "diamond",
            },
            "line_dash": "condition",
            "line_dash_map": {
                "neutralcue2": "solid",
                "interference_story_spr_end_continued": "solid",
                "interference_story_spr_end_separated": "solid",
                "neutralcue": "dash",
            },
            # plot save config
            "study": STUDY,
            "save": True,
            "scale": 2,
            "width": 1140,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "ts_lightbulb_aligned_fa_start_f4",
        }
    )

    console.print("\nIntegration attempt", style="yellow")
    plot_numeric_measure(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "interference_story_spr_end_continued": POST_NOFILTER,
                            "interference_story_spr_end_separated": POST_NOFILTER,
                        },
                    )
                },
            ),
            # plot data config
            "measure_name": "integration_attempt",
            "summary_func": np.nanmean,
            # plot config
            # "title": "While reading Part 2 I was<br>trying to relate it to Part 1.",
            "title": "",
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "orientation": "h",
            "showlegend": False,
            "x_ticktext": [],
            "x_tickvals": [],
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "axes_linewidth": 7,
            "x_title": "Condition",
            "y_title": "Effort to integrate",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": COL1,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "legend": None,
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # save config
            "save": True,
            "width": 720,
            "height": 420,
            "scale": 2.0,
            "filepostfix": "f4",
            "study": STUDY,
            "filetype": FILETYPE,
        }
    )

    return


def suppl_stats_plots_new_story_separated_integrated():
    console.print("\n\nSupplement Separated/Integrated: stats", style="red bold")

    console.print("\n Number of participants Separated/Integrated", style="yellow")
    story_spr_questionnaire_df = load_questionnaire(
        {"story": "carver_original", "condition": "interference_story_spr"}
    )
    n_separated = (
        story_spr_questionnaire_df["stories_distinct"] == "story-start"
    ).sum()
    n_integrated = (
        story_spr_questionnaire_df["stories_distinct"] != "story-start"
    ).sum()
    print(f"N Separated: {n_separated} | N Integrated: {n_integrated}")

    console.print("\nStats: Integrated v Separated", style="green")

    test_difference_bin_means(
        {
            "console_comment": ": aligned-by main-story: < 150s",
            "name1": "Integrated",
            "name2": "Separated",
            "config1": {
                "condition": "interference_story_spr_integrated",
                "exclude": [
                    ("gte", "timestamp", 150000),
                    ("eq", "stories_distinct", "story-start"),
                ],
            },
            "config2": {
                "condition": "interference_story_spr_separated",
                "include": [("eq", "stories_distinct", "story-start")],
                "exclude": ("gte", "timestamp", 150000),
            },
            "position": "post",
            "story": "carver_original",
            "key_maps": {
                "condition": {
                    "interference_story_spr_separated": "interference_story_spr",
                    "interference_story_spr_integrated": "interference_story_spr",
                }
            },
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "two-sided",  # two-sided, at this point this is exploratory
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": aligned-by main-story: 60s - 90s",
            "name1": "Integrated",
            "name2": "Separated",
            "config1": {
                "condition": "interference_story_spr_integrated",
                "exclude": [
                    ("lt", "timestamp", 60000),
                    ("gte", "timestamp", 90000),
                    ("eq", "stories_distinct", "story-start"),
                ],
            },
            "config2": {
                "condition": "interference_story_spr_separated",
                "include": [("eq", "stories_distinct", "story-start")],
                "exclude": [
                    ("lt", "timestamp", 60000),
                    ("gte", "timestamp", 90000),
                ],
            },
            "position": "post",
            "story": "carver_original",
            "key_maps": {
                "condition": {
                    "interference_story_spr_separated": "interference_story_spr",
                    "interference_story_spr_integrated": "interference_story_spr",
                }
            },
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "alternative": "greater",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # plot
    console.print("\nIntegrated/Separated aligned reading end.", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_story_spr_separated": POST_STORY_AWARE_FILTER,  # noqa:E501
                                    "interference_story_spr_integrated": POST_STORY_UNAWARE_FILTER,  # noqa:E501
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            "key_maps": {
                "condition": {
                    "interference_story_spr_separated": "interference_story_spr",
                    "interference_story_spr_integrated": "interference_story_spr",
                }
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            "min_bin_n": 200,
            "color": "condition",
            "color_map": {
                "neutralcue2": COL_NEUTRALCUE2,
                "interference_story_spr_separated": "#07CC00",
                "interference_story_spr_integrated": "#0A7300",
            },
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "Story relatedness",
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": {
                "interference_story_spr_integrated": "Integrated",
                "interference_story_spr_separated": "Separated",
                "neutralcue2": "Baseline",
            },
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE_SUPPL,
            "filepostfix": "suppl_separated_integrated",
        }
    )


def suppl_methods_experiment_overview():
    console.print("Supplemental Methods: Experiment Overview", style="blue")

    def func_print_n_participants(config: dict, data_df: pd.DataFrame):
        n_participants = len(data_df.index.unique())
        print(f"{config['story']} | {config['condition']} | N = {n_participants}")

    aggregator(
        config={
            "load_spec": ("all", {"all": ("story", ALL_STORIES_CONDITIONS_DCT)}),
            "aggregate_on": "condition",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            "corrections": True,
            "column": "story_relatedness",
        },
        load_func=load_questionnaire,
        call_func=func_print_n_participants,
    )


def suppl_methods_procedure_numbers():
    console.print(
        "\nSupplemental Methods: Experimental Procedure numbers", style="red bold"
    )

    words_df_pre = load_wordchains(
        {"story": "carver_original", "condition": "button_press", "position": "pre"}
    )
    words_df_post = load_wordchains(
        {"story": "carver_original", "condition": "button_press", "position": "post"}
    )

    n_words_pre = words_df_pre.groupby("participantID").count()["word_text"]
    n_words_post = words_df_post.groupby("participantID").count()["word_text"]

    mean_pre = round(n_words_pre.mean(), 1)
    mean_post = round(n_words_post.mean(), 1)

    std_pre = round(n_words_pre.std(), 1)
    std_post = round(n_words_post.std(), 1)

    print(f"Intact | pre | mean: {mean_pre} (SD: {std_pre})")
    print(f"Intact | post | mean: {mean_post} (SD: {std_post})")

    console.print("\nSupplemental Methods: Experiment 1: button_press", style="blue")
    button_press_questionnaire_df = load_questionnaire(
        {"story": "carver_original", "condition": "button_press"}
    )

    spr_wcg = button_press_questionnaire_df["spr-wcg-break"] / 1000
    spr_wcg_mean = round(spr_wcg.mean(), 2)
    spr_wcg_std = round(spr_wcg.std(), 2)
    spr_wcg_min = round(spr_wcg.min(), 2)
    spr_wcg_max = round(spr_wcg.max(), 2)
    print(
        f"carver | button_press | spr-wcg break time (s)"
        f" | mean: {spr_wcg_mean} | std: {spr_wcg_std}"
        f" | min: {spr_wcg_min} | max: {spr_wcg_max}"
    )

    spr_time = button_press_questionnaire_df["spr_time"] / 1000 / 60
    spr_time_mean = round(spr_time.mean(), 2)
    spr_time_std = round(spr_time.std(), 2)
    spr_time_min = round(spr_time.min(), 2)
    spr_time_max = round(spr_time.max(), 2)
    print(
        f"carver | button_press | spr task time (m)"
        f" | mean: {spr_time_mean} | std: {spr_time_std}"
        f" | min: {spr_time_min} | max: {spr_time_max}"
    )


def suppl_stats_words_generated():
    print("Supplemental Methods: Experiment 1: Words generated.")

    def func_load_words(config: dict) -> pd.DataFrame:
        return load_wordchains(config)

    def print_n_words(config: dict, data_df: pd.DataFrame):
        n_words_produced = len(data_df["word_text"])
        print(f"all | n words: {n_words_produced}")

    aggregator(
        config={
            "load_spec": ("all", {"all": ("story", ALL_STORIES_CONDITIONS_DCT)}),
            "aggregate_on": "story",
        },
        load_func=func_load_words,
        call_func=print_n_words,
    )

    def func_load_rated_words(config: dict) -> pd.DataFrame:
        return load_rated_wordchains(config)

    def print_n_unique_words(config: dict, data_df: pd.DataFrame):
        n_words_produced = len(data_df["word_text"].unique())
        print(f"all | n unique words: {n_words_produced}")
        n_rated_words = data_df["story_relatedness"].notna().sum()
        print(f"all | n rated words: {n_rated_words}")
        n_unique_rated_words = (
            data_df.drop_duplicates("word_text")["story_relatedness"].notna().sum()
        )
        print(f"all | n unique rated words: {n_unique_rated_words}")

    aggregator(
        config={
            "load_spec": ("all", {"all": ("story", ALL_STORIES_CONDITIONS_DCT)}),
            "aggregate_on": "all",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            "corrections": True,
            "column": "story_relatedness",
        },
        load_func=func_load_rated_words,
        call_func=print_n_unique_words,
    )

    # across all
    compute_word_stats(
        config={
            "load_spec": (
                "all",
                {"all": ("story", ALL_STORIES_CONDITIONS_DCT)},
            ),
            "aggregate_on": "all",
            "column": "story_relatedness",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            "study": STUDY,
        }
    )
    # individual conditions
    compute_word_stats(
        config={
            "load_spec": (
                "all",
                {"all": ("story", ALL_STORIES_CONDITIONS_DCT)},
            ),
            "aggregate_on": "condition",
            "column": "story_relatedness",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            "study": STUDY,
        }
    )


def suppl_plots_stats_volition():
    console.print("\n Volition and persistent mental content", style="red bold")
    # Don't let the function name fool you, this just gets an output
    # on the console and not a plot.
    console.print("\n > Volition categories ungrouped -> supplement", style="yellow")
    plot_categorical_measure(
        {
            # data
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {"button_press": POST_NOFILTER},
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "normalize": True,
            "measure_name": "volition",
            "x": "condition",
            "replace_columns": REPLACE_COLUMNS_VOLITION,
            "save": False,
            "latex": True,
            "latex_columns": ["volition", "count", "proportion"],
        }
    )
    plot_categorical_measure(
        {
            # data
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press_suppress": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "normalize": True,
            "measure_name": "volition",
            "x": "condition",
            "replace_columns": REPLACE_COLUMNS_VOLITION,
            "save": False,
            "latex": True,
            "latex_columns": ["volition", "count", "proportion"],
        }
    )

    # Plots
    console.print(
        "\n > Volition plots ungrouped story relatedness-> supplement", style="yellow"
    )
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "keep_columns": ["volition"],
            "additional_grouping_columns": ["volition"],
            "color": "volition",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            "replace_columns": REPLACE_COLUMNS_VOLITION,
            # plot visual config
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "color_map": COLOR_MAP_VOLITION_ALL,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "legend": LEGEND_RIGHT_NEXT,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "volition_bp",
        }
    )
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press_suppress": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "keep_columns": ["volition"],
            "additional_grouping_columns": ["volition"],
            "color": "volition",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            "replace_columns": REPLACE_COLUMNS_VOLITION,
            # plot visual config
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "color_map": COLOR_MAP_VOLITION_SUPPRESS_ALL,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "legend": LEGEND_RIGHT_NEXT,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "volition_bps",
        }
    )

    console.print(
        "\n > Volition plots ungrouped story thoughts -> supplement", style="yellow"
    )
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "double_press",
            "column": "double_press",
            "keep_columns": ["volition"],
            "additional_grouping_columns": ["volition"],
            "color": "volition",
            # "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            "replace_columns": REPLACE_COLUMNS_VOLITION,
            # plot visual config
            "x_title": "Time from start of of free association",
            "y_title": "Story thoughts",
            "x_range": [0, 6.05],
            "y_range": STORY_THOUGHTS_Y_RANGE_SUPPL,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_THOUGHTS_Y_VALS_TICKS_SUPPL,
            "y_ticktext": STORY_THOUGHTS_Y_VALS_TICKS_SUPPL,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "color_map": COLOR_MAP_VOLITION_ALL,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "legend": LEGEND_RIGHT_NEXT,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "volition_story_thoughts_bp",
        }
    )
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press_suppress": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "double_press",
            "column": "double_press",
            "keep_columns": ["volition"],
            "additional_grouping_columns": ["volition"],
            "color": "volition",
            # "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            "replace_columns": REPLACE_COLUMNS_VOLITION,
            # plot visual config
            "x_title": "Time from start of of free association",
            "y_title": "Story thoughts",
            "x_range": [0, 6.05],
            "y_range": STORY_THOUGHTS_Y_RANGE_SUPPL,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_THOUGHTS_Y_VALS_TICKS_SUPPL,
            "y_ticktext": STORY_THOUGHTS_Y_VALS_TICKS_SUPPL,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "color_map": COLOR_MAP_VOLITION_SUPPRESS_ALL,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "legend": LEGEND_RIGHT_NEXT,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "volition_story_thoughts_bps",
        }
    )


def suppl_stats_unintentional():
    console.print("\nUnintentional persistence of mental content", style="red bold")

    # Compute the stats on particiapnts
    test_two(
        {
            "name1": "Unintentional post",
            "name2": "Unintentional pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "story": "carver_original",
            "condition": "button_press",
            "include": ("eq", "volition", "unintentional"),
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",  # for consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": first 30s",
            "name1": "Unintentional post",
            "name2": "Unintentional pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "condition": "button_press",
            "include": ("eq", "volition", "unintentional"),
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",  # for consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": last 30s",
            "name1": "Unintentional post",
            "name2": "Unintentional pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("lt", "timestamp", 150000)],
            "story": "carver_original",
            "condition": "button_press",
            "include": ("eq", "volition", "unintentional"),
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Unintentional story thoughts",
            "name2": "Unintentional food thoughts",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "story": "carver_original",
            "condition": "button_press",
            "include": ("eq", "volition", "unintentional"),
            "ratings": RATINGS_CARVER,
            "measure": "thought_entries",
            "te_filter": dict(),
            "questionnaire_filter": dict(),
            "test_type": "wilcoxon",  # for consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Unintentional post",
            "name2": "Scrambled post",
            "config1": {
                "condition": "button_press",
                "include": ("eq", "volition", "unintentional"),
            },
            "config2": {"condition": "word_scrambled"},
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",  # for consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Unintentional",
            "name2": "Scrambled",
            "config1": {
                "condition": "button_press",
                "include": ("eq", "volition", "unintentional"),
            },
            "config2": {"condition": "word_scrambled"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",  # for consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def suppl_plots_stats_wcg_strategy():
    console.print("\nSupplement: Stats strategies", style="red bold")

    console.print("\nInter-rater reliability", style="green")
    krippendorf_alpha(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": NOFILTER,
                                },
                            ),
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "no_extra_columns": True,
            "field": "wcg_strategy",
            "raters": ["rater1", "rater2"],
            "n_categories": 6,
        }
    )

    krippendorf_alpha(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press_suppress": NOFILTER,
                                },
                            ),
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "no_extra_columns": True,
            "field": "wcg_strategy",
            "raters": ["rater1", "rater2"],
            "n_categories": 7,  # rater2 missed two participants -> 7 categories
        }
    )

    console.print("\nStats no-strategy vs strategy", style="green")

    test_two(
        {
            "console_comment": " - Intact",
            "name1": "Overt strategy",
            "name2": "No Strategy",
            "config1": {
                "condition": "button_press",
                "include": [("eq", "wcg_strategy_category", "strategy")],
            },
            "config2": {
                "condition": "button_press",
                "exclude": [("eq", "wcg_strategy_category", "strategy")],
            },  # no normality (barely)
            "ratings": RATINGS_CARVER,
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",  # group participatns into
            # no_strategy only if all raters did so.
            "story": "carver_original",
            "position": "post",
            "column": "story_relatedness",
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    test_two(
        {
            "console_comment": " - Intact",
            "name1": "Overt strategy",
            "name2": "No Strategy",
            "config1": {
                "condition": "button_press",
                "include": [("eq", "wcg_strategy_category", "strategy")],
            },
            "config2": {
                "condition": "button_press",
                "exclude": [("eq", "wcg_strategy_category", "strategy")],
            },
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",
            "story": "carver_original",
            "position": "post",
            "measure": "thought_entries",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    test_two(
        {
            "console_comment": " - Intact",
            "name1": "Overt strategy",
            "name2": "No Strategy",
            "config1": {
                "condition": "button_press",
                "include": [("eq", "wcg_strategy_category", "strategy")],
            },
            "config2": {
                "condition": "button_press",
                "exclude": [("eq", "wcg_strategy_category", "strategy")],
            },
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",
            "story": "carver_original",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # Suppress
    test_two(
        {
            "console_comment": " - Suppress",
            "name1": "Overt strategy",
            "name2": "No Strategy",
            "config1": {
                "condition": "button_press_suppress",
                "include": [("eq", "wcg_strategy_category", "strategy")],
            },
            "config2": {
                "condition": "button_press_suppress",
                "exclude": [("eq", "wcg_strategy_category", "strategy")],
            },
            "ratings": RATINGS_CARVER,
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",
            "story": "carver_original",
            "position": "post",
            "column": "story_relatedness",
            "measure": "story_relatedness",
            "test_type": "mwu",  # for consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    test_two(
        {
            "console_comment": " - Suppress",
            "name1": "Overt strategy",
            "name2": "No Strategy",
            "config1": {
                "condition": "button_press_suppress",
                "include": [("eq", "wcg_strategy_category", "strategy")],
            },
            "config2": {
                "condition": "button_press_suppress",
                "exclude": [("eq", "wcg_strategy_category", "strategy")],
            },
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",
            "story": "carver_original",
            "position": "post",
            "measure": "thought_entries",
            "test_type": "ind",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    test_two(
        {
            "console_comment": " - Suppress",
            "name1": "Overt strategy",
            "name2": "No Strategy",
            "config1": {
                "condition": "button_press_suppress",
                "include": [("eq", "wcg_strategy_category", "strategy")],
            },
            "config2": {
                "condition": "button_press_suppress",
                "exclude": [("eq", "wcg_strategy_category", "strategy")],
            },
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",
            "story": "carver_original",
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nSUPPL: Strategies: Table with ratings", style="green")
    # Rater 1: AL, Rater 2: AA
    console.print("\nRater 1:", style="yellow")
    plot_categorical_measure(
        {
            # data
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_NOFILTER,
                                    "button_press_suppress": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "normalize": True,
            "x": "condition",
            "measure_name": "wcg_strategy_category",
            "fields": ["wcg_strategy"],
            "method": "rater:rater2",
            "multiple_category_strategy": "expand",
            "replace_columns": REPLACE_COLUMNS_STRATEGIES,
            "save": False,
        }
    )
    console.print("\nRater 2:", style="yellow")
    plot_categorical_measure(
        {
            # data
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_NOFILTER,
                                    "button_press_suppress": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            "normalize": True,
            "x": "condition",
            "measure_name": "wcg_strategy_category",
            "fields": ["wcg_strategy"],
            "method": "rater:rater1",
            "multiple_category_strategy": "expand",
            "replace_columns": REPLACE_COLUMNS_STRATEGIES,
            "save": False,
        }
    )

    legend_name_mapping_strategy = {
        "button_press-no_strategy": "Intact - No Strategy",
        "button_press-strategy": "Intact - Overt Strategy",
        "button_press_suppress-no_strategy": "Suppress - No Strategy",
        "button_press_suppress-strategy": "Suppress - Overt Strategy",
    }

    color_map_strategy = {
        "button_press-no_strategy": "#C41414",
        "button_press-strategy": "#5E0909",
        "button_press_suppress-no_strategy": "#2F6B2F",
        "button_press_suppress-strategy": "#163316",
    }
    line_dash_map_strategy = {
        "button_press-no_strategy": "longdash",
        "button_press-strategy": "dot",
        "button_press_suppress-no_strategy": "longdash",
        "button_press_suppress-strategy": "dot",
    }
    symbol_map_strategy = {
        "button_press-no_strategy": "circle",
        "button_press-strategy": "diamond",
        "button_press_suppress-no_strategy": "circle",
        "button_press_suppress-strategy": "diamond",
    }
    # offset_config_strategy = {
    #     "wcg_strategy_category": [("no_strategy", 0.05), ("strategy", -0.05)]
    # }

    console.print("\nSUPPL: PLOT: Strategy v No Strategy - story relatedness")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_TIMEFILTER,
                                    "button_press_suppress": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",
            "keep_columns": ["wcg_strategy_category"],
            "additional_grouping_columns": ["wcg_strategy_category"],
            "merged_columns": ["condition", "wcg_strategy_category"],
            "color": "merged_columns",
            "color_map": color_map_strategy,
            "symbol": "merged_columns",
            "line_dash_map": line_dash_map_strategy,
            "symbol_map": symbol_map_strategy,
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": legend_name_mapping_strategy,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_bps_story_relatedness_strategy",
        }
    )

    console.print("\nSUPPL: PLOT: Strategy v No Strategy - story thoughts")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_TIMEFILTER,
                                    "button_press_suppress": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "double_press",
            "column": "double_press",
            "fields": ["wcg_strategy"],
            "method": "strategy_no_strategy_strict",
            "keep_columns": ["wcg_strategy_category"],
            "additional_grouping_columns": ["wcg_strategy_category"],
            "merged_columns": ["condition", "wcg_strategy_category"],
            "color": "merged_columns",
            "color_map": color_map_strategy,
            "symbol": "merged_columns",
            "line_dash_map": line_dash_map_strategy,
            "symbol_map": symbol_map_strategy,
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "x_title": "Time from start of free association",
            "y_title": "Story thoughts",
            "x_range": [0, 6.05],
            "y_range": STORY_THOUGHTS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_THOUGHTS_Y_VALS_TICKS,
            "y_ticktext": STORY_THOUGHTS_Y_VALS_TICKS,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": legend_name_mapping_strategy,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_bps_story_thoughts_strategy",
        }
    )

    color_map_strategies = {
        "No Strategy": "#C41414",
        "Categories": "#FF1414",
        "Surroundings": "#F4A4A1",
        "Rhyming": "#BCA4A1",
        "Other": "#454545",
    }

    line_dash_map_strategies = {
        "No Strategy": "longdash",
        "Categories": "dot",
        "Surroundings": "dashdot",
        "Rhyming": "dash",
        "Other": "longdashdot",
    }

    symbol_map_strategies = {
        "No Strategy": "circle",
        "Categories": "diamond",
        "Surroundings": "square",
        "Rhyming": "cross",
        "Other": "x",
    }

    print("\n > wcg_strategy plots ungrouped -> supplement")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "fields": ["wcg_strategy"],
            "method": "rater:rater2",
            "multiple_category_strategy": "exclude",
            "keep_columns": ["wcg_strategy_category"],
            "additional_grouping_columns": ["wcg_strategy_category"],
            "color": "wcg_strategy_category",
            "color_map": color_map_strategies,
            "symbol": "wcg_strategy_category",
            "symbol_map": symbol_map_strategies,
            "line_dash_map": line_dash_map_strategies,
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            "replace_columns": REPLACE_COLUMNS_STRATEGIES,
            # plot visual config
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "legend": LEGEND_RIGHT_NEXT,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE_SUPPL,
            "filepostfix": "strategy",
        }
    )


def suppl_choice_baseline_fig_3_and_distribution_first_bin_aligned():
    console.print(
        "\nFig 3: Baseline choice & Distribution within first bin\n", style="red bold"
    )
    # At some point we switched to button_press as comparison condition to
    # the interference conditions.
    # However, we found a significant difference comparing the aligned-by-story end
    # button_press and situation condition, which wasn't apparent before because we used
    # the mean of all words in a bin, vs the mean of the within-participant mean in the
    # sbin.

    bp_30s_60s_bin_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "exclude": [
                ("lt", "timestamp", 30000),
                ("gte", "timestamp", 60000),
            ],
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "column": "story_relatedness",
        }
    )
    mean_across_participants = bp_30s_60s_bin_df["story_relatedness"].mean()
    mean_mean_within_participants = (
        bp_30s_60s_bin_df.groupby("participantID")["story_relatedness"].mean().mean()
    )
    print(
        f"Mean across participants: {mean_across_participants}"
        f"\nMean of mean within participants: {mean_mean_within_participants}"
    )

    # This raised following question:

    # How should mean story relatedness be computed?
    # Should the within-participant mean be computed first, or does that upweigh
    # outliers inaccurately?

    import plotly.express as px

    plot_distribution(
        {
            "load_spec": (
                "condition",
                {
                    "button_press": ("filter", {}),
                    "interference_situation": ("filter", {}),
                },
            ),
            "aggregate_on": "condition",
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "exclude": [
                ("lt", "timestamp", 30000),
                ("gte", "timestamp", 60000),
            ],
            "measure": "story_relatedness",
            # plot visual config
            "nbins": 12,
            "bargap": 0.1,
            "descriptive_lines": True,
            "group_column": "participantID",
            "min_x": 1,
            "max_x": 7,
            "y_range": [0, 404],
            "color_sequence": px.colors.sequential.Rainbow,
            # saving config
            "save": True,
            "study": STUDY_SUPPL,
            "scale": 2,
            "width": 810,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "post.across_participants.<condition>",
            "show": False,
        }
    )

    plot_distribution(
        {
            "load_spec": (
                "condition",
                {
                    "button_press": ("filter", {}),
                    "interference_situation": ("filter", {}),
                },
            ),
            "aggregate_on": "condition",
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "exclude": [
                ("lt", "timestamp", 30000),
                ("gte", "timestamp", 60000),
            ],
            "measure": "story_relatedness",
            "within_participant_summary": True,
            # plot visual config
            "nbins": 12,
            "bargap": 0.1,
            "descriptive_lines": True,
            "group_column": "participantID",
            "min_x": 1,
            "max_x": 7,
            "y_range": [0, 50],
            "color_sequence": px.colors.sequential.Rainbow,
            # saving config
            "save": True,
            "study": STUDY_SUPPL,
            "scale": 2,
            "width": 810,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "post.within_participants.<condition>",
            "show": False,
        }
    )
    # Unfortunately these plots are not very helpful (because of the high n), but it
    # seems to make more sense to compute the mean of the mean of each participant, and
    # the plots do not seem to speak against that idea.

    # We also wondered that the difference in computing means may arose from an effect
    # in which participans who produced high-story related words only produced very few
    # words, and then taking within-participant means upweighting these observations.
    # Thus we computed, for the by-end-of-story-aligned 30s-60s time-bin in button_press
    # the relationship between mean_story_relatedness and number of words for each
    # participant:
    n_words = bp_30s_60s_bin_df.groupby("participantID")["story_relatedness"].count()
    n_words.name = "n_words"
    mean_sr = bp_30s_60s_bin_df.groupby("participantID")["story_relatedness"].mean()
    mean_sr.name = "mean_story_relatedness"
    corr_msr_nwords = np.corrcoef(n_words, mean_sr)[0, 1]
    print(f"Correlation mean story relatedness & n words in bin: {corr_msr_nwords}")

    # Indeed there seems to be a correlation: -0.2
    # So what if the participants producing few high story relatedness words are
    # different in this condition, because they interact in some way with the button
    # presses of the thought entries?
    n_te_df = load_n_thought_entries(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "column": "story_relatedness",
        },
        {
            "exclude": [
                ("lt", "timestamp", 30000),
                ("gte", "timestamp", 60000),
            ],
        },
        {},
    )[["thought_entries"]]
    aggs_df = pd.merge(
        pd.merge(n_words, mean_sr, left_index=True, right_index=True),
        n_te_df,
        left_index=True,
        right_index=True,
    )

    from oc_pmc.utils import save_plot

    fig = px.scatter(
        aggs_df,
        x="n_words",
        y="mean_story_relatedness",
        trendline="ols",
        color="thought_entries",
    )
    save_plot(
        {
            "width": 900,
            "height": 900,
            "scale": 2,
        },
        fig,
        "distribution/bp_30s_60s_bin_msr_n_words.png",
    )

    # Looking at the plot you can see:
    # 1. Less data points in the top right
    # 2. Most people who pressed the button more often are in/towards the top-left
    # => thus there seems to be some interaction in which button presses affect how
    # people report/generate words, and button_press is not the appropriate baseline
    # for the interfere conditions.

    # Furthemore, computing the difference between the conditions at different bin
    # positions reveals that at all but position 25s, and 30s the difference is not
    # significant. Furthermore, the significance at 25s and 30s wouldn't survive
    # multiple comparison correction.
    bin_starts_and_ends = [
        (15000, 45000),
        (20000, 50000),
        (25000, 55000),
        (30000, 60000),
        (35000, 65000),
        (40000, 70000),
        (45000, 75000),
        (50000, 80000),
    ]
    for bin_start, bin_end in bin_starts_and_ends:
        console.print(f"Bin position: {bin_start / 1000}s", style="yellow")
        sr_two(
            {
                "config1": {
                    "condition": "button_press",
                    "exclude": [
                        ("lt", "timestamp", bin_start),
                        ("gte", "timestamp", bin_end),
                    ],
                },
                "config2": {
                    "condition": "interference_situation",
                    "exclude": [
                        ("lt", "timestamp", bin_start),
                        ("gte", "timestamp", bin_end),
                    ],
                },
                "story": "carver_original",
                "position": "post",
                "ratings": RATINGS_CARVER,
                "align_timestamp": "reading_task_end",
                "column": "story_relatedness",
                "within_participant_summary": True,
                "test_type": "ind",
            }
        )

    # We thus feel justified in concluding the difference in the bin starting at
    # 25s and 30s between button_press and situation is not reflective of the
    # persistence of mental content being blocked.


def suppl_plots_by_words():
    console.print("\nSupplement: Plots by words", style="red bold")

    MARKER_SIZE_BY_WORDS = 13
    LINE_WIDTH_BY_WORDS = 4
    X_RANGE_BY_WORDS = [0, 12.1]

    console.print("Fig 1 Intact v Word Scrambled", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": PRE_POST_TIMEFILTER,
                                    "word_scrambled": PRE_POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "x_column": "word_count",
            "color": "condition",
            "symbol": "position",
            "plotkind": "line",
            "step": 10,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Words since start of free association",
            "y_title": "Story relatedness",
            "x_range": X_RANGE_BY_WORDS,
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "axes_linewidth": 7,
            "marker_size": MARKER_SIZE_BY_WORDS,
            "line_width": LINE_WIDTH_BY_WORDS,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": False,
            "legend": LEGEND_TOP_MID,
            "legend_name_mapping": LEGEND_NAME_MAPPING,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_ws_suppl_f1",
        }
    )

    console.print("Fig 2 volition: all v unintentional", style="yellow")
    # Volition
    # Need to do data loading & plotting manually
    bp_all_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "keep_columns": ["linger_rating"],
        }
    )
    bps_all_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "keep_columns": ["linger_rating"],
        }
    )
    bp_unintentional_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "include": [("eq", "volition", "unintentional")],
            "keep_columns": ["linger_rating"],
        }
    )
    bps_unintentional_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "exclude": [("gte", "timestamp", 180000)],
            "include": [("eq", "volition", "unintentional")],
            "keep_columns": ["linger_rating"],
        }
    )

    bp_all_df["condition"] = "all-button_press"
    bps_all_df["condition"] = "all-button_press_suppress"
    bp_unintentional_df["condition"] = "unintentional-button_press"
    bps_unintentional_df["condition"] = "unintentional-button_press_suppress"

    data_df = pd.concat(
        (bp_all_df, bps_all_df, bp_unintentional_df, bps_unintentional_df)
    )
    # to add the grouping columns, easier than custumizable grouping columns
    data_df["story"] = "carver_original"
    data_df["position"] = "post"

    from oc_pmc.plot.by_time_shifted import func_plot_by_time

    func_plot_by_time(
        config={
            "column": "story_relatedness",
            "x_column": "word_count",
            "mode": "relatedness",
            "step": 10,
            "min_bin_n": 1,
            "plotkind": "line",
            "color": "condition",
            "x_title": "Words since start of free association",
            "y_title": "Story relatedness",
            "x_range": X_RANGE_BY_WORDS,
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "axes_linewidth": 7,
            "marker_size": MARKER_SIZE_BY_WORDS,
            "line_width": LINE_WIDTH_BY_WORDS,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_VOLITION_MERGED,
            "category_orders": ORDER_CONDITIONS_VOLITION_MERGED,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": False,
            "legend": LEGEND_TOP_MID,
            "legend_name_mapping": LEGEND_NAME_MAPPING,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "bp_bps_volition_suppl_f2",
        },
        data_df=data_df,
    )

    console.print("\nFig. 3 Interference", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_geometry": POST_NOFILTER,
                                    "interference_situation": POST_NOFILTER,
                                    "interference_tom": POST_NOFILTER,
                                    "interference_story_spr": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "x_column": "word_count",
            "step": 10,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Words since start of free association",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": X_RANGE_BY_WORDS,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "axes_linewidth": 7,
            "marker_size": MARKER_SIZE_BY_WORDS,
            "line_width": LINE_WIDTH_BY_WORDS,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": False,
            "legend": LEGEND_TOP_MID,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "interference_suppl_f3",
        }
    )

    console.print("\nFig. 4 Continued/Separated", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_story_spr_end_continued": POST_NOFILTER,  # noqa: E501
                                    "interference_story_spr_end_separated": POST_NOFILTER,  # noqa: E501
                                    "interference_story_spr": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "x_column": "word_count",
            "step": 10,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Words since start of free association",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": X_RANGE_BY_WORDS,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "axes_linewidth": 7,
            "marker_size": MARKER_SIZE_BY_WORDS,
            "line_width": LINE_WIDTH_BY_WORDS,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": False,
            "legend": LEGEND_TOP_MID,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "interference_suppl_f4",
        }
    )


def suppl_stats_submission_time():
    console.print("\nSupplement: Submission time\n", style="red bold")

    console.print(" > Mean times", style="yellow")

    def print_mean_sd(config: dict, data_df: pd.DataFrame):
        participant_mean_df = data_df.groupby(
            ["story", "condition", "position", "participantID"]
        ).agg({"word_time": "mean"})
        data_aggr = (
            participant_mean_df.groupby(["position", "story", "condition"])
            .agg(
                mean=("word_time", "mean"),
                std=("word_time", "std"),
                n=("word_time", "count"),
            )
            .round(2)
        )
        print(data_aggr)

    aggregator(
        config={"load_spec": ("story", ALL_STORIES_CONDITIONS_DCT)},
        load_func=load_wordchains,
        call_func=print_mean_sd,
    )

    console.print("\n > Intact vs Scrambled in times", style="yellow")
    test_two(
        {
            "name1": "Intact",
            "name2": "Scrambled",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "word_scrambled"},
            "story": "carver_original",
            "position": "post",
            "measure": "word_time",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Intact vs Suppress in times", style="yellow")
    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "story": "carver_original",
            "position": "post",
            "measure": "word_time",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Baseline vs Suppress No Button Press in times", style="yellow")
    test_two(
        {
            "name1": "Baseline",
            "name2": "Suppress No Button Press",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "suppress"},
            "story": "carver_original",
            "position": "post",
            "measure": "word_time",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Interference conditions", style="yellow")
    test_multiple(
        {
            "configs": [
                {"story": "carver_original", "condition": "neutralcue2"},
                {"story": "carver_original", "condition": "interference_situation"},
                {"story": "carver_original", "condition": "interference_tom"},
                {"story": "carver_original", "condition": "interference_story_spr"},
                {"story": "carver_original", "condition": "interference_geometry"},
                {"story": "carver_original", "condition": "interference_pause"},
                # {"story": "dark_bedroom", "condition": "neutralcue"},
            ],
            "position": "post",
            "measure": "word_time",
            "test_type": "kw",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Pairwise comparisons", style="green")
    conditions = [
        "neutralcue2",
        "interference_situation",
        "interference_tom",
        "interference_story_spr",
        "interference_geometry",
        "interference_pause",
    ]
    condition_combinations = combinations(conditions, 2)

    multiple_comparions: list[tuple[str, float]] = list()
    for condition1, condition2 in condition_combinations:
        name1 = NAME_MAPPING[condition1]
        name2 = NAME_MAPPING[condition2]
        console.print(
            f"\n > {name1} - {name2}",
            style="yellow",
        )
        pval = test_two(
            {
                "name1": name1,
                "name2": name2,
                "config1": {"condition": condition1},
                "config2": {"condition": condition2},
                "story": "carver_original",
                "position": "post",
                "measure": "word_time",
                "test_type": "kw",
                "threshold": P_DISPLAY_THRESHOLD,
            }
        )
        multiple_comparions.append((f"{name1}, {name2}", pval))
    # sort ascending
    multiple_comparions.sort(key=lambda x: x[1])
    # threshold p values
    thresholds = [
        SIGNIFICANCE_THRESHHOLD / idx
        for idx in range(math.comb(len(conditions), 2), 0, -1)
    ]
    print("\nHolm-Bonferroni correction:")
    violated = False
    for comparison, threshold in zip(multiple_comparions, thresholds):
        if comparison[1] >= threshold:
            violated = True
        if violated:
            console.print(
                f"{comparison[0]} - p = {round(comparison[1], 4)}"
                f" > {round(threshold, 4)}",
                style="red",
            )
        else:
            console.print(
                f"{comparison[0]} - p = {round(comparison[1], 4)}"
                f" < {round(threshold, 4)}",
                style="green",
            )


def suppl_plots_submission_time():
    console.print("\nSuppl Materials: Submission time plots", style="red bold")

    console.print("\n > Word times: Intact, Scrambled", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "position",
                {
                    "post": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": NOFILTER,
                                    "word_scrambled": TIMEFILTER,
                                },
                            )
                        },
                    ),
                    "pre": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": NOFILTER,
                                    "word_scrambled": TIMEFILTER,
                                },
                            )
                        },
                    ),
                },
            ),
            "aggregate_on": "position",
            # plot data config
            "mode": "word_time",
            "column": "word_time",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Submission time (ms)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": WORD_TIME_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 21,
            "line_width": 5,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_LEFT_MEDIUM,
            "legend_name_mapping": LEGEND_NAME_MAPPING_WITH_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            "symbol_map": SYMBOL_MAP_POSITION,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_word_time_bp_ws",
        }
    )

    console.print("\n > Word times: New Story Alone", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "position",
                {
                    "post": (
                        "story",
                        {
                            "dark_bedroom": (
                                "condition",
                                {
                                    "neutralcue": NOFILTER,
                                },
                            ),
                        },
                    ),
                    "pre": (
                        "story",
                        {
                            "dark_bedroom": (
                                "condition",
                                {
                                    "neutralcue": NOFILTER,
                                },
                            ),
                        },
                    ),
                },
            ),
            "aggregate_on": "position",
            # plot data config
            "mode": "word_time",
            "column": "word_time",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Submission time (ms)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": WORD_TIME_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 21,
            "line_width": 5,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_LEFT_MEDIUM,
            "legend_name_mapping": LEGEND_NAME_MAPPING_WITH_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            "symbol_map": SYMBOL_MAP_POSITION,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_word_time_lightbulb",
        }
    )

    console.print("\n > Word times: Intact, Suppress", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "position",
                {
                    "post": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": NOFILTER,
                                    "button_press_suppress": NOFILTER,
                                },
                            )
                        },
                    ),
                    "pre": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "button_press": NOFILTER,
                                    "button_press_suppress": NOFILTER,
                                },
                            )
                        },
                    ),
                },
            ),
            "aggregate_on": "position",
            # plot data config
            "mode": "word_time",
            "column": "word_time",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Submission time (ms)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": WORD_TIME_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 21,
            "line_width": 5,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_LEFT_MEDIUM,
            "legend_name_mapping": LEGEND_NAME_MAPPING_WITH_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            "symbol_map": SYMBOL_MAP_POSITION,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_word_time_intact_suppress",
        }
    )

    console.print("\n > Word times: Baseline, Suppress No Button Press", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "position",
                {
                    "post": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "suppress": NOFILTER,
                                    "neutralcue2": NOFILTER,
                                },
                            )
                        },
                    ),
                    "pre": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "suppress": NOFILTER,
                                    "neutralcue2": NOFILTER,
                                },
                            )
                        },
                    ),
                },
            ),
            "aggregate_on": "position",
            # plot data config
            "mode": "word_time",
            "column": "word_time",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Submission time (ms)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": WORD_TIME_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 21,
            "line_width": 5,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_LEFT_MEDIUM,
            "legend_name_mapping": LEGEND_NAME_MAPPING_WITH_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            "symbol_map": SYMBOL_MAP_POSITION,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_word_time_baseline_suppress_simple",
        }
    )

    console.print("\n > Word times: Interference", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "position",
                {
                    "post": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": NOFILTER,
                                    "interference_situation": NOFILTER,
                                    "interference_tom": NOFILTER,
                                    "interference_geometry": NOFILTER,
                                    "interference_story_spr": NOFILTER,
                                    "interference_pause": NOFILTER,
                                    "interference_end_pause": NOFILTER,
                                },
                            )
                        },
                    ),
                    "pre": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": NOFILTER,
                                    "interference_situation": NOFILTER,
                                    "interference_tom": NOFILTER,
                                    "interference_geometry": NOFILTER,
                                    "interference_story_spr": NOFILTER,
                                    "interference_pause": NOFILTER,
                                    "interference_end_pause": NOFILTER,
                                },
                            )
                        },
                    ),
                },
            ),
            "aggregate_on": "position",
            # plot data config
            "mode": "word_time",
            "column": "word_time",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Submission time (ms)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": WORD_TIME_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 21,
            "line_width": 5,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_LEFT_MEDIUM,
            "legend_name_mapping": LEGEND_NAME_MAPPING_WITH_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_word_time_interference",
        }
    )

    console.print("\n > Word times: Continued/Separated/Delayed", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "position",
                {
                    "post": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": NOFILTER,
                                    "interference_story_spr_end_continued": NOFILTER,  # noqa: E501
                                    "interference_story_spr_end_separated": NOFILTER,  # noqa: E501
                                    "interference_story_spr_end_delayed_continued": NOFILTER,  # noqa: E501
                                },
                            )
                        },
                    ),
                    "pre": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": NOFILTER,
                                    "interference_story_spr_end_continued": NOFILTER,  # noqa: E501
                                    "interference_story_spr_end_separated": NOFILTER,  # noqa: E501
                                    "interference_story_spr_end_delayed_continued": NOFILTER,  # noqa: E501
                                },
                            )
                        },
                    ),
                },
            ),
            "aggregate_on": "position",
            # plot data config
            "mode": "word_time",
            "column": "word_time",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Submission time (ms)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": WORD_TIME_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 21,
            "line_width": 5,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": COL1,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_LEFT_MEDIUM,
            "legend_name_mapping": LEGEND_NAME_MAPPING_WITH_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_word_time_separated_continued",
        }
    )

    console.print(
        "\n > Supplemental supplement: distribution word submission"
        "times in Scrambled (not used in the paper)",
        style="blue",
    )
    plot_distribution(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "button_press": POST_TIMEFILTER,
                            "word_scrambled": POST_TIMEFILTER,
                        },
                    )
                },
            ),
            "measure": "word_time",
            "color": "condition",
            "histnorm": "percent",
            "title": None,
            "x_title": "Mean submission time (ms)",
            "y_title": "Proportion of participants (%)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": AXES_COLOR,
            "axes_tickcolor": AXES_COLOR,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": {
                "button_press": "Intact",
                "word_scrambled": "Scrambled",
            },
            # save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 900,
            "height": 720,
            "filetype": FILETYPE_SUPPL,
            "filepostfix": "supp_supp_distribution_submission_time",
        }
    )


def suppl_plots_stats_lightbulb():
    console.print("\nSuppl Materials: New Story Alone", style="red bold")

    test_two(
        {
            "console_comment": ": first 30s: TOWARDS LIGHTBULB",
            "name1": "New Story Alone post 0s-30s",
            "name2": "New Story Alone pre 0s-30s",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "dark_bedroom",
            "condition": "neutralcue",
            "ratings": RATINGS_LIGHTBULB,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",  # consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "New Story Alone post 150s-180s",
            "name2": "New Story Alone pre 150s-180s",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "story": "dark_bedroom",
            "condition": "neutralcue",
            "ratings": RATINGS_LIGHTBULB,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_difference_bin_means(
        {
            "console_comment": ": TOWARDS LIGHTBULB",
            "name1": "Baseline post",
            "name2": "Baseline pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "condition": "neutralcue2",
            "story": "carver_original",
            "ratings": RATINGS_LIGHTBULB,
            "measure": "story_relatedness",
            "alternative": "two-sided",
            "step": 30000,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": first 30s: TOWARDS LIGHTBULB",
            "name1": "New Story Alone post 0s-30s",
            "name2": "Baseline post 0s-30s",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {"story": "carver_original", "condition": "neutralcue2"},
            "exclude": [("gte", "timestamp", 30000)],
            "position": "post",
            "ratings": RATINGS_LIGHTBULB,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": last 30s: TOWARDS LIGHTBULB",
            "name1": "New Story Alone post 150s-180s",
            "name2": "Baseline post 150s-180s",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {"story": "carver_original", "condition": "neutralcue2"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "position": "post",
            "ratings": RATINGS_LIGHTBULB,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_difference_bin_means(
        {
            "console_comment": ": TOWARDS ORIGINAL STORY",
            "name1": "New Story Alone post",
            "name2": "New Story Alone pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "condition": "neutralcue",
            "story": "dark_bedroom",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "two-sided",
            "step": 30000,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": first 30s: TOWARDS ORIGINAL STORY",
            "name1": "New Story Alone post 0s-30s",
            "name2": "Baseline post 0s-30s",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {"story": "carver_original", "condition": "neutralcue2"},
            "exclude": [("gte", "timestamp", 30000)],
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "console_comment": ": last 30s: TOWARDS ORIGINAL STORY",
            "name1": "New Story Alone post 150s-180s",
            "name2": "Baseline post 150s-180s",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {"story": "carver_original", "condition": "neutralcue2"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "New Story Alone",
            "name2": "Baseline",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {"story": "carver_original", "condition": "neutralcue2"},
            "measure": "linger_rating",
            "test_type": "mwu",  # consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "New Story Alone post 0s-30s",
            "name2": "New Story Alone pre 0s-30s",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "dark_bedroom",
            "condition": "neutralcue",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "New Story Alone post 150s-180s",
            "name2": "New Story Alone pre 150s-180s",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "story": "dark_bedroom",
            "condition": "neutralcue",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Plot: New Story Alone Lightbulb-Relatedness", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "neutralcue2": PRE_POST_TIMEFILTER,
                        },
                    ),
                    "dark_bedroom": (
                        "condition",
                        {
                            "neutralcue": PRE_POST_TIMEFILTER,
                        },
                    ),
                },
            ),
            "verbose": True,
            "ratings": RATINGS_LIGHTBULB,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "color": "condition",
            "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "<b>New story</b> relatedness",
            "x_range": None,
            "y_range": THEME_SIMILARITY_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": {
                "neutralcue2, post": "Baseline - Post",
                "neutralcue2, pre": "Baseline - Pre",
                "neutralcue, post": "New Story Alone - Post",
                "neutralcue, pre": "New Story Alone - Pre",
            },
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_lightbulb_ts_lightbulb",
        }
    )

    console.print("\n > Plot: New Story Alone Carver-Relatedness", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "neutralcue2": PRE_POST_TIMEFILTER,
                        },
                    ),
                    "dark_bedroom": (
                        "condition",
                        {
                            "neutralcue": PRE_POST_TIMEFILTER,
                        },
                    ),
                },
            ),
            "verbose": True,
            "ratings": RATINGS_CARVER,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "color": "condition",
            "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "<b>Original story</b> relatedness",
            "x_range": None,
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_TOP_RIGHT,
            "legend_name_mapping": {
                "neutralcue2, post": "Baseline - Post",
                "neutralcue2, pre": "Baseline - Pre",
                "neutralcue, post": "New Story Alone - Post",
                "neutralcue, pre": "New Story Alone - Pre",
            },
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 990,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_lightbulb_sr_carver",
        }
    )

    console.print("\n > Plot: New Story Alone Self Reported Lingering", style="yellow")
    plot_numeric_measure(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                },
                            ),
                            "dark_bedroom": (
                                "condition",
                                {
                                    "neutralcue": POST_NOFILTER,
                                },
                            ),
                        },
                    )
                },
            ),
            "aggregate_on": "all",
            # plot data config
            "measure_name": "linger_rating",
            "summary_func": np.nanmean,
            # plot config
            "title": None,
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "orientation": "h",
            "showlegend": False,
            "x_ticktext": [],
            "x_tickvals": [],
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "y_title": "Self-reported lingering",
            "y_title_font_size": 42,
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # Lines
            "hlines": [
                {
                    "y": 2.62,
                    "line": {
                        "dash": "dash",
                        "color": COLOR_SEQUENCE_ORDERED[
                            ORDER_CONDITIONS["condition"].index("word_scrambled")
                        ],
                        "width": 9,
                    },
                },
            ],
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # save config
            "save": True,
            "width": 660,
            "height": 420,
            "scale": 2.0,
            "filepostfix": "suppl_lightbulb",
            "study": STUDY_SUPPL,
            "filetype": FILETYPE,
            # kruskal
            "kruskal": False,
        }
    )


def suppl_plots_stats_lightbulb_after_carver():
    console.print("\nEffect of Original story on New Story", style="red bold")

    console.print("\nStory relatedness: multiple comparisons", style="green")

    console.print("\n Stat test first 30s", style="yellow")
    test_multiple(
        config={
            "configs": [
                {"condition": "interference_story_spr_end_continued"},
                {"condition": "interference_story_spr_end_separated"},
                {"condition": "interference_story_spr_end_delayed_continued"},
                {"condition": "interference_story_spr"},
                {"story": "dark_bedroom", "condition": "neutralcue"},
            ],
            "story": "carver_original",
            "ratings": RATINGS_LIGHTBULB,
            "position": "post",
            "measure": "story_relatedness",
            "exclude": ("gte", "timestamp", 30000),
            "test_type": "kw",  # Levene test significant
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    multiple_comparions: list[tuple[str, float]] = list()

    console.print("\n New Story Alone v continued", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "Continued",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_continued",
            },
            "position": "post",
            "exclude": ("gte", "timestamp", 30000),
            "measure": "story_relatedness",
            "ratings": RATINGS_LIGHTBULB,
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, Continued", pval))

    console.print("\n New Story Alone v separated", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "Separated",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_separated",
            },
            "position": "post",
            "exclude": ("gte", "timestamp", 30000),
            "measure": "story_relatedness",
            "ratings": RATINGS_LIGHTBULB,
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, Separated", pval))

    console.print("\n New Story Alone v Delayed continued", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "Delayed continued",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_delayed_continued",
            },
            "position": "post",
            "exclude": ("gte", "timestamp", 30000),
            "measure": "story_relatedness",
            "ratings": RATINGS_LIGHTBULB,
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, Delayed continued", pval))

    console.print("\n New Story Alone v New Story", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "New Story",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr",
            },
            "position": "post",
            "exclude": ("gte", "timestamp", 30000),
            "measure": "story_relatedness",
            "ratings": RATINGS_LIGHTBULB,
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, New Story", pval))

    # sort ascending
    multiple_comparions.sort(key=lambda x: x[1])
    # threshold p values
    thresholds = [
        SIGNIFICANCE_THRESHHOLD / idx for idx in range(len(multiple_comparions), 0, -1)
    ]
    console.print("\nHolm-Bonferroni correction:", style="yellow")
    violated = False
    for comparison, threshold in zip(multiple_comparions, thresholds):
        if comparison[1] >= threshold:
            violated = True
        if violated:
            console.print(
                f"{comparison[0]} - p = {round(comparison[1], 4)}"
                f" > {round(threshold, 4)}",
                style="red",
            )
        else:
            console.print(
                f"{comparison[0]} - p = {round(comparison[1], 4)}"
                f" < {round(threshold, 4)}",
                style="green",
            )

    console.print("\nLinger rating: multiple comparisons", style="green")

    multiple_comparions: list[tuple[str, float]] = list()

    console.print("\n New Story Alone v continued", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "Continued",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_continued",
                "custom_measure": "linger_rating_interference",
            },
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, Continued", pval))

    console.print("\n New Story Alone v separated", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "Separated",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_separated",
                "custom_measure": "linger_rating_interference",
            },
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, Separated", pval))

    console.print("\n New Story Alone v Delayed continued", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "Delayed continued",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr_end_delayed_continued",
                "custom_measure": "linger_rating_interference",
            },
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, Delayed continued", pval))

    console.print("\n New Story Alone v New Story", style="yellow")
    pval = test_two(
        {
            "name1": "New Story Alone",
            "name2": "New Story",
            "config1": {"story": "dark_bedroom", "condition": "neutralcue"},
            "config2": {
                "story": "carver_original",
                "condition": "interference_story_spr",
                "custom_measure": "linger_rating_interference",
            },
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )
    multiple_comparions.append(("New Story Alone, New Story", pval))

    # sort ascending
    multiple_comparions.sort(key=lambda x: x[1])
    # threshold p values
    thresholds = [
        SIGNIFICANCE_THRESHHOLD / idx for idx in range(len(multiple_comparions), 0, -1)
    ]
    console.print("\nHolm-Bonferroni correction:", style="yellow")
    violated = False
    for comparison, threshold in zip(multiple_comparions, thresholds):
        if comparison[1] >= threshold:
            violated = True
        if violated:
            console.print(
                f"{comparison[0]} - p = {round(comparison[1], 4)}"
                f" > {round(threshold, 4)}",
                style="red",
            )
        else:
            console.print(
                f"{comparison[0]} - p = {round(comparison[1], 4)}"
                f" < {round(threshold, 4)}",
                style="green",
            )

    console.print("\n Theme Similarity aligned by FA start", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "interference_story_spr_end_continued": POST_NOFILTER,
                            "interference_story_spr_end_separated": POST_NOFILTER,
                            "interference_story_spr_end_delayed_continued": POST_NOFILTER,  # noqa: E501
                            "interference_story_spr": POST_NOFILTER,
                        },
                    ),
                    "dark_bedroom": ("condition", {"neutralcue": POST_NOFILTER}),
                },
            ),
            "ratings": RATINGS_LIGHTBULB,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "<b>New story</b> relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": THEME_SIMILARITY_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": None,
            "y_ticktext": None,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "min_bin_n": 200,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": LEGEND_NAME_MAPPING,
            "show": False,
            "color": "condition",
            "symbol": "condition",
            "symbol_map": {
                "interference_story_spr_end_continued": "circle",
                "interference_story_spr_end_separated": "circle",
                "interference_story_spr_end_delayed_continued": "circle",
                "interference_story_spr": "circle",
                "neutralcue": "diamond",
            },
            "line_dash": "condition",
            "line_dash_map": {
                "interference_story_spr_end_continued": "solid",
                "interference_story_spr_end_separated": "solid",
                "interference_story_spr_end_delayed_continued": "solid",
                "interference_story_spr": "solid",
                "neutralcue": "dash",
            },
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE_SUPPL,
            "filepostfix": "suppl_ts_after_carver",
        }
    )


def suppl_stats_control_correlations_story_thoughts():
    console.print(
        "\n > CORR: Control Linger rating & food thoughts: button_press", style="yellow"
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "pre",
            "x_measure": "double_press",
            "y_measure": "linger_rating",
        }
    )

    console.print(
        "\n > CORR: Story relatedness post & story thoughts: button_press",
        style="yellow",
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "x_measure": "story_relatedness",
            "y_measure": "thought_entries",
            "ratings": RATINGS_CARVER,
        }
    )
    console.print(
        "\n > CORR: Control Story relatedness pre & food thoughts: button_press",
        style="yellow",
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "pre",
            "x_measure": "story_relatedness",
            "y_measure": "thought_entries",
            "ratings": RATINGS_CARVER,
        }
    )

    # control by correlation:
    # "If story thoughts are generally driven by the instruction to report them, then
    # number of food thoughts and story thoughts should be correlated"
    print("\n > Control: Story thoughts & food thoughts: button_press")
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "x_measure": "total_double_press_count_post",
            "y_measure": "total_double_press_count_pre",
        }
    )


def suppl_highly_story_related_wrds():
    # most story related wors
    rated_words_post_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "column": "story_relatedness",
        },
    )
    rated_words_post_df["position"] = "post"
    rated_words_pre_df = load_rated_wordchains(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "pre",
            "ratings": RATINGS_CARVER,
            "column": "story_relatedness",
        },
    )
    rated_words_pre_df["position"] = "pre"
    rated_words_df = pd.concat([rated_words_post_df, rated_words_pre_df], axis=0)

    # get high story relatedness words
    high_sr_words = rated_words_df.loc[
        rated_words_df["story_relatedness"] > THRESHOLD_HIGH_SR
    ]["word_text"].unique()
    print("\n > High story relatedness words")
    print(f"Threshold: {THRESHOLD_HIGH_SR}")
    print(high_sr_words)
    print(f"carver_original | button_press | total high_sr words: {len(high_sr_words)}")

    # get how many of these were produced by each participant
    rated_words_post_df["high_sr_word"] = (
        rated_words_post_df["story_relatedness"] > THRESHOLD_HIGH_SR
    )
    median_high_sr_words = (
        rated_words_post_df["high_sr_word"].groupby("participantID").sum().median()
    )
    print(
        f"carver_original | button_press | median_high_sr words: {median_high_sr_words}"
    )


def suppl_transp_and_pmc():
    console.print("\nTransportation & Lingering measures", style="red bold")

    conditions = [
        "neutralcue2",
        "suppress",
        "button_press",
        "button_press_suppress",
        "interference_situation",
        "interference_tom",
        "interference_geometry",
        "interference_story_spr",
        "interference_pause",
        "neutralcue",
    ]
    correlation_records = list()
    for condition in conditions:
        measures = ["linger_rating", "story_relatedness"]
        if condition in ["button_press", "button_press_suppress"]:
            measures += ["thought_entries"]

        row = dict(condition=NAME_MAPPING[condition])
        for measure in measures:
            story = "carver_original" if condition != "neutralcue" else "dark_bedroom"
            result_obj = correlate_two(
                {
                    "story": story,
                    "condition": condition,
                    "position": "post",
                    "x_measure": "tran_prop"
                    if condition != "suppress"
                    else "tran_prop_10",
                    "y_measure": measure,
                    "ratings": RATINGS_CARVER,
                    "verbose": False,
                }
            )
            if result_obj.params[1] < 0:
                print(f"Negative relationship: {condition}")
            row[f"{measure}"] = round(result_obj.rsquared, 2)
            # row[f"{measure} p"] = result_obj.f_pvalue

        correlation_records.append(row)

    correlation_df = pd.DataFrame.from_records(correlation_records)
    print(correlation_df)
    console.print("\n > Transportation & Linger rating R^2", style="yellow")
    latex_table_sr = correlation_df.to_latex(
        columns=["condition", "linger_rating", "story_relatedness", "thought_entries"],
        header=[
            "Condition",
            "$R^2$ - Linger Rating",
            "$R^2$ - Story relatedness",
            "$R^2$ - Story thoughts",
        ],
        index=False,
        na_rep="",
        float_format=lambda num: f"{num:.2f}".lstrip("0"),
        column_format="lccc",
        escape=True,
        caption=(
            "The table reports the $R^2$ of the correlation between measures of"
            " self-reported transportation \\cite{green_role_2000} and"
            " self-reported lingering."
        ),
        label="supp:materials:tab:transportation_and_pmc",
        position="h",
    )
    latex_table_sr = latex_table_sr.replace("\\caption", "\\centering\n\\caption")
    print(latex_table_sr)


def suppl_plots_stats_pause_and_end_pause_cue():
    console.print("\nSuppl Materials: Pause & Pause-End", style="red bold")
    # Pause: https://aspredicted.org/ym73-srmz.pdf
    # End Cue + Pause: https://aspredicted.org/6zr6-wkqs.pdf

    console.print("\nStory relatedness", style="green")
    test_two(
        {
            "name1": "Pause pre 30s-60s",
            "name2": "Pause post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_pause",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "End Cue + Pause pre 30s-60s",
            "name2": "End Cue + Pause post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_end_pause",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pause pre 150s-180s",
            "name2": "Pause post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_pause",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "End Cue + Pause pre 150s-180s",
            "name2": "End Cue + Pause post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_end_pause",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nWords submission time", style="green")
    test_two(
        {
            "name1": "Pause pre 30s-60s",
            "name2": "Pause post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_pause",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "End Cue + Pause pre 30s-60s",
            "name2": "End Cue + Pause post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_end_pause",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pause pre 150s-180s",
            "name2": "Pause post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_pause",
            "story": "carver_original",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "End Cue + Pause pre 150s-180s",
            "name2": "End Cue + Pause post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_end_pause",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nCompare to Baseline", style="green")

    test_two(
        {
            "name1": "Baseline 30s-60s",
            "name2": "Pause 0s-30s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "condition": "interference_pause",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 30s-60s",
            "name2": "End Cue + Pause 0s-30s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "condition": "interference_end_pause",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 150s-180s",
            "name2": "Pause 120s-150s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "condition": "interference_pause",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 150s-180s",
            "name2": "End Cue + Pause 120s-150s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "condition": "interference_end_pause",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n Plots", style="green")

    console.print("\n > Pause Relatedness", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_pause": POST_NOFILTER,
                                    "interference_end_pause": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": RATINGS_CARVER,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "color": "condition",
            "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            "align_timestamp": "reading_task_end",
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "Story relatedness",
            "x_range": None,
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1500,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_pause_end_pause",
        }
    )

    console.print(
        "\n > Pause & End cue + Pause Self Reported Lingering", style="yellow"
    )
    plot_numeric_measure(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_pause": POST_NOFILTER,
                                    "interference_end_pause": POST_NOFILTER,
                                },
                            ),
                        },
                    )
                },
            ),
            "aggregate_on": "all",
            # plot data config
            "measure_name": "linger_rating",
            "summary_func": np.nanmean,
            # plot config
            "title": None,
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "orientation": "h",
            "x_ticktext": [],
            "x_tickvals": [],
            "x_title": "Condition",
            "y_title": "Self-reported lingering",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": COL1,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # Legend
            "showlegend": False,
            "legend": LEGEND_TOP_MID,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            # Lines
            "hlines": [
                {
                    "y": 2.62,
                    "line": {
                        "dash": "dash",
                        "color": COLOR_SEQUENCE_ORDERED[
                            ORDER_CONDITIONS["condition"].index("word_scrambled")
                        ],
                        "width": 9,
                    },
                },
            ],
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # save config
            "save": True,
            "width": 660,
            "height": 660,
            "scale": 2.0,
            "filepostfix": "suppl_pause_end_pause",
            "study": STUDY_SUPPL,
            "filetype": FILETYPE,
        }
    )


def suppl_prereg_volition():
    # https://aspredicted.org/6stx-344p.pdf
    console.print(
        "\n Pre-reg: volition studies (button_press, button_press_suppress)",
        style="red bold",
    )

    for condition in ["button_press", "button_press_suppress"]:
        console.print(f"\nCondition: {condition}", style="blue")

        console.print("\nThought entries", style="green")
        test_two(
            {
                "name1": "1st min.",
                "name2": "2nd min.",
                "config1": {"te_filter": {"exclude": [("gte", "timestamp", 60000)]}},
                "config2": {
                    "te_filter": {
                        "exclude": [
                            ("lt", "timestamp", 60000),
                            ("gte", "timestamp", 120000),
                        ]
                    }
                },
                "story": "carver_original",
                "condition": condition,
                "position": "post",
                "measure": "thought_entries",
                "test_type": "wilcoxon",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
            }
        )

        test_two(
            {
                "name1": "2nd min.",
                "name2": "3rd min.",
                "config1": {
                    "te_filter": {
                        "exclude": [
                            ("lt", "timestamp", 60000),
                            ("gte", "timestamp", 120000),
                        ]
                    }
                },
                "config2": {"te_filter": {"exclude": [("lt", "timestamp", 120000)]}},
                "story": "carver_original",
                "condition": condition,
                "position": "post",
                "measure": "thought_entries",
                "test_type": "wilcoxon",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
            }
        )

        test_two(
            {
                "name1": "1st min.",
                "name2": "3rd min.",
                "config1": {"te_filter": {"exclude": [("gte", "timestamp", 60000)]}},
                "config2": {"te_filter": {"exclude": [("lt", "timestamp", 120000)]}},
                "story": "carver_original",
                "condition": condition,
                "position": "post",
                "measure": "thought_entries",
                "test_type": "wilcoxon",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
            }
        )

        console.print("\nStory relatedness", style="green")
        test_two(
            {
                "name1": "1st min.",
                "name2": "2nd min.",
                "config1": {"exclude": [("gte", "timestamp", 60000)]},
                "config2": {
                    "exclude": [
                        ("lt", "timestamp", 60000),
                        ("gte", "timestamp", 120000),
                    ]
                },
                "story": "carver_original",
                "condition": condition,
                "position": "post",
                "ratings": RATINGS_CARVER,
                "measure": "story_relatedness",
                "test_type": "wilcoxon",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
            }
        )

        test_two(
            {
                "name1": "2nd min.",
                "name2": "3rd min.",
                "config1": {
                    "exclude": [
                        ("lt", "timestamp", 60000),
                        ("gte", "timestamp", 120000),
                    ]
                },
                "config2": {"exclude": [("lt", "timestamp", 120000)]},
                "story": "carver_original",
                "condition": condition,
                "position": "post",
                "ratings": RATINGS_CARVER,
                "measure": "story_relatedness",
                "test_type": "wilcoxon",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
            }
        )

        test_two(
            {
                "name1": "1st min.",
                "name2": "3rd min.",
                "config1": {"exclude": [("gte", "timestamp", 60000)]},
                "config2": {"exclude": [("lt", "timestamp", 120000)]},
                "story": "carver_original",
                "condition": condition,
                "position": "post",
                "measure": "story_relatedness",
                "ratings": RATINGS_CARVER,
                "test_type": "wilcoxon",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
            }
        )

    console.print("\n Intact v Suppress", style="blue")

    console.print("\nThought entries", style="green")
    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "te_filter": {"exclude": [("gte", "timestamp", 60000)]},
            "story": "carver_original",
            "position": "post",
            "measure": "thought_entries",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "te_filter": {
                "exclude": [("lt", "timestamp", 60000), ("gte", "timestamp", 120000)]
            },
            "story": "carver_original",
            "position": "post",
            "measure": "thought_entries",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "te_filter": {"exclude": [("lt", "timestamp", 120000)]},
            "story": "carver_original",
            "position": "post",
            "measure": "thought_entries",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    console.print("\nStory relatedness", style="green")
    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "exclude": [("gte", "timestamp", 60000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "exclude": [("lt", "timestamp", 60000), ("gte", "timestamp", 120000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "exclude": [("lt", "timestamp", 120000)],
            "story": "carver_original",
            "position": "post",
            "measure": "story_relatedness",
            "ratings": RATINGS_CARVER,
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    console.print("\nSubmission time", style="green")
    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "exclude": [("gte", "timestamp", 60000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "word_time",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "exclude": [("lt", "timestamp", 60000), ("gte", "timestamp", 120000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "word_time",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "exclude": [("lt", "timestamp", 120000)],
            "story": "carver_original",
            "position": "post",
            "measure": "word_time",
            "ratings": RATINGS_CARVER,
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "print_for_table": True,
        }
    )

    console.print(
        "\n > H3: Intact: CORR: Linger rating & story thoughts", style="yellow"
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "x_measure": "thought_entries",
            "y_measure": "linger_rating",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print(
        "\n > H3: Intact: CORR: Linger rating start & story thoughts start",
        style="yellow",
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "x_measure": "thought_entries",
            "y_measure": "linger_rating_start",
            "te_filter": {"exclude": [("gte", "timestamp", 60000)]},
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print(
        "\n > H3: Intact: CORR: Linger rating end & story thoughts end", style="yellow"
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press",
            "position": "post",
            "x_measure": "thought_entries",
            "y_measure": "linger_rating_end",
            "te_filter": {"exclude": [("lt", "timestamp", 120000)]},
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > A1: Intact: Post v Pre thought entries", style="yellow")
    test_two(
        {
            "name1": "Story",
            "name2": "Food",
            "config1": {
                "position": "post",
            },
            "config2": {
                "position": "pre",
            },
            "story": "carver_original",
            "condition": "button_press",
            "measure": "thought_entries",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > A2: Pre: Intact v Suppress: Thought entries", style="yellow")
    test_two(
        {
            "name1": "Intact",
            "name2": "Suppress",
            "config1": {"condition": "button_press"},
            "config2": {"condition": "button_press_suppress"},
            "position": "pre",
            "story": "carver_original",
            "measure": "thought_entries",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def suppl_prereg_baseline():
    # https://aspredicted.org/jmst-yrrq.pdf
    # (only analyses/plots that are not covered already somewhere else)
    console.print("\n Pre-reg: baseline", style="red bold")

    test_two(
        {
            "name1": "Pre 0s-30s",
            "name2": "Post 0s-30s",
            "config1": {"position": "pre"},
            "config2": {"position": "post"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "condition": "neutralcue2",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 150s-180s",
            "config1": {"position": "pre"},
            "config2": {"position": "post"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "story": "carver_original",
            "condition": "neutralcue2",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 0s-30s",
            "name2": "Post 0s-30s",
            "config1": {"position": "pre"},
            "config2": {"position": "post"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "condition": "neutralcue2",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 150s-180s",
            "config1": {"position": "pre"},
            "config2": {"position": "post"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "story": "carver_original",
            "condition": "neutralcue2",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nCompare to neutralcue", style="green")

    test_two(
        {
            "name1": "Baseline 0s-30s",
            "name2": "Neutralcue 0s-30s",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "neutralcue"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 150s-180s",
            "name2": "Neutralcue 150s-180s",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "neutralcue"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "story": "carver_original",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 0s-30s",
            "name2": "Neutralcue 0s-30s",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "neutralcue"},
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "position": "post",
            "measure": "word_time",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 150s-180s",
            "name2": "Neutralcue 150s-180s",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "neutralcue"},
            "exclude": [("lt", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "story": "carver_original",
            "position": "post",
            "measure": "word_time",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nPlots (compare neutralcue/baseline)", style="green")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_TIMEFILTER,
                                    "neutralcue": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": RATINGS_CARVER,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "min_bin_n": 200,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_map": {
                "neutralcue": "#82100C",
                "neutralcue2": COL_NEUTRALCUE2,
            },
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": {
                "neutralcue, post": "Neutralcue",
                "neutralcue2, post": "Baseline",
            },
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_sr_baseline_v_neutralcue",
        }
    )

    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_TIMEFILTER,
                                    "neutralcue": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            # plot data config
            "mode": "word_time",
            "column": "word_time",
            "step": 30000,
            "min_bin_n": 200,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Submission time (ms)",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": WORD_TIME_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_map": {
                "neutralcue": "#82100C",
                "neutralcue2": COL_NEUTRALCUE2,
            },
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": {
                "neutralcue, post": "Neutralcue",
                "neutralcue2, post": "Baseline",
            },
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1350,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_wt_baseline_v_neutralcue",
        }
    )


def suppl_prereg_continued_separated_delayed_continued():
    # https://aspredicted.org/fdkh-fdmc.pdf
    # only analyses which were not run before
    console.print(
        "\nSUPPL: prereg: Continued, Separated, Continued-delayed", style="red bold"
    )

    test_difference_bin_means(
        {
            "console_comment": ": aligned-by main-story: all bins",
            "name1": "Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            "position": "post",
            "story": "carver_original",
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "greater",
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_difference_bin_means(
        {
            "console_comment": ": aligned-by main-story: > 150s",
            "name1": "Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            "position": "post",
            "story": "carver_original",
            "exclude": ("lt", "timestamp", 150000),
            "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "greater",
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_difference_bin_means(
        {
            "console_comment": ": aligned-by interference story: all bins",
            "name1": "Delayed Continued",
            "name2": "Separated",
            "config1": {"condition": "interference_story_spr_end_delayed_continued"},
            "config2": {"condition": "interference_story_spr_end_separated"},
            "position": "post",
            "story": "carver_original",
            "align_timestamp": "interference_reading_testing_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "two-sided",
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_difference_bin_means(
        {
            "console_comment": ": aligned-by interference story: all bins",
            "name1": "Delayed Continued",
            "name2": "Continued",
            "config1": {"condition": "interference_story_spr_end_delayed_continued"},
            "config2": {"condition": "interference_story_spr_end_continued"},
            "position": "post",
            "story": "carver_original",
            "align_timestamp": "interference_reading_testing_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            # test config
            "alternative": "less",
            "step": 30000,
            "min_bin_n": 200,
            "n_bootstrap": 5000,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def suppl_prereg_tom():
    # https://aspredicted.org/fps7-3n3f.pdf
    # (only analyses/plots that are not covered already somewhere else)
    console.print("\n Pre-reg: ToM", style="red bold")

    test_two(
        {
            "name1": "Pre 30s-60s",
            "name2": "Post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_tom",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_pause",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # word time
    test_two(
        {
            "name1": "Pre 30s-60s",
            "name2": "Post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_tom",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_tom",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # compare to baseline
    test_two(
        {
            "name1": "Baseline 30s-60s",
            "name2": "ToM 0s-30s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "condition": "interference_tom",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 150s-180s",
            "name2": "ToM 120s-150s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "condition": "interference_tom",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def suppl_prereg_geometry():
    # https://aspredicted.org/yxvh-9dpp.pdf
    console.print("\n Pre-reg: Geometry", style="red bold")

    test_two(
        {
            "name1": "Pre 30s-60s",
            "name2": "Post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_geometry",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_geometry",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # word time
    test_two(
        {
            "name1": "Pre 30s-60s",
            "name2": "Post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_geometry",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_geometry",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # compare to baseline
    test_two(
        {
            "name1": "Baseline 30s-60s",
            "name2": "Geometry 0s-30s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "condition": "interference_geometry",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 150s-180s",
            "name2": "Geometry 120s-150s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "condition": "interference_geometry",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def suppl_prereg_new_story():
    # https://aspredicted.org/yxvh-9dpp.pdf
    console.print("\n Pre-reg: New Story", style="red bold")

    test_two(
        {
            "name1": "Pre 30s-60s",
            "name2": "Post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_story_spr",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_story_spr",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # word time
    test_two(
        {
            "name1": "Pre 30s-60s",
            "name2": "Post 0s-30s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "story": "carver_original",
            "condition": "interference_story_spr",
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Pre 150s-180s",
            "name2": "Post 120s-150s",
            "config1": {
                "position": "pre",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "position": "post",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "condition": "interference_story_spr",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "word_time",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    # compare to baseline
    test_two(
        {
            "name1": "Baseline 30s-60s",
            "name2": "New Story 0s-30s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            },
            "config2": {
                "condition": "interference_story_spr",
                "exclude": [("gte", "timestamp", 30000)],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline 150s-180s",
            "name2": "New Story 120s-150s",
            "config1": {
                "condition": "neutralcue2",
                "exclude": [
                    ("lt", "timestamp", 150000),
                    ("gte", "timestamp", 180000),
                ],
            },
            "config2": {
                "condition": "interference_story_spr",
                "exclude": [
                    ("lt", "timestamp", 120000),
                    ("gte", "timestamp", 150000),
                ],
            },
            "position": "post",
            "story": "carver_original",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print(
        "\nComparison to interference for participants <60s interference", style="green"
    )

    conditions = [
        "interference_pause",
        "interference_end_pause",
        "interference_situation",
        "interference_tom",
        "interference_geometry",
    ]

    for condition2 in conditions:
        test_two(
            {
                "name1": "New Story (<60s)",
                "name2": f"{condition2}",
                "config1": {
                    "condition": "interference_story_spr",
                    "exclude": [
                        ("gte", "timestamp", 30000),
                        ("gt", "interference_reading_testing_time", 60000),
                    ],
                },
                "config2": {
                    "condition": condition2,
                    "exclude": [("gte", "timestamp", 30000)],
                },
                "story": "carver_original",
                "position": "post",
                "ratings": RATINGS_CARVER,
                "measure": "story_relatedness",
                "test_type": "mwu",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
                "print_for_table_compact": True,
            }
        )


def suppl_prereg_table_interference():
    console.print("\nSuppl: pre-reg table interference conditions", style="red bold")

    conditions = [
        "interference_pause",
        "interference_end_pause",
        "interference_situation",
        "interference_tom",
        "interference_geometry",
        "interference_story_spr",
    ]

    for condition1, condition2 in combinations(conditions, 2):
        if condition1 == condition2:
            continue
        test_two(
            {
                "name1": f"{condition1}",
                "name2": f"{condition2}",
                "config1": {"condition": condition1},
                "config2": {"condition": condition2},
                "story": "carver_original",
                "position": "post",
                "exclude": [("gte", "timestamp", 30000)],
                "ratings": RATINGS_CARVER,
                "measure": "story_relatedness",
                "test_type": "mwu",
                "threshold": P_DISPLAY_THRESHOLD,
                "print_for_table": True,
                "print_for_table_compact": True,
            }
        )


def suppl_prereg_plot_interference():
    console.print("\nSuppl: pre-reg plot interference conditions", style="red bold")

    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_geometry": POST_NOFILTER,
                                    "interference_situation": POST_NOFILTER,
                                    "interference_tom": POST_NOFILTER,
                                    "interference_story_spr": POST_NOFILTER,
                                    "interference_pause": POST_NOFILTER,
                                    "interference_end_pause": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            "min_bin_n": 300,
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1560,
            "height": 660,
            "filetype": FILETYPE_SUPPL,
            "filepostfix": "all_interference_conds",
        }
    )


def suppl_interference_task_performance():
    console.print("\nInterference task performance", style="red bold")

    console.print("\nSituation interference", style="green")
    qdata_situation = load_questionnaire(
        {"story": "carver_original", "condition": "interference_situation"}
    )
    acc_situation_all = qdata_situation["interference_correct"].mean()
    acc_situation_jeff = qdata_situation.loc[
        qdata_situation["question_index"] == 3, "interference_correct"
    ].mean()
    n_situation_jeff = len(qdata_situation.loc[qdata_situation["question_index"] == 3])
    acc_situation_ceo = qdata_situation.loc[
        qdata_situation["question_index"] == 13, "interference_correct"
    ].mean()
    n_situation_ceo = len(qdata_situation.loc[qdata_situation["question_index"] == 13])

    print(f"Total: {round(acc_situation_all, 4)}")
    print(
        f"Q1 (Jeff) - N={n_situation_jeff}"
        f" - Mean correct={round(acc_situation_jeff, 4)}"
    )
    print(
        f"Q2 (CEO) - N={n_situation_ceo} - Mean correct={round(acc_situation_ceo, 4)}"
    )

    console.print("\n > Correlations", style="yellow")
    for measure in ["linger_rating", "story_relatedness", "tran_prop"]:
        correlate_two(
            {
                "story": "carver_original",
                "condition": "interference_situation",
                "position": "post",
                "ratings": RATINGS_CARVER,
                "x_measure": "interference_correct",
                "y_measure": measure,
            }
        )

    console.print("\nToM interference", style="green")
    qdata_tom = load_questionnaire(
        {"story": "carver_original", "condition": "interference_tom"}
    )
    acc_tom_all = qdata_tom["interference_correct"].mean()
    acc_tom_sarah = qdata_tom.loc[
        qdata_tom["question_index"] == 0, "interference_correct"
    ].mean()
    n_tom_sarah = len(qdata_tom.loc[qdata_tom["question_index"] == 0])
    acc_tom_garcia = qdata_tom.loc[
        qdata_tom["question_index"] == 7, "interference_correct"
    ].mean()
    n_tom_garcia = len(qdata_tom.loc[qdata_tom["question_index"] == 7])

    print(f"Total: {round(acc_tom_all, 4)}")
    print(f"Q1 (Sarah) - N={n_tom_sarah} - Mean correct={round(acc_tom_sarah, 4)}")
    print(f"Q2 (Garcia) - N={n_tom_garcia} - Mean correct={round(acc_tom_garcia, 4)}")

    console.print("\n > Correlations", style="yellow")
    for measure in ["linger_rating", "story_relatedness", "tran_prop"]:
        correlate_two(
            {
                "story": "carver_original",
                "condition": "interference_tom",
                "position": "post",
                "ratings": RATINGS_CARVER,
                "x_measure": "interference_correct",
                "y_measure": measure,
            }
        )

    console.print("\nGeometry interference", style="green")
    qdata_geometry = load_questionnaire(
        {"story": "carver_original", "condition": "interference_geometry"}
    )
    acc_geometry = qdata_geometry["answered_correct"].mean()
    undercounted_by_one = sum(qdata_geometry["answer"] == "5") / len(qdata_geometry)
    print(
        f"Total: N={qdata_geometry['answered_correct'].sum()} {round(acc_geometry, 4)}"
    )
    print("Answer distribution:")
    print(qdata_geometry["answer"].value_counts())
    print(
        f"N undercounted by one: N={sum(qdata_geometry['answer'] == '5')}"
        f" {round(undercounted_by_one, 4)}"
    )

    console.print("\n > Correlations", style="yellow")
    for measure in ["linger_rating", "story_relatedness", "tran_prop"]:
        correlate_two(
            {
                "story": "carver_original",
                "condition": "interference_geometry",
                "position": "post",
                "ratings": RATINGS_CARVER,
                "x_measure": "answered_correct",
                "y_measure": measure,
            }
        )


def suppl_plots_stats_suppress_no_button_press():
    console.print("\nSUPPL: Suppress No Button Press", style="red bold")

    console.print("\nStats", style="green")

    test_two(
        {
            "name1": "post",
            "name2": "pre",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "story": "carver_original",
            "condition": "suppress",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "wilcoxon",  # consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    test_two(
        {
            "name1": "Baseline",
            "name2": "Suppress No Button Press",
            "config1": {"condition": "neutralcue2"},
            "config2": {"condition": "suppress"},
            "story": "carver_original",
            "position": "post",
            "measure": "linger_rating",
            "test_type": "mwu",  # consistency
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\nPlots", style="green")

    console.print("\nStory relatedness", style="yellow")
    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": PRE_POST_TIMEFILTER,
                                    "button_press_suppress": PRE_POST_TIMEFILTER,
                                    "suppress": PRE_POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "verbose": True,
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "color": "condition",
            "symbol": "position",
            "plotkind": "line",
            "step": 30000,
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": LEGEND_NAME_MAPPING_WITH_POSITION,
            "show": False,
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1500,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_suppress_no_button_press",
        }
    )

    console.print("\nLinger rating", style="yellow")
    plot_numeric_measure(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_TIMEFILTER,
                                    "button_press_suppress": POST_TIMEFILTER,
                                    "suppress": POST_TIMEFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "all",
            # plot data config
            "measure_name": "linger_rating",
            "summary_func": np.nanmean,
            # plot config
            "title": "",
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "orientation": "h",
            "showlegend": False,
            "x_ticktext": [],
            "x_tickvals": [],
            "x_title": "Condition",
            "y_title": "Self-reported Lingering",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "hlines": [
                {
                    "y": 2.62,
                    "line": {
                        "dash": "dash",
                        "color": COLOR_SEQUENCE_ORDERED[
                            ORDER_CONDITIONS["condition"].index("word_scrambled")
                        ],
                        "width": 9,
                    },
                },
            ],
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # save config
            "save": True,
            "width": 720,
            "height": 660,
            "scale": 2.0,
            "filepostfix": "suppl_suppress_no_button_press",
            "study": STUDY_SUPPL,
            "filetype": FILETYPE,
            # kruskal
            "kruskal": False,
        }
    )


def suppl_plots_all_bins():
    console.print("\nSUPPL: Plots with all bins", style="red bold")

    console.print("\nSUPPL: Plots with all bins: Fig 3C", style="green")

    plot_by_time_shifted(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {
                                    "neutralcue2": POST_NOFILTER,
                                    "interference_geometry": POST_NOFILTER,
                                    "interference_situation": POST_NOFILTER,
                                    "interference_tom": POST_NOFILTER,
                                    "interference_story_spr": POST_NOFILTER,
                                },
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            "min_bin_n": 1,
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": [0, 13.1],
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": True,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1560,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_all_bins_aligned_reading_end_f3",
        }
    )

    console.print("\nSUPPL: Plots with all bins: Fig 4C", style="green")

    plot_by_time_shifted(
        {
            "load_spec": (
                "story",
                {
                    "carver_original": (
                        "condition",
                        {
                            "neutralcue2": POST_NOFILTER,
                            "interference_story_spr_end_continued": POST_NOFILTER,
                            "interference_story_spr_end_separated": POST_NOFILTER,
                        },
                    )
                },
            ),
            "aggregate_on": "story",
            "ratings": {
                "approach": "human",
                "model": "moment",
                "story": "carver_original",
                "file": "all.csv",
            },
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "Story relatedness",
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": [0, 13.1],
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
            "axes_linewidth": 7,
            "marker_size": 24,
            "line_width": 7,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "min_bin_n": 1,
            # plot misc config
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            "showlegend": True,
            "legend": LEGEND_RIGHT_NEXT,
            "legend_name_mapping": LEGEND_NAME_MAPPING_POSITION,
            "show": False,
            "color": "condition",
            "symbol": "position",
            # plot save config
            "study": STUDY_SUPPL,
            "save": True,
            "scale": 2,
            "width": 1560,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_all_bins_continued_separated_aligned_reading_end_f4",
        }
    )


def suppl_thought_entries_mlm():
    console.print("\nSUPPL: Mixed-effect linear model", style="red bold")

    test_mlm(
        {
            "config1": {"position": "pre"},
            "config2": {"position": "post"},
            "exclude": ("gt", "timestamp", 180000),
            "story": "carver_original",
            "condition": "button_press",
            "measure": "thought_entries",
            "step": 30000,
            "comparison_category": "position",
            "comparison_within_participants": True,
            "replace_columns": {
                "position": {"post": "Story thought", "pre": "Food thought"}
            },
            "transform": "sqrt",
            "model_kind": "slopes",
            "model_method": "powell",
            "threshold": P_DISPLAY_THRESHOLD,
            "latex": True,
            "assumptions_save": True,
            "assumptions_width": 1200,
            "assumptions_height": 2400,
            "assumptions_show": False,
            "study": STUDY_SUPPL,
        }
    )


def suppl_demographic_stats():
    console.print("\nDemographic stats - Methods", style="red bold")
    demographic_stats(
        {
            "load_spec": ("story", ALL_STORIES_CONDITIONS_DCT_POST),
            "aggregate_on": "position",
            "name_mapping": NAME_MAPPING,
            "latex": True,
        }
    )


def submission_demographic_exclusion_stats():
    console.print("\nReporting Summary", style="red bold")

    console.print("\nGender stats", style="blue")
    demographic_stats(
        {
            "load_spec": ("story", ALL_STORIES_CONDITIONS_DCT_POST),
            "aggregate_on": "position",
            "name_mapping": NAME_MAPPING,
            "just_gender": True,
        }
    )

    console.print("\nDemographic stats", style="blue")
    demographic_stats(
        {
            "load_spec": ("story", ALL_STORIES_CONDITIONS_DCT_POST),
            "aggregate_on": "position",
            "name_mapping": NAME_MAPPING,
        }
    )

    console.print("\nExclusions", style="blue")
    demographic_stats(
        {
            "load_spec": ("story", ALL_STORIES_CONDITIONS_DCT_POST),
            "aggregate_on": "position",
            "name_mapping": NAME_MAPPING,
            "just_exclusions": True,
        }
    )


def main():
    # Results
    console.print("\n\nResults", style="red bold")
    #    Narrative content persists in mind, influencing thought and behavior.
    stats_experiment_1_button_press()
    plots_fig_1_paradigm_results1()

    #    Narrative content persists without and against volition.
    stats_experiment_2_button_press_suppress()
    plots_fig_2_results2()

    #    Narrative content does not persist in limited capacity short-term memory
    #    N2 geometry
    stats_experiment_3_interference()
    plots_fig_3_results3()

    #    Narrative content starts to 'decay' depending on situational understanding
    stats_experiment_4_continued_separated()
    plots_fig_4_results()

    # Supplemental materials/figures
    console.print("\n\nMethods", style="red bold")
    suppl_methods_experiment_overview()
    suppl_methods_procedure_numbers()
    suppl_demographic_stats()

    console.print("\n\nSupplementary Information", style="red bold")
    suppl_stats_words_generated()
    suppl_thought_entries_mlm()
    suppl_plots_stats_volition()
    suppl_stats_unintentional()
    suppl_plots_stats_wcg_strategy()
    suppl_transp_and_pmc()
    suppl_interference_task_performance()
    suppl_stats_plots_new_story_separated_integrated()

    # suppl results
    suppl_plots_stats_suppress_no_button_press()
    suppl_plots_stats_pause_and_end_pause_cue()
    suppl_plots_stats_lightbulb()

    suppl_plots_stats_lightbulb_after_carver()
    suppl_stats_submission_time()
    suppl_plots_submission_time()
    suppl_plots_by_words()
    suppl_plots_all_bins()

    # pre-registration analyses not covered before
    suppl_prereg_volition()
    suppl_prereg_plot_interference()
    suppl_prereg_baseline()
    suppl_prereg_continued_separated_delayed_continued()
    suppl_prereg_tom()
    suppl_prereg_geometry()
    suppl_prereg_new_story()
    suppl_prereg_table_interference()

    submission_demographic_exclusion_stats()
    # suppl_choice_baseline_fig_3_and_distribution_first_bin_aligned()
    print("\nDone")


if __name__ == "__main__":
    main()
