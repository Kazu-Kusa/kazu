from typing import List, Tuple  #用于从 typing 模块中导入 List 和 Tuple 类型提示工具

from mentabotix.modules.botix import MovingTransition #从 mentabotix 模块的 botix 子模块中导入 MovingTransition 类 

from kazu.compile import (  #IM123从 kazu 模块的 compile 子模块中导入 make_reboot_handler、make_std_battle_handler、make_always_on_stage_battle_handler 和 make_always_off_stage_battle_handler 函数
    make_reboot_handler,
    make_std_battle_handler,
    make_always_on_stage_battle_handler,
    make_always_off_stage_battle_handler,
)
from kazu.config import APPConfig, RunConfig
from kazu.hardwares import tag_detector
from kazu.signal_light import sig_light_registry


def assembly_AFG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:    
    """
    Assembles the AFG schema by calling the `make_always_off_stage_battle_handler` function with the    #根据给定的 `app_config` 和 `run_config` 参数调用 `make_always_off_stage_battle_handler` 函数来组装 AFG 模式。
    given `app_config` and `run_config` parameters.

    Args:
        app_config (APPConfig): The application configuration object.   #应用程序配置对象。
        run_config (RunConfig): The run configuration object.   #运行配置对象。

    Returns:
        List[MovingTransition]: A list of moving transitions representing the AFG schema.   #表示 AFG 模式的移动过渡列表。
    """
    return make_always_off_stage_battle_handler(app_config, run_config)[-1]     #返回 `make_always_off_stage_battle_handler` 函数的最后一个移动过渡对象。


def assembly_ANG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """
    Assembles the ANG battle schema based on application and runtime configurations.    #根据应用程序和运行时配置组装 ANG 战斗模式。

    Parameters:
        app_config (APPConfig): An object containing application runtime configuration details.     #包含应用程序运行时配置详细信息的对象。
        run_config (RunConfig): A runtime configuration object with specific settings for the battle process.   #具有战斗过程特定设置的运行时配置对象。

    Returns:
        A list of MovingTransitions for managing stage effects in the ANG battle schema.    #管理 ANG 战斗模式中舞台效果的 MovingTransitions 列表。
    """
    # Constructs the always-on-stage battle handler and returns the last MovingTransition
    return make_always_on_stage_battle_handler(app_config, run_config)[-1]


def assembly_NGS_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """
    Assembles the NGS battle schema based on    #根据应用程序和运行时配置组装 NGS 战斗模式。
    application and run configurations.

    Parameters:
        app_config (APPConfig): An object containing configuration details for the workflow.    #包含工作流配置详细信息的对象。
        run_config (RunConfig): An object specifying configurations for the current run.    #指定当前运行配置的对象。

    Returns:
        A list of MovingTransitions representing the assembled workflow stages and transitions.     #表示组装的工作流阶段和过渡的 MovingTransitions 列表。
    """

    # Creates a package of standard battle handling stages using the app and run configurations,    #使用应用程序和运行时配置创建标准战斗处理阶段包。
    # potentially including the tag group   #可能包括标签组。
    stage_pack = make_std_battle_handler(app_config, run_config)

    # Returns the last element of the stage pack, which is the final stage and transition   #返回阶段包的最后一个元素，即最终阶段和过渡。
    return stage_pack[-1]


def assembly_FGS_schema(
    app_config: APPConfig, run_config: RunConfig
) -> Tuple[List[MovingTransition], List[MovingTransition]]:
    """
    Assembles the FGS  battle schema    #根据应用程序和运行时配置组装 FGS 战斗模式。

    Based on the application configuration and runtime configuration, generates lists of moving transition effects  #根据应用程序配置和运行时配置生成移动过渡效果的列表。
    for both the reboot scene and the off-stage-start scene.

    Parameters:
        app_config (APPConfig): An object containing global configuration information for the game.     #包含游戏全局配置信息的对象。
        run_config (RunConfig): An object with specific configuration details for the current runtime environment.  #具有当前运行时环境特定配置详细信息的对象。

    Returns:
        Tuple[List[MovingTransition], List[MovingTransition]]: A tuple containing two lists.    #包含两个列表的元组。
      The first list represents moving transitions for the reboot scene, and the second for the full game scene.    #第一个列表表示重启场景的移动过渡，第二个表示全游戏场景。
    """

    # Generates standard battle handling routines, potentially utilizing the created tag group  #生成标准战斗处理程序，可能使用创建的标签组。
    stage_pack = make_std_battle_handler(
        app_config,
        run_config,
    )
    # Generates reboot handling routines    #生成重启处理程序。
    with sig_light_registry:
        states, boot_transition_pack = make_reboot_handler(app_config, run_config)  #使用信号灯注册表生成重启处理程序。
    if app_config.vision.use_camera:    #如果使用相机
        states[0].before_entering.extend([tag_detector.halt_detection, tag_detector.apriltag_detect_start])     #在进入之前添加停止检测和 AprilTag 检测开始标签。
    # Returns the last moving transition effect for both reboot and standard battle scenes  #返回重启和标准战斗场景的最后一个移动过渡效果。
    return boot_transition_pack, stage_pack[-1]


def assembly_FGDL_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """
    Assembles the FGDL schema based on the provided application and run configurations.     #根据提供的应用程序和运行时配置组装 FGDL 模式。

    Args:
        app_config (APPConfig): Configuration object for the application settings.  #应用程序设置配置对象。
        run_config (RunConfig): Configuration object specifying runtime settings.   #指定运行时设置的配置对象。

    Returns:
        List[MovingTransition]: A list of MovingTransition objects representing the assembled schema.   #表示组装模式的 MovingTransition 对象列表。
    """

    # Generates a reboot handler pack using the application and run configurations  #使用应用程序和运行时配置生成重启处理程序包。
    reboot_pack = make_reboot_handler(app_config, run_config)

    # Returns the last element of the reboot handler pack, which is part of the assembled schema    #返回重启处理程序包的最后一个元素，它是组装模式的一部分。
    return reboot_pack[-1]
