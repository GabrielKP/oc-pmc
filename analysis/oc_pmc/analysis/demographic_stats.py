import numpy as np
import pandas as pd

from oc_pmc import console
from oc_pmc.load import load_questionnaire
from oc_pmc.utils.aggregator import aggregator


def func_demographic_stats(config: dict, data_df: pd.DataFrame):
    condition_name = config["condition"]
    latex = config.get("latex", False)
    if config.get("name_mapping"):
        condition_name = config["name_mapping"][config["condition"]]

    n_participants = len(list(data_df.index.unique()))
    n_participants_finished = len(load_questionnaire({**config, "filter": False}))

    if config.get("just_exclusions"):
        print(f"{condition_name} condition: {n_participants_finished - n_participants}")
        return

    # gender
    n_female = sum(data_df["demographics_gender"] == "F")
    n_male = sum(data_df["demographics_gender"] == "M")
    n_neither = sum(data_df["demographics_gender"] == "NEITHER")
    n_none_gender = sum(data_df["demographics_gender"] == "NONE")

    n_none_gender_str = ""
    if n_none_gender == 1:
        n_none_gender_str = (
            f', with {n_none_gender} participant selecting "Prefer not to identify"'
        )
    elif n_none_gender > 1:
        n_none_gender_str = (
            f', with {n_none_gender} participants selecting "Prefer not to identify"'
        )

    if latex:
        experiment_str = ""
        if config["condition"] in [
            "button_press",
            "button_press_suppress",
            "interference_spr_end_continued",
            "interference_spr_end_separated",
            "interference_spr_end_delayed_continued",
        ]:
            experiment_str = " of the experiment"

        n_excluded = n_participants_finished - n_participants
        gender_txt = (
            f"In total, {n_participants_finished} participants finished this condition"
            f"{experiment_str}."
            f"\n{n_excluded} were excluded"
            " (Exclusion criteria; \\hyperref[methods:exclusion_criteria]{Methods})."
            f"\nThe remaining {n_participants} participants formed"
            f" the final sample ($N_\\text{{female}} = {n_female}"
            f", N_\\text{{male}}={n_male}, N_\\text{{neither}}={n_neither}$"
            f"{n_none_gender_str})."
        )
    else:
        gender_txt = (
            f"After exclusions a total of {n_participants} participants were included"
            f" in the final sample (N_female = {n_female}"
            f", N_male={n_male}, N_neither={n_neither}"
            f"{n_none_gender_str})."
        )

    if config.get("just_gender", False):
        print(f"\n{condition_name} condition:")
        print(gender_txt)
        return

    # age
    age_strs = [
        "18-19",
        "20-24",
        "25-29",
        "30-34",
        "35-39",
        "40-44",
        "45-49",
        "50-54",
        "55-59",
        "60-64",
        "65-69",
        "70-74",
        "75-79",
        "80-84",
        "85+",
        "NONE",
    ]
    int_to_ages_dct = {idx: age_str for idx, age_str in enumerate(age_strs)}
    ages_to_int_dct = {age_str: idx for idx, age_str in enumerate(age_strs)}

    pd.set_option("future.no_silent_downcasting", True)
    data_df["demographics_age_int"] = (
        data_df["demographics_age"].replace(ages_to_int_dct).astype(int)
    )
    pd.set_option("future.no_silent_downcasting", False)

    age_none = np.array(data_df["demographics_age"] == "NONE")
    age_median = int_to_ages_dct[
        int(data_df.loc[~age_none, "demographics_age_int"].median())
    ]
    age_Q1 = int_to_ages_dct[
        int(data_df.loc[~age_none, "demographics_age_int"].quantile(0.25))
    ]
    age_Q3 = int_to_ages_dct[
        int(data_df.loc[~age_none, "demographics_age_int"].quantile(0.75))
    ]
    age_min = int_to_ages_dct[int(data_df.loc[~age_none, "demographics_age_int"].min())]
    age_max = int_to_ages_dct[int(data_df.loc[~age_none, "demographics_age_int"].max())]
    n_none_age = sum(age_none)

    n_none_age_str = ""
    if n_none_age == 1:
        n_none_age_str = (
            f', with {n_none_age} participant selecting "Prefer not to identify"'
        )
    elif n_none_age > 1:
        n_none_age_str = (
            f', with {n_none_age} participants selecting "Prefer not to identify"'
        )

    if latex:
        age_text = (
            f"Median age range was {age_median} years of age"
            f" ($Q_1 = {age_Q1}, Q_3 = {age_Q3}, \\min = {age_min},"
            f" \\max = {age_max}${n_none_age_str})."
        )
    else:
        age_text = (
            f"Median age range was {age_median} years of age"
            f" (Q1 = {age_Q1}, Q3 = {age_Q3}, min = {age_min},"
            f" max = {age_max}{n_none_age_str})."
        )

    # education
    education_levels = [
        "Less than high school degree",
        "High school degree or equivalent",
        "Some college but no degree",
        "Associate degree",
        "Bachelor degree",
        "Master degree",
        "Doctoral degree",
    ]
    int_to_education_level_dct = {
        idx: education_level for idx, education_level in enumerate(education_levels)
    }

    data_df["demographics_education"] = data_df["demographics_education"].astype(int)

    education_median = int_to_education_level_dct[
        int(data_df["demographics_education"].median())
    ]
    education_Q1 = int_to_education_level_dct[
        int(data_df["demographics_education"].quantile(0.25))
    ]
    education_Q3 = int_to_education_level_dct[
        int(data_df["demographics_education"].quantile(0.75))
    ]
    education_min = int_to_education_level_dct[
        int(data_df["demographics_education"].min())
    ]
    education_max = int_to_education_level_dct[
        int(data_df["demographics_education"].max())
    ]

    if latex:
        education_text = (
            f"Median level of education was ``{education_median}''"
            f" ($Q_1 = \\text{{``{education_Q1}''}},"
            f" Q_3 = \\text{{``{education_Q3}''}},"
            f" \\min = \\text{{``{education_min}''}},"
            f" \\max = \\text{{``{education_max}''}}$)."
        )
    else:
        education_text = (
            f'Median level of education was "{education_median}"'
            f' (Q1 = "{education_Q1}", Q3 = "{education_Q3}",'
            f' min = "{education_min}", max = "{education_max}").'
        )

    # Race
    race_str_dct = {
        "Black": "African American or Black",
        "NativeAmerican": "American Indian or Native American",
        "Asian": "Asian",
        "NativeHawaiianPacificIslander": "Native Hawaiian or Pacific Islander",
        "White": "White",
        "MORE": "More than one race",
        "NONE": "None of the above / Prefer not to identify",
    }
    race_ratios_dct = (
        data_df["demographics_race"].value_counts(normalize=True).to_dict()
    )
    race_none_str = ""

    if latex:
        if "NONE" in race_ratios_dct:
            race_none_str = (
                f", and {100 * race_ratios_dct.pop('NONE'):.2f}\\%"
                " choosing not to identify"
            )
        race_strs = [
            f"``{race_str_dct[race]}'' ({100 * percentage:.2f}\\%)"
            for race, percentage in race_ratios_dct.items()
        ]
    else:
        if "NONE" in race_ratios_dct:
            race_none_str = (
                f", and {100 * race_ratios_dct.pop('NONE'):.2f}%"
                " choosing not to identify"
            )
        race_strs = [
            f'"{race_str_dct[race]}" ({100 * percentage:.2f}%)'
            for race, percentage in race_ratios_dct.items()
        ]

    race_text = (
        f"The majority of our participants identified as {race_strs[0]}, "
        f"followed by {', '.join(race_strs[1:])}{race_none_str}."
    )

    console.print(f"\n{condition_name} condition:", style="yellow")

    sep = "\n" if latex else " "
    print(sep.join([gender_txt, age_text, education_text, race_text]))


def demographic_stats(config: dict):
    aggregator(
        config,
        load_func=load_questionnaire,
        call_func=func_demographic_stats,
    )
