from numbers import Number
from typing import Dict, Tuple, Union

Filterspec = Tuple[str, str, Union[str, Number]]
Loadspec = Tuple[str, Dict[str, Union["Loadspec", Filterspec]]]
