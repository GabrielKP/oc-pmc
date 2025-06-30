import argparse
import os
from typing import Dict, Optional

import pandas as pd

from oc_pmc import DATA_DIR
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import check_make_dirs


def export_field_for_annotation(config: Dict):
    # load data
    questionnaire_df = load_questionnaire({**config, "filter": False})
    questionnaire_df.index.name = "participantID"

    # create dir after loading data (avoid creating unnecessary dirs in case data does
    # not exist)
    join_with_annotation = (
        f"_for_{config['join_with']}" if config.get("join_with") else ""
    )
    output_path = os.path.join(
        DATA_DIR,
        "manual",
        "fields",
        config["story"],
        config["condition"],
        # it is easier to share with the condition name
        f"{config['field_for_annotation']}_{config['condition']}{join_with_annotation}.csv",
    )
    check_make_dirs(output_path)

    # select
    field_df = questionnaire_df.loc[:, [config["field_for_annotation"]]]
    field_df[f"{config['field_for_annotation']}_group"] = ""

    # join with existing
    if config.get("join_with"):
        join_with_path = os.path.join(
            DATA_DIR,
            "manual",
            "fields",
            config["story"],
            config["condition"],
            f"{config['field_for_annotation']}_{config['condition']}_{config['join_with']}.csv",
        )
        join_with_df = pd.read_csv(join_with_path, index_col=0)
        field_df = field_df[[config["field_for_annotation"]]].join(
            join_with_df[[f"{config['field_for_annotation']}_group"]],
            on="participantID",
        )

    # export
    field_df.sort_values(by="participantID", axis="index", inplace=True)
    field_df.to_csv(output_path)


def export_all(join_with: Optional[str] = None):
    stories = ["carver_original", "dark_bedroom"]
    conditions = [
        "button_press",
        "button_press_suppress",
        "neutralcue",
        "suppress",
        "neutralcue2",
        "interference_story",
        "interference_story_control",
        "interference_story_spr",
        "interference_geometry",
        "interference_tom",
        "interference_situation",
        "interference_pause",
    ]
    fields = ["wcg_strategy", "wcg_diff_general", "wcg_diff_explanation"]
    for story in stories:
        for condition in conditions:
            for field in fields:
                config = {
                    "story": story,
                    "condition": condition,
                    "field_for_annotation": field,
                    "join_with": join_with,
                }
                try:
                    export_field_for_annotation(config)
                except FileNotFoundError as err:
                    print(f"File not found: {err}")


if __name__ == "__main__":
    """There are some things that need a clean solution,
    and some things that need a solution.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-j", "--join_with", type=str, help="Join with already rated file."
    )
    parser.add_argument("-a", "--all", action="store_true", help="Export all cleanly.")
    parser.add_argument("-c", "--condition", type=str, help="condition to export")
    parser.add_argument("-s", "--story", type=str, help="story to export")
    parser.add_argument("-F", "--field", type=str, help="field to export")

    args = parser.parse_args()

    print(args)

    if args.all:
        export_all(args.join_with)
    elif not (args.condition is None or args.story is None or args.field is None):
        config = {
            "story": "carver_original",
            "condition": args.condition,
            "field_for_annotation": args.field,
            "join_with": args.join_with,
        }
        export_field_for_annotation(config)
    else:
        parser.print_usage()
