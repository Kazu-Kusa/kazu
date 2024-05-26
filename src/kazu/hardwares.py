from dataclasses import dataclass

from bdmc.modules.controller import CloseLoopController
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
