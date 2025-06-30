import os
import pickle
from typing import Any, Dict, Union

import numpy as np
import pandas as pd

from oc_pmc import CACHE_DIR, DATA_DIR, EXTERNAL_DIR, get_logger
from oc_pmc.model_objects.model_object import ModelObject
from oc_pmc.utils import check_make_dirs

log = get_logger(__name__)


class Glove(ModelObject):
    def __init__(self, config: Dict) -> None:
        path_glove = config.get(
            "path_glove",
            os.path.join(DATA_DIR, EXTERNAL_DIR, "glove/glove.6B.300d.txt"),
        )
        cache_dir = config.get("cache_dir", CACHE_DIR)

        glove_name = os.path.basename(path_glove).replace(".txt", "")
        path_cache_glove = os.path.join(cache_dir, f"{glove_name}.pkl")
        if not os.path.isfile(path_cache_glove):
            # load and save embeddings in faster format for speedup.
            try:
                df = pd.read_csv(
                    path_glove, sep=" ", quoting=3, header=None, index_col=0
                )
            except FileNotFoundError as err:
                log.critical(
                    f"Cannot find embeddings at: {path_glove}"
                    " - Please download glove embeddings"
                    " (https://nlp.stanford.edu/projects/glove/ - glove.6B.zip)"
                    " and unzip them into the data/external/glove/ directory. "
                )
                raise err
            log.info(f"Loading glove embeddings from {path_glove}")
            embedding_dict = {key: val.values for key, val in df.T.items()}
            check_make_dirs(path_cache_glove, verbose=False)
            with open(path_cache_glove, "wb") as f_out:
                pickle.dump(embedding_dict, f_out)
            log.info(f"Cached glove embeddings to {path_glove}.")

        log.info(f"Loading glove embeddings from cache: {path_cache_glove}")
        with open(path_cache_glove, "rb") as f_in:
            self.embedding_dict = pickle.load(f_in)

        self.embed_dim = config.get("embed_dim", 300)
        self.model_name = "glove"

    def embedding(
        self,
        config: Dict[str, Any],
        word: str,
    ) -> Union[np.ndarray, None]:
        return self.embedding_dict.get(word.lower(), None)
