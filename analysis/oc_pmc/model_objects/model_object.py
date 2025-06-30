from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


class ModelObject:
    model_name: str
    max_bulk_size: int

    def incontext_bulk(
        self,
        **kwargs,
    ) -> Tuple[List[Dict], bool]:
        raise NotImplementedError(
            "ModelObject requires 'incontext_bulk' to be implemented!"
        )

    def incontext(
        self, **kwargs
    ) -> Dict[str, Union[Optional[int], float, str, Dict, list]]:
        raise NotImplementedError("ModelObject requires 'incontext' to be implemented!")

    def embeddings(
        self,
        config: Dict[str, Any],
        words: List[str],
    ) -> Union[np.ndarray, List[Union[np.ndarray, None]]]:
        return [self.embedding(config, word) for word in words]

    def embedding(
        self,
        config: Dict[str, Any],
        word: str,
    ) -> Union[np.ndarray, None]:
        raise NotImplementedError("embedding function not implemented for this model!")
