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

controller = CloseLoopController()
screen = Screen()

tag_detector = TagDetector()
sensors = OnBoardSensors()
menta = Menta(
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
class SamplerIndexes:
    """
    Indexes of the samplers in the menta module.
    """

    adc_all: int = 0
    io_all: int = 1
    io_level_idx: int = 2
    io_mode_all: int = 3
    atti_all: int = 4
    gyro_all: int = 5
    acc_all: int = 6


def inited_controller(app_config: APPConfig) -> CloseLoopController:
    """
    Initializes the controller with the given configuration.

    Args:
        app_config (APPConfig): The application configuration containing the motor information and port.

    Returns:
        None

    Description:
        This function initializes the controller with the given configuration. It sets the motor information
        of the controller object using the motor information provided in the application configuration. It also
        sets the port of the serial client of the controller object to the port specified in the application
        configuration. Finally, it opens the serial client, starts the message sending process, and sends a reset
        command to the controller.
    """
    controller.motor_infos = (
        MotorInfo(*app_config.motion.motor_fl),
        MotorInfo(*app_config.motion.motor_rl),
        MotorInfo(*app_config.motion.motor_rr),
        MotorInfo(*app_config.motion.motor_fr),
    )
    controller.serial_client.port = app_config.motion.port
    controller.serial_client.open()
    return controller.start_msg_sending().send_cmd(CMD.RESET)


def inited_tag_detector(app_config: APPConfig, retry_interval: float = 0.5) -> TagDetector:
    """
    Initializes the tag detector with the given configuration.

    Args:
        retry_interval (float, optional): The retry interval in seconds. Defaults to 0.5.
        app_config (APPConfig): The application configuration containing the tag information and port.

    Returns:
        None

    Description:
        This function initializes the tag detector with the given configuration. It sets the tag information
        of the tag detector object using the tag information provided in the application configuration. It also
        sets the port of the serial client of the tag detector object to the port specified in the application
        configuration. Finally, it opens the serial client, and starts the message sending process.
    """
    _logger.info(f"Open Camera-{app_config.vision.camera_device_id}")
    tag_detector.open_camera(app_config.vision.camera_device_id)

    tag_detector.set_cam_resolution_mul(app_config.vision.resolution_multiplier)
    success, _ = tag_detector.camera_device.read()
    if success:
        _logger.info("Camera is successfully opened !")
    else:
        _logger.error("Failed to open Camera !, retrying ...")
        sleep(retry_interval)
        success, _ = tag_detector.camera_device.read()
        if not success:

            _logger.critical(f"Failed to open Camera-{app_config.vision.camera_device_id}")
            _logger.warning("Camera will not be used.")
            app_config.vision.use_camera = False
    return tag_detector
