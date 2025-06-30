from scipy.stats import f_oneway, kruskal, levene, normaltest

from oc_pmc.load import (
    load_per_participant_data,
    load_questionnaire,
    load_rated_wordchains,
    load_wordchains,
)


def test_multiple(config: dict):
    test_type = config.get("test_type", "anova")
    measure = config["measure"]

    samples = list()
    for sample_config in config["configs"]:
        samples.append(load_per_participant_data({**config, **sample_config})[measure])

    # 1. test for normality
    print("Needs to be significant to use ANOVA:")
    for idx, sample in enumerate(samples):
        norm_stat, norm_pval = normaltest(sample)
        print(
            f" - Normality sample {idx}: s^2 + k^2={norm_stat:.5f}, p={norm_pval:.5f}"
        )

    # 2. Equality of variances
    print("\nIf significant, cannot use ANOVA:")
    lev_statistic, lev_pvalue = levene(*samples)
    print(f" - Levene test: F={lev_statistic:.3f} p={lev_pvalue:.5f}\n")

    # 3. Print means
    for idx, sample in enumerate(samples):
        print(
            f"Sample {idx} M={sample.mean():.3f},"
            f" SD = {sample.std():.3f},"
            f" N = {sample.count()}"
        )

    # 4. Run test
    if test_type == "anova":
        stat, pval = f_oneway(*samples)
        print(f"\nF={stat:.4f}, p={pval:.5f}")
    elif test_type in ["kruskal", "kw"]:
        stat, pval = kruskal(*samples, nan_policy=config.get("nan_policy", "propagate"))
        print(f"Kruskal-Wallis H test: {stat:4f}, p={pval:5f}")
    else:
        raise ValueError(f"Invalid test-type: {test_type}")
