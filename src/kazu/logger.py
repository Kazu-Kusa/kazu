import logging

import coloredlogs
from colorama import Style

# 初始化logger
_logger = logging.getLogger("kazu")
coloredlogs.install(logger=_logger, level=logging.DEBUG)


def set_log_level(level: int | str):
    """
    设置日志级别
    :param level: 日志级别
    :return:
    """
    _logger.setLevel(level)


def int_to_rgb(color_int):
    """将整数颜色值转换为RGB元组"""
    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    return red, green, blue


def colorful(string: str, r: int, g: int, b: int) -> str:
    """生成带有指定RGB颜色的文本"""
    # 构建ANSI转义序列
    return f"\033[38;2;{r};{g};{b}m{string}\033[0m{Style.RESET_ALL}"


def colorful_int(string, color: int) -> str:
    """color with a single 24-bit number"""
    return colorful(string, *int_to_rgb(color))


set_log_level(logging.INFO)

if __name__ == "__main__":

    _logger.debug("This is a debug log.")
    _logger.info("This is a info log.")
    _logger.warning("This is a warning log.")
    _logger.error("This is a error log.")
    _logger.critical("This is a critical log.")
