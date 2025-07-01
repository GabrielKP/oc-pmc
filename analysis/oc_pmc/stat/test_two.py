from typing import Any, Dict, Optional

import pandas as pd
from scipy.stats import (
    kruskal,
    levene,
    mannwhitneyu,
    normaltest,
    ttest_ind,
    ttest_rel,
    wilcoxon,
)

from oc_pmc import console
from oc_pmc.analysis.cohens_d import cohens_d_1d
from oc_pmc.load import load_per_participant_data
from oc_pmc.utils import cut_small_value


def stat_latex_str(
    config: dict,
    data1_sr: pd.Series,
    data2_sr: pd.Series,
    statistic: float,
    pvalue: float,
    df: float,
) -> str:
    test_type = config["test_type"]
    measure = config["measure"]
    threshold = config.get("threshold", 0.05)
    name1 = config.get("name1", "name1")
    name2 = config.get("name2", "name2")
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

    if test_type in ["kw", "kruskal"]:
        test_type_str = "Kruskal-Wallis$,\\;H(1)"
    elif test_type == "rel":
        test_type_str = f"dependent t-test$,\\;t({int(df)})"
    elif test_type == "ind":
        test_type_str = f"independent t-test$,\\;t({int(df)})"
    elif test_type == "wilcoxon":
        test_type_str = "Wilcoxon signed-rank test$,\\;W"
    elif test_type == "mwu":
        test_type_str = "Mann-Whitney U test$,\\;U"
    else:
        test_type_str = "invalid test_type"

    alternative = ""
    if config.get("alternative", "two-sided") != "two-sided":
        alternative = "one-sided "  # assume two-sided

    if config.get("measure_letter"):
        letter = config["measure_letter"]
    elif measure is not None:
        measure_letters = {
            "story_relatedness": "M",
            "word_time": "T",
            "linger_rating": "L",
            "thought_entries": "S",
        }
        letter = measure_letters.get(measure, "RPLC")
    else:
        letter = "RPLC"

    return (
        f"${letter}_\\text{{\\textit{{{name1}}}}}={round(data1_sr.mean(), 2)},\\;"
        f"{letter}_\\text{{\\textit{{{name2}}}}}={round(data2_sr.mean(), 2)},\\;"
        f"${alternative}{test_type_str} = {round(statistic, 2)},\\;"
        f"{pvalue_str}$"
    )


def test_two(
    config: Dict[str, Any],
    data1_sr: Optional[pd.Series] = None,
    data2_sr: Optional[pd.Series] = None,
) -> float:
    measure: str = config["measure"]
    if config.get("name1") and config.get("name2"):
        console_comment = config.get("console_comment", "")
        console.print(
            f"\n > Test_two: {measure}: {config['name1']} v"
            f" {config['name2']}{console_comment}",
            style="yellow",
        )
    test_type = config.get("test_type", "anova")

    if data1_sr is None or data2_sr is None:
        data1_sr = load_per_participant_data({**config, **config["config1"]})[measure]
        data2_sr = load_per_participant_data({**config, **config["config2"]})[measure]

    # drop nans
    data1_sr = data1_sr.dropna()
    data2_sr = data2_sr.dropna()

    # for dependent tests, make sure to only include overlapping data
    if test_type in ["rel", "wilcoxon"]:
        overlap = list(set(data1_sr.index).intersection(data2_sr.index))
        assert len(overlap) != 0
        if len(overlap) != len(data1_sr):
            print("Data 1 trimmed to ensure overlap.")
        data1_sr = data1_sr[overlap]
        if len(overlap) != len(data2_sr):
            print("Data 2 trimmed to ensure overlap.")
        data2_sr = data2_sr[overlap]

    # Assumptions
    if test_type in ["rel", "ind"]:
        # 1. check normality
        stat1, pval1 = normaltest(data1_sr)
        stat2, pval2 = normaltest(data2_sr)
        print("Needs to be significant to use t-test:")
        print(f" - Normality sample 1: s^2 + k^2={stat1:.5f}, p={pval1:.5f}")
        print(f" - Normality sample 2: s^2 + k^2={stat2:.5f}, p={pval2:.5f}")

        # 2. check equal variance
        statistic, pvalue = levene(data1_sr, data2_sr)
        print("\nNeeds to be not significant to use t-test:")
        print(f" - Levene test: F={statistic:.3f} p={pvalue:.5f}\n")

    if "levene" in test_type:
        statistic, pvalue = levene(data1_sr, data2_sr)
        print(
            "Levene test (if significant, do not use t-test):"
            f" F={statistic:.3f} p={pvalue:.5f}"
        )

    alt = "(two-sided)"
    if config.get("alternative"):
        alt = f" ({config['alternative']})"

    # Run tests
    pvalue = None
    statistic = None
    cohens_d = None
    if "rel" in test_type:
        result = ttest_rel(
            data1_sr,
            data2_sr,
            axis=config.get("axis", 0),
            nan_policy=config.get("nan_policy", "propagate"),
            alternative=config.get("alternative", "two-sided"),
        )
        pvalue, statistic, df = result.pvalue, result.statistic, result.df  # type: ignore
        print(f"Dependent t-test: {statistic:.3f}, p={pvalue:.5f}, df={df} {alt}")

        cohens_d = cohens_d_1d(
            {"paired": True}, data1_sr.to_numpy(), data2_sr.to_numpy()
        )
        print(f"Cohen's d paired: {cohens_d}")
        print(stat_latex_str(config, data1_sr, data2_sr, statistic, pvalue, df=df))

    if "ind" in test_type:
        result = ttest_ind(
            data1_sr,
            data2_sr,
            axis=config.get("axis", 0),
            equal_var=config.get("equal_var", True),
            nan_policy=config.get("nan_policy", "propagate"),
            permutations=config.get("permutations"),
            random_state=config.get("random_state"),
            alternative=config.get("alternative", "two-sided"),
            trim=config.get("trim", 0),
        )
        pvalue, statistic, df = result.pvalue, result.statistic, result.df  # type: ignore
        print(f"Independent t-test: {statistic:.3f}, p={pvalue:.5f}, df={df} {alt}")
        print(stat_latex_str(config, data1_sr, data2_sr, statistic, pvalue, df=df))

    stat_letter = "undefined"
    if "mwu" in test_type:
        result = mannwhitneyu(
            data1_sr,
            data2_sr,
            alternative=config.get("alternative", "two-sided"),
        )
        statistic, pvalue = result.statistic, result.pvalue  # type: ignore
        print(f"Mann-Whitney: U={statistic:3f}, p={pvalue:5f} {alt}")
        print(stat_latex_str(config, data1_sr, data2_sr, statistic, pvalue, df=0))
        stat_letter = "U"
    if "kw" in test_type:
        statistic, pvalue = kruskal(
            data1_sr, data2_sr, nan_policy=config.get("nan_policy", "propagate")
        )
        print(f"Kruskal-Wallis H test: {statistic:3f}, p={pvalue:5f}")
        print(stat_latex_str(config, data1_sr, data2_sr, statistic, pvalue, df=0))
        stat_letter = "H"
    if "wilcoxon" in test_type:
        result = wilcoxon(
            data1_sr, data2_sr, alternative=config.get("alternative", "two-sided")
        )
        statistic, pvalue = result.statistic, result.pvalue  # type: ignore
        print(f"Wilcoxon signed rank test: W = {statistic:3f}, p={pvalue:5f} {alt}")  # type: ignore
        print(stat_latex_str(config, data1_sr, data2_sr, statistic, pvalue, df=0))
        stat_letter = "W"

    print(
        f"Data1 mean: {data1_sr.mean():.3f},"
        f" sd = {data1_sr.std():.3f},"
        f" n = {data1_sr.count()}"
    )
    print(
        f"Data2 mean: {data2_sr.mean():.3f},"
        f" sd = {data2_sr.std():.3f},"
        f" n = {data2_sr.count()}"
    )

    if not config.get("no_effect_size", False):
        if "paired" not in config:
            config["paired"] = (
                "rel" in config["test_type"] or "wilcoxon" in config["test_type"]
            )
        paired_str = " (paired)" if config["paired"] else ""
        cohens_d = cohens_d_1d(config, data1_sr.to_numpy(), data2_sr.to_numpy())
        cohens_d_val = f"{round(cohens_d, 2):.2f}"
        if cohens_d < 1:
            cohens_d_val = cohens_d_val[1:]
        print(f"Cohen's d: {cohens_d_val}{paired_str}")
        print(f", Cohen's d$= {cohens_d_val}$")

    if config.get("print_for_table", False):
        assert pvalue is not None
        assert statistic is not None
        assert cohens_d is not None

        threshold = config.get("threshold", 0.05)
        pvalue_exact = config.get("pvalue_exact", False)
        if pvalue_exact:
            pstring = f"p = {f'{pvalue:f}'[1:]}"
        elif pvalue < (threshold - 0.2 * threshold):
            pstring = f"p < {threshold}".replace("0.", ".")
        else:
            if pvalue < 0.09:
                pstring = f"p = {cut_small_value(pvalue)}"
            else:
                pstring = f"p = {str(round(pvalue, 2))[1:]}"

        cohens_d_val = f"{round(cohens_d, 2):.2f}"
        if cohens_d < 1:
            cohens_d_val = cohens_d_val[1:]

        if config.get("print_for_table_compact"):
            print(
                f"\\makecell{{{round(data1_sr.mean(), 2):.2f} v {round(data2_sr.mean(), 2):.2f}\\\\"  # noqa: E501
                f"${stat_letter}={round(statistic, 2):.2f}$,\\\\${pstring}$\\\\"
                f"Cohen's d$= {cohens_d_val}$}}"
            )
        else:
            print(
                f"\\makecell{{{round(data1_sr.mean(), 2):.2f} v {round(data2_sr.mean(), 2):.2f}\\\\"  # noqa: E501
                f"${stat_letter}={round(statistic, 2):.2f}, {pstring}$\\\\"
                f"Cohen's d$= {cohens_d_val}$}}"
            )

    if pvalue is None:
        raise ValueError("pvalue is None")

    if config.get("return_cohens_d"):
        if cohens_d is None:
            raise ValueError("cohens d is None")
        return cohens_d
    return pvalue
