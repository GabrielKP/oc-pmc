import pandas as pd

from oc_pmc.load import load_questionnaire


def filter_non_exclusion_rows(pID_questionnaire: pd.DataFrame) -> pd.DataFrame:
    chosen_cols = [
        col for col in pID_questionnaire.columns.to_list() if col.endswith("_excl")
    ]
    return pID_questionnaire.loc[:, chosen_cols]


def stat_only_exclusion(exclusions_df: pd.DataFrame, exclusion_stat: str) -> pd.Series:
    """Returns bool series which marks participants which have been
    only excluded by the given exclusion criterium."""

    # Separate stat * other exclusion reason.
    stat = exclusions_df.loc[:, [exclusion_stat]]
    exclusions_df.drop(columns=[exclusion_stat], inplace=True)

    # 2. Do all exclusions
    exclusions_df["exclusion"] = exclusions_df.any(axis=1)

    # 3. Add stat back
    exclusions_df[exclusion_stat] = stat

    # 4. Return all exclusive exclusions
    return ~exclusions_df["exclusion"] & exclusions_df[exclusion_stat]


def print_exclusive_exclusions(exclusions_df: pd.DataFrame):
    exclusions_df = exclusions_df.copy()
    if "exclusion" in exclusions_df.columns:
        exclusions_df.drop(columns=["exclusion"], inplace=True)
    exclusion_stats = exclusions_df.columns.to_list()
    print(" Exclusive amount of particpants excluded by stat:")
    for exclusion_stat in exclusion_stats:
        n_only = stat_only_exclusion(exclusions_df.copy(), exclusion_stat).sum()
        print(f"{exclusion_stat}: {n_only}")


if __name__ == "__main__":
    config = {
        "story": "carver_original",
        "condition": "suppress",
    }
    pID_questionnaire = load_questionnaire(config)
    exclusions_df = filter_non_exclusion_rows(pID_questionnaire)
    time_away_exclusive_excl = stat_only_exclusion(exclusions_df, "time_away_excl")
    print(time_away_exclusive_excl.index[time_away_exclusive_excl].to_list())
