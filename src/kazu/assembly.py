from typing import List, Tuple

from mentabotix.modules.botix import MovingTransition

from kazu.compile import (
    make_always_off_stage_battle_handler,
    make_always_on_stage_battle_handler,
    make_reboot_handler,
    make_std_battle_handler,
)
from kazu.config import APPConfig, RunConfig
from kazu.hardwares import tag_detector
from kazu.signal_light import sig_light_registry


def assembly_AFG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """Assembles the AFG schema by calling the `make_always_off_stage_battle_handler` function with the
    given `app_config` and `run_config` parameters.

    Args:
        app_config (APPConfig): The application configuration object.
        run_config (RunConfig): The run configuration object.

    Returns:
        List[MovingTransition]: A list of moving transitions representing the AFG schema.
    """
    return make_always_off_stage_battle_handler(app_config, run_config)[-1]


def assembly_ANG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """Assembles the ANG battle schema based on application and runtime configurations.

    Parameters:
        app_config (APPConfig): An object containing application runtime configuration details.
        run_config (RunConfig): A runtime configuration object with specific settings for the battle process.

    Returns:
        A list of MovingTransitions for managing stage effects in the ANG battle schema.
    """
    # Constructs the always-on-stage battle handler and returns the last MovingTransition
    return make_always_on_stage_battle_handler(app_config, run_config)[-1]


def assembly_NGS_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """Assembles the NGS battle schema based on
    application and run configurations.

    Parameters:
        app_config (APPConfig): An object containing configuration details for the workflow.
        run_config (RunConfig): An object specifying configurations for the current run.

    Returns:
        A list of MovingTransitions representing the assembled workflow stages and transitions.
    """
    # Creates a package of standard battle handling stages using the app and run configurations,
    # potentially including the tag group
    stage_pack = make_std_battle_handler(app_config, run_config)

    # Returns the last element of the stage pack, which is the final stage and transition
    return stage_pack[-1]


def assembly_FGS_schema(
    app_config: APPConfig, run_config: RunConfig
) -> Tuple[List[MovingTransition], List[MovingTransition]]:
    """Assembles the FGS  battle schema.

    Based on the application configuration and runtime configuration, generates lists of moving transition effects
    for both the reboot scene and the off-stage-start scene.

    Parameters:
        app_config (APPConfig): An object containing global configuration information for the game.
        run_config (RunConfig): An object with specific configuration details for the current runtime environment.

    Returns:
        Tuple[List[MovingTransition], List[MovingTransition]]: A tuple containing two lists.
      The first list represents moving transitions for the reboot scene, and the second for the full game scene.
    """
    # Generates standard battle handling routines, potentially utilizing the created tag group
    stage_pack = make_std_battle_handler(
        app_config,
        run_config,
    )
    # Generates reboot handling routines
    with sig_light_registry:
        states, boot_transition_pack = make_reboot_handler(app_config, run_config)
    if app_config.vision.use_camera:
        states[0].before_entering.extend([tag_detector.halt_detection, tag_detector.apriltag_detect_start])
    # Returns the last moving transition effect for both reboot and standard battle scenes
    return boot_transition_pack, stage_pack[-1]


def assembly_FGDL_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """Assembles the FGDL schema based on the provided application and run configurations.

    Args:
        app_config (APPConfig): Configuration object for the application settings.
        run_config (RunConfig): Configuration object specifying runtime settings.

    Returns:
        List[MovingTransition]: A list of MovingTransition objects representing the assembled schema.
    """
    # Generates a reboot handler pack using the application and run configurations
    reboot_pack = make_reboot_handler(app_config, run_config)

    # Returns the last element of the reboot handler pack, which is part of the assembled schema
    return reboot_pack[-1]
