from bdmc import CloseLoopController
from cv2 import VideoCapture
from pyuptech import OnBoardSensors
from upic import TagDetector

from kazu.logger import _logger


def check_motor(controller: CloseLoopController) -> bool:
    _logger.info("Start checking motor communication channel.")
    if controller.seriald.is_open:
        _logger.info("Motor communication channel is ready.")
        return True
    else:
        _logger.error("Motor communication channel is not ready.")
        return False


def check_camera(tag_detector: TagDetector) -> bool:

    camera: VideoCapture = tag_detector.camera_device
    _logger.info("Start checking camera device.")
    read_success, _ = camera.read()
    if read_success:
        _logger.info("Camera communication channel is ready.")
        return True
    else:
        _logger.error("Camera communication channel is not ready.")
        return False


def check_adc(sensors: OnBoardSensors) -> bool:
    _logger.info("Start checking ADC device.")
    try:
        first = sensors.adc_all_channels()
    except Exception as e:
        _logger.error(f"Encounter exception: {e}")
        return False
    if any(first):
        _logger.info("ADC communication channel is ready.")
        return True
    else:
        _logger.error("ADC communication channel is not ready.")
        return False


def check_io(sensors: OnBoardSensors) -> bool:
    _logger.info("Start checking IO device.")
    try:
        first = sensors.set_all_io_mode(0).io_all_channels()
    except Exception as e:
        _logger.error(f"Encounter exception: {e}")
        return False

    if all([first << i for i in range(8)]):

        _logger.info("IO communication channel is ready.")
        return True
    else:
        _logger.error("IO communication channel is not ready.")
        return False


def check_mpu(sensors: OnBoardSensors) -> bool:
    _logger.info("Start checking MPU device.")

    try:

        atti_data = sensors.atti_all()
        gyro_data = sensors.gyro_all()
        acc_data = sensors.acc_all()
    except Exception as e:
        _logger.error(f"Encounter exception: {e}")
        return False
    if all(acc_data) and all(gyro_data):
        _logger.info("MPU communication channel is ready.")
        return True
    else:
        _logger.error("MPU communication channel is not ready.")
        return False


def check_power(sensors: OnBoardSensors) -> bool:
    _logger.info("Start checking power supply.")

    try:
        voltage = sensors.adc_all_channels()[-1] * 3.3 * 4.0 / 4096 #formula copied from the uptech source code
    except Exception as e:
        _logger.error(f"Encounter exception: {e}")
        return False
    if voltage > 7.0:
        _logger.info("Extension board power supply is ready.")
        return True
    else:
        _logger.error(f"Extension board power supply is not ready, low voltage: {voltage:2f}V. Is the power supply plugged in the extension board?")
        return False
