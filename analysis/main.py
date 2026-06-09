import math
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.io as pio
from oc_pmc import DATA_DIR, RATEDWORDS_DIR, console
from oc_pmc.analysis.demographic_stats import demographic_stats
from oc_pmc.analysis.krippendorf_alpha import krippendorf_alpha
from oc_pmc.analysis.word_position import compute_rank_spearman_correlation
from oc_pmc.analysis.word_stats import compute_word_stats
from oc_pmc.load import (
    load_n_thought_entries,
    load_per_participant_data,
    load_questionnaire,
    load_rated_wordchains,
    load_story_sentences_grouped,
    load_word_position,
    load_wordchains,
)
from oc_pmc.plot import (
    plot_bars_match_score,
    plot_by_time_shifted,
    plot_categorical_measure,
    plot_example_wcs,
    plot_numeric_measure,
)
from oc_pmc.plot.by_time_shifted import func_load, func_plot_by_time
from oc_pmc.plot.distribution import plot_distribution
from oc_pmc.plot.numeric_measure import func_plot_numeric_measure
from oc_pmc.plot.scatter_measures import plot_scatter_measures
from oc_pmc.plot.word_position import (
    plot_by_time_shifted_without_section,
    plot_match_score_across_conditions,
    plot_match_score_by_time_sections,
)
from oc_pmc.stat import (
    correlate_two,
    sr_two,
    test_mlm,
    test_multiple,
    test_two,
)
from oc_pmc.stat.difference_bin_means import test_difference_bin_means
from oc_pmc.utils import cut_small_value, remove_words_in_sections
from oc_pmc.utils.aggregator import aggregator
from rich.table import Table

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
SUBJECTIVE_LINGERING_Y_RANGE = [1, 7.1]
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


AXES_COLOR = "#6c6c6c"
AXES_COLOR_SUPPL = "#000000"


# consistent sizing for main plots
MAIN_PLOTS_ARGS = {
    "marker_size": 24,
    "line_width": 7,
    "axes_linewidth": 7,
    "x_ticks": "outside",
    "x_tickwidth": 7,
    "y_tickwidth": 7,
    "x_ticklen": None,
    "y_ticklen": None,
    "x_tickfont": dict(size=36),
    "y_tickfont": dict(size=36),
    "x_title_standoff": None,
    "y_title_standoff": None,
    "x_title_font_color": COL1,
    "y_title_font_color": COL1,
    "x_title_font_size": 42,
    "y_title_font_size": 42,
    "axes_tickcolor": AXES_COLOR,
    "axes_linecolor": AXES_COLOR,
    "font_color": COL1,
    "bgcolor": COL_BG,
    "axes_gridcolor": "#dddddd",
    "margin": dict(t=60),
}

# MAIN_PLOTS_ARGS_REJECTED = {
#     "marker_size": 5.1,
#     "line_width": 1.65,
#     "axes_linewidth": 1.5,
#     "error_y": dict(
#         width=2.4,
#         thickness=0.9,
#     ),
#     "x_ticks": "outside",
#     "x_tickwidth": 2.1,
#     "y_tickwidth": 2.1,
#     "x_ticklen": 1.5,
#     "y_ticklen": 1.5,
#     "x_tickfont": dict(size=9),
#     "y_tickfont": dict(size=9),
#     "x_title_standoff": 7.2,
#     "y_title_standoff": 7.2,
#     "x_title_font_color": COL1,
#     "y_title_font_color": COL1,
#     "x_title_font_size": 10.8,
#     "y_title_font_size": 10.8,
#     "axes_tickcolor": "#000000",
#     "axes_linecolor": "#000000",
#     "font_color": COL1,
#     "bgcolor": COL_BG,
#     "axes_gridcolor": "#dddddd",
#     "margin": dict(l=1, r=1, t=1, b=1),
# }

MAIN_LEGEND_TOP_RIGHT = dict(
    yanchor="top",
    y=1,
    xanchor="right",
    x=1,
    font_size=6.2,
    title=None,
)


SIGNIFICANCE_THRESHHOLD = 0.05
P_DISPLAY_THRESHOLD = 0.0001


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
            "button_press": PRE_POST_NOFILTER,
            "word_scrambled": PRE_POST_NOFILTER,
            "button_press_suppress": PRE_POST_NOFILTER,
            "neutralcue2": PRE_POST_NOFILTER,
            "suppress": PRE_POST_NOFILTER,
            "interference_situation": PRE_POST_NOFILTER,
            "interference_tom": PRE_POST_NOFILTER,
            "interference_story_spr": PRE_POST_NOFILTER,
            "interference_geometry": PRE_POST_NOFILTER,
            "interference_story_spr_end_continued": PRE_POST_NOFILTER,
            "interference_story_spr_end_separated": PRE_POST_NOFILTER,
            "interference_story_spr_end_delayed_continued": PRE_POST_NOFILTER,
            "interference_pause": PRE_POST_NOFILTER,
            "interference_end_pause": PRE_POST_NOFILTER,
            "multi_day_carver_july": PRE_POST_NOFILTER,
            "multi_day_july_carver": PRE_POST_NOFILTER,
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
            "multi_day_carver_july": POST_NOFILTER,
            "multi_day_july_carver": POST_NOFILTER,
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

RATINGS_CARVER_MULTI_DAY = {
    "approach": "incontext",
    "model": "gpt-5-mini-2025-08-07",
    "story": "carver_original",
    "file": "ratings.csv",
}

RATINGS_JULY_MULTI_DAY = {
    "approach": "incontext",
    "model": "gpt-5-mini-2025-08-07",
    "story": "july_original",
    "file": "ratings.csv",
}

RATINGS_LIGHTBULB = {
    "approach": "themesim",
    "model": "glove",
    "story": "dark_bedroom",
    "file": "19.csv",
}

WORD_POSITION_EXACT_MATCH = {
    "story": "carver_original",
    "mode": "exact_match",
    "model_name": "all_matches",
}

WORD_POSITION_SEMANTIC_MATCH = {
    "story": "carver_original",
    "mode": "incontext",
    "method": "thresholded_3",
    "model_name": "gpt-5-mini-2025-08-07",
}

WORD_POSITION_EXACT_MATCH_JULY = {
    **WORD_POSITION_EXACT_MATCH,
    "story": "july_original",
}

WORD_POSITION_SEMANTIC_MATCH_JULY = {
    **WORD_POSITION_SEMANTIC_MATCH,
    "story": "july_original",
}


CONDITIONS_RECENCY_CORRELATIONS = [
    "neutralcue2",
    "button_press",
    "multi_day_carver_july",
    "multi_day_july_carver",
    "interference_situation",
    "interference_tom",
    "interference_geometry",
    "interference_story_spr",
    "interference_pause",
]


CONDITIONS_RECENCY_CORRELATIONS_DIFFERENCE = [
    "interference_situation",
    "interference_tom",
    "interference_geometry",
    "interference_story_spr",
    "interference_pause",
]

MATCH_CONFIG_DICT = {
    "semantic_match": (
        WORD_POSITION_SEMANTIC_MATCH,
        "semantic_match",
        "Semantic match",
        [(0.0, 1.77)],  # y_ranges_post_pre_30s_bins
        [(-1.11, 3.6)],  # y_ranges_0_180
        [(-0.75, 1.11)],  # y_ranges_30s_bins
        (-1.3, 1.02),  # y_range_across_conditions
        True,  # not_normalize
    ),
    "exact_match": (
        WORD_POSITION_EXACT_MATCH,
        "exact_match",
        "Exact match",
        [(0.0, 0.75)],  # y_ranges_post_pre_30s_bins
        [(-1.11, 1.56)],  # y_ranges_0_180
        [(-0.51, 0.57)],  # y_ranges_30s_bins
        (-0.84, 0.75),  # y_range_across_conditions
        False,  # not_normalize
    ),
}


ORDER_CONDITIONS = {
    "condition": [
        "button_press",
        "neutralcue2",
        "word_scrambled",
        "interference_situation",
        "interference_tom",
        "interference_pause",
        "interference_end_pause",
        "interference_story_spr",
        "interference_story_spr_aware",
        "interference_story_spr_unaware",
        "interference_geometry",
        "suppress",
        "button_press_suppress",
        "neutralcue",  # dark_bedroom condition
        "interference_story_spr_end_continued",
        "interference_story_spr_end_separated",
        "interference_story_spr_end_delayed_continued",
        "multi_day_carver_july",
        "multi_day_july_carver",
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
    "multi_day_carver_july": "Multi Day Carver-July",
    "multi_day_july_carver": "Multi Day July-Carver",
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
    "#8399FF",  # pause
    "#F8AAD6",  # end_pause
    "#09A000",  # interference_story_spr
    "#07CC00",  # interference_story_spr_aware
    "#0A7300",  # interference_story_spr_unaware
    "#0173DB",  # geometry
    "#A12371",  # suppress
    "#09A000",  # button_press_suppress
    "#ffc000",  # neutralcue (dark_bedroom)
    "#356BEB",  # continued
    "#09E3AC",  # separated
    "#A12371",  # delayed_continued
    "#F74639",  # multi_day_carver_july
    "#FFAE00",  # multi_day_july_carver
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


def stats_preview_intro():
    console.print("\nPreview: Introduction", style="red bold")

    console.print("\n > Number of participants", style="yellow")
    all_stories_conditions = [
        ("carver_original", "button_press"),
        ("carver_original", "word_scrambled"),
        ("carver_original", "button_press_suppress"),
        ("carver_original", "neutralcue2"),
        ("carver_original", "suppress"),
        ("carver_original", "interference_situation"),
        ("carver_original", "interference_tom"),
        ("carver_original", "interference_story_spr"),
        ("carver_original", "interference_geometry"),
        ("carver_original", "interference_story_spr_end_continued"),
        ("carver_original", "interference_story_spr_end_separated"),
        ("carver_original", "interference_story_spr_end_delayed_continued"),
        ("carver_original", "interference_pause"),
        ("carver_original", "interference_end_pause"),
        ("dark_bedroom", "neutralcue"),
        ("carver_original", "multi_day_carver_july"),
        ("carver_original", "multi_day_july_carver"),
    ]

    n_participants = 0
    for story, condition in all_stories_conditions:
        data_df = load_questionnaire({"story": story, "condition": condition})
        n_participants += len(data_df.index.unique())
    print(f"Number of participants: {n_participants}\n")


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
        median_words_produced: float = (
            data_df.groupby(["participantID", "position"]).count().median()["word_text"]  # type: ignore
        )
        mean_words_produced: float = (
            data_df.groupby(["participantID", "position"]).count().mean()["word_text"]  # type: ignore
        )
        sd_words_produced: float = (
            data_df.groupby(["participantID", "position"]).count().std()["word_text"]  # type: ignore
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
                                    "button_press": PRE_POST_NOFILTER,
                                    "word_scrambled": PRE_POST_NOFILTER,
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
    mean_sts_post = sts_post.mean().item()  # type: ignore
    median_sts_post = sts_post.median().item()  # type: ignore
    std_sts_post = sts_post.std().item()  # type: ignore
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
    mean_sts_pre = sts_pre.mean().item()  # type: ignore
    median_sts_pre = sts_pre.median().item()  # type: ignore
    std_sts_pre = sts_pre.std().item()  # type: ignore
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
    mean_sts_post_first30 = sts_post_first30[["thought_entries"]].mean().item()  # type: ignore
    median_sts_post_first30 = sts_post_first30[["thought_entries"]].median().item()  # type: ignore
    std_sts_post_first30 = sts_post_first30[["thought_entries"]].std().item()  # type: ignore
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
    mean_sts_pre_first30 = sts_pre_first30[["thought_entries"]].mean().item()  # type: ignore
    median_sts_pre_first30 = sts_pre_first30[["thought_entries"]].median().item()  # type: ignore
    std_sts_pre_first30 = sts_pre_first30[["thought_entries"]].std().item()  # type: ignore
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
    mean_sts_post_last30 = sts_post_last30[["thought_entries"]].mean().item()  # type: ignore
    median_sts_post_last30 = sts_post_last30[["thought_entries"]].median().item()  # type: ignore
    std_sts_post_last30 = sts_post_last30[["thought_entries"]].std().item()  # type: ignore
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
    mean_sts_pre_last30 = sts_pre_last30[["thought_entries"]].mean().item()  # type: ignore
    median_sts_pre_last30 = sts_pre_last30[["thought_entries"]].median().item()  # type: ignore
    std_sts_pre_last30 = sts_pre_last30[["thought_entries"]].std().item()  # type: ignore
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
    mean_sts_beginnning = sts_beginning.mean().item()  # type: ignore
    median_sts_beginnning = sts_beginning.median().item()  # type: ignore
    std_sts_beginnning = sts_beginning.std().item()  # type: ignore
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
    mean_sts_end = sts_end.mean().item()  # type: ignore
    median_sts_end = sts_end.median().item()  # type: ignore
    std_sts_end = sts_end.std().item()  # type: ignore
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
            "threshold": P_DISPLAY_THRESHOLD,
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
            "threshold": P_DISPLAY_THRESHOLD,
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
            **MAIN_PLOTS_ARGS,
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
            **MAIN_PLOTS_ARGS,
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
            **MAIN_PLOTS_ARGS,
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            "x_range": [0, 6.05],
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
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
            **MAIN_PLOTS_ARGS,
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story thoughts",
            "y_tickvals": STORY_THOUGHTS_Y_VALS_TICKS,
            "y_ticktext": STORY_THOUGHTS_Y_VALS_TICKS,
            "y_range": STORY_THOUGHTS_Y_RANGE,
            "x_range": [0, 6.05],
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
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
            **MAIN_PLOTS_ARGS,
            "color": "condition",
            "title": None,
            "nbins": 7,
            "barmode": "group",
            "histnorm": "percent",
            "bargap": 0.12,
            "x_range": [0.5, 7.5],
            "y_range": [0, 41],
            "marker": dict(line_width=3, line_color="black"),
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "showlegend": False,
            "x_ticktext": [1, 2, 3, 4, 5, 6, 7],
            "x_tickvals": [1, 2, 3, 4, 5, 6, 7],
            "y_ticktext": [0, 10, 20, 30, 40],
            "y_tickvals": [0, 10, 20, 30, 40],
            "x_title": "Self-reported lingering",
            "y_title": "Proportion Participants",
            "x_showgrid": False,
            "y_showgrid": False,
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
    print(f"Percentage intentional: {round(n_intentional / n_total * 100, 1):.1f}")
    print(f"Percentage both: {round(n_both / n_total * 100, 1):.1f}")
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
    mean_sts_beginnning = sts_beginning.mean().item()  # type: ignore
    median_sts_beginnning = sts_beginning.median().item()  # type: ignore
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
    mean_sts_end = sts_end.mean().item()  # type: ignore
    median_sts_end = sts_end.median().item()  # type: ignore
    print(
        f"Mean: {round(mean_sts_end, 2)} in last 30s -> {round(mean_sts_end / 3, 2)}"
        " / 10s"
    )
    print(
        f"Median: {median_sts_end} in last 30s -> {round(median_sts_end / 3, 2)} / 10s"
    )

    console.print(
        "\n > Suppress: CORR: Story relatedness (post) & story thoughts (post)",
        style="yellow",
    )
    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "x_measure": "story_relatedness",
            "y_measure": "thought_entries",
            "ratings": RATINGS_CARVER,
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print(
        "\n > Suppress: CORR: CONTROL Story relatedness (pre) & story thoughts (post)",
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
            "threshold": P_DISPLAY_THRESHOLD,
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
            "threshold": P_DISPLAY_THRESHOLD,
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
            "replace_columns": {"volition": VOLITION_GROUPS},
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
            "replace_columns": {"volition": VOLITION_GROUPS},
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
            **MAIN_PLOTS_ARGS,
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
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_VOLITION_MERGED,
            "category_orders": ORDER_CONDITIONS_VOLITION_MERGED,
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
            **MAIN_PLOTS_ARGS,
            "measure_name": "linger_rating",
            "x": "condition",
            "title": "",
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_VOLITION_MERGED,
            "category_orders": ORDER_CONDITIONS_VOLITION_MERGED,
            "orientation": "h",
            "x_ticktext": [],
            "x_tickvals": [],
            "x_title": "Condition",
            "y_title": "Self-reported lingering",
            "x_title_standoff": 50,
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
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
            "ratings": RATINGS_CARVER,
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
            **MAIN_PLOTS_ARGS,
            "x_title": "Time from start of free association",
            "y_title": "Story thoughts",
            "x_range": [0, 6.05],
            "y_range": STORY_THOUGHTS_Y_RANGE,
            "y_tickvals": STORY_THOUGHTS_Y_VALS_TICKS,
            "y_ticktext": STORY_THOUGHTS_Y_VALS_TICKS,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_VOLITION_MERGED,
            "category_orders": ORDER_CONDITIONS_VOLITION_MERGED,
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
            "ratings": RATINGS_CARVER,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": None,
            "min_bin_n": 300,
            # plot visual config
            **MAIN_PLOTS_ARGS,
            "title": None,
            "x_title": "Time from start of free association",
            "y_title": "Story relatedness",
            # "x_range": [0, 6.05],
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_skip_first_tick": True,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
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
            "filepostfix": "aligned_fa_start_f3",
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
            "ratings": RATINGS_CARVER,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            "min_bin_n": 300,
            # plot visual config
            **MAIN_PLOTS_ARGS,
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "Story relatedness",
            "x_range": None,
            "x_skip_first_tick": True,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
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
            **MAIN_PLOTS_ARGS,
            "title": "",
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "orientation": "h",
            "showlegend": False,
            "x_ticktext": [],
            "x_tickvals": [],
            "y_tickfont": dict(color=COL1, size=42),
            # "y_ticktext": [1, 2, 3, 4, 5, 6, 7],
            # "y_tickvals": [1, 2, 3, 4, 5, 6, 7],
            "x_title": "Condition",
            "y_title": "Self-reported lingering",
            "bargap": None,
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
            "threshold": P_DISPLAY_THRESHOLD,
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
            "ratings": RATINGS_CARVER,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "step": 30000,
            "align_timestamp": "reading_task_end",
            # plot visual config
            "title": None,
            "x_title": "Time from end of original story",
            "y_title": "<b>Original story</b> relatedness",
            **MAIN_PLOTS_ARGS,
            "x_range": None,
            "x_skip_first_tick": True,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_ticks": "outside",
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": COL1,
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
            **MAIN_PLOTS_ARGS,
            "x_range": None,
            "x_skip_first_tick": True,
            "x_rangemode": "tozero",
            "y_range": THEME_SIMILARITY_RANGE,
            "x_ticks": "outside",
            "y_tickvals": None,
            "y_ticktext": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "axes_linecolor": COL1,
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
            **MAIN_PLOTS_ARGS,
            "title": "",
            "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "orientation": "h",
            "showlegend": False,
            "x_ticktext": [],
            "x_tickvals": [],
            "x_title": "Condition",
            "y_title": "Effort to integrate",
            "bargap": None,
            "x_showgrid": False,
            "y_showgrid": False,
            "axes_linecolor": COL1,
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


def suppl_stats_persistence_recency_correlations(multiple_comparisons: bool = False):
    # requires output from
    # python src/rate_word_position.py -m exact_match -s carver_original
    # python src/rate_word_position.py -m exact_match -s july_original
    # python src/rate_word_position.py \
    #    -m incontext -M gpt-5-mini-2025-08-07 -s carver_original
    # python src/rate_word_position.py \
    #    -m incontext -M gpt-5-mini-2025-08-07 -s july_original
    # (using default batch size 45)
    # (incontext rating has to be run multiple times to fix the errors
    # that inevitably happen.)
    console.print(
        "\n\nSupplement: Stats: Recency correlations",
        style="red bold",
    )

    match_config_dct = MATCH_CONFIG_DICT
    only_high_sr = False
    high_sr_threshold = 3.5

    console.print("\nRecency gradient in Baseline? Spearman correlation:", style="blue")
    recency_corrs_dict: dict[
        str,
        dict[
            str,
            dict[str, tuple[float, float, float, float, float, int]],
        ],
    ] = dict[str, dict[str, dict[str, tuple[float, float, float, float, float, int]]]]()
    for condition in CONDITIONS_RECENCY_CORRELATIONS:
        recency_corrs_dict[condition] = dict()
        for match_config in match_config_dct.values():
            word_position_dct, _, match_title, _, _, _, _, not_normalize = match_config
            recency_corrs_dict[condition][match_title] = dict()
            console.print(f"{condition} - {match_title} full time")

            # hardcoded and not beautiful, but simplicity beats generality here
            story = "carver_original"
            ratings = RATINGS_CARVER
            word_position_dct_ = word_position_dct
            if condition == "multi_day_july_carver":
                ratings = RATINGS_JULY_MULTI_DAY
                story = "july_original"
                word_position_dct_ = WORD_POSITION_EXACT_MATCH_JULY
                if match_title == "Semantic match":
                    word_position_dct_ = WORD_POSITION_SEMANTIC_MATCH_JULY
            pvalue, statistic, cohens_d, mean1, sd1, n1, _, _, _ = (
                compute_rank_spearman_correlation(
                    {
                        "story": story,
                        "condition": condition,
                        "ratings": ratings,
                        "word_position": word_position_dct_,
                        "not_normalize": not_normalize,
                        "exclude": [("gte", "timestamp", 180000)],
                        "only_high_sr": only_high_sr,
                        "high_sr_threshold": high_sr_threshold,
                    },
                    verbose=False,
                )
            )
            recency_corrs_dict[condition][match_title]["full_time"] = (
                pvalue,
                statistic,
                cohens_d,
                mean1,
                sd1,
                n1,
            )

            console.print(f"{condition} - {match_title} first 30s")
            pvalue, statistic, cohens_d, mean1, sd1, n1, _, _, _ = (
                compute_rank_spearman_correlation(
                    {
                        "story": story,
                        "condition": condition,
                        "ratings": ratings,
                        "word_position": word_position_dct_,
                        "not_normalize": not_normalize,
                        "exclude": [("gte", "timestamp", 30000)],
                        "only_high_sr": only_high_sr,
                        "high_sr_threshold": high_sr_threshold,
                        "threshold": P_DISPLAY_THRESHOLD,
                    },
                    verbose=False,
                )
            )
            recency_corrs_dict[condition][match_title]["first_30s"] = (
                pvalue,
                statistic,
                cohens_d,
                mean1,
                sd1,
                n1,
            )

    # print table
    console.print(
        "\nTable: Recency correlations (multiple comparisons)", style="yellow"
    )
    print("    \\begin{tabular}{l | cc | cc}")
    print(
        "        "
        "& \\multicolumn{2}{c|}{Exact Match} & \\multicolumn{2}{c}{Semantic Match}\\\\"
    )
    print("        \\hline")
    print(
        "        "
        "& \\makecell{all 180s} & \\makecell{first 30s}"
        " & \\makecell{all 180s} & \\makecell{first 30s}\\\\"
    )
    print("        \\hline")
    for condition in recency_corrs_dict.keys():
        print("        \\hline")
        condition_name = NAME_MAPPING[condition]
        if condition_name == "Suppress No Button Press":
            condition_name = "Suppress No\\\\Button Press"
        elif condition == "multi_day_carver_july":
            condition_name = "Multi Day\\\\Day 1: Carver"
        elif condition == "multi_day_july_carver":
            condition_name = "Multi Day\\\\Day 1: July"
        print(f"        \\makecell{{{condition_name}}}", end="")
        for match_title in ["Exact match", "Semantic match"]:
            for time_range in ["full_time", "first_30s"]:
                pvalue, statistic, cohens_d, mean1, sd1, n1 = recency_corrs_dict[
                    condition
                ][match_title][time_range]

                # p string
                threshold = P_DISPLAY_THRESHOLD
                if pvalue < (threshold - 0.2 * threshold):
                    pstring = f"p < {threshold}".replace("0.", ".")
                else:
                    cut_pval = cut_small_value(pvalue)
                    if pvalue < 0.05:
                        pstring = f"p = \\mathbf{{{cut_pval}}}"
                    else:
                        pstring = f"p = {cut_pval}"

                print(
                    " &\n        "
                    f"\\makecell{{$\\rho = {mean1:.2f}\\;({sd1:.2f})$\\\\"
                    f"$W={statistic:.1f},\\;n = {n1}$"
                    f"\\\\${pstring}$}}",
                    end="",
                )
        print("\\\\")

    print("    \\end{tabular}")


def suppl_stats_persistence_recency_correlations_difference(
    multiple_comparisons: bool = False,
):
    console.print(
        "\n\nSupplement: Stats: Recency correlations difference",
        style="red bold",
    )

    match_config_dct = MATCH_CONFIG_DICT
    only_high_sr = False
    high_sr_threshold = 3.5

    recency_corrs_comparison_dict: dict[
        str,
        list[
            tuple[str, str, float, float, float, float, float, int, float, float, int]
        ],
    ] = defaultdict(list)
    for condition in CONDITIONS_RECENCY_CORRELATIONS_DIFFERENCE:
        for match_config in match_config_dct.values():
            word_position_dct, _, match_title, _, _, _, _, not_normalize = match_config

            console.print(f"Neutralcue2 vs {condition} - {match_title} full time")
            pvalue, statistic, cohens_d, mean1, sd1, n1, mean2, sd2, n2 = (
                compute_rank_spearman_correlation(
                    {
                        "story": "carver_original",
                        "name1": "neutralcue2",
                        "name2": condition,
                        "config1": {"condition": "neutralcue2"},
                        "config2": {"condition": condition},
                        "ratings": RATINGS_CARVER,
                        "word_position": word_position_dct,
                        "not_normalize": not_normalize,
                        "exclude": [("gte", "timestamp", 180000)],
                        "only_high_sr": only_high_sr,
                        "high_sr_threshold": high_sr_threshold,
                        "threshold": P_DISPLAY_THRESHOLD,
                    },
                    verbose=False,
                )
            )
            recency_corrs_comparison_dict[match_title].append(
                (
                    condition,
                    "full_time",
                    pvalue,
                    statistic,
                    cohens_d,
                    mean1,
                    sd1,
                    n1,
                    mean2,
                    sd2,
                    n2,
                )
            )

            console.print(f"Neutralcue2 vs {condition} - {match_title} first 30s")
            pvalue, statistic, cohens_d, mean1, sd1, n1, mean2, sd2, n2 = (
                compute_rank_spearman_correlation(
                    {
                        "story": "carver_original",
                        "name1": "neutralcue2",
                        "name2": condition,
                        "config1": {"condition": "neutralcue2"},
                        "config2": {"condition": condition},
                        "ratings": RATINGS_CARVER,
                        "word_position": word_position_dct,
                        "not_normalize": not_normalize,
                        "exclude": [("gte", "timestamp", 30000)],
                        "only_high_sr": only_high_sr,
                        "high_sr_threshold": high_sr_threshold,
                        "threshold": P_DISPLAY_THRESHOLD,
                    },
                    verbose=False,
                )
            )

            recency_corrs_comparison_dict[match_title].append(
                (
                    condition,
                    "first_30s",
                    pvalue,
                    statistic,
                    cohens_d,
                    mean1,
                    sd1,
                    n1,
                    mean2,
                    sd2,
                    n2,
                )
            )

    if multiple_comparisons:
        for match_title, data_tuples in recency_corrs_comparison_dict.items():
            # sort for correction by p-value
            data_tuples.sort(key=lambda x: x[2])

            # threshold p values
            thresholds = [
                SIGNIFICANCE_THRESHHOLD / idx for idx in range(len(data_tuples), 0, -1)
            ]

            console.print(
                f"Holm-Bonferroni correction (alpha = 0.05): {match_title}",
                style="yellow",
            )
            # place things back into a dict to order them
            # dict[180s/30s -> dict[condition -> (
            #     rank, pvalue, statistic, cohens_d, mean1, sd1, n1, mean2, sd2, n2
            # )]]
            table_dct: dict[
                str,
                dict[
                    str,
                    tuple[
                        int,
                        float,
                        float,
                        float,
                        float,
                        float,
                        float,
                        int,
                        float,
                        float,
                        int,
                    ],
                ],
            ] = defaultdict(dict)
            violated = False
            for rank, (data_tuple, threshold) in enumerate(
                zip(data_tuples, thresholds)
            ):
                if data_tuple[2] >= threshold:
                    violated = True
                if violated:
                    console.print(
                        f"{data_tuple[0]} ({data_tuple[1]}) -"
                        " p = {round(data_tuple[2], 4)}"
                        f" > {round(threshold, 4)}",
                        style="red",
                    )
                else:
                    console.print(
                        f"{data_tuple[0]} ({data_tuple[1]}) -"
                        " p = {round(data_tuple[2], 4)}"
                        f" < {round(threshold, 4)}",
                        style="green",
                    )
                table_dct[data_tuple[1]][data_tuple[0]] = (
                    rank + 1,
                    threshold,
                    *data_tuple[2:],
                )

            # table header
            console.print(
                f"\nTable: Recency comparisons {match_title} with multiple comparisons",
                style="yellow",
            )

            print("    \\begin{tabular}{l | ccccc}")
            print(
                "        "
                "& \\makecell{Time\\\\period}"
                " & \\makecell{Comparison}"
                " & \\makecell{p-value\\\\uncorrected}"
                " & \\makecell{Adjusted\\\\alpha}"
                " & \\makecell{Rank}\\\\"
            )

            for time_range in ["full_time", "first_30s"]:
                print("        \\hline")
                for condition in CONDITIONS_RECENCY_CORRELATIONS_DIFFERENCE:
                    condition_name = NAME_MAPPING[condition]
                    (
                        rank,
                        threshold,
                        pvalue,
                        statistic,
                        cohens_d,
                        mean1,
                        sd1,
                        n1,
                        mean2,
                        sd2,
                        n2,
                    ) = table_dct[time_range][condition]

                    print("        \\hline")
                    print(f"        \\makecell{{{condition_name}}}", end="")
                    # p string
                    display_threshold = P_DISPLAY_THRESHOLD
                    if pvalue < (display_threshold - 0.2 * display_threshold):
                        pstring = f"p < {display_threshold}".replace("0.", ".")
                    else:
                        if pvalue < 0.09:
                            pstring = f"p = {cut_small_value(pvalue)}"
                        else:
                            pstring = f"p = {str(round(pvalue, 2))[1:]}"

                    initial = condition_name[0].upper()
                    print(
                        " &\n        "
                        f"0s - {time_range}"
                        f" & \\makecell{{$\\rho = {mean1:.2f}\\;"
                        f" v\\;\\rho = {mean2:.2f}$\\\\"
                        f" $n_\\text{{B}} = {n1}$,\\;$n_\\text{{{initial}}} = {n2}$\\\\"
                        f"$W={statistic:.1f}$}}"
                        f" & ${pstring}$"
                        f" & ${str(round(threshold, 4))[1:]}$"
                        f" & ${rank}$\\\\"
                    )

            print("    \\end{tabular}\n\n")
    else:
        # 1. make a useful table dct
        # condition
        #   -> match_title
        #     -> time_range
        #       -> pvalue, statistic, cohens_d, mean1, sd1, n1, mean2, sd2, n2
        table_dct_no_mc: dict[
            str,
            dict[
                str,
                dict[
                    str,
                    tuple[
                        float,
                        float,
                        float,
                        float,
                        float,
                        int,
                        float,
                        float,
                        int,
                    ],
                ],
            ],
        ] = dict()
        for match_title in ["Exact match", "Semantic match"]:
            for (
                condition,
                time_range,
                pvalue,
                statistic,
                cohens_d,
                mean1,
                sd1,
                n1,
                mean2,
                sd2,
                n2,
            ) in recency_corrs_comparison_dict[match_title]:
                if condition not in table_dct_no_mc:
                    table_dct_no_mc[condition] = defaultdict(dict)
                table_dct_no_mc[condition][match_title][time_range] = (
                    pvalue,
                    statistic,
                    cohens_d,
                    mean1,
                    sd1,
                    n1,
                    mean2,
                    sd2,
                    n2,
                )

        console.print("\nTable: Recency correlation comparisons", style="yellow")
        print("    \\begin{tabular}{l | cc | cc}")
        print(
            "        "
            "& \\multicolumn{2}{c|}{Exact Match}"
            " & \\multicolumn{2}{c}{Semantic Match}\\\\"
        )
        print("        \\hline")
        print(
            "        "
            "& \\makecell{all 180s} & \\makecell{first 30s}"
            " & \\makecell{all 180s} & \\makecell{first 30s}\\\\"
        )
        print("        \\hline")

        for condition in table_dct_no_mc.keys():
            print("        \\hline")
            condition_name = NAME_MAPPING[condition]
            if condition_name == "Suppress No Button Press":
                condition_name = "Suppress No\\\\Button Press"
            elif condition_name == "Suppress No Button Press":
                condition_name = "Suppress No\\\\Button Press"
            elif condition == "multi_day_carver_july":
                condition_name = "Multi Day\\\\Day 1: Carver"
            elif condition == "multi_day_july_carver":
                condition_name = "Multi Day\\\\Day 1: July"
            print(f"        \\makecell{{{condition_name}}}", end="")
            for match_title in ["Exact match", "Semantic match"]:
                for time_range in ["full_time", "first_30s"]:
                    pvalue, statistic, cohens_d, mean1, sd1, n1, mean2, sd2, n2 = (
                        table_dct_no_mc[condition][match_title][time_range]
                    )

                    # p string
                    threshold = P_DISPLAY_THRESHOLD
                    if pvalue < (threshold - 0.2 * threshold):
                        pstring = f"p < {threshold}".replace("0.", ".")
                    else:
                        cut_pval = cut_small_value(pvalue)
                        if pvalue < 0.05:
                            pstring = f"p = \\mathbf{{{cut_pval}}}"
                        else:
                            pstring = f"p = {cut_pval}"

                    print(
                        " &\n        "
                        f"\\makecell{{$\\rho = {mean1:.2f}\\;"
                        f" v\\;\\rho = {mean2:.2f}$\\\\"
                        f"$W={statistic:.1f}$,\\\\"
                        f"${pstring}$}}",
                        end="",
                    )
            print("\\\\")

        print("    \\end{tabular}")

    return


def suppl_intuitive_meaning_match_scores():
    console.print(
        "\nSuppl: Intuitive meaning of exact match score (normalized):",
        style="red bold",
    )

    only_high_sr = False
    high_sr_threshold = 3.5

    # get a feeling for what a 'match score' of 1 means
    # (1) for semantic match (without normalization):
    #     1 for section X means:
    #         a single word matches to section,
    #         or, 2 words match to 2 sections
    # (2) for exact match (with normalization):
    #     1 for section X means:
    #         a single word matches to section / norm_factor.
    #         norm_factor is  expected_section_length / actual_section_length
    #         = (sum(n_section_lengths) / n_sections) / section_length
    # Thus to get a feeling what 'exact match score' means,
    # (a) print the norm_factor for each section (shows contribution of single word)

    any_word_re = re.compile(r"\b\w+\b", flags=re.IGNORECASE)
    section_lengths = np.array(
        [
            len(any_word_re.findall("\n".join(section_sentences_)))
            for section_sentences_ in load_story_sentences_grouped(
                story="carver_original", story_file="sectioned.txt"
            )
        ]
    )
    expected_section_length = sum(section_lengths) / len(section_lengths)
    norm_factor = expected_section_length / section_lengths
    print(
        "ACTUAL := sum(section_lengths) / len(section_lengths)"
        " ('actual section length')"
    )
    print(
        "NORM FACTOR := expected_section_length / section_length"
        " ('how much match score one word gets you)"
    )
    print("1-SCORE := 1 / norm_factor ('how many words to get 1-score')")
    print("0.2-SCORE := 0.2 / norm_factor ('how many words to get 0.2-score')")
    print()
    table = Table()
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("EXPECTED", style="green", justify="center")
    table.add_column("ACTUAL", style="magenta", justify="center")
    table.add_column("NORM FACTOR", style="red", justify="center")
    table.add_column("1-SCORE", style="blue", justify="center")
    table.add_column("0.2-SCORE", justify="center")
    for idx_section, (section_length, norm_factor) in enumerate(
        zip(section_lengths, norm_factor)
    ):
        table.add_row(
            str(idx_section + 1),
            f"{expected_section_length:.2f}",
            f"{section_length:.2f}",
            f"{norm_factor:.2f}",
            f"{1 / norm_factor:.2f}",
            f"{0.2 / norm_factor:.2f}",
        )
    console.print(table)

    plot_bars_match_score(
        config={
            "story": "carver_original",
            "condition": "interference_story_spr",
            "ratings": RATINGS_CARVER,
            "word_position": WORD_POSITION_EXACT_MATCH,
            "not_normalize": False,
            "time_ranges": [(0, 30000)],
            "only_high_sr": only_high_sr,
            "high_sr_threshold": high_sr_threshold,
            # plot visual config
            "y_ranges": [(None, None)],
            "x_title": "Segment number",
            "y_title": "Exact match score",
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "title": "",
            "color_pre": "lightsalmon",
            "color_post": "indianred",
            # bootstrap
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # save
            "save": True,
            "width": 400,
            "height": 360,
            "study": STUDY_SUPPL,
            "filetype": FILETYPE,
            "suffix": (
                "outisde_exact_match_pre_post_interference_story_0_30_to_get_a_feeling"
            ),
        }
    )


def suppl_plots_persistence_recency_correlations():
    console.print(
        "\n\nSupplement: Plots: Recency / Separate story segments",
        style="red bold",
    )

    match_config_dct = MATCH_CONFIG_DICT
    only_high_sr = False
    high_sr_threshold = 3.5

    for match_config in match_config_dct.values():
        (
            word_position_dct,
            match_type,
            match_title,
            y_ranges_post_pre_30s_bins,
            y_ranges_0_180,
            y_ranges_30s_bins,
            y_range_across_conditions,
            not_normalize,
        ) = match_config

        console.print(f"\n{match_type}", style="blue")

        console.print("\nPost & Pre Match score neutralcue2", style="yellow")
        plot_bars_match_score(
            config={
                "story": "carver_original",
                "condition": "neutralcue2",
                "ratings": RATINGS_CARVER,
                "word_position": word_position_dct,
                "not_normalize": not_normalize,
                "time_ranges": [(0, 180000)],
                "only_high_sr": only_high_sr,
                "high_sr_threshold": high_sr_threshold,
                # plot visual config
                "y_ranges": [(None, None)],
                "x_title": "Segment number",
                "y_title": f"{match_title} score",
                "axes_tickcolor": AXES_COLOR_SUPPL,
                "axes_linecolor": AXES_COLOR_SUPPL,
                "title": "",
                "color_pre": "lightsalmon",
                "color_post": "indianred",
                # bootstrap
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # save
                "save": True,
                "width": 400,
                "height": 360,
                "study": STUDY_SUPPL,
                "filetype": FILETYPE,
                "suffix": f"suppl_{match_type}_pre_post_neutralcue2_0_180",
            }
        )
        plot_bars_match_score(
            config={
                "story": "carver_original",
                "condition": "neutralcue2",
                "ratings": RATINGS_CARVER,
                "word_position": word_position_dct,
                "not_normalize": not_normalize,
                "time_ranges": [
                    (0, 30000),
                    (30000, 60000),
                    (60000, 90000),
                    (90000, 120000),
                    (120000, 150000),
                    (150000, 180000),
                ],
                "only_high_sr": only_high_sr,
                "high_sr_threshold": high_sr_threshold,
                # plot visual config
                "y_ranges": y_ranges_post_pre_30s_bins,
                "x_title": "Segment number",
                "y_title": f"{match_title} score",
                "axes_tickcolor": AXES_COLOR_SUPPL,
                "axes_linecolor": AXES_COLOR_SUPPL,
                "title": "",
                "color_pre": "lightsalmon",
                "color_post": "indianred",
                # bootstrap
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # save
                "save": True,
                "width": 1920,
                "height": 360,
                "study": STUDY_SUPPL,
                "filetype": FILETYPE,
                "suffix": f"suppl_{match_type}_pre_post_neutralcue2_30s_bins",
            }
        )

        console.print("\n Post - Pre Match score", style="yellow")
        for condition in CONDITIONS_RECENCY_CORRELATIONS:
            color = COLOR_SEQUENCE_ORDERED[
                ORDER_CONDITIONS["condition"].index(condition)
            ]
            # hardcoded and not beautiful, but simplicity beats generality here
            story = "carver_original"
            ratings = RATINGS_CARVER
            word_position_dct_ = word_position_dct
            x_tickfont = dict(size=21)
            if condition == "multi_day_july_carver":
                ratings = RATINGS_JULY_MULTI_DAY
                story = "july_original"
                x_tickfont = dict(size=16)
                word_position_dct_ = WORD_POSITION_EXACT_MATCH_JULY
                if match_title == "Semantic match":
                    word_position_dct_ = WORD_POSITION_SEMANTIC_MATCH_JULY
            plot_bars_match_score(
                config={
                    "diff": True,
                    "story": story,
                    "condition": condition,
                    "ratings": ratings,
                    "word_position": word_position_dct_,
                    "not_normalize": not_normalize,
                    "time_ranges": [(0, 180000)],
                    "only_high_sr": only_high_sr,
                    "high_sr_threshold": high_sr_threshold,
                    "show_rho": True,
                    # plot visual config
                    "y_ranges": y_ranges_0_180,
                    "x_title": "Segment number",
                    "y_title": f"Post - Pre<br>{match_title} score",
                    "y_title_diff": "",
                    "x_tickfont": x_tickfont,
                    "axes_tickcolor": AXES_COLOR_SUPPL,
                    "axes_linecolor": AXES_COLOR_SUPPL,
                    "title": "",
                    "color": color,
                    # bootstrap
                    "n_bootstrap": N_BOOTSTRAP,
                    "ci": 0.95,
                    # save
                    "save": True,
                    "width": 430,
                    "height": 360,
                    "study": STUDY_SUPPL,
                    "filetype": FILETYPE,
                    "suffix": f"suppl_{match_type}_diff_{condition}_0_180",
                }
            )
            plot_bars_match_score(
                config={
                    "diff": True,
                    "story": story,
                    "condition": condition,
                    "ratings": ratings,
                    "word_position": word_position_dct_,
                    "not_normalize": not_normalize,
                    "time_ranges": [
                        (0, 30000),
                        (30000, 60000),
                        (60000, 90000),
                        (90000, 120000),
                        (120000, 150000),
                        (150000, 180000),
                    ],
                    "only_high_sr": only_high_sr,
                    "high_sr_threshold": high_sr_threshold,
                    "show_rho": True,
                    # plot visual config
                    "y_ranges": y_ranges_30s_bins,
                    "x_title": "Segment number",
                    "y_title": f"Post - Pre<br>{match_title} score",
                    "y_title_diff": "",
                    "x_tickfont": x_tickfont,
                    "axes_tickcolor": AXES_COLOR_SUPPL,
                    "axes_linecolor": AXES_COLOR_SUPPL,
                    "title": "",
                    "color": color,
                    # bootstrap
                    "n_bootstrap": N_BOOTSTRAP,
                    "ci": 0.95,
                    # save
                    "save": True,
                    "width": 1950,
                    "height": 360,
                    "study": STUDY_SUPPL,
                    "filetype": FILETYPE,
                    "suffix": f"suppl_{match_type}_diff_{condition}_30s_bins",
                }
            )


def suppl_plots_persistence_recency_correlations_difference():
    console.print(
        "\n\nSupplement: Plots: Recency correlations DIFFERENCE",
        style="red bold",
    )

    match_config_dct = MATCH_CONFIG_DICT
    only_high_sr = False
    high_sr_threshold = 3.5
    config_baseline = {
        "story": "carver_original",
        "condition": "neutralcue2",
    }

    for match_config in match_config_dct.values():
        (
            word_position_dct,
            match_type,
            match_title,
            y_ranges_post_pre_30s_bins,
            y_ranges_0_180,
            y_ranges_30s_bins,
            y_range_across_conditions,
            not_normalize,
        ) = match_config

        console.print(f"\n{match_type}", style="blue")

        console.print(
            "\nDifference & Diff to Baseline Match score neutralcue2", style="yellow"
        )
        for condition in CONDITIONS_RECENCY_CORRELATIONS_DIFFERENCE:
            color = COLOR_SEQUENCE_ORDERED[
                ORDER_CONDITIONS["condition"].index(condition)
            ]
            plot_bars_match_score(
                config={
                    "diff": True,
                    "story": "carver_original",
                    "condition": condition,
                    "ratings": RATINGS_CARVER,
                    "word_position": word_position_dct,
                    "not_normalize": not_normalize,
                    "config_baseline": {
                        **config_baseline,
                        "ratings": RATINGS_CARVER,
                        "word_position": word_position_dct,
                    },
                    "time_ranges": [(0, 180000)],
                    "only_high_sr": only_high_sr,
                    "high_sr_threshold": high_sr_threshold,
                    # plot visual config
                    "y_ranges": y_ranges_0_180,
                    "x_title": "Segment number",
                    "y_title": (
                        f"Difference to Baseline<br>Post - Pre<br>{match_title} score"
                    ),
                    "y_title_diff": "",
                    "axes_tickcolor": AXES_COLOR_SUPPL,
                    "axes_linecolor": AXES_COLOR_SUPPL,
                    "title": "",
                    "color": color,
                    # bootstrap
                    "n_bootstrap": N_BOOTSTRAP,
                    "ci": 0.95,
                    # save
                    "save": True,
                    "width": 460,
                    "height": 360,
                    "study": STUDY_SUPPL,
                    "filetype": FILETYPE,
                    "suffix": (
                        f"suppl_{match_type}_diff_to_baseline_{condition}_0_180"
                    ),
                }
            )
            plot_bars_match_score(
                config={
                    "diff": True,
                    "story": "carver_original",
                    "condition": condition,
                    "ratings": RATINGS_CARVER,
                    "word_position": word_position_dct,
                    "not_normalize": not_normalize,
                    "config_baseline": {
                        **config_baseline,
                        "ratings": RATINGS_CARVER,
                        "word_position": word_position_dct,
                    },
                    "time_ranges": [
                        (0, 30000),
                        (30000, 60000),
                        (60000, 90000),
                        (90000, 120000),
                        (120000, 150000),
                        (150000, 180000),
                    ],
                    "only_high_sr": only_high_sr,
                    "high_sr_threshold": high_sr_threshold,
                    # plot visual config
                    "y_ranges": y_ranges_30s_bins,
                    "x_title": "Segment number",
                    "y_title": (
                        f"Difference to Baseline<br>Post - Pre<br>{match_title} score"
                    ),
                    "y_title_diff": "",
                    "axes_tickcolor": AXES_COLOR_SUPPL,
                    "axes_linecolor": AXES_COLOR_SUPPL,
                    "title": "",
                    "color": color,
                    # bootstrap
                    "n_bootstrap": N_BOOTSTRAP,
                    "ci": 0.95,
                    # save
                    "save": True,
                    "width": 1980,
                    "height": 360,
                    "study": STUDY_SUPPL,
                    "filetype": FILETYPE,
                    "suffix": (
                        f"suppl_{match_type}_diff_to_baseline_{condition}_30s_bins"
                    ),
                }
            )


def suppl_plots_recency_difference_across_conditions():
    console.print(
        "\n\nSupplement: Plots: Recency difference across conditions",
        style="red bold",
    )

    match_config_dct = MATCH_CONFIG_DICT
    only_high_sr = False
    high_sr_threshold = 3.5

    for match_config in match_config_dct.values():
        (
            word_position_dct,
            match_type,
            match_title,
            _,
            _,
            _,
            y_range_across_conditions,
            not_normalize,
        ) = match_config

        console.print(f"\n{match_type}", style="blue")

        console.print("\nMatch score diff across conditions", style="yellow")
        for time_range in [(0, 180000), (0, 30000)]:
            start_time, end_time = time_range
            start_str = f"{int(start_time / 1000)}"
            end_str = f"{int(end_time / 1000)}"
            plot_match_score_across_conditions(
                config={
                    "story": "carver_original",
                    "ratings": RATINGS_CARVER,
                    "config_baseline": {
                        "condition": "neutralcue2",
                    },
                    "configs": [
                        {"condition": condition}
                        for condition in CONDITIONS_RECENCY_CORRELATIONS_DIFFERENCE
                    ],
                    "word_position": word_position_dct,
                    "not_normalize": not_normalize,
                    "time_range": time_range,
                    "only_high_sr": only_high_sr,
                    "high_sr_threshold": high_sr_threshold,
                    "color_map": {
                        "interference_situation": "#C701FF",
                        "interference_tom": "#FFAE00",
                        "interference_geometry": "#0173DB",
                        "interference_story_spr": "#09A000",
                        # "interference_story_spr_end_continued": "#356BEB",
                        # "interference_story_spr_end_separated": "#09E3AC",
                        "interference_pause": "#8399FF",
                    },
                    "category_orders": {
                        "name": CONDITIONS_RECENCY_CORRELATIONS_DIFFERENCE
                    },
                    "x_title": "Segment number",
                    "y_title": (
                        f"Difference to Baseline<br>Post - Pre<br>{match_title} score"
                    ),
                    "title": "",
                    **MAIN_PLOTS_ARGS,
                    "y_range": y_range_across_conditions,
                    "marker_size": 15,
                    # bootstrap
                    "n_bootstrap": N_BOOTSTRAP,
                    "ci": 0.95,
                    "save": True,
                    "width": 990,
                    "height": 600,
                    "study": STUDY_SUPPL,
                    "filetype": FILETYPE,
                    "suffix": (
                        f"suppl_{match_type}_across_conditions_{start_str}_{end_str}"
                    ),
                }
            )


def suppl_stats_persistence_without_recency():
    console.print(
        "\n\nSupplement: Stats: Persistence without recency", style="red bold"
    )

    word_position_dct = load_word_position(WORD_POSITION_SEMANTIC_MATCH)

    removed_sections = [7, 8]

    def get_decrease_score(config: dict) -> tuple[pd.Series, pd.Series, pd.Series]:
        data_df = load_rated_wordchains(config=config)
        data_df_removed_sections = remove_words_in_sections(
            data_df=data_df,
            word_position_dct=word_position_dct,
            removed_sections=removed_sections,
            unique_in_section=False,
        )

        original_means: pd.Series = data_df.groupby("participantID")[
            "story_relatedness"
        ].mean()  # type: ignore
        removed_sections_means: pd.Series = data_df_removed_sections.groupby(
            "participantID"
        )["story_relatedness"].mean()  # type: ignore

        decrease_scores = removed_sections_means - original_means
        # participants may have all their words removed, and thus won't appear
        # in the removed sections means - need to remove the nans
        removed_all_words = decrease_scores.isna()
        decrease_scores = decrease_scores[~removed_all_words]
        original_means = original_means[~removed_all_words]  # type: ignore
        return decrease_scores, original_means, removed_sections_means

    # 1. get decrease score for neutralcue2 from 0 to 30s
    (
        neutralcue2_decrease_scores,
        neutralcue2_original_means,
        neutralcue2_removed_sections_means,
    ) = get_decrease_score(
        {
            "story": "carver_original",
            "condition": "neutralcue2",
            "position": "post",
            "ratings": RATINGS_CARVER,
            "align_timestamp": "reading_task_end",
            "exclude": [
                ("lt", "timestamp", 0),
                ("gte", "timestamp", 30000),
            ],
        }
    )
    # 2. aggregate decrease scores for interference conditions
    interference_decrease_scores_ls = list()
    interference_original_means_ls = list()
    interference_removed_sections_means_ls = list()
    for condition in [
        "interference_situation",
        "interference_tom",
        "interference_geometry",
        "interference_story_spr",
        "interference_pause",
    ]:
        (
            decrease_scores,
            original_means,
            removed_sections_means,
        ) = get_decrease_score(
            {
                "story": "carver_original",
                "condition": condition,
                "position": "post",
                "ratings": RATINGS_CARVER,
                "align_timestamp": "reading_task_end",
                "exclude": [
                    ("lt", "timestamp", 30000),
                    ("gte", "timestamp", 60000),
                ],
            }
        )
        interference_decrease_scores_ls.append(decrease_scores)
        interference_original_means_ls.append(original_means)
        interference_removed_sections_means_ls.append(removed_sections_means)
    interference_decrease_scores: pd.Series = pd.concat(interference_decrease_scores_ls)  # type: ignore
    # interference_original_means: pd.Series = pd.concat(interference_original_means_ls)
    # interference_removed_sections_means: pd.Series = pd.concat(
    #     interference_removed_sections_means_ls
    # )  # type: ignore

    # 3. test for difference
    console.print(
        (
            "\nSemantic match: Difference in decrease after"
            " removing sections 8 & 9 stronger in Baseline?"
        ),
        style="yellow",
    )
    test_two(
        {
            "name1": "Baseline (0s - 30s)",
            "name2": "Interference (30s - 60s, pooled)",
            "measure": "story_relatedness",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data1_sr=neutralcue2_decrease_scores,
        data2_sr=interference_decrease_scores,
    )

    # console.print(
    #     (
    #         "\nSemantic match: Difference in baseline and interference"
    #         " for original data."
    #     ),
    #     style="yellow",
    # )
    # test_two(
    #     {
    #         "name1": "Baseline (0s - 30s)",
    #         "name2": "Interference (30s - 60s, pooled)",
    #         "measure": "story_relatedness",
    #         "test_type": "mwu",
    #         "threshold": P_DISPLAY_THRESHOLD,
    #     },
    #     data1_sr=neutralcue2_original_means,
    #     data2_sr=interference_original_means,
    # )

    # console.print(
    #     (
    #         "\nSemantic match: Difference in baseline and interference"
    #         " for removed sections data."
    #     ),
    #     style="yellow",
    # )
    # test_two(
    #     {
    #         "name1": "Baseline (0s - 30s)",
    #         "name2": "Interference (30s - 60s, pooled)",
    #         "measure": "story_relatedness",
    #         "test_type": "mwu",
    #         "threshold": P_DISPLAY_THRESHOLD,
    #     },
    #     data1_sr=neutralcue2_removed_sections_means,
    #     data2_sr=interference_removed_sections_means,
    # )


def suppl_plots_persistence_without_recency():
    console.print(
        "\nPlot main persistence curve without section 8 & 9", style="red bold"
    )

    # sections are 0-indexed, 8 -> section 9
    removed_sections = [7, 8]

    original_symbol = "x"
    original_line_dash = "dot"

    removed_section_symbol = "circle"
    removed_section_line_dash = "solid"
    show_original = True
    width = 1350

    marker_size = 12
    marker_line = dict(width=2, color="DarkSlateGrey")
    line_width = 4

    console.print("\nExact match", style="yellow")
    plot_by_time_shifted_without_section(
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
            "ratings": RATINGS_CARVER,
            "word_position": WORD_POSITION_EXACT_MATCH,
            "mode": "relatedness",
            "column": "story_relatedness",
            "removed_sections": removed_sections,
            "step": 30000,
            # only remove words that are exclusively in the removed sections
            # -> these words are so seldom that the difference between
            # original and removed graph is basically zero.
            "unique_in_section": False,
            # make sure that original only shows participants that are also present
            # in the removed section data
            "equalize_participants_on_column": "group",
            "align_timestamp": "reading_task_end",
            "min_bin_n": 200,
            "show_original": show_original,
            "color": "condition",
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "symbol": "group",
            "symbol_map": {
                "original": original_symbol,
                "removed section": removed_section_symbol,
            },
            "line_dash": "group",
            "line_dash_map": {
                "original": original_line_dash,
                "removed section": removed_section_line_dash,
            },
            "title": None,
            # axes
            "x_title": "Time from end of reading",
            "y_title": ("Story relatedness"),
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": False,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": marker_size,
            "marker_line": marker_line,
            "line_width": line_width,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # legend
            "show": False,
            "showlegend": False,
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # saving
            "save": True,
            "study": STUDY_SUPPL,
            "width": width,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_reading_end_no_exact_match_8_9",
        }
    )

    console.print("\nSemantic match", style="yellow")
    plot_by_time_shifted_without_section(
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
            "ratings": RATINGS_CARVER,
            "word_position": WORD_POSITION_SEMANTIC_MATCH,
            "mode": "relatedness",
            "column": "story_relatedness",
            # sections are 0-indexed, 8 -> section 9
            "removed_sections": removed_sections,
            "step": 30000,
            "equalize_participants_on_column": "group",
            "align_timestamp": "reading_task_end",
            "min_bin_n": 200,
            "show_original": show_original,
            "color": "condition",
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "symbol": "group",
            "symbol_map": {
                "original": original_symbol,
                "removed section": removed_section_symbol,
            },
            "line_dash": "group",
            "line_dash_map": {
                "original": original_line_dash,
                "removed section": removed_section_line_dash,
            },
            "title": None,
            # axes
            "x_title": "Time from end of reading",
            "y_title": ("Story relatedness"),
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": False,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": marker_size,
            "marker_line": marker_line,
            "line_width": line_width,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # legend
            "show": False,
            "showlegend": False,
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # saving
            "save": True,
            "study": STUDY_SUPPL,
            "width": width,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_reading_end_no_semantic_match_8_9",
        }
    )

    console.print("\nExact match - fa start", style="yellow")
    plot_by_time_shifted_without_section(
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
            "ratings": RATINGS_CARVER,
            "word_position": WORD_POSITION_EXACT_MATCH,
            "mode": "relatedness",
            "column": "story_relatedness",
            "removed_sections": removed_sections,
            "step": 30000,
            "equalize_participants_on_column": "group",
            "align_timestamp": None,
            "min_bin_n": 200,
            "show_original": show_original,
            "color": "condition",
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "symbol": "group",
            "symbol_map": {
                "original": original_symbol,
                "removed section": removed_section_symbol,
            },
            "line_dash": "group",
            "line_dash_map": {
                "original": original_line_dash,
                "removed section": removed_section_line_dash,
            },
            "title": None,
            # axes
            "x_title": "Time from start of free association",
            "y_title": ("Story relatedness"),
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": False,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": marker_size,
            "marker_line": marker_line,
            "line_width": line_width,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # legend
            "show": False,
            "showlegend": False,
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # saving
            "save": True,
            "study": STUDY_SUPPL,
            "width": width,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_fa_start_no_exact_match_8_9",
        }
    )

    console.print("\nSemantic match - fa start", style="yellow")
    plot_by_time_shifted_without_section(
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
            "ratings": RATINGS_CARVER,
            "word_position": WORD_POSITION_SEMANTIC_MATCH,
            "mode": "relatedness",
            "column": "story_relatedness",
            # sections are 0-indexed, 8 -> section 9
            "removed_sections": removed_sections,
            "step": 30000,
            "equalize_participants_on_column": "group",
            "align_timestamp": None,
            "min_bin_n": 200,
            "show_original": show_original,
            "color": "condition",
            "color_sequence": COLOR_SEQUENCE_ORDERED,
            "category_orders": ORDER_CONDITIONS,
            "symbol": "group",
            "symbol_map": {
                "original": original_symbol,
                "removed section": removed_section_symbol,
            },
            "line_dash": "group",
            "line_dash_map": {
                "original": original_line_dash,
                "removed section": removed_section_line_dash,
            },
            "title": None,
            # axes
            "x_title": "Time from start of free association",
            "y_title": ("Story relatedness"),
            "x_title_font_size": 42,
            "y_title_font_size": 42,
            "x_range": None,
            "x_rangemode": "tozero",
            "y_range": STORY_RELATEDNESS_Y_RANGE,
            "x_tickfont": dict(size=36),
            "y_tickfont": dict(size=36),
            "x_ticks": "outside",
            "x_skip_first_tick": False,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS,
            "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT,
            "axes_linecolor": AXES_COLOR_SUPPL,
            "axes_tickcolor": AXES_COLOR_SUPPL,
            "axes_linewidth": 7,
            "marker_size": marker_size,
            "marker_line": marker_line,
            "line_width": line_width,
            "x_showgrid": False,
            "y_showgrid": False,
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            # legend
            "show": False,
            "showlegend": False,
            # bootstrap
            "bootstrap": True,
            "n_bootstrap": N_BOOTSTRAP,
            "ci": 0.95,
            # saving
            "save": True,
            "study": STUDY_SUPPL,
            "width": width,
            "height": 660,
            "filetype": FILETYPE,
            "filepostfix": "suppl_fa_start_no_semantic_match_8_9",
        }
    )


def suppl_plots_match_score_by_sections():
    for condition in [
        "neutralcue2",
        "interference_situation",
        "interference_tom",
        "interference_geometry",
        "interference_story_spr",
        "interference_pause",
        "button_press",
        "button_press_suppress",
        "suppress",
    ]:
        console.print(f"{condition} - exact match", style="yellow")
        plot_match_score_by_time_sections(
            {
                "load_spec": (
                    "all",
                    {
                        "all": (
                            "story",
                            {
                                "carver_original": (
                                    "condition",
                                    {condition: POST_NOFILTER},
                                )
                            },
                        )
                    },
                ),
                "aggregate_on": "position",
                "ratings": RATINGS_CARVER,
                "word_position": WORD_POSITION_EXACT_MATCH,
                "mode": "exact_match_score",
                "step": 30000,
                "normalize": True,
                "min_bin_n": 200,
                "title": f"{condition}, normalized",
                "x_title": "Time from start of free association",
                "y_title": "Post - Pre<br>Exact match score",
                "x_range": None,
                "x_rangemode": "tozero",
                "y_range": (-0.03, 0.06),
                "x_title_font_size": 42,
                "y_title_font_size": 42,
                "x_tickfont": dict(size=36),
                "y_tickfont": dict(size=36),
                "x_ticks": "outside",
                "y_zeroline": True,
                # bootstrap
                "bootstrap": True,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # legend
                "showlegend": True,
                "legend": LEGEND_TOP_RIGHT_SMALL,
                # saving
                "save": True,
                "study": STUDY_SUPPL,
                "width": 1200,
                "height": 660,
                "filepostfix": "suppl_word_position_by_section_normalized_fa_start",
            }
        )
        plot_match_score_by_time_sections(
            {
                "load_spec": (
                    "all",
                    {
                        "all": (
                            "story",
                            {
                                "carver_original": (
                                    "condition",
                                    {condition: POST_NOFILTER},
                                )
                            },
                        )
                    },
                ),
                "aggregate_on": "position",
                "ratings": RATINGS_CARVER,
                "word_position": WORD_POSITION_EXACT_MATCH,
                "mode": "exact_match_score",
                "step": 30000,
                "align_timestamp": "reading_task_end",
                "normalize": True,
                "min_bin_n": 200,
                "title": f"{condition}, normalized",
                "x_title": "Time from end of reading",
                "y_title": "Post - Pre<br>Exact match score",
                "x_range": None,
                "x_rangemode": "tozero",
                "y_range": (-0.03, 0.06),
                "x_title_font_size": 42,
                "y_title_font_size": 42,
                "x_tickfont": dict(size=36),
                "y_tickfont": dict(size=36),
                "x_ticks": "outside",
                "y_zeroline": True,
                # bootstrap
                "bootstrap": True,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # legend
                "showlegend": True,
                "legend": LEGEND_TOP_RIGHT_SMALL,
                # saving
                "save": True,
                "study": STUDY_SUPPL,
                "width": 1200,
                "height": 660,
                "filepostfix": "suppl_word_position_by_section_normalized_reading_end",
            }
        )

        console.print(f"{condition} - semantic match", style="yellow")
        plot_match_score_by_time_sections(
            {
                "load_spec": (
                    "all",
                    {
                        "all": (
                            "story",
                            {
                                "carver_original": (
                                    "condition",
                                    {condition: POST_NOFILTER},
                                )
                            },
                        )
                    },
                ),
                "aggregate_on": "position",
                "ratings": RATINGS_CARVER,
                "word_position": WORD_POSITION_SEMANTIC_MATCH,
                "mode": "semantic_match_score",
                "step": 30000,
                "normalize": False,
                "min_bin_n": 200,
                "title": f"{condition}",
                "x_title": "Time from start of free association",
                "y_title": "Post - Pre<br>Semantic match score",
                "x_range": None,
                "x_rangemode": "tozero",
                "y_range": (-0.04, 0.15),
                "x_title_font_size": 42,
                "y_title_font_size": 42,
                "x_tickfont": dict(size=36),
                "y_tickfont": dict(size=36),
                "x_ticks": "outside",
                "y_zeroline": True,
                # bootstrap
                "bootstrap": True,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # legend
                "showlegend": True,
                "legend": LEGEND_TOP_RIGHT_SMALL,
                # saving
                "save": True,
                "study": STUDY_SUPPL,
                "width": 1200,
                "height": 660,
                "filepostfix": "suppl_word_position_by_section_fa_start",
            }
        )
        plot_match_score_by_time_sections(
            {
                "load_spec": (
                    "all",
                    {
                        "all": (
                            "story",
                            {
                                "carver_original": (
                                    "condition",
                                    {condition: POST_NOFILTER},
                                )
                            },
                        )
                    },
                ),
                "aggregate_on": "position",
                "ratings": RATINGS_CARVER,
                "word_position": WORD_POSITION_SEMANTIC_MATCH,
                "mode": "semantic_match_score",
                "step": 30000,
                "align_timestamp": "reading_task_end",
                "normalize": False,
                "min_bin_n": 200,
                "title": f"{condition}",
                "x_title": "Time from end of reading",
                "y_title": "Post - Pre<br>Semantic match score",
                "x_range": None,
                "x_rangemode": "tozero",
                "y_range": (-0.04, 0.15),
                "x_title_font_size": 42,
                "y_title_font_size": 42,
                "x_tickfont": dict(size=36),
                "y_tickfont": dict(size=36),
                "x_ticks": "outside",
                "y_zeroline": True,
                # bootstrap
                "bootstrap": True,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # legend
                "showlegend": True,
                "legend": LEGEND_TOP_RIGHT_SMALL,
                # saving
                "save": True,
                "study": STUDY_SUPPL,
                "width": 1200,
                "height": 660,
                "filepostfix": "suppl_word_position_by_section_reading_end",
            }
        )
        plot_match_score_by_time_sections(
            {
                "load_spec": (
                    "all",
                    {
                        "all": (
                            "story",
                            {
                                "carver_original": (
                                    "condition",
                                    {condition: POST_NOFILTER},
                                )
                            },
                        )
                    },
                ),
                "aggregate_on": "position",
                "ratings": RATINGS_CARVER,
                "word_position": WORD_POSITION_SEMANTIC_MATCH,
                "mode": "semantic_match_score",
                "step": 30000,
                "normalize": True,
                "min_bin_n": 200,
                "title": f"{condition}, normalized",
                "x_title": "Time from start of free association",
                "y_title": "Post - Pre<br>Semantic match score",
                "x_range": None,
                "x_rangemode": "tozero",
                "y_range": (-0.04, 0.15),
                "x_title_font_size": 42,
                "y_title_font_size": 42,
                "x_tickfont": dict(size=36),
                "y_tickfont": dict(size=36),
                "x_ticks": "outside",
                "y_zeroline": True,
                # bootstrap
                "bootstrap": True,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # legend
                "showlegend": True,
                "legend": LEGEND_TOP_RIGHT_SMALL,
                # saving
                "save": True,
                "study": STUDY_SUPPL,
                "width": 1200,
                "height": 660,
                "filepostfix": "suppl_word_position_by_section_normalized_fa_start",
            }
        )
        plot_match_score_by_time_sections(
            {
                "load_spec": (
                    "all",
                    {
                        "all": (
                            "story",
                            {
                                "carver_original": (
                                    "condition",
                                    {condition: POST_NOFILTER},
                                )
                            },
                        )
                    },
                ),
                "aggregate_on": "position",
                "ratings": RATINGS_CARVER,
                "word_position": WORD_POSITION_SEMANTIC_MATCH,
                "mode": "semantic_match_score",
                "step": 30000,
                "align_timestamp": "reading_task_end",
                "normalize": True,
                "min_bin_n": 200,
                "title": f"{condition}, normalized",
                "x_title": "Time from end of reading",
                "y_title": "Post - Pre<br>Semantic match score",
                "x_range": None,
                "x_rangemode": "tozero",
                "y_range": (-0.04, 0.15),
                "x_title_font_size": 42,
                "y_title_font_size": 42,
                "x_tickfont": dict(size=36),
                "y_tickfont": dict(size=36),
                "x_ticks": "outside",
                "y_zeroline": True,
                # bootstrap
                "bootstrap": True,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                # legend
                "showlegend": True,
                "legend": LEGEND_TOP_RIGHT_SMALL,
                # saving
                "save": True,
                "study": STUDY_SUPPL,
                "width": 1200,
                "height": 660,
                "filepostfix": "suppl_word_position_by_section_normalized_reading_end",
            }
        )


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
            "ratings": RATINGS_CARVER,
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
        name = NAME_MAPPING[config["condition"]]
        print(f"{config['story']} | {name} | N = {n_participants}")

    aggregator(
        config={
            "load_spec": ("all", {"all": ("story", ALL_STORIES_CONDITIONS_DCT)}),
            "aggregate_on": "condition",
            "ratings": RATINGS_CARVER,
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


def suppl_methods_stats_words_rated():
    console.print("\nSupplemental Methods: Words rated.", style="red bold")

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
            "ratings": RATINGS_CARVER,
            "corrections": True,
            "column": "story_relatedness",
        },
        load_func=func_load_rated_words,
        call_func=print_n_unique_words,
    )


def suppl_methods_stats_words_generated():
    console.print("\nSupplemental Methods: Words generated.", style="red bold")

    # across all
    compute_word_stats(
        config={
            "load_spec": (
                "all",
                {"all": ("story", ALL_STORIES_CONDITIONS_DCT)},
            ),
            "aggregate_on": "all",
            "column": "story_relatedness",
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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
    # rater1: DA
    # rater2: AA -> in paper: Rater 2
    # rater3: AL -> in paper: Rater 1
    # (paper actually has chronological order correct)
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
            "raters": ["rater2", "rater3"],
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
            "method": "rater:rater3",
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
            "method": "rater:rater2",
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
            # plot data config
            "mode": "relatedness",
            "column": "story_relatedness",
            "fields": ["wcg_strategy"],
            "method": "rater:rater3",
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
    # GKP: Coming to this a year later, it seems the goal of this is:
    # (a) investigate the difference between computing the mean of all words in a bin,
    #     vs the mean of the within-participant mean in the bin.
    # (b) investigate the significant difference between the button_press and situation
    #     condition.
    # As clarification, in the end we used neutralcue2 as baseline.
    # I left the code and comments here untouched.
    # Good luck traveler.

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
    mean_sr: pd.Series = bp_30s_60s_bin_df.groupby("participantID")[  # type: ignore
        "story_relatedness"
    ].mean()
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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

    multiple_comparions = list()

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
            "threshold": P_DISPLAY_THRESHOLD,
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
            "threshold": P_DISPLAY_THRESHOLD,
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
            "threshold": P_DISPLAY_THRESHOLD,
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
            "threshold": P_DISPLAY_THRESHOLD,
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
                    "threshold": P_DISPLAY_THRESHOLD,
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
        header=[  # type: ignore
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

    test_two(
        {
            "name1": "Continued",
            "name2": "Delayed Continued",
            "config1": {"condition": "interference_story_spr_end_continued"},
            "config2": {"condition": "interference_story_spr_end_delayed_continued"},
            "position": "post",
            "exclude": [("gte", "timestamp", 30000)],
            "story": "carver_original",
            "alternative": "greater",
            # "align_timestamp": "reading_task_end",
            "ratings": RATINGS_CARVER,
            "measure": "story_relatedness",
            "test_type": "mwu",
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
            "ratings": RATINGS_CARVER,
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
                "threshold": P_DISPLAY_THRESHOLD,
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
                "threshold": P_DISPLAY_THRESHOLD,
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
                "threshold": P_DISPLAY_THRESHOLD,
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


def suppl_plots_sr_st_suppress():
    console.print("\nSUPPL: Story thoughts & story relatedness", style="red bold")

    plot_scatter_measures(
        {
            "load_spec": (
                "all",
                {
                    "all": (
                        "story",
                        {
                            "carver_original": (
                                "condition",
                                {"button_press_suppress": POST_NOFILTER},
                            )
                        },
                    )
                },
            ),
            "aggregate_on": "condition",
            # on what measure
            "x_measure": "mean_sr_post",
            "y_measure": "total_double_press_count_post",
            # plot config
            "color": "condition",
            # "x_range": [0.9, 7.09],
            "y_range": None,
            "x_title": "Story relatedness",
            "y_title": "Story thoughts",
            "color_sequence": ["#09A000"],
            "x_showgrid": False,
            "y_showgrid": False,
            # "x_tickvals": [1, 2, 3, 4, 5, 6, 7],
            # "x_ticktext": ["1", "2", "3", "4", "5", "6", "7"],
            "trendline_color": COL1,
            "tickcolor": COL1,
            "axes_linecolor": COL1,
            "axes_tickcolor": COL1,
            "axes_linewidth": 7,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickfont": dict(color=COL1, size=36),
            "x_tickfont": dict(color=COL1, size=36),
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "showlegend": False,
            # bootstrap
            "n_bootstrap": N_BOOTSTRAP,
            # save config
            "save": True,
            "width": 660,
            "height": 660,
            "scale": 2.0,
            "filepostfix": "suppl_sr_st_suppress",
            "study": STUDY_SUPPL,
            "filetype": FILETYPE,
            "regression": True,
            "regression_on_plot": True,
        }
    )

    correlate_two(
        {
            "story": "carver_original",
            "condition": "button_press_suppress",
            "position": "post",
            "x_measure": "story_relatedness",
            "y_measure": "thought_entries",
            "ratings": RATINGS_CARVER,
            "threshold": P_DISPLAY_THRESHOLD,
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
            "ratings": RATINGS_CARVER,
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
            "ratings": RATINGS_CARVER,
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


def load_sr_multi_day_all_positions(condition: str):
    if condition == "multi_day_carver_july":
        story1 = "carver_original"
        story2 = "july_original"
        ratings1 = RATINGS_CARVER_MULTI_DAY
        ratings2 = RATINGS_JULY_MULTI_DAY
    elif condition == "multi_day_july_carver":
        story1 = "july_original"
        story2 = "carver_original"
        ratings1 = RATINGS_JULY_MULTI_DAY
        ratings2 = RATINGS_CARVER_MULTI_DAY
    else:
        raise ValueError(f"Invalid condition: {condition}")
    sr1 = load_per_participant_data(
        {
            "story": story1,
            "condition": condition,
            "position": "pre",
            "measure": "story_relatedness",
            "ratings": ratings1,
        }
    ).loc[:, "story_relatedness"]
    sr2 = load_per_participant_data(
        {
            "story": story1,
            "condition": condition,
            "position": "post",
            "measure": "story_relatedness",
            "ratings": ratings1,
        }
    ).loc[:, "story_relatedness"]
    sr3 = load_per_participant_data(
        {
            "story": story2,
            "condition": condition,
            "position": "pre",
            "measure": "story_relatedness",
            "ratings": ratings2,
        }
    ).loc[:, "story_relatedness"]
    sr4 = load_per_participant_data(
        {
            "story": story2,
            "condition": condition,
            "position": "post",
            "measure": "story_relatedness",
            "ratings": ratings2,
        }
    ).loc[:, "story_relatedness"]

    sr_diff_sr2_sr1 = sr2 - sr1
    sr_diff_sr4_sr3 = sr4 - sr3

    return sr1, sr2, sr3, sr4, sr_diff_sr2_sr1, sr_diff_sr4_sr3


def suppl_linger_multi_day_plots():
    console.print("\nSUPPL: Linger multi-day plots", style="red bold")

    multi_day_pooled_color_map = {
        "Day 1": COL_NEUTRALCUE2,
        "Day 2": "#09A000",
    }
    multi_day_carver_july_color_map = {
        "Day 1": "#C701FF",
        "Day 2": "#FFAE00",
    }
    multi_day_july_carver_color_map = {
        "Day 1": "#FFAE00",
        "Day 2": "#C701FF",
    }
    multi_day_category_orders = {
        "condition": ["Day 1", "Day 2"],
    }
    multi_day_legend_name_mapping = {
        "Day 1, post": "Day 1 (Baseline) - Post",
        "Day 1, pre": "Day 1 (Baseline) - Pre",
        "Day 2, post": "Day 2 (Suppress) - Post",
        "Day 2, pre": "Day 2 (Suppress) - Pre",
    }
    multi_day_legend_name_mapping_carver_july = {
        "Day 1, post": "Day 1: Carver (Baseline) - Post",
        "Day 1, pre": "Day 1: Carver (Baseline) - Pre",
        "Day 2, post": "Day 2: July (Suppress) - Post",
        "Day 2, pre": "Day 2: July (Suppress) - Pre",
    }
    multi_day_legend_name_mapping_july_carver = {
        "Day 1, post": "Day 1: July (Baseline) - Post",
        "Day 1, pre": "Day 1: July (Baseline) - Pre",
        "Day 2, post": "Day 2: Carver (Suppress) - Post",
        "Day 2, pre": "Day 2: Carver (Suppress) - Pre",
    }

    def _load_sr_pre_post(
        story, condition, ratings, align_timestamp, fa_key, label_condition
    ):
        dfs = []
        for pos in ["pre", "post"]:
            load_config = {
                "mode": "relatedness",
                "story": story,
                "condition": condition,
                "position": pos,
                "ratings": ratings,
                "align_timestamp": align_timestamp,
            }
            if fa_key is not None:
                load_config["free_association_post_task_start_key"] = {
                    condition: fa_key
                }
            df = func_load(load_config)
            df["story"] = "carver_original"
            df["condition"] = label_condition
            df["position"] = pos
            dfs.append(df)
        return pd.concat(dfs)

    def _load_linger(story, condition, measure_name, label_condition):
        df = load_per_participant_data(
            {
                "story": story,
                "condition": condition,
                "measure_name": measure_name,
            }
        )
        df = df.rename(columns={measure_name: "linger_rating"})
        df["story"] = "carver_original"
        df["condition"] = label_condition
        df["position"] = "post"
        return df

    def _plot_sr(
        data_df: pd.DataFrame,
        legend_name_mapping: dict,
        color_map: dict,
        filepostfix: str,
        legend: bool,
    ):
        func_plot_by_time(
            config={
                "mode": "relatedness",
                "column": "story_relatedness",
                "color": "condition",
                "symbol": "position",
                "step": 30000,
                "align_timestamp": "reading_task_end",
                "min_bin_n": 10,
                "title": None,
                "x_title": "Time from end of story",
                "y_title": "Story relatedness<br>(LLM-rated)",
                "x_title_font_size": 42,
                "y_title_font_size": 42,
                "x_tickfont": dict(size=36),
                "y_tickfont": dict(size=36),
                "x_ticks": "outside",
                "x_skip_first_tick": True,
                "x_tickwidth": 7,
                "y_tickwidth": 7,
                "y_range": STORY_RELATEDNESS_Y_RANGE_SUPPL,
                "y_tickvals": STORY_RELATEDNESS_Y_TICKVALS_SUPPL,
                "y_ticktext": STORY_RELATEDNESS_Y_TICKTEXT_SUPPL,
                "axes_linecolor": AXES_COLOR_SUPPL,
                "axes_tickcolor": AXES_COLOR_SUPPL,
                "axes_linewidth": 7,
                "marker_size": 24,
                "line_width": 7,
                "x_showgrid": False,
                "y_showgrid": False,
                "color_map": color_map,
                "category_orders": multi_day_category_orders,
                "symbol_map": SYMBOL_MAP_POSITION,
                "x_title_font_color": COL1,
                "y_title_font_color": COL1,
                "font_color": COL1,
                "bgcolor": COL_BG,
                # no bootstrap for plots with legends
                "bootstrap": not legend,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                "showlegend": legend,
                "legend": LEGEND_RIGHT_NEXT,
                "legend_name_mapping": legend_name_mapping,
                "show": False,
                "study": STUDY_SUPPL,
                "save": True,
                "scale": 2,
                "width": 1650 if legend else 1200,
                "height": 660,
                "filetype": FILETYPE,
                "filepostfix": filepostfix + "_legend" if legend else filepostfix,
            },
            data_df=data_df,
        )

    def _plot_linger(
        measure_df: pd.DataFrame,
        color_map: dict,
        filepostfix: str,
    ):
        func_plot_numeric_measure(
            config={
                "measure_name": "linger_rating",
                "summary_fun": np.nanmean,
                "title": "",
                "y_range": SUBJECTIVE_LINGERING_Y_RANGE,
                "color_map": color_map,
                "category_orders": multi_day_category_orders,
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
                "bootstrap": True,
                "n_bootstrap": N_BOOTSTRAP,
                "ci": 0.95,
                "save": True,
                "width": 720,
                "height": 660,
                "scale": 2.0,
                "filepostfix": filepostfix,
                "study": STUDY_SUPPL,
                "filetype": FILETYPE,
            },
            data_df=measure_df,
        )

    # --- Pooled (both counterbalance orders) ---
    console.print("\nPooled multi-day SR (post vs pre)", style="yellow")
    sr_dfs = [
        _load_sr_pre_post(
            "carver_original",
            "multi_day_carver_july",
            RATINGS_CARVER_MULTI_DAY,
            "reading_task_end_1",
            "free_association_post_task_start_1",
            "Day 1",
        ),
        _load_sr_pre_post(
            "july_original",
            "multi_day_july_carver",
            RATINGS_JULY_MULTI_DAY,
            "reading_task_end_1",
            "free_association_post_task_start_1",
            "Day 1",
        ),
        _load_sr_pre_post(
            "july_original",
            "multi_day_carver_july",
            RATINGS_JULY_MULTI_DAY,
            "reading_task_end_2",
            "free_association_post_task_start_2",
            "Day 2",
        ),
        _load_sr_pre_post(
            "carver_original",
            "multi_day_july_carver",
            RATINGS_CARVER_MULTI_DAY,
            "reading_task_end_2",
            "free_association_post_task_start_2",
            "Day 2",
        ),
    ]
    _plot_sr(
        data_df=pd.concat(sr_dfs),
        legend_name_mapping=multi_day_legend_name_mapping,
        color_map=multi_day_pooled_color_map,
        filepostfix="suppl_multi_day_pooled",
        legend=True,
    )
    _plot_sr(
        data_df=pd.concat(sr_dfs),
        legend_name_mapping=multi_day_legend_name_mapping,
        color_map=multi_day_pooled_color_map,
        filepostfix="suppl_multi_day_pooled",
        legend=False,
    )

    console.print("\nPooled multi-day linger rating", style="yellow")
    lr_dfs = [
        _load_linger(
            "carver_original",
            "multi_day_carver_july",
            "linger_rating_1",
            "Day 1",
        ),
        _load_linger(
            "july_original",
            "multi_day_july_carver",
            "linger_rating_1",
            "Day 1",
        ),
        _load_linger(
            "july_original",
            "multi_day_carver_july",
            "linger_rating_2",
            "Day 2",
        ),
        _load_linger(
            "carver_original",
            "multi_day_july_carver",
            "linger_rating_2",
            "Day 2",
        ),
    ]
    _plot_linger(
        pd.concat(lr_dfs),
        color_map=multi_day_pooled_color_map,
        filepostfix="suppl_multi_day_linger_pooled",
    )

    # --- carver_july only ---
    console.print("\ncarver_july SR (post vs pre)", style="yellow")
    sr_dfs_cj = [
        _load_sr_pre_post(
            "carver_original",
            "multi_day_carver_july",
            RATINGS_CARVER_MULTI_DAY,
            "reading_task_end_1",
            "free_association_post_task_start_1",
            "Day 1",
        ),
        _load_sr_pre_post(
            "july_original",
            "multi_day_carver_july",
            RATINGS_JULY_MULTI_DAY,
            "reading_task_end_2",
            "free_association_post_task_start_2",
            "Day 2",
        ),
    ]
    _plot_sr(
        pd.concat(sr_dfs_cj),
        legend_name_mapping=multi_day_legend_name_mapping_carver_july,
        color_map=multi_day_carver_july_color_map,
        filepostfix="suppl_multi_day_carver_july",
        legend=True,
    )
    _plot_sr(
        data_df=pd.concat(sr_dfs_cj),
        legend_name_mapping=multi_day_legend_name_mapping_carver_july,
        color_map=multi_day_carver_july_color_map,
        filepostfix="suppl_multi_day_carver_july",
        legend=False,
    )

    console.print("\ncarver_july linger rating", style="yellow")
    lr_dfs_cj = [
        _load_linger(
            "carver_original",
            "multi_day_carver_july",
            "linger_rating_1",
            "Day 1",
        ),
        _load_linger(
            "july_original",
            "multi_day_carver_july",
            "linger_rating_2",
            "Day 2",
        ),
    ]
    _plot_linger(
        pd.concat(lr_dfs_cj),
        color_map=multi_day_carver_july_color_map,
        filepostfix="suppl_multi_day_linger_carver_july",
    )

    # --- july_carver only ---
    console.print("\njuly_carver SR (post vs pre)", style="yellow")
    sr_dfs_jc = [
        _load_sr_pre_post(
            "july_original",
            "multi_day_july_carver",
            RATINGS_JULY_MULTI_DAY,
            "reading_task_end_1",
            "free_association_post_task_start_1",
            "Day 1",
        ),
        _load_sr_pre_post(
            "carver_original",
            "multi_day_july_carver",
            RATINGS_CARVER_MULTI_DAY,
            "reading_task_end_2",
            "free_association_post_task_start_2",
            "Day 2",
        ),
    ]
    _plot_sr(
        pd.concat(sr_dfs_jc),
        legend_name_mapping=multi_day_legend_name_mapping_july_carver,
        color_map=multi_day_july_carver_color_map,
        filepostfix="suppl_multi_day_july_carver",
        legend=True,
    )
    _plot_sr(
        pd.concat(sr_dfs_jc),
        legend_name_mapping=multi_day_legend_name_mapping_july_carver,
        color_map=multi_day_july_carver_color_map,
        filepostfix="suppl_multi_day_july_carver",
        legend=False,
    )

    console.print("\njuly_carver linger rating", style="yellow")
    lr_dfs_jc = [
        _load_linger(
            "july_original",
            "multi_day_july_carver",
            "linger_rating_1",
            "Day 1",
        ),
        _load_linger(
            "carver_original",
            "multi_day_july_carver",
            "linger_rating_2",
            "Day 2",
        ),
    ]
    _plot_linger(
        measure_df=pd.concat(lr_dfs_jc),
        color_map=multi_day_july_carver_color_map,
        filepostfix="suppl_multi_day_linger_july_carver",
    )


def suppl_linger_multi_day_stats():
    console.print("\nSUPPL: Linger multi-day", style="red bold")

    # show post pre test
    console.print("\n|a1| story-relatedness stats", style="blue")
    cj_sr1, cj_sr2, cj_sr3, cj_sr4, cj_diff_sr2_sr1, cj_diff_sr4_sr3 = (
        load_sr_multi_day_all_positions("multi_day_carver_july")
    )
    jc_sr1, jc_sr2, jc_sr3, jc_sr4, jc_diff_sr2_sr1, jc_diff_sr4_sr3 = (
        load_sr_multi_day_all_positions("multi_day_july_carver")
    )
    sr1: pd.Series = pd.concat([cj_sr1, jc_sr1])  # type: ignore
    sr2: pd.Series = pd.concat([cj_sr2, jc_sr2])  # type: ignore
    sr3: pd.Series = pd.concat([cj_sr3, jc_sr3])  # type: ignore
    sr4: pd.Series = pd.concat([cj_sr4, jc_sr4])  # type: ignore
    test_two(
        {
            "name1": "Post",
            "name2": "Pre",
            "superscript1": "Day 1",
            "superscript2": "Day 1",
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data1_sr=sr2,
        data2_sr=sr1,
    )

    test_two(
        {
            "name1": "Post",
            "name2": "Pre",
            "superscript1": "Day 2",
            "superscript2": "Day 2",
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data1_sr=sr4,
        data2_sr=sr3,
    )

    # [a1]  (sr2 - sr1) vs (sr4 - sr3)
    console.print("\n|a1| main replication", style="blue")
    console.print(
        "\n|a1| behavioral elimination: (sr2 - sr1) vs (sr4 - sr3)", style="yellow"
    )

    diff_sr2_sr1: pd.Series = pd.concat([cj_diff_sr2_sr1, jc_diff_sr2_sr1])  # type: ignore
    diff_sr4_sr3: pd.Series = pd.concat([cj_diff_sr4_sr3, jc_diff_sr4_sr3])  # type: ignore
    test_two(
        {
            "name1": "Post - Pre",
            "name2": "Post - Pre",
            "superscript1": "Day 1",
            "superscript2": "Day 2",
            "measure": "story_relatedness",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data1_sr=diff_sr2_sr1,
        data2_sr=diff_sr4_sr3,
    )

    # [a1] linger_rating_1 vs linger_rating_2
    console.print(
        "\n|a1| subjective non-elimination: linger_rating_1 vs linger_rating_2",
        style="yellow",
    )

    test_two(
        {
            "name1": "Day 2",
            "name2": "Day 1",
            "measure": "linger_rating",
            "config1": {
                "combined_configs": [
                    {
                        "story": "july_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "carver_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
                "measure": "linger_rating_2",
            },
            "config2": {
                "combined_configs": [
                    {
                        "story": "carver_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "july_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
                "measure": "linger_rating_1",
            },
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        },
    )

    # to check suppress v neutralcue, suppress_button_press vs button_press
    test_two(
        {
            "name1": "Suppress No Button Press",
            "name2": "Baseline",
            "story": "carver_original",
            "config1": {"condition": "suppress"},
            "config2": {"condition": "neutralcue2"},
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        },
    )

    # to check suppress v neutralcue, suppress_button_press vs button_press
    test_two(
        {
            "name1": "Suppress",
            "name2": "Intact",
            "story": "carver_original",
            "config1": {"condition": "button_press_suppress"},
            "config2": {"condition": "button_press"},
            "measure": "linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
        },
    )

    # day 2 vs word_scrambled
    console.print(
        "\n Posthoc check: linger_rating_2 vs word_scrambled",
        style="yellow",
    )

    test_two(
        {
            "name1": "Day 2",
            "name2": "Scrambled",
            "measure": "linger_rating",
            "config1": {
                "combined_configs": [
                    {
                        "story": "july_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "carver_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
                "measure": "linger_rating_2",
            },
            "config2": {
                "story": "carver_original",
                "condition": "word_scrambled",
                "measure": "linger_rating",
            },
            "test_type": "mwu",
            "measure_letter": "L",
            "threshold": P_DISPLAY_THRESHOLD,
        },
    )

    console.print("\n\n|a2| order effects", style="blue")

    # [a2] differences between carver-july and july-carver for |a1|
    console.print(
        "\n|a2| differences between carver-july and july-carver for |a1| sr",
        style="yellow",
    )

    cj_diff_day1_day2 = cj_diff_sr4_sr3 - cj_diff_sr2_sr1
    cj_diff_day1_day2.name = "diff_sr_day2_day1"
    jc_diff_day1_day2 = jc_diff_sr4_sr3 - jc_diff_sr2_sr1
    jc_diff_day1_day2.name = "diff_sr_day2_day1"

    test_two(
        {
            "name1": "Post - Pre; Day 2 - Day 1",
            "name2": "Post - Pre; Day 2 - Day 1",
            "superscript1": "Carver July",
            "superscript2": "July Carver",
            "measure": "diff_sr_day2_day1",
            "test_type": "mwu",
            "measure_letter": "M",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data1_sr=cj_diff_day1_day2,
        data2_sr=jc_diff_day1_day2,
    )

    # [a2] differences between carver-july and july-carver for |a1| lingering
    console.print(
        "\n|a2| differences between carver-july and july-carver for |a1| linger-rating",
        style="yellow",
    )
    linger_rating_cj_1 = load_per_participant_data(
        {
            "story": "carver_original",
            "condition": "multi_day_carver_july",
            "measure_name": "linger_rating_1",
        }
    ).loc[:, "linger_rating_1"]
    linger_rating_cj_2 = load_per_participant_data(
        {
            "story": "july_original",
            "condition": "multi_day_carver_july",
            "measure_name": "linger_rating_2",
        }
    ).loc[:, "linger_rating_2"]
    linger_rating_jc_1 = load_per_participant_data(
        {
            "story": "carver_original",
            "condition": "multi_day_july_carver",
            "measure_name": "linger_rating_1",
        }
    ).loc[:, "linger_rating_1"]
    linger_rating_jc_2 = load_per_participant_data(
        {
            "story": "july_original",
            "condition": "multi_day_july_carver",
            "measure_name": "linger_rating_2",
        }
    ).loc[:, "linger_rating_2"]
    diff_linger_rating_cj = linger_rating_cj_2 - linger_rating_cj_1
    diff_linger_rating_cj.name = "diff_linger_rating"
    diff_linger_rating_jc = linger_rating_jc_2 - linger_rating_jc_1
    diff_linger_rating_jc.name = "diff_linger_rating"

    test_two(
        {
            "name1": "Day 2 - Day 1",
            "name2": "Day 2 - Day 1",
            "superscript1": "Carver July",
            "superscript2": "July Carver",
            "measure": "diff_linger_rating",
            "test_type": "mwu",
            "threshold": P_DISPLAY_THRESHOLD,
            "measure_letter": "L",
        },
        data1_sr=diff_linger_rating_cj,
        data2_sr=diff_linger_rating_jc,
    )

    console.print(
        "\n|a2.1| differences between day 2 and day 1 for carver-july only",
        style="yellow",
    )

    test_two(
        {
            "name1": "linger_rating_1",
            "name2": "linger_rating_2",
            "measure": "linger_rating",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data1_sr=linger_rating_cj_1,
        data2_sr=linger_rating_cj_2,
    )

    console.print(
        "\n|a2.2| differences between day 2 and day 1 for july-carver only",
        style="yellow",
    )

    test_two(
        {
            "name1": "linger_rating_1",
            "name2": "linger_rating_2",
            "measure": "linger_rating",
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data1_sr=linger_rating_jc_1,
        data2_sr=linger_rating_jc_2,
    )

    console.print("\n\n|b1| linger24h_rating", style="blue")

    console.print(
        "\n|b1| linger24h_rating vs linger_rating_1",
        style="yellow",
    )
    correlate_two(
        {
            "x_measure": "linger_24h_rating_2",
            "config1": {
                "combined_configs": [
                    {
                        "story": "july_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "carver_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
            },
            "y_measure": "linger_rating_1",
            "config2": {
                "combined_configs": [
                    {
                        "story": "carver_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "july_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
            },
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print(
        "\n|b1| linger24h_rating vs (sr2 - sr1 <30s)",
        style="yellow",
    )
    sr1_df = load_per_participant_data(
        {
            "combined_configs": [
                {
                    "story": "carver_original",
                    "condition": "multi_day_carver_july",
                    "ratings": RATINGS_CARVER_MULTI_DAY,
                },
                {
                    "story": "july_original",
                    "condition": "multi_day_july_carver",
                    "ratings": RATINGS_JULY_MULTI_DAY,
                },
            ],
            "position": "pre",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )
    sr2_df = load_per_participant_data(
        {
            "combined_configs": [
                {
                    "story": "carver_original",
                    "condition": "multi_day_carver_july",
                    "ratings": RATINGS_CARVER_MULTI_DAY,
                },
                {
                    "story": "july_original",
                    "condition": "multi_day_july_carver",
                    "ratings": RATINGS_JULY_MULTI_DAY,
                },
            ],
            "position": "post",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )

    sr_diff_sr2_sr1 = sr2_df - sr1_df  # type: ignore

    correlate_two(
        {
            "x_measure": "linger_24h_rating_2",
            "config1": {
                "combined_configs": [
                    {
                        "story": "july_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "carver_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
            },
            "y_measure": "story_relatedness",
            "threshold": P_DISPLAY_THRESHOLD,
        },
        data2_df=sr_diff_sr2_sr1,
    )

    console.print("\n\n|b2| rii", style="blue")

    console.print(
        "\n|b2| rii vs linger_rating_1",
        style="yellow",
    )
    for rii_measure in [
        "rii_total_prop_2",
        "rii_character_prop_2",
        "rii_event_prop_2",
        "rii_universe_prop_2",
        "rii_backstory_prop_2",
    ]:
        correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "linger_rating_1",
                # questionnaire data summary combines both days, can only load one
                "combined_configs": [
                    {
                        "story": "july_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "carver_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
                "threshold": P_DISPLAY_THRESHOLD,
            },
        )

    console.print(
        "\n|b2| rii vs (sr2 - sr1 <30s)",
        style="yellow",
    )
    sr1_df = load_per_participant_data(
        {
            "combined_configs": [
                {
                    "story": "carver_original",
                    "condition": "multi_day_carver_july",
                    "ratings": RATINGS_CARVER_MULTI_DAY,
                },
                {
                    "story": "july_original",
                    "condition": "multi_day_july_carver",
                    "ratings": RATINGS_JULY_MULTI_DAY,
                },
            ],
            "position": "pre",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )
    sr2_df = load_per_participant_data(
        {
            "combined_configs": [
                {
                    "story": "carver_original",
                    "condition": "multi_day_carver_july",
                    "ratings": RATINGS_CARVER_MULTI_DAY,
                },
                {
                    "story": "july_original",
                    "condition": "multi_day_july_carver",
                    "ratings": RATINGS_JULY_MULTI_DAY,
                },
            ],
            "position": "post",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )
    sr_diff_sr2_sr1 = sr2_df - sr1_df
    for rii_measure in [
        "rii_total_prop_2",
        "rii_character_prop_2",
        "rii_event_prop_2",
        "rii_universe_prop_2",
        "rii_backstory_prop_2",
    ]:
        correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "story_relatedness",
                "config1": {
                    "combined_configs": [
                        {
                            "story": "july_original",
                            "condition": "multi_day_carver_july",
                        },
                        {
                            "story": "carver_original",
                            "condition": "multi_day_july_carver",
                        },
                    ],
                },
                "threshold": P_DISPLAY_THRESHOLD,
            },
            data2_df=sr_diff_sr2_sr1,
        )

    console.print(
        "\n|b2| rii vs linger_24h_rating_2",
        style="yellow",
    )
    for rii_measure in [
        "rii_total_prop_2",
        "rii_character_prop_2",
        "rii_event_prop_2",
        "rii_universe_prop_2",
        "rii_backstory_prop_2",
    ]:
        correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "linger_24h_rating_2",
                # questionnaire data summary combines both days, can only load one
                "combined_configs": [
                    {
                        "story": "july_original",
                        "condition": "multi_day_carver_july",
                    },
                    {
                        "story": "carver_original",
                        "condition": "multi_day_july_carver",
                    },
                ],
                "threshold": P_DISPLAY_THRESHOLD,
            },
        )


def suppl_prereg_linger_multi_day():
    console.print("\nSUPPL: Linger multi-day (preregistration)", style="red bold")

    console.print("\n\n|c1| long-term story-relatedness?", style="blue")

    console.print(
        "\n|c1| SR1 (story1) vs SR3 (to story1)",
        style="yellow",
    )

    test_two(
        {
            "name1": "Day 1; Pre; SR to Story 1",
            "name2": "Day 2; Pre; SR to Story 1",
            "measure": "story_relatedness",
            "config1": {
                "combined_configs": [
                    {
                        "story": "carver_original",
                        "condition": "multi_day_carver_july",
                        "position": "pre",
                        "ratings": RATINGS_CARVER_MULTI_DAY,
                    },
                    {
                        "story": "july_original",
                        "condition": "multi_day_july_carver",
                        "position": "pre",
                        "ratings": RATINGS_JULY_MULTI_DAY,
                    },
                ],
            },
            "config2": {
                "combined_configs": [
                    {
                        "story": "july_original",
                        "condition": "multi_day_carver_july",
                        "position": "pre",
                        "ratings": RATINGS_CARVER_MULTI_DAY,
                    },
                    {
                        "story": "carver_original",
                        "condition": "multi_day_july_carver",
                        "position": "pre",
                        "ratings": RATINGS_JULY_MULTI_DAY,
                    },
                ],
            },
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        },
    )


# plot all rii correlations in table
def suppl_stats_rii_correlations():
    console.print(
        "\n\nSupplement: Stats: RII correlations with dependent variables",
        style="red bold",
    )

    rii_measures = {
        "rii_total_prop_2": "Overall RII Score",
        "rii_character_prop_2": "Character",
        "rii_event_prop_2": "Event",
        "rii_universe_prop_2": "Universe",
        "rii_backstory_prop_2": "Backstory",
    }

    combined_configs_questionnaire = [
        {
            "story": "july_original",
            "condition": "multi_day_carver_july",
        },
        {
            "story": "carver_original",
            "condition": "multi_day_july_carver",
        },
    ]

    combined_configs_ratings_day1 = [
        {
            "story": "carver_original",
            "condition": "multi_day_carver_july",
            "ratings": RATINGS_CARVER_MULTI_DAY,
        },
        {
            "story": "july_original",
            "condition": "multi_day_july_carver",
            "ratings": RATINGS_JULY_MULTI_DAY,
        },
    ]

    combined_configs_ratings_day2 = [
        {
            "story": "july_original",
            "condition": "multi_day_carver_july",
            "ratings": RATINGS_JULY_MULTI_DAY,
        },
        {
            "story": "carver_original",
            "condition": "multi_day_july_carver",
            "ratings": RATINGS_CARVER_MULTI_DAY,
        },
    ]

    # Load SR pre/post and compute SR2 - SR1.
    sr1_df = load_per_participant_data(
        {
            "combined_configs": combined_configs_ratings_day1,
            "position": "pre",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )

    sr2_df = load_per_participant_data(
        {
            "combined_configs": combined_configs_ratings_day1,
            "position": "post",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )

    sr_diff_sr2_sr1 = sr2_df - sr1_df

    # Load SR pre/post and compute SR4 - SR3.
    sr3_df = load_per_participant_data(
        {
            "combined_configs": combined_configs_ratings_day2,
            "position": "pre",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )
    sr4_df = load_per_participant_data(
        {
            "combined_configs": combined_configs_ratings_day2,
            "position": "post",
            "measure": "story_relatedness",
            "exclude": ("gt", "timestamp", 30000),
        }
    )
    sr_diff_sr4_sr3 = sr4_df - sr3_df

    results_dict = {
        "linger_rating_1": {},
        "linger_rating_2": {},
        "linger_24h_rating_2": {},
        "sr2_minus_sr1_first_30s": {},
        "sr4_minus_sr3_first_30s": {},
    }

    for rii_measure in rii_measures:
        results_dict["linger_rating_1"][rii_measure] = correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "linger_rating_1",
                "combined_configs": combined_configs_questionnaire,
                "threshold": P_DISPLAY_THRESHOLD,
                "verbose": False,
            },
        )

        results_dict["sr2_minus_sr1_first_30s"][rii_measure] = correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "story_relatedness",
                "config1": {
                    "combined_configs": combined_configs_questionnaire,
                },
                "threshold": P_DISPLAY_THRESHOLD,
                "verbose": False,
            },
            data2_df=sr_diff_sr2_sr1,
        )

        results_dict["linger_24h_rating_2"][rii_measure] = correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "linger_24h_rating_2",
                "combined_configs": combined_configs_questionnaire,
                "threshold": P_DISPLAY_THRESHOLD,
                "verbose": False,
            },
        )
        results_dict["sr4_minus_sr3_first_30s"][rii_measure] = correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "story_relatedness",
                "config1": {
                    "combined_configs": combined_configs_questionnaire,
                },
                "threshold": P_DISPLAY_THRESHOLD,
                "verbose": False,
            },
            data2_df=sr_diff_sr4_sr3,
        )
        results_dict["linger_rating_2"][rii_measure] = correlate_two(
            {
                "x_measure": rii_measure,
                "y_measure": "linger_rating_2",
                "combined_configs": combined_configs_questionnaire,
                "threshold": P_DISPLAY_THRESHOLD,
                "verbose": False,
            },
        )

    console.print("\nTable: RII correlations", style="yellow")

    print("    \\begin{tabular}{l | ccccc}")
    print(
        "        "
        " & \\makecell{Increase in Story Relatedness\\\\Day 1}"
        "& \\makecell{Immediate Lingering\\\\Day 1}"
        " & \\makecell{Extended\\\\Lingering}"
        " & \\makecell{Increase in Story Relatedness\\\\Day 2}"
        "& \\makecell{Immediate Lingering\\\\Day 2}\\\\"
    )
    print("        \\hline")

    for rii_measure, rii_name in rii_measures.items():
        print("        \\hline")
        print(f"        \\makecell{{{rii_name}}}", end="")

        for dependent_variable in [
            "sr2_minus_sr1_first_30s",
            "linger_rating_1",
            "linger_24h_rating_2",
            "sr4_minus_sr3_first_30s",
            "linger_rating_2",
        ]:
            result = results_dict[dependent_variable][rii_measure]

            # r2 = float(result.rsquared)
            r = result.rsquared**0.5
            if result.params[1] < 0:
                r = -r
            pvalue = float(result.pvalues[1])

            threshold = P_DISPLAY_THRESHOLD
            if pvalue < (threshold - 0.2 * threshold):
                pstring = f"p < {threshold}".replace("0.", ".")
            elif pvalue < 0.09:
                pstring = f"p = {cut_small_value(pvalue)}"
            else:
                pstring = f"p = {str(round(pvalue, 2))[1:]}"

            print(
                f" &\n        \\makecell{{$r = {r:.2f}$\\\\${pstring}$}}",
                end="",
            )

        print("\\\\")

    print("    \\end{tabular}")

    return


def suppl_linger_multi_day_submission_time():
    console.print("\nSUPPL: Linger multi-day submission time", style="red bold")

    multi_day_pooled_color_map = {
        "Day 1": COL_NEUTRALCUE2,
        "Day 2": "#09A000",
    }
    multi_day_category_orders = {
        "condition": ["Day 1", "Day 2"],
    }
    multi_day_legend_name_mapping = {
        "Day 1, post": "Day 1 (Baseline) - Post",
        "Day 1, pre": "Day 1 (Baseline) - Pre",
        "Day 2, post": "Day 2 (Suppress) - Post",
        "Day 2, pre": "Day 2 (Suppress) - Pre",
    }

    def _load_pooled(story: str, condition: str, position: str, day_label: str):
        df = func_load(
            {
                "mode": "word_time",
                "story": story,
                "condition": condition,
                "position": position,
                "align_timestamp": None,
            }
        )
        df = df.copy()
        df["story"] = "pooled"
        df["condition"] = day_label
        df["position"] = position
        return df

    dfs = [
        _load_pooled("carver_original", "multi_day_carver_july", "pre", "Day 1"),
        _load_pooled("carver_original", "multi_day_carver_july", "post", "Day 1"),
        _load_pooled("july_original", "multi_day_july_carver", "pre", "Day 1"),
        _load_pooled("july_original", "multi_day_july_carver", "post", "Day 1"),
        _load_pooled("july_original", "multi_day_carver_july", "pre", "Day 2"),
        _load_pooled("july_original", "multi_day_carver_july", "post", "Day 2"),
        _load_pooled("carver_original", "multi_day_july_carver", "pre", "Day 2"),
        _load_pooled("carver_original", "multi_day_july_carver", "post", "Day 2"),
    ]
    combined_df = pd.concat(dfs, axis=0)
    combined_df = combined_df.copy()
    combined_df["log_word_time"] = np.log1p(combined_df["word_time"].astype(float))
    combined_df["log_key_onset"] = np.log1p(combined_df["key_onset"].astype(float))

    base_plot_config = {
        "mode": "word_time",
        "step": 30000,
        "align_timestamp": None,
        "min_bin_n": 10,
        "title": None,
        "x_title": "Time from start of free association",
        "x_title_font_size": 42,
        "y_title_font_size": 42,
        "x_rangemode": "tozero",
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
        "axes_linecolor": AXES_COLOR_SUPPL,
        "axes_tickcolor": AXES_COLOR_SUPPL,
        "x_title_font_color": COL1,
        "y_title_font_color": COL1,
        "font_color": COL1,
        "bgcolor": COL_BG,
        "bootstrap": True,
        "n_bootstrap": N_BOOTSTRAP,
        "ci": 0.95,
        "showlegend": True,
        "legend": LEGEND_TOP_LEFT_MEDIUM,
        "show": False,
        "color": "condition",
        "symbol": "position",
        "symbol_map": SYMBOL_MAP_POSITION,
        "category_orders": multi_day_category_orders,
        "color_map": multi_day_pooled_color_map,
        "legend_name_mapping": multi_day_legend_name_mapping,
        "study": STUDY_SUPPL,
        "save": True,
        "scale": 2,
        "width": 990,
        "height": 660,
        "filetype": FILETYPE,
    }

    console.print("\n > Multi-day word time (pre vs post)", style="yellow")
    func_plot_by_time(
        config={
            **base_plot_config,
            "column": "word_time",
            "y_title": "Submission time (ms)",
            "y_range": [2100, 5100],
            "filepostfix": "suppl_multi_day_word_time_pre_post_pooled",
            "width": 1200,
        },
        data_df=combined_df,
    )

    # console.print("\n > Multi-day word time (post)", style="yellow")
    # func_plot_by_time(
    #     config={
    #         **base_plot_config,
    #         "column": "word_time",
    #         "y_title": "Submission time (ms)",
    #         "y_range": WORD_TIME_Y_RANGE,
    #         "filepostfix": "suppl_multi_day_word_time_post_pooled",
    #     },
    #     data_df=combined_df.loc[combined_df["position"] == "post"],
    # )

    # console.print("\n > Multi-day key onset (pre vs post)", style="yellow")
    # func_plot_by_time(
    #     config={
    #         **base_plot_config,
    #         "column": "key_onset",
    #         "y_title": "Key-onset time (ms)",
    #         "y_range": None,
    #         "filepostfix": "suppl_multi_day_key_onset_pre_post_pooled",
    #     },
    #     data_df=combined_df,
    # )

    # console.print("\n > Multi-day key onset (post)", style="yellow")
    # func_plot_by_time(
    #     config={
    #         **base_plot_config,
    #         "column": "key_onset",
    #         "y_title": "Key-onset time (ms)",
    #         "y_range": None,
    #         "filepostfix": "suppl_multi_day_key_onset_post_pooled",
    #     },
    #     data_df=combined_df.loc[combined_df["position"] == "post"],
    # )

    # console.print(
    #     "\n > Multi-day log submission time (pre vs post), PNG", style="yellow"
    # )
    # func_plot_by_time(
    #     config={
    #         **base_plot_config,
    #         "column": "log_word_time",
    #         "y_title": "Log submission time<br>(ln(1 + ms))",
    #         "y_range": None,
    #         "filetype": "png",
    #         "filepostfix": "suppl_multi_day_word_time_pre_post_pooled_log",
    #     },
    #     data_df=combined_df,
    # )

    # console.print("\n > Multi-day log submission time (post), PNG", style="yellow")
    # func_plot_by_time(
    #     config={
    #         **base_plot_config,
    #         "column": "log_word_time",
    #         "y_title": "Log submission time<br>(ln(1 + ms))",
    #         "y_range": None,
    #         "filetype": "png",
    #         "filepostfix": "suppl_multi_day_word_time_post_pooled_log",
    #     },
    #     data_df=combined_df.loc[combined_df["position"] == "post"],
    # )

    # console.print("\n > Multi-day log key onset (pre vs post), PNG", style="yellow")
    # func_plot_by_time(
    #     config={
    #         **base_plot_config,
    #         "column": "log_key_onset",
    #         "y_title": "Log key-onset time<br>(ln(1 + ms))",
    #         "y_range": None,
    #         "filetype": "png",
    #         "filepostfix": "suppl_multi_day_key_onset_pre_post_pooled_log",
    #     },
    #     data_df=combined_df,
    # )

    # console.print("\n > Multi-day log key onset (post), PNG", style="yellow")
    # func_plot_by_time(
    #     config={
    #         **base_plot_config,
    #         "column": "log_key_onset",
    #         "y_title": "Log key-onset time<br>(ln(1 + ms))",
    #         "y_range": None,
    #         "filetype": "png",
    #         "filepostfix": "suppl_multi_day_key_onset_post_pooled_log",
    #     },
    #     data_df=combined_df.loc[combined_df["position"] == "post"],
    # )


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


def suppl_info_story_end_separated_continued():
    console.print(
        "\nSupplemental Methods: New Story End: Separated, Continued", style="red bold"
    )

    console.print("\nManipulation believed: ", style="yellow")
    # they all answered yes.
    plot_distribution(
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
            "measure": "manipulation_believed",
            "auto_exclude": True,
            # plot config
            # "title": "While reading Part 2 I was<br>trying to relate it to Part 1.",
            "title": "",
            "y_range": None,
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
            "x_title": "Answer",
            "y_title": "Believed manipulation",
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
            "filepostfix": "suppl_mb",
            "study": STUDY,
            "filetype": FILETYPE,
        }
    )


def suppl_info_effect_size_last_30s():
    console.print("\nSupplemental Methods: Effect size last 30s", style="red bold")

    console.print("\n > Neutralcue2 (150s-180s)", style="yellow")
    test_two(
        {
            "name1": "Post (150s-180s)",
            "name2": "Pre (150s-180s)",
            "story": "carver_original",
            "condition": "neutralcue2",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("lte", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "measure": "story_relatedness",
            "ratings": RATINGS_CARVER,
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )

    console.print("\n > Neutralcue (270s-300s)", style="yellow")
    test_two(
        {
            "name1": "Post (270s-300s)",
            "name2": "Pre (270s-300s)",
            "story": "carver_original",
            "condition": "neutralcue",
            "config1": {"position": "post"},
            "config2": {"position": "pre"},
            "exclude": [("lte", "timestamp", 270000), ("gte", "timestamp", 300000)],
            # "exclude": [("lte", "timestamp", 150000), ("gte", "timestamp", 180000)],
            "measure": "story_relatedness",
            "ratings": RATINGS_CARVER,
            "test_type": "wilcoxon",
            "threshold": P_DISPLAY_THRESHOLD,
        }
    )


def suppl_plot_correlation_sr_st():
    console.print(
        "\nSUPPL:Corr story relatedness and story thoughts",
        style="red bold",
    )

    plot_scatter_measures(
        {
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
            # on what measure
            "x_measure": "mean_sr_post",
            "y_measure": "total_double_press_count_post",
            # plot config
            "color": "condition",
            # "x_range": [0.9, 7.09],
            "y_range": None,
            "x_title": "Story relatedness",
            "y_title": "Story thoughts",
            "color_sequence": ["#F74639"],
            "x_showgrid": False,
            "y_showgrid": False,
            # "x_tickvals": [1, 2, 3, 4, 5, 6, 7],
            # "x_ticktext": ["1", "2", "3", "4", "5", "6", "7"],
            "trendline_color": COL1,
            "tickcolor": COL1,
            "axes_linecolor": COL1,
            "axes_tickcolor": COL1,
            "axes_linewidth": 7,
            "x_tickwidth": 7,
            "y_tickwidth": 7,
            "y_tickfont": dict(color=COL1, size=36),
            "x_tickfont": dict(color=COL1, size=36),
            "x_title_font_color": COL1,
            "y_title_font_color": COL1,
            "font_color": COL1,
            "bgcolor": COL_BG,
            "showlegend": False,
            # bootstrap
            "n_bootstrap": N_BOOTSTRAP,
            # save config
            "save": True,
            "width": 660,
            "height": 660,
            "scale": 2.0,
            "filepostfix": "suppl_sr_st",
            "study": STUDY_SUPPL,
            "filetype": FILETYPE_SUPPL,
            "regression": True,
            "regression_on_plot": True,
        }
    )


def main():
    # Preview intro
    stats_preview_intro()

    # Results
    console.print("\n\nResults", style="red bold")
    #    Narrative content persists in mind, influencing thought and behavior.
    stats_experiment_1_button_press()
    plots_fig_1_paradigm_results1()

    #    Narrative persistence was not abolished by volitional suppression.
    stats_experiment_2_button_press_suppress()
    plots_fig_2_results2()

    #    Persistence was invariant to the content of post-reading tasks
    stats_experiment_3_interference()
    plots_fig_3_results3()

    #    Narrative content starts to 'decay' depending on situational understanding
    stats_experiment_4_continued_separated()
    plots_fig_4_results()

    # Integrating unrelated material prolonged mental persistence
    console.print("\n\nMethods", style="red bold")
    suppl_methods_experiment_overview()
    suppl_methods_procedure_numbers()
    suppl_demographic_stats()
    suppl_methods_stats_words_rated()
    submission_demographic_exclusion_stats()

    console.print("\n\nSupplementary Information", style="red bold")
    # 5 Most common associates occurring during free association
    suppl_methods_stats_words_generated()

    # 6 Rate of decrease of story and food thoughts
    suppl_thought_entries_mlm()

    # 7 Suppression: Preserved correlation between story thoughts and
    #   story-relatedness under
    suppl_plots_sr_st_suppress()

    # 8 Self-reports of volition during the persistence of mental content
    suppl_plots_stats_volition()

    # 9 Restricting analyses to participants reporting unintentional persistence
    suppl_stats_unintentional()

    # 10 Self-reports of free association strategies
    suppl_plots_stats_wcg_strategy()

    # 11 Relationship between transportation and measures of persistence
    suppl_transp_and_pmc()

    # 12 Interference task performance
    suppl_interference_task_performance()

    # 13 Weak evidence for recency effect of late vs early story elements
    suppl_stats_persistence_recency_correlations()
    suppl_plots_persistence_recency_correlations()

    # 14 Inconsistent evidence for disruption recency effect
    suppl_stats_persistence_recency_correlations_difference()
    suppl_plots_recency_difference_across_conditions()

    # extra recency analyses not included in manuscript
    # suppl_plots_persistence_recency_correlations_difference()
    # suppl_intuitive_meaning_match_scores()
    # suppl_stats_persistence_without_recency()
    # suppl_plots_persistence_without_recency()
    # suppl_plots_match_score_by_sections()

    # 15 Integration and separation of new story in New Story condition
    suppl_stats_plots_new_story_separated_integrated()

    # 16 Results: Suppress No Button Press condition
    suppl_plots_stats_suppress_no_button_press()

    # 17 Results: Pause and End Cue + Pause
    suppl_plots_stats_pause_and_end_pause_cue()

    # 18 Results: New Story Alone condition
    suppl_plots_stats_lightbulb()

    # 19 Results: Multi Day condition
    suppl_linger_multi_day_stats()
    suppl_linger_multi_day_plots()
    suppl_stats_rii_correlations()
    suppl_linger_multi_day_submission_time()

    # 20 Persistence of new story after original story
    suppl_plots_stats_lightbulb_after_carver()

    # 21 Submission time of associates
    suppl_stats_submission_time()
    suppl_plots_submission_time()

    # 22 Data curves with number of associates as x-axis
    suppl_plots_by_words()

    # 23 Data curves with excluded time bins
    suppl_plots_all_bins()

    # 24 Preregistered analyses
    suppl_prereg_table_interference()
    suppl_prereg_plot_interference()
    # 24.1 Intact & Suppress condition
    suppl_prereg_volition()
    # 24.3 Baseline condition
    suppl_prereg_baseline()
    # 24.4 ToM condition
    suppl_prereg_tom()
    # 24.5 Geometry condition
    suppl_prereg_geometry()
    # 24.7 New Story condition
    suppl_prereg_new_story()
    # 24.9 Continued, Separated, and Delayed Continued condition
    suppl_prereg_continued_separated_delayed_continued()
    # 24.10 Multi Day Condition
    suppl_prereg_linger_multi_day()

    # Explorations & information not included in manuscript or supplement.
    suppl_choice_baseline_fig_3_and_distribution_first_bin_aligned()
    suppl_info_story_end_separated_continued()
    suppl_info_effect_size_last_30s()
    suppl_plot_correlation_sr_st()

    console.print("\nDone", style="green bold")


if __name__ == "__main__":
    main()
