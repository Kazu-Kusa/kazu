from typing import List, Tuple

from mentabotix.modules.botix import MovingTransition

from kazu.compile import (
    make_reboot_handler,
    make_surrounding_handler,
    make_scan_handler,
    make_edge_handler,
    make_stage_handler,
)
from kazu.config import APPConfig, RunConfig, make_tag_group


def assmbly_AFG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    pass


def assmbly_ANG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    if app_config.vision.use_camera:
        tag_group = make_tag_group(app_config)
    else:
        tag_group = None
        app_config.vision.use_camera = False

    edge_pack = make_edge_handler(app_config, run_config)

    surr_pack = make_surrounding_handler(app_config, run_config, tag_group)
    scan_pack = make_scan_handler(app_config, run_config)


def assmbly_NGS_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    pass


def assmbly_FGS_schema(
    app_config: APPConfig, run_config: RunConfig
) -> Tuple[List[MovingTransition], List[MovingTransition]]:
    if app_config.vision.use_camera:
        tag_group = make_tag_group(app_config)
    else:
        tag_group = None
        app_config.vision.use_camera = False
    stage_pack = make_stage_handler(app_config, run_config, tag_group=tag_group)
    boot_pack = make_reboot_handler(app_config, run_config)
    return boot_pack[-1], stage_pack[-1]


def assmbly_FGDL_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:

    reboot_pack = make_reboot_handler(app_config, run_config)

    return reboot_pack[-1]
