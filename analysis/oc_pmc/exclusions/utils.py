import os
from typing import Dict, List, Optional, Union

import pandas as pd
import plotly.express as px

from oc_pmc import console, get_logger
from oc_pmc.load import load_screen_recording_exclusions
from oc_pmc.utils import check_make_dirs

log = get_logger(__name__)

BASEDIR = "outputs/plots/exclusions"


def plot_exclusion_plots(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: float,
    colname: str,
    title: str,
    nbins: Optional[int] = None,
    x_range: Optional[List] = None,
    skip_to_compare: bool = False,
) -> None:
    condition_name = config.get("to_exclude_name", "to_exclude")

    plot_path = os.path.join(
        BASEDIR, condition_name, f"{colname.replace('/', '-').replace(' ', '_')}.png"
    )
    check_make_dirs(plot_path)

    to_exclude["condition"] = condition_name
    data_df = to_exclude
    if not skip_to_compare:
        assert to_compare is not None, (
            f"to_compare must be provided if {skip_to_compare=}"
        )
        to_compare["condition"] = config.get("to_compare_name", "to_compare")
        data_df = pd.concat([to_exclude, to_compare])

    if x_range is not None and any(data_df[colname] > x_range[1]):
        log.info(f"Cutting off data > {x_range[1]}")
        data_df = data_df[data_df[colname] <= x_range[1]]

    plot = px.histogram(
        data_df,
        x=colname,
        nbins=nbins,
        title=title,
        range_x=x_range,
        color="condition",
        barmode="overlay",
    ).add_vline(x=threshold)
    plot.write_image(plot_path)
    print("---")


# I know that at this point all of these functions could have been the
# same, clean function. But going back and refactoring may
# break something unexpected, so I'll keep the mess.
def exclusion_spr_char_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: float,
    interference: bool = False,
    colname: str = "spr/char",
) -> pd.Series:
    """Returns bool Series marking all participants excluded with spr/char correlation
    being lower than the threshold."""

    if interference:
        colname = "spr/char_interference"

    print(f"Corr: {colname} threshold: {threshold}")
    spr_char_exclusion = to_exclude[colname] < threshold
    spr_char_exclusion.name = colname
    print(f"Exclusions: {spr_char_exclusion.sum()}")

    # plot
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        "Distribution spr/char correlations. exclusions < threshold",
        15,
        [-0.5, 1],
        skip_to_compare=to_compare is None,
    )

    return spr_char_exclusion


def exclusion_spr_char(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with spr/char correlation
    being lower than 25th percentile - 1.5  * iqr."""

    iqr = to_compare["spr/char"].quantile(0.75) - to_compare["spr/char"].quantile(0.25)
    threshold = to_compare["spr/char"].quantile(0.25) - 1.5 * iqr

    return exclusion_spr_char_abs(config, to_exclude, to_compare, threshold)


def exclusion_spr_wcg_break(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with time between reading
    and wcg being higher than 75th percentile + 1.5  * iqr."""

    iqr = to_compare["spr-wcg-break"].quantile(0.75) - to_compare[
        "spr-wcg-break"
    ].quantile(0.25)

    threshold = to_compare["spr-wcg-break"].quantile(0.75) + 1.5 * iqr
    print(f"spr-wcg-break threshold: {threshold}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "spr-wcg-break",
        "Distribution spr-wcg-break times. threshold < exclusions",
        40,
    )

    spr_wcg_break_exclusion = to_exclude["spr-wcg-break"] > threshold

    return spr_wcg_break_exclusion


def exclusion_spr_wcg_break_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: int,
    colname: str = "spr-wcg-break",
    skip_to_compare: bool = False,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with time between reading
    and wcg being higher than threshold given."""

    print(f"{colname} threshold: {threshold}")
    spr_wcg_break_exclusion = to_exclude[colname] > threshold
    spr_wcg_break_exclusion.name = colname
    print(f"Exclusions: {spr_wcg_break_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        "Distribution spr-wcg-break times. threshold < exclusions",
        40,
        x_range=[0, 200_000],
        skip_to_compare=skip_to_compare,
    )

    return spr_wcg_break_exclusion


def exclusion_reaction_time_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: Union[int, float],
    colname: str = "rt_mean",
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a mean
    reaction time higher than the threshold."""

    print(f"{colname} threshold: {threshold}")
    rt_time_exclusion = to_exclude[colname] > threshold
    rt_time_exclusion.name = colname
    print(f"Exclusions: {rt_time_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        f"Distribution {colname}. threshold < exclusions",
        40,
        x_range=[0, 25_000],
        skip_to_compare=to_compare is None,
    )

    return rt_time_exclusion


def exclusion_reaction_time(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a mean
    reaction time higher than 75th percentile + 1.5  * iqr."""

    iqr = to_compare["rt_mean"].quantile(0.75) - to_compare["rt_mean"].quantile(0.25)
    threshold = to_compare["rt_mean"].quantile(0.75) + 1.5 * iqr

    return exclusion_reaction_time_abs(config, to_exclude, to_compare, threshold)


def exclusion_reaction_time_max(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: int = 20000,
    post_only: bool = False,
    colname: str = "rt_max",
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a max reaction
    time bigger than given threshold."""
    print(f"{colname} threshold: {threshold}")
    colname = f"{colname}_post" if post_only else colname
    rt_time_exclusion = to_exclude[colname] > threshold
    rt_time_exclusion.name = colname
    print(f"Exclusions: {rt_time_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        f"Distribution {colname}. threshold < exclusions",
        40,
        x_range=[0, 100_000],
        skip_to_compare=to_compare is None,
    )

    return rt_time_exclusion


def exclusion_comp_prop(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: float = 0.25,
    colname: str = "comp_prop",
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a comprehension
    proportion of smaller/equal to given threshold."""
    print(f"{colname} threshold: {threshold}")
    comp_prop_exclusion = to_exclude[colname] <= threshold
    comp_prop_exclusion.name = colname
    print(f"Exclusions: {comp_prop_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        f"Distribution {colname}. threshold <= Exclusions",
        40,
        [0, 1],
        skip_to_compare=to_compare is None,
    )

    return comp_prop_exclusion


def exclusion_catch_prop(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: float = 0.5,
    colname: str = "catch_prop",
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a comprehension
    proportion of smaller to given threshold."""
    print(f"{colname} threshold: < {threshold}")
    catch_prop_exclusion = to_exclude[colname] < threshold
    print(f"Exclusions: {catch_prop_exclusion.sum()}")

    print(f"Catch prop   0: {(to_exclude[colname] == 0).sum()}")
    print(f"Catch prop 0.5: {(to_exclude[colname] == 0.5).sum()}")
    print(f"Catch prop   1: {(to_exclude[colname] == 1).sum()}")
    print("---")

    return catch_prop_exclusion


def exclusion_story_read(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    colname: str = "read_story",
) -> pd.Series:
    """Returns bool Series marking all participants excluded which already
    read the story."""

    print(f"{colname} threshold: Y")
    comp_prop_exclusion = to_exclude[colname] == "Y"
    print(f"Exclusions: {comp_prop_exclusion.sum()}")

    print(f"{colname} Y: {comp_prop_exclusion.sum()}")
    print(f"{colname} N: {(~comp_prop_exclusion).sum()}")
    print("---")

    comp_prop_exclusion.name = colname
    return comp_prop_exclusion


def exclusion_time_away(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with a time away
    higher than 75th percentile + 1.5  * iqr."""

    iqr = to_compare["time away (m)"].quantile(0.75) - to_compare[
        "time away (m)"
    ].quantile(0.25)

    threshold = to_compare["time away (m)"].quantile(0.75) + 1.5 * iqr
    print(f"time away (m) threshold: {threshold}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        "time away (m)",
        "Distribution time away (m). threshold < exclusions",
        40,
        [0, 80],
    )

    rt_time_exclusion = to_exclude["time away (m)"] > threshold

    return rt_time_exclusion


def exclusion_exp_time_away_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: float,
    colname: str = "exp_time_away",
) -> pd.Series:
    """Returns bool Series marking all participants excluded which where longer away
    than threshold during main_experiment stages.
    """

    print(f"{colname} threshold: {threshold}")
    exp_time_exclusion = to_exclude[colname] > threshold
    exp_time_exclusion.name = colname
    print(f"Exclusions: {exp_time_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        f"Distribution {colname}. threshold < exclusions",
        40,
        [0, 100_000],
        skip_to_compare=to_compare is None,
    )

    return exp_time_exclusion


def exclusion_focusevents_abs(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    threshold: Union[int, float],
    colname: str = "focusevents",
) -> pd.Series:
    print(f"{colname} threshold: {threshold}")
    focus_events_exclusion = to_exclude[colname] > threshold
    focus_events_exclusion.name = colname
    print(f"Exclusions: {focus_events_exclusion.sum()}")

    # plot distributions and threshold
    plot_exclusion_plots(
        config,
        to_exclude,
        to_compare,
        threshold,
        colname,
        f"Distribution {colname}. threshold < exclusions",
        40,
        [0, 50],
        skip_to_compare=to_compare is None,
    )

    return focus_events_exclusion


def exclusion_focusevents(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
) -> pd.Series:
    """Returns bool Series marking all participants excluded with focusevents outlier:
    All data points above 75th percentile + 1.5  * iqr the comparison df."""

    iqr = to_compare["focusevents"].quantile(0.75) - to_compare["focusevents"].quantile(
        0.25
    )
    threshold = to_compare["focusevents"].quantile(0.75) + 1.5 * iqr

    return exclusion_focusevents_abs(config, to_exclude, to_compare, threshold)


def exclusion_suppress_probe(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: Optional[pd.DataFrame],
    check_for_food: bool = True,
    colname_story: str = "guess_suppres_2",
) -> pd.Series:
    """Returns a bool series marking participants as excluded if they do not
    answer with "food" or "story" in the suppression probe.

    colname_story is for:
        - 'suppress' condition, in which 'guess_suppress_2' was
           mistakingly written as 'guess_suppres_2'
        - 'multi_day' condition, in which the column was named
          'check_suppress_topic_2'
    """

    print("suppress_probe threshold: 'food', 'story'")

    def _not_food(row):
        probe = str(row["guess_suppress_1"]).lower()
        return (
            "food" not in probe
            and "aliments" not in probe
            and "foot" not in probe
            and "eat" not in probe
        )

    def _not_story(row, colname_story: str):
        probe = str(row[colname_story]).lower()
        return (
            "story" not in probe
            and "stories" not in probe
            and "sotry" not in probe
            and "passage" not in probe
            and "the text" not in probe
            and "in the read" not in probe
        )

    not_story = to_exclude.apply(_not_story, axis=1, colname_story=colname_story)

    if check_for_food:
        not_food = to_exclude.apply(_not_food, axis=1)
        suppress_probe_exclusion = not_food | not_story
        print((f"Not Food: {not_food.sum()}"))
    else:
        suppress_probe_exclusion = not_story

    print((f"Not Story: {not_story.sum()}"))
    print(f"Excluded: {suppress_probe_exclusion.sum()}")
    print("---")

    return suppress_probe_exclusion


def exclusion_time_unpressed(
    config: Dict,
    to_exclude: pd.DataFrame,
    to_compare: pd.DataFrame,
    threshold: float,
) -> pd.Series:
    """Returns a bool series marking participants as excluded if they unpressed the
    pause button for longer than threshold."""

    print(f"time_unpressed threshold: {threshold}")

    time_unpressed = to_exclude["time_unpressed"] > threshold

    time_unpressed.name = "time_unpressed"
    return time_unpressed


def exclusion_spr_max(
    config: Dict, to_exclude_df: pd.DataFrame, threshold: int
) -> pd.Series:
    print(f"spr_max threshold: {threshold}")

    plot_exclusion_plots(
        config,
        to_exclude_df,
        pd.DataFrame(),
        threshold,
        "spr_max",
        "SPR max",
        nbins=15,
        x_range=[0, 100000],
        skip_to_compare=True,
    )

    spr_max = to_exclude_df["spr_max"] > threshold
    spr_max.name = "spr_max"
    return spr_max


def exclusion_spr_time(
    config: Dict, to_exclude_df: pd.DataFrame, threshold: int
) -> pd.Series:
    print(f"spr_time threshold: {threshold}" + "\n---")
    spr_time = (
        to_exclude_df["reading_stage_end"] - to_exclude_df["reading_stage_start"]
        < threshold
    )
    spr_time.name = "spr_time"
    return spr_time


def exclusion_screen_recording(config: Dict, suffix: Optional[str] = None) -> pd.Series:
    screen_recording_exclusions_df = load_screen_recording_exclusions(config)
    screen_recording = screen_recording_exclusions_df["exclusion"] != "included"
    if suffix is None:
        suffix = ""
    screen_recording.name = f"screen_recording{suffix}"

    print(f"Screen recording exclusions | {config['story']} | {config['condition']}:")
    reasons_and_counts = screen_recording_exclusions_df.loc[
        screen_recording, "reason"
    ].value_counts()
    print(f"Total: {sum(screen_recording)}")
    print(reasons_and_counts, end="\n---\n")

    return screen_recording


def print_stage_times(pID_stage_times: pd.DataFrame):
    stage_time_names = [
        name for name in pID_stage_times.columns if name.endswith("_time")
    ]
    max_len = max(map(len, stage_time_names))
    console.print("Stage Times (post-excluded)", style="yellow")
    for stage_time_name in stage_time_names:
        stage_time_mean = (pID_stage_times[stage_time_name] / 1000).mean()
        stage_time_std = (pID_stage_times[stage_time_name] / 1000).std()
        stage_time_mean_min = stage_time_mean / 60

        whitespaces = " " * (max_len - len(stage_time_name))
        print(
            f"{stage_time_name}{whitespaces} | {round(stage_time_mean, 2):6.2f}s"
            f" ({round(stage_time_std, 2):6.2f})"
            f" | {round(stage_time_mean_min, 2):6.2f}m"
        )
