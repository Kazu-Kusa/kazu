from pyuptech import Color

from kazu.hardwares import screen

set_all = screen.set_all_leds_same
set_all_single = screen.set_all_leds_single


def set_all_red() -> None:
    set_all(Color.RED)


def set_all_green() -> None:
    set_all(Color.GREEN)


def set_all_yellow() -> None:
    set_all(Color.YELLOW)


def set_all_blue() -> None:
    set_all(Color.BLUE)


def set_all_white() -> None:
    set_all(Color.WHITE)


def set_all_black() -> None:
    set_all(Color.BLACK)


def set_red_green() -> None:
    set_all_single(Color.RED, Color.GREEN)


def set_blue_yellow() -> None:
    set_all_single(Color.BLUE, Color.YELLOW)
