import argparse
import os
from typing import Dict, Optional

import pandas as pd

from oc_pmc import DATA_DIR
from oc_pmc.load import load_questionnaire
from oc_pmc.utils import check_make_dirs


def export_fields(config: Dict):
    # load data
    questionnaire_df = load_questionnaire(
        {**config, "filter": not config["no_exclude"]}
    )
    questionnaire_df.index.name = "participantID"

    # select
    field_df = questionnaire_df.loc[:, config["fields"]]

    # create dir after loading data (avoid creating unnecessary dirs in case
    # data/fields do not exist)
    first_letters = "".join([field[0] for field in config["fields"]])
    output_path = os.path.join(
        DATA_DIR,
        "manual",
        "export",
        config["story"],
        config["condition"],
        # it is easier to share with the condition name
        f"fields_{first_letters}_{config['condition']}.csv",
    )
    check_make_dirs(output_path)

    # export
    field_df.sort_values(by="participantID", axis="index", inplace=True)
    field_df.to_csv(output_path)


if __name__ == "__main__":
    # There are some things that need a clean solution, and some things that need a
    # solution.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-j", "--join_with", type=str, help="Join with already rated file."
    )
    parser.add_argument("-c", "--condition", type=str, help="condition to export")
    parser.add_argument("-s", "--story", type=str, help="story to export")
    parser.add_argument("-F", "--fields", nargs="+", help="fields to export")
    parser.add_argument(
        "--no_exclude", action="store_true", help="Export excluded participants"
    )

    args = parser.parse_args()

    print(args)

    config = {
        "story": "carver_original",
        "condition": args.condition,
        "fields": args.fields,
        "join_with": args.join_with,
        "no_exclude": args.no_exclude,
    }
    export_fields(config)
