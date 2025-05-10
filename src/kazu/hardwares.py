from dataclasses import dataclass
from time import sleep

from bdmc.modules.cmd import CMD
from bdmc.modules.controller import CloseLoopController, MotorInfo
from mentabotix.modules.menta import Menta
from pyuptech.modules.screen import Screen
from pyuptech.modules.sensors import OnBoardSensors
from upic.vision.tagdetector import TagDetector

from kazu.config import APPConfig
from kazu.logger import _logger

controller: CloseLoopController = CloseLoopController()     #����һ�� CloseLoopController ���ʵ���������丳ֵ������ controller
screen = Screen()   #����һ�� Screen ���ʵ���������丳ֵ������ screen

tag_detector = TagDetector()    #����һ�� TagDetector ���ʵ���������丳ֵ������ tag_detector
sensors = OnBoardSensors()  #����һ�� OnBoardSensors ���ʵ���������丳ֵ������ sensors
menta = Menta(  # ����һ�� Menta ���ʵ���������丳ֵ������ menta
    samplers=[
        sensors.adc_all_channels,
        sensors.io_all_channels,
        sensors.get_io_level,
        sensors.get_all_io_mode,
        sensors.atti_all,
        sensors.gyro_all,
        sensors.acc_all,
    ]
)


@dataclass
class SamplerIndexes:   #����һ����Ϊ SamplerIndexes ��������
    """
    Indexes of the samplers in the menta module.    # mentaģ���в�������������
    """

    adc_all: int = 0
    io_all: int = 1
    io_level_idx: int = 2
    io_mode_all: int = 3
    atti_all: int = 4
    gyro_all: int = 5
    acc_all: int = 6


def inited_controller(app_config: APPConfig) -> CloseLoopController:    #����һ����Ϊ inited_controller �ĺ������ú�������һ����Ϊ app_config �Ĳ�����������һ�� CloseLoopController ���͵Ķ���  
    """
    Initializes the controller with the given configuration.    # ʹ�ø��������ó�ʼ����������

    Args:
        app_config (APPConfig): The application configuration containing the motor information and port.    # Ӧ�ó������ã����������Ϣ�Ͷ˿ڡ�

    Returns:
        None    # �޷���ֵ��

    Description:
        This function initializes the controller with the given configuration. It sets the motor information    # ʹ�ø��������ó�ʼ���������������õ����Ϣ
        of the controller object using the motor information provided in the application configuration. It also     # ʹ��Ӧ�ó����������ṩ�ĵ����Ϣ
        sets the port of the serial client of the controller object to the port specified in the application    # ������������Ĵ��пͻ��˵Ķ˿�����ΪӦ�ó���������ָ���Ķ˿ڡ�
        configuration. Finally, it opens the serial client, starts the message sending process, and sends a reset   # ������������Ĵ��пͻ��˵Ķ˿�����ΪӦ�ó���������ָ���Ķ˿ڡ�������򿪴��пͻ��ˣ�������Ϣ���͹��̣�������һ��
        command to the controller.  #  �������������
    """
    controller.motor_infos = (
        MotorInfo(*app_config.motion.motor_fl),     # ��Ӧ�ó����������ṩ�ĵ����Ϣ����Ϊ����������ĵ����Ϣ
        MotorInfo(*app_config.motion.motor_rl),     # ��Ӧ�ó����������ṩ�ĵ����Ϣ����Ϊ����������ĵ����Ϣ
        MotorInfo(*app_config.motion.motor_rr),
        MotorInfo(*app_config.motion.motor_fr),
    )
    return controller.open(app_config.motion.port).send_cmd(CMD.RESET)  # �򿪴��пͻ��ˣ�������Ϣ���͹��̣�������һ�������������������


def inited_tag_detector(app_config: APPConfig, retry_interval: float = 0.5) -> TagDetector:     # ����һ����Ϊ inited_tag_detector �ĺ������ú�����������������������һ�� TagDetector ���͵Ķ���  
    """
    Initializes the tag detector with the given configuration.  # ʹ�ø��������ó�ʼ����ǩ�������

    Args:
        retry_interval (float, optional): The retry interval in seconds. Defaults to 0.5.   # ���Լ��������Ϊ��λ����Ĭ��ֵΪ0.5��
        app_config (APPConfig): The application configuration containing the tag information and port.  # Ӧ�ó������ã�������ǩ��Ϣ�Ͷ˿ڡ�

    Returns:
        None

    Description:
        This function initializes the tag detector with the given configuration. It sets the tag information    # ʹ�ø��������ó�ʼ����ǩ������������ñ�ǩ��Ϣ   
        of the tag detector object using the tag information provided in the application configuration. It also     # ʹ��Ӧ�ó����������ṩ�ı�ǩ��Ϣ
        sets the port of the serial client of the tag detector object to the port specified in the application  # ����ǩ���������Ĵ��пͻ��˵Ķ˿�����ΪӦ�ó���������ָ���Ķ˿ڡ�
        configuration. Finally, it opens the serial client, and starts the message sending process.     # ����ǩ���������Ĵ��пͻ��˵Ķ˿�����ΪӦ�ó���������ָ���Ķ˿ڡ�������򿪴��пͻ��ˣ���������Ϣ���͹��̡�
    """
    _logger.info(f"Open Camera-{app_config.vision.camera_device_id}")   # �����
    tag_detector.open_camera(app_config.vision.camera_device_id)    # �����

    tag_detector.set_cam_resolution_mul(app_config.vision.resolution_multiplier)    # ��������ֱ��ʱ���
    success, _ = tag_detector.camera_device.read()  # ��ȡ�������
    if success:
        _logger.info("Camera is successfully opened !")     # ����ɹ���
    else:
        _logger.error("Failed to open Camera ! retrying ...")   # �����ʧ�ܣ�����
        sleep(retry_interval)   # ����һ��ʱ��
        success, _ = tag_detector.camera_device.read()  # ���¶�ȡ�������
        if success:

            _logger.info("Camera is successfully opened !")     # ����ɹ���
        else:
            _logger.critical(f"Failed to open Camera-{app_config.vision.camera_device_id}")     # �����ʧ��
            _logger.warning("Camera will not be used.")     # ���������ʹ��
            app_config.vision.use_camera = False    # ���������ʹ��
    return tag_detector     # ���ر�ǩ���������
