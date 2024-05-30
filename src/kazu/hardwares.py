from dataclasses import dataclass

from bdmc.modules.cmd import CMD
from bdmc.modules.controller import CloseLoopController, MotorInfo
from mentabotix.modules.menta import Menta
from pyuptech.modules.screen import Screen
from pyuptech.modules.sensors import OnBoardSensors
from upic.vision.tagdetector import TagDetector

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
    adc_all: int = 0
    io_all: int = 1
    io_level_idx: int = 2
    io_mode_all: int = 3
    atti_all: int = 4
    gyro_all: int = 5
    acc_all: int = 6


def inited_controller(app_config) -> CloseLoopController:
    """
    Initializes the controller with the given configuration.

    Args:
        con (CloseLoopController): The controller object to be initialized.
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
