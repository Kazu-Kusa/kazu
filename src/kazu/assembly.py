from typing import List

from mentabotix.modules.botix import MovingTransition

from .compile import make_reboot_handler, make_surrounding_handler, make_scan_handler, make_edge_handler
from .config import APPConfig, RunConfig


def assmbly_AFG_schema():
    pass


def assmbly_ANG_schema(app_config: APPConfig, run_config: RunConfig, tag_group) -> List[MovingTransition]:
    edge_pack = make_edge_handler(app_config, run_config)

    surr_pack = make_surrounding_handler(app_config, run_config, tag_group)
    scan_pack = make_scan_handler(app_config, run_config)


def assmbly_NGS_schema():
    pass


def assmbly_FGS_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:

    pass


def assmbly_FGDL_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    reboot_pack = make_reboot_handler(app_config, run_config)

    return reboot_pack[-1]
    # TODO add soft con
