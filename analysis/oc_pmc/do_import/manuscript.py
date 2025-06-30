from oc_pmc.do_import.data_carver_original_buddhika import (
    do_import_exclusion_data_buddhika,
)
from oc_pmc.do_import.linger_fa_dark_bedroom import do_import_linger_fa_dark_bedroom
from oc_pmc.do_import.linger_interference_end_pause import (
    do_import_linger_interference_end_pause,
)
from oc_pmc.do_import.linger_interference_geometry import (
    do_import_linger_interference_geometry,
)
from oc_pmc.do_import.linger_interference_pause import (
    do_import_linger_interference_pause,
)
from oc_pmc.do_import.linger_interference_situation import (
    do_import_linger_interference_situation,
)
from oc_pmc.do_import.linger_interference_story_spr import (
    do_import_linger_interference_story_spr,
)
from oc_pmc.do_import.linger_interference_story_spr_end import (
    do_import_linger_interference_story_spr_end,
)
from oc_pmc.do_import.linger_interference_tom import do_import_linger_interference_tom
from oc_pmc.do_import.linger_neutralcue2 import do_import_linger_neutralcue2
from oc_pmc.do_import.linger_volition_button_press import (
    do_import_volition_button_press,
)
from oc_pmc.do_import.linger_volition_button_press_suppress import (
    do_import_linger_volition_button_press_suppress,
)
from oc_pmc.do_import.linger_volition_suppress import do_import_linger_volition_suppress


def do_import_all():
    do_import_exclusion_data_buddhika()
    do_import_linger_fa_dark_bedroom()
    do_import_linger_interference_end_pause()
    do_import_linger_interference_geometry()
    do_import_linger_interference_pause()
    do_import_linger_interference_situation()
    do_import_linger_interference_story_spr()
    do_import_linger_interference_story_spr_end()
    do_import_linger_interference_tom()
    do_import_linger_neutralcue2()
    do_import_volition_button_press()
    do_import_linger_volition_button_press_suppress()
    do_import_linger_volition_suppress()


if __name__ == "__main__":
    do_import_all()
