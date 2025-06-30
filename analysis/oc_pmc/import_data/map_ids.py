import json
import os
from typing import Dict, List, Tuple

from oc_pmc import STUDYDATA_DIR

MAPPING_FILE = "id_mapping.json"


def load_mapping(study_data_dir: str) -> Dict:
    mapfile = os.path.join(study_data_dir, MAPPING_FILE)
    # dirname("x/") = "x" -> thus make following line a bit complicated
    parent_mapfile = os.path.join(
        os.path.dirname(os.path.dirname(mapfile)), MAPPING_FILE
    )
    studies_id_mapping_path = os.path.join(STUDYDATA_DIR, MAPPING_FILE)

    # first search in parent directory of study_data
    if os.path.exists(parent_mapfile):
        print(f"Found mapping in parent dir of study_data: {parent_mapfile}")
        with open(parent_mapfile, "r") as f_mapping:
            mapping = json.load(f_mapping)

    # second search in directory of study_data
    elif os.path.exists(mapfile):
        print(f"Found mapping in study_data dir: {mapfile}")
        with open(mapfile, "r") as f_mapping:
            mapping = json.load(f_mapping)

    # third search in STUDYDATA DIR, which should point towards the mapping
    # synced with 'studies'
    elif os.path.exists(studies_id_mapping_path):
        print(f"Found mapping in STUDYDATA_DIR dir: {studies_id_mapping_path}")
        with open(studies_id_mapping_path, "r") as f_mapping:
            mapping = json.load(f_mapping)

    # If all fails ask for new mapping
    else:
        print(f"Mapping not found in {mapfile} nor in {parent_mapfile}")
        print("Create a new mapping between pIDs and anonymous IDs? (y/n)")
        if input() != "y":
            print("Did not answer 'y'. Aborting.")
            import sys

            sys.exit(1)

        mapping = dict()
    return mapping


def save_mapping(study_data_dir: str, mapping: Dict):
    """Saves mapping to study_data_dir."""
    parent_mapfile = os.path.join(os.path.dirname(study_data_dir), MAPPING_FILE)
    mapfile = os.path.join(study_data_dir, MAPPING_FILE)

    if os.path.exists(parent_mapfile):
        path_to_save = parent_mapfile
    elif os.path.exists(mapfile):
        path_to_save = mapfile
    else:
        path_to_save = parent_mapfile
    with open(path_to_save, "w") as f_mapping:
        json.dump(mapping, f_mapping)


def mapIds(study_data_dir: str, ids: List[str]) -> Tuple[List[int], Dict[str, int]]:
    mapping = load_mapping(study_data_dir)

    mapped_ids = list()
    for id in ids:
        if id not in mapping:
            mapping[id] = len(mapping) + 1000
        mapped_ids.append(mapping[id])

    save_mapping(study_data_dir, mapping)

    return mapped_ids, mapping
