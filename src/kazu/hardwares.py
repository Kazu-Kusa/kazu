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

controller: CloseLoopController = CloseLoopController()     #创建一个 CloseLoopController 类的实例，并将其赋值给变量 controller
screen = Screen()   #创建一个 Screen 类的实例，并将其赋值给变量 screen

tag_detector = TagDetector()    #创建一个 TagDetector 类的实例，并将其赋值给变量 tag_detector
sensors = OnBoardSensors()  #创建一个 OnBoardSensors 类的实例，并将其赋值给变量 sensors
menta = Menta(  # 创建一个 Menta 类的实例，并将其赋值给变量 menta
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
class SamplerIndexes:   #创建一个名为 SamplerIndexes 的数据类
    """
    Indexes of the samplers in the menta module.    # menta模块中采样器的索引。
    """

    adc_all: int = 0
    io_all: int = 1
    io_level_idx: int = 2
    io_mode_all: int = 3
    atti_all: int = 4
    gyro_all: int = 5
    acc_all: int = 6


def inited_controller(app_config: APPConfig) -> CloseLoopController:    #定义一个名为 inited_controller 的函数，该函数接受一个名为 app_config 的参数，并返回一个 CloseLoopController 类型的对象  
    """
    Initializes the controller with the given configuration.    # 使用给定的配置初始化控制器。

    Args:
        app_config (APPConfig): The application configuration containing the motor information and port.    # 应用程序配置，包含电机信息和端口。

    Returns:
        None    # 无返回值。

    Description:
        This function initializes the controller with the given configuration. It sets the motor information    # 使用给定的配置初始化控制器。它设置电机信息
        of the controller object using the motor information provided in the application configuration. It also     # 使用应用程序配置中提供的电机信息
        sets the port of the serial client of the controller object to the port specified in the application    # 将控制器对象的串行客户端的端口设置为应用程序配置中指定的端口。
        configuration. Finally, it opens the serial client, starts the message sending process, and sends a reset   # 将控制器对象的串行客户端的端口设置为应用程序配置中指定的端口。最后，它打开串行客户端，启动消息发送过程，并发送一个
        command to the controller.  #  命令给控制器。
    """
    controller.motor_infos = (
        MotorInfo(*app_config.motion.motor_fl),     # 将应用程序配置中提供的电机信息设置为控制器对象的电机信息
        MotorInfo(*app_config.motion.motor_rl),     # 将应用程序配置中提供的电机信息设置为控制器对象的电机信息
        MotorInfo(*app_config.motion.motor_rr),
        MotorInfo(*app_config.motion.motor_fr),
    )
    return controller.open(app_config.motion.port).send_cmd(CMD.RESET)  # 打开串行客户端，启动消息发送过程，并发送一个重置命令给控制器。


def inited_tag_detector(app_config: APPConfig, retry_interval: float = 0.5) -> TagDetector:     # 定义一个名为 inited_tag_detector 的函数，该函数接受两个参数，并返回一个 TagDetector 类型的对象  
    """
    Initializes the tag detector with the given configuration.  # 使用给定的配置初始化标签检测器。

    Args:
        retry_interval (float, optional): The retry interval in seconds. Defaults to 0.5.   # 重试间隔（以秒为单位）。默认值为0.5。
        app_config (APPConfig): The application configuration containing the tag information and port.  # 应用程序配置，包含标签信息和端口。

    Returns:
        None

    Description:
        This function initializes the tag detector with the given configuration. It sets the tag information    # 使用给定的配置初始化标签检测器。它设置标签信息   
        of the tag detector object using the tag information provided in the application configuration. It also     # 使用应用程序配置中提供的标签信息
        sets the port of the serial client of the tag detector object to the port specified in the application  # 将标签检测器对象的串行客户端的端口设置为应用程序配置中指定的端口。
        configuration. Finally, it opens the serial client, and starts the message sending process.     # 将标签检测器对象的串行客户端的端口设置为应用程序配置中指定的端口。最后，它打开串行客户端，并启动消息发送过程。
    """
    _logger.info(f"Open Camera-{app_config.vision.camera_device_id}")   # 打开相机
    tag_detector.open_camera(app_config.vision.camera_device_id)    # 打开相机

    tag_detector.set_cam_resolution_mul(app_config.vision.resolution_multiplier)    # 设置相机分辨率倍数
    success, _ = tag_detector.camera_device.read()  # 读取相机数据
    if success:
        _logger.info("Camera is successfully opened !")     # 相机成功打开
    else:
        _logger.error("Failed to open Camera ! retrying ...")   # 相机打开失败，重试
        sleep(retry_interval)   # 休眠一段时间
        success, _ = tag_detector.camera_device.read()  # 重新读取相机数据
        if success:

            _logger.info("Camera is successfully opened !")     # 相机成功打开
        else:
            _logger.critical(f"Failed to open Camera-{app_config.vision.camera_device_id}")     # 相机打开失败
            _logger.warning("Camera will not be used.")     # 相机将不被使用
            app_config.vision.use_camera = False    # 相机将不被使用
    return tag_detector     # 返回标签检测器对象
