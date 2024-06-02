from typing import List, Tuple

from mentabotix.modules.botix import MovingTransition

from kazu.compile import (
    make_reboot_handler,
    make_std_battle_handler,
    make_always_on_stage_battle_handler,
    make_always_off_stage_battle_handler,
)
from kazu.config import APPConfig, RunConfig, make_tag_group


def assmbly_AFG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    return make_always_off_stage_battle_handler(app_config, run_config)[-1]


def assmbly_ANG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    if app_config.vision.use_camera:
        tag_group = make_tag_group(app_config)
    else:
        tag_group = None
        app_config.vision.use_camera = False
    return make_always_on_stage_battle_handler(app_config, run_config, tag_group=tag_group)[-1]


def assmbly_NGS_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    if app_config.vision.use_camera:
        tag_group = make_tag_group(app_config)
    else:
        tag_group = None
    app_config.vision.use_camera = False
    stage_pack = make_std_battle_handler(app_config, run_config, tag_group=tag_group)
    return stage_pack[-1]


def assmbly_FGS_schema(
    app_config: APPConfig, run_config: RunConfig
) -> Tuple[List[MovingTransition], List[MovingTransition]]:
    if app_config.vision.use_camera:
        tag_group = make_tag_group(app_config)
    else:
        tag_group = None
        app_config.vision.use_camera = False
    stage_pack = make_std_battle_handler(app_config, run_config, tag_group=tag_group)
    boot_pack = make_reboot_handler(app_config, run_config)
    return boot_pack[-1], stage_pack[-1]


def assmbly_FGDL_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:

    reboot_pack = make_reboot_handler(app_config, run_config)

    return reboot_pack[-1]
