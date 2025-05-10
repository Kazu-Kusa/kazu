from typing import List, Tuple  #���ڴ� typing ģ���е��� List �� Tuple ������ʾ����

from mentabotix.modules.botix import MovingTransition #�� mentabotix ģ��� botix ��ģ���е��� MovingTransition �� 

from kazu.compile import (  #IM123�� kazu ģ��� compile ��ģ���е��� make_reboot_handler��make_std_battle_handler��make_always_on_stage_battle_handler �� make_always_off_stage_battle_handler ����
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
    Assembles the AFG schema by calling the `make_always_off_stage_battle_handler` function with the    #���ݸ����� `app_config` �� `run_config` �������� `make_always_off_stage_battle_handler` ��������װ AFG ģʽ��
    given `app_config` and `run_config` parameters.

    Args:
        app_config (APPConfig): The application configuration object.   #Ӧ�ó������ö���
        run_config (RunConfig): The run configuration object.   #�������ö���

    Returns:
        List[MovingTransition]: A list of moving transitions representing the AFG schema.   #��ʾ AFG ģʽ���ƶ������б�
    """
    return make_always_off_stage_battle_handler(app_config, run_config)[-1]     #���� `make_always_off_stage_battle_handler` ���������һ���ƶ����ɶ���


def assembly_ANG_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """
    Assembles the ANG battle schema based on application and runtime configurations.    #����Ӧ�ó��������ʱ������װ ANG ս��ģʽ��

    Parameters:
        app_config (APPConfig): An object containing application runtime configuration details.     #����Ӧ�ó�������ʱ������ϸ��Ϣ�Ķ���
        run_config (RunConfig): A runtime configuration object with specific settings for the battle process.   #����ս�������ض����õ�����ʱ���ö���

    Returns:
        A list of MovingTransitions for managing stage effects in the ANG battle schema.    #���� ANG ս��ģʽ����̨Ч���� MovingTransitions �б�
    """
    # Constructs the always-on-stage battle handler and returns the last MovingTransition
    return make_always_on_stage_battle_handler(app_config, run_config)[-1]


def assembly_NGS_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """
    Assembles the NGS battle schema based on    #����Ӧ�ó��������ʱ������װ NGS ս��ģʽ��
    application and run configurations.

    Parameters:
        app_config (APPConfig): An object containing configuration details for the workflow.    #����������������ϸ��Ϣ�Ķ���
        run_config (RunConfig): An object specifying configurations for the current run.    #ָ����ǰ�������õĶ���

    Returns:
        A list of MovingTransitions representing the assembled workflow stages and transitions.     #��ʾ��װ�Ĺ������׶κ͹��ɵ� MovingTransitions �б�
    """

    # Creates a package of standard battle handling stages using the app and run configurations,    #ʹ��Ӧ�ó��������ʱ���ô�����׼ս������׶ΰ���
    # potentially including the tag group   #���ܰ�����ǩ�顣
    stage_pack = make_std_battle_handler(app_config, run_config)

    # Returns the last element of the stage pack, which is the final stage and transition   #���ؽ׶ΰ������һ��Ԫ�أ������ս׶κ͹��ɡ�
    return stage_pack[-1]


def assembly_FGS_schema(
    app_config: APPConfig, run_config: RunConfig
) -> Tuple[List[MovingTransition], List[MovingTransition]]:
    """
    Assembles the FGS  battle schema    #����Ӧ�ó��������ʱ������װ FGS ս��ģʽ��

    Based on the application configuration and runtime configuration, generates lists of moving transition effects  #����Ӧ�ó������ú�����ʱ���������ƶ�����Ч�����б�
    for both the reboot scene and the off-stage-start scene.

    Parameters:
        app_config (APPConfig): An object containing global configuration information for the game.     #������Ϸȫ��������Ϣ�Ķ���
        run_config (RunConfig): An object with specific configuration details for the current runtime environment.  #���е�ǰ����ʱ�����ض�������ϸ��Ϣ�Ķ���

    Returns:
        Tuple[List[MovingTransition], List[MovingTransition]]: A tuple containing two lists.    #���������б��Ԫ�顣
      The first list represents moving transitions for the reboot scene, and the second for the full game scene.    #��һ���б��ʾ�����������ƶ����ɣ��ڶ�����ʾȫ��Ϸ������
    """

    # Generates standard battle handling routines, potentially utilizing the created tag group  #���ɱ�׼ս��������򣬿���ʹ�ô����ı�ǩ�顣
    stage_pack = make_std_battle_handler(
        app_config,
        run_config,
    )
    # Generates reboot handling routines    #���������������
    with sig_light_registry:
        states, boot_transition_pack = make_reboot_handler(app_config, run_config)  #ʹ���źŵ�ע������������������
    if app_config.vision.use_camera:    #���ʹ�����
        states[0].before_entering.extend([tag_detector.halt_detection, tag_detector.apriltag_detect_start])     #�ڽ���֮ǰ���ֹͣ���� AprilTag ��⿪ʼ��ǩ��
    # Returns the last moving transition effect for both reboot and standard battle scenes  #���������ͱ�׼ս�����������һ���ƶ�����Ч����
    return boot_transition_pack, stage_pack[-1]


def assembly_FGDL_schema(app_config: APPConfig, run_config: RunConfig) -> List[MovingTransition]:
    """
    Assembles the FGDL schema based on the provided application and run configurations.     #�����ṩ��Ӧ�ó��������ʱ������װ FGDL ģʽ��

    Args:
        app_config (APPConfig): Configuration object for the application settings.  #Ӧ�ó����������ö���
        run_config (RunConfig): Configuration object specifying runtime settings.   #ָ������ʱ���õ����ö���

    Returns:
        List[MovingTransition]: A list of MovingTransition objects representing the assembled schema.   #��ʾ��װģʽ�� MovingTransition �����б�
    """

    # Generates a reboot handler pack using the application and run configurations  #ʹ��Ӧ�ó��������ʱ����������������������
    reboot_pack = make_reboot_handler(app_config, run_config)

    # Returns the last element of the reboot handler pack, which is part of the assembled schema    #���������������������һ��Ԫ�أ�������װģʽ��һ���֡�
    return reboot_pack[-1]
