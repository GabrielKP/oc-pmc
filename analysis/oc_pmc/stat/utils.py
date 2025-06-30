from typing import Dict

import pandas as pd
from scipy.stats import kruskal, levene, mannwhitneyu, normaltest, ttest_ind, ttest_rel

from oc_pmc.analysis.cohens_d import cohens_d_1d


def test_two(config: Dict, data1_sr: pd.Series, data2_sr: pd.Series):
    test_type = config["test_type"]

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

    if "rel" in test_type:
        result = ttest_rel(
            data1_sr,
            data2_sr,
            axis=config.get("axis", 0),
            nan_policy=config.get("nan_policy", "propagate"),
            alternative=config.get("alternative", "two-sided"),
        )
        print(
            f"Dependent t-test: {result.statistic:.3f},"  # type: ignore
            f" p={result.pvalue:.5f}, df={result.df}"  # type: ignore
        )

        cohens_d = cohens_d_1d(
            {"paired": True}, data1_sr.to_numpy(), data2_sr.to_numpy()
        )
        print(f"Cohen's d: {cohens_d}")
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
        print(
            f"Independent t-test: {result.statistic:.3f},"  # type: ignore
            f" p={result.pvalue:.5f}, df={result.df}"  # type: ignore
        )
    if "mwu" in test_type:
        result = mannwhitneyu(
            data1_sr,
            data2_sr,
            alternative=config.get("alternative", "two-sided"),
        )
        print(f"Mann-Whitney: U={result.statistic:3f}, p={result.pvalue:5f} ")
    if "kw" in test_type:
        statistic, pvalue = kruskal(
            data1_sr, data2_sr, nan_policy=config.get("nan_policy", "propagate")
        )
        print(f"Kruskal-Wallis H test: {statistic:3f}, p={pvalue:5f}")
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
            config["paired"] = "rel" in config["test_type"]
        cohens_d = cohens_d_1d(config, data1_sr.to_numpy(), data2_sr.to_numpy())
        print(f"Cohen's d: {round(cohens_d, 3):.3f}")
