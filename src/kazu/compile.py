from typing import Callable

from bdmc import CloseLoopController
from mentabotix import MovingChainComposer, Botix, Menta
from pyuptech import OnBoardSensors

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
controller = CloseLoopController()

botix = Botix(controller=controller)

composer = MovingChainComposer()


def make_edge_handler() -> Callable:
    raise NotImplementedError


def make_surrounding_handler() -> Callable:
    raise NotImplementedError


def make_normal_handler() -> Callable:
    raise NotImplementedError


def make_fence_handler() -> Callable:
    raise NotImplementedError


def make_start_handler() -> Callable:
    raise NotImplementedError


def make_reboot_handler() -> Callable:
    raise NotImplementedError
