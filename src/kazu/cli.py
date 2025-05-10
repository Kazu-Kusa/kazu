from enum import Enum   # 在Python中，enum 是一个内置库，用于创建枚举类型。枚举类型是一种数据类型，它允许你定义一组命名常量。
from pathlib import Path  # pathlib 是 Python 3.4 及以上版本中引入的一个标准库，用于处理文件系统路径。它提供了一种面向对象的路径操作方式，使得路径操作更加直观和易于使用
from time import sleep  # sleep() 函数用于暂停程序的执行，它接受一个参数，表示暂停的时间（以秒为单位）。
from typing import Callable, Optional, Tuple, List, Type    # typing 是 Python 3.5 及以上版本中引入的一个标准库，用于提供类型提示和注解。 

import click    # click 是一个用于创建命令行接口（CLI）的 Python 库。它提供了一种简单而强大的方式来定义命令行参数和选项
from click import secho, echo, clear # click 是一个用于创建命令行接口（CLI）的 Python 库。它提供了一种简单而强大的方式来定义命令行参数和选项
from colorama import Fore    # colorama 是一个用于在终端中显示彩色文本的 Python 库。它提供了一种简单而强大的方式来在终端中显示彩色文本

from kazu import __version__, __command__   # 从 kazu 模块中导入 __version__ 和 __command__ 变量
from kazu.callbacks import (    # 从 kazu.callbacks 模块中导入一些回调函数
    export_default_app_config,
    export_default_run_config,
    disable_cam_callback,
    team_color_callback,
    bench_add_app,
    bench_aps,
    set_port_callback,
    set_camera_callback,
    log_level_callback,
    set_res_multiplier_callback,
    bench_sleep_precision,
    led_light_shell_callback,
    disable_siglight_callback,
    bench_siglight_switch_freq, 
)
from kazu.config import ( # 从 kazu.config 模块中导入一些配置相关的类和函数
    DEFAULT_APP_CONFIG_PATH,
    APPConfig,
    _InternalConfig,
    ContextVar,
    load_run_config,
    load_app_config,
)
from kazu.constant import Env, RunMode, QUIT     # 从 kazu.constant 模块中导入一些常量
from kazu.logger import _logger # 从 kazu.logger 模块中导入 _logger 对象
from kazu.signal_light import sig_light_registry    # 从 kazu.signal_light 模块中导入 sig_light_registry 对象
from kazu.static import get_timestamp # 从 kazu.static 模块中导入 get_timestamp 函数
from kazu.visualize import print_colored_toml    # 从 kazu.visualize 模块中导入 print_colored_toml 函数


@click.group(   #click.group 是 Click 库中的一个装饰器，用于创建一个命令组。命令组允许你将多个命令组合在一起，形成一个更大的命令集合。
    epilog=r"For more details, Check at https://github.com/Kazu-Kusa/kazu", # epilog 参数用于指定命令组的结尾文本，它将在命令组的帮助信息中显示。
)
@click.help_option("-h", "--help")  # help_option 参数用于指定命令组的帮助选项。它接受一个或多个选项名称，这些选项将在命令组的帮助信息中显示。
@click.version_option(   # version_option 参数用于指定命令组的版本选项。它接受一个或多个选项名称，这些选项将在命令组的帮助信息中显示。
    __version__,
    "-v",
    "--version",
    message=f""" 
{Fore.MAGENTA}______ __                    
___  //_/_____ __________  __
__  ,<  _  __ `/__  /_  / / /
_  /| | / /_/ /__  /_/ /_/ / 
/_/ |_| \__,_/ _____/\__,_/  
{Fore.RESET}
{Fore.YELLOW}Kazu: A Dedicated Robots Control System
{Fore.GREEN}Version: {__command__}-v{__version__}{Fore.RESET}
                             """,
)
@click.pass_context     
@click.option(  # option 参数用于指定命令组的选项。它接受一个或多个选项名称，这些选项将在命令组的帮助信息中显示。
    "-a",
    "--app-config-path",
    envvar=Env.KAZU_APP_CONFIG_PATH,
    default=DEFAULT_APP_CONFIG_PATH,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help=f"config file path, also can receive env {Env.KAZU_APP_CONFIG_PATH}",
)
@click.option(
    "-l",
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Change log level temporarily.",
    default=None,
    show_default=True,
)
@click.option(
    "-s",
    "--disable-siglight",
    is_flag=True,
    default=False,
    help="Disable signal light",
)
def main(ctx: click.Context, app_config_path: Path, log_level: str, disable_siglight: bool): # main 函数是命令组的入口点，它接受一个 click.Context 对象作为参数，该对象包含了命令组的上下文信息。
    """A Dedicated Robots Control System"""
    app_config = load_app_config(app_config_path)

    ctx.obj = _InternalConfig(app_config=app_config, app_config_file_path=app_config_path)

    log_level_callback(ctx=ctx, _=None, value=log_level)
    disable_siglight_callback(ctx=ctx, _=None, value=disable_siglight)


@main.command("config")     #@main.command 是 Click 库中的一个装饰器，用于创建一个命令。它接受一个命令名称作为参数，并返回一个函数，该函数将作为命令的实现。
@click.pass_obj
@click.pass_context
@click.help_option("-h", "--help")
@click.option(
    "-r",
    "--export-run-conf-path",
    help=f"Path of the exported run config template file",
    default=None,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    callback=export_default_run_config,
)
@click.option(
    "-a",
    "--export-app-conf-path",
    help="Path of the exported app config template file",
    default=None,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    callback=export_default_app_config,
)
@click.argument("kv", type=(str, str), required=False, default=None)
def configure(  # configure 函数是 config 命令的实现，它接受一个 _InternalConfig 对象和一个 click.Context 对象作为参数，以及一个 kv 参数，该参数是一个元组，包含一个键和一个值。
    ctx: click.Context,     # ctx 是一个 click.Context 对象，它包含了命令组的上下文信息。
    config: _InternalConfig, # config 是一个 _InternalConfig 对象，它包含了应用程序的配置信息。
    kv: Optional[Tuple[str, str]],  # kv 是一个可选的元组，包含一个键和一个值。它用于指定要修改的配置项和要设置的值。
    **_,
):
    """
    Configure KAZU  
    """

    app_config = config.app_config  # app_config 是一个 APPConfig 对象，它包含了应用程序的配置信息。
    if kv is None:  
        from tomlkit import dumps      # 从 tomlkit 模块中导入 dumps 函数，用于将 Python 对象转换为 TOML 格式的字符串。

        secho(f"Config file at {Path(config.app_config_file_path).absolute().as_posix()}", fg="green", bold=True)   # secho 是 Click 库中的一个函数，用于打印彩色文本。它接受一个字符串和一个颜色作为参数，并打印出彩色文本。
        print_colored_toml(dumps(APPConfig.model_dump(app_config)))     # print_colored_toml 是一个自定义函数，用于打印出 TOML 格式的配置文件。它接受一个 TOML 格式的字符串作为参数，并打印出彩色文本。
        return
    key, value = kv     # key 和 value 是 kv 元组的两个元素，它们分别表示要修改的配置项和要设置的值。
    try:
        exec(f"app_config.{key} = '{value}'") # exec 是 Python 中的一个内置函数，用于执行一个字符串中的 Python 代码。它接受一个字符串作为参数，并执行该字符串中的代码。
    except Exception as e:
        secho(e, fg="red", bold=True)   # secho 是 Click 库中的一个函数，用于打印彩色文本。它接受一个字符串和一个颜色作为参数，并打印出彩色文本。
    finally:
        with open(config.app_config_file_path, "w") as fp:   # with open 是 Python 中的一个上下文管理器，用于打开文件。它接受一个文件路径和一个模式作为参数，并返回一个文件对象。
            APPConfig.dump_config(fp, app_config)      # APPConfig.dump_config 是一个自定义函数，用于将 APPConfig 对象保存到文件中。它接受一个文件对象和一个 APPConfig 对象作为参数，并将 APPConfig 对象保存到文件中。
        ctx.exit(0)        # ctx.exit 是 Click 库中的一个函数，用于退出命令组。它接受一个退出码作为参数，并退出命令组。


@main.command("run")
@click.pass_obj
@click.pass_context
@click.help_option("-h", "--help")
@click.option(
    "-d",
    "--disable-camera",
    is_flag=True,
    default=False,
    show_default=True,
    help="Run with the camera disabled.",
    callback=disable_cam_callback,
)
@click.option(
    "-p",
    "--port",
    type=click.STRING,
    help="Set the serial port temporarily",
    default=None,
    show_default=True,
    callback=set_port_callback,
)
@click.option(
    "-c",
    "--camera",
    type=click.INT,
    help="Set camera id temporarily",
    default=None,
    show_default=True,
    callback=set_camera_callback,
)
@click.option(
    "-l",
    "--camera-res-mul",
    type=click.FLOAT,
    help="Set the camera resolution multiplier temporarily",
    default=None,
    show_default=True,
    callback=set_res_multiplier_callback,
)
@click.option(
    "-t",
    "--team-color",
    default=None,
    type=click.Choice(["blue", "yellow"]),
    help="Change allay team color temporarily.",
    callback=team_color_callback,
)
@click.option(
    "-r",
    "--run-config-path",
    show_default=True,
    default=None,
    help=f"config file path, also can receive env {Env.KAZU_RUN_CONFIG_PATH}",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    envvar=Env.KAZU_RUN_CONFIG_PATH,
)
@click.option(
    "-m",
    "--mode",
    show_default=True,
    default=RunMode.FGS,
    type=click.Choice(RunMode.export()),
    help=f"run mode, also can receive env {Env.KAZU_RUN_MODE}",
    envvar=Env.KAZU_RUN_MODE,
)
def run(ctx: click.Context, conf: _InternalConfig, run_config_path: Path | None, mode: str, **_): # IM123run 函数是 run 命令的实现，它接受一个 _InternalConfig 对象和一个 click.Context 对象作为参数，以及一个 run_config_path 参数，该参数是一个路径，用于指定要使用的运行配置文件。
    """
    Run command for the main group.
    """
    from kazu.compile import botix      # IM123从 kazu.compile 模块中导入 botix 对象，它是一个编译器对象，用于将 KAZU 语言编写的代码编译为 Python 代码。
    from bdmc import CMD    # IM123从 bdmc 模块中导入 CMD 对象，它是一个命令对象，用于发送命令给机器人。

    run_config = load_run_config(run_config_path)    # load_run_config 是一个自定义函数，用于加载运行配置文件。它接受一个路径作为参数，并返回一个 RunConfig 对象。

    app_config = conf.app_config    # app_config 是一个 APPConfig 对象，它包含了应用程序的配置信息。

    from kazu.hardwares import inited_controller, sensors, inited_tag_detector  # IM123从 kazu.hardwares 模块中导入 inited_controller、sensors 和 inited_tag_detector 函数，它们用于初始化控制器、传感器和标签检测器。
    from kazu.signal_light import set_all_black     # IM123从 kazu.signal_light 模块中导入 set_all_black 函数，它用于将所有的信号灯设置为黑色。

    sensors.adc_io_open().MPU6500_Open()    # IM123sensors.adc_io_open() 是一个自定义函数，用于打开 ADC 和 IO。MPU6500_Open() 是一个自定义函数，用于打开 MPU6500 传感器。
    tag_detector = inited_tag_detector(app_config)  # IM123inited_tag_detector 是一个自定义函数，用于初始化标签检测器。它接受一个 APPConfig 对象作为参数，并返回一个 TagDetector 对象。
    con = inited_controller(app_config) # IM123inited_controller 是一个自定义函数，用于初始化控制器。它接受一个 APPConfig 对象作为参数，并返回一个 Controller 对象。
    con.context.update(ContextVar.export_context())     # ContextVar.export_context() 是一个自定义函数，用于导出上下文变量。它返回一个字典，其中包含了所有的上下文变量。
    _logger.info(f"Run Mode: {mode}")    # _logger 是一个日志对象，用于记录日志信息。它使用 INFO 级别的日志记录器，并记录一条消息，表示运行模式。
    try:
        match mode:
            case RunMode.FGS:    # match 是 Python 中的一个关键字，用于实现模式匹配。它接受一个表达式和一个或多个模式作为参数，并根据模式匹配的结果执行相应的代码块。
                # O[F]F STA[G]E [S]TART
                from kazu.assembly import assembly_FGS_schema   # IM123从 kazu.assembly 模块中导入 assembly_FGS_schema 函数，它用于组装 FGS 模式的代码。

                boot_pool, stage_pool = assembly_FGS_schema(app_config, run_config)     # assembly_FGS_schema 是一个自定义函数，用于组装 FGS 模式的代码。它接受一个 APPConfig 对象和一个 RunConfig 对象作为参数，并返回两个 TokenPool 对象，分别表示启动代码和阶段代码。
                botix.token_pool = boot_pool    # botix 是一个编译器对象，它将 TokenPool 对象编译为 Python 代码。boot_pool 是一个 TokenPool 对象，表示启动代码。
                boot_func = botix.compile()    # botix.compile() 是一个编译函数，它将 TokenPool 对象编译为 Python 代码，并返回一个可调用的函数。
                botix.token_pool = stage_pool   # stage_pool 是一个 TokenPool 对象，表示阶段代码。
                stage_func = botix.compile()    # botix.compile() 是一个编译函数，它将 TokenPool 对象编译为 Python 代码，并返回一个可调用的函数。
                boot_func()     # boot_func 是一个可调用的函数，它表示启动代码。boot_func() 是一个函数调用，它执行启动代码。
                while 1:
                    stage_func()    # stage_func 是一个可调用的函数，它表示阶段代码。stage_func() 是一个函数调用，它执行阶段代码。
            case RunMode.NGS:   # IM123
                # O[N] STA[G]E [S]TART
                from kazu.assembly import assembly_NGS_schema # IM123从 kazu.assembly 模块中导入 assembly_NGS_schema 函数，它用于组装 NGS 模式的代码。

                botix.token_pool = assembly_NGS_schema(app_config, run_config) # assembly_NGS_schema 是一个自定义函数，用于组装 NGS 模式的代码。它接受一个 APPConfig 对象和一个 RunConfig 对象作为参数，并返回一个 TokenPool 对象，表示阶段代码。
                stage_func = botix.compile()    # botix.compile() 是一个编译函数，它将 TokenPool 对象编译为 Python 代码，并返回一个可调用的函数。
                while 1:
                    stage_func()    # stage_func 是一个可调用的函数，它表示阶段代码。stage_func() 是一个函数调用，它执行阶段代码。
            case RunMode.AFG:    # IM123
                # [A]LWAYS O[F]F STA[G]E
                from kazu.assembly import assembly_AFG_schema

                botix.token_pool = assembly_AFG_schema(app_config, run_config)  # assembly_AFG_schema 是一个自定义函数，用于组装 AFG 模式的代码。它接受一个 APPConfig 对象和一个 RunConfig 对象作为参数
                off_stage_func = botix.compile()    # botix.compile() 是一个编译函数，它将 TokenPool 对象编译为 Python 代码，并返回一个可调用的函数。
                while 1:
                    off_stage_func()
            case RunMode.ANG:    # IM123
                # [A]LWAYS O[N] STA[G]E
                from kazu.assembly import assembly_ANG_schema      # 从 kazu.assembly 模块中导入 assembly_ANG_schema 函数，它用于组装 ANG 模式的代码。

                botix.token_pool = assembly_ANG_schema(app_config, run_config)
                on_stage_func = botix.compile()
                while 1:
                    on_stage_func()
            case RunMode.FGDL:    # IM123
                # O[F]F STA[G]E [D]ASH [L]OOP
                from kazu.assembly import assembly_FGDL_schema

                botix.token_pool = assembly_FGDL_schema(app_config, run_config)
                boot_func = botix.compile()
                while 1:
                    boot_func()
    except KeyboardInterrupt:
        _logger.info("KAZU stopped by keyboard interrupt.") # _logger 是一个日志对象，用于记录日志信息。它使用 INFO 级别的日志记录器，并记录一条消息，表示程序被键盘中断停止。
    except Exception as e:
        _logger.critical(e)     # _logger 是一个日志对象，用于记录日志信息。它使用 CRITICAL 级别的日志记录器，并记录一条消息，表示程序发生了严重错误。
    finally:
        _logger.info(f"Releasing hardware resources...")    # _logger 是一个日志对象，用于记录日志信息。它使用 INFO 级别的日志记录器，并记录一条消息，表示正在释放硬件资源。
        set_all_black()        # set_all_black() 是一个自定义函数，用于将所有 LED 灯设置为黑色。
        con.send_cmd(CMD.FULL_STOP).send_cmd(CMD.RESET).close()     # con.send_cmd(CMD.FULL_STOP) 是一个自定义函数，用于发送全停止命令。con.send_cmd(CMD.RESET) 是一个自定义函数，用于发送复位命令。con.close() 是一个自定义函数，用于关闭控制器连接。
        tag_detector.apriltag_detect_end()  # tag_detector.apriltag_detect_end() 是一个自定义函数，用于结束 AprilTag 检测。
        tag_detector.release_camera()    # tag_detector.release_camera() 是一个自定义函数，用于释放相机资源。
        sensors.adc_io_close()  # sensors.adc_io_close() 是一个自定义函数，用于关闭 ADC 和 IO。
        _logger.info(f"KAZU stopped.")  # _logger 是一个日志对象，用于记录日志信息。它使用 INFO 级别的日志记录器，并记录一条消息，表示程序已停止。
        ctx.exit(0)     # ctx 是一个上下文对象，用于管理命令行参数和选项。ctx.exit(0) 是一个函数调用，它退出程序并返回 0，表示程序成功执行。


@main.command("check")
@click.help_option("-h", "--help")
@click.option(
    "-p",
    "--port",
    type=click.STRING,
    help="Set the serial port temporarily",
    default=None,
    show_default=True,
    callback=set_port_callback,
)
@click.option(
    "-c",
    "--camera",
    type=click.INT,
    help="Set camera id temporarily",
    default=None,
    show_default=True,
    callback=set_camera_callback,
)
@click.pass_obj
@click.argument(
    "device",
    type=click.Choice(devs := ["mot", "cam", "adc", "io", "mpu", "pow", "all"]),
    nargs=-1,
)
def test(conf: _InternalConfig, device: str, **_):  #IM123检查所有的设备的正常功能函数
    """
    Check devices' normal functions     # 检查设备的正常功能
    """
    app_config: APPConfig = conf.app_config     # app_config 是一个 APPConfig 对象，用于存储应用程序的配置信息。

    from kazu.checkers import check_io, check_camera, check_adc, check_motor, check_power, check_mpu    # 从 kazu.checkers 模块中导入 check_io、check_camera、check_adc、check_motor、check_power 和 check_mpu 函数，它们用于检查设备的正常功能。
    from terminaltables import SingleTable  # 从 terminaltables 模块中导入 SingleTable 类，它用于创建表格。

    def _shader(dev_name: str, success: bool) -> List[str]:        # _shader 函数用于创建一个包含设备名称和检查结果的字符串列表。
        return [
            f"{Fore.LIGHTYELLOW_EX if success else Fore.RED}{dev_name}{Fore.RESET}",    # 设备名称
            f"{Fore.GREEN if success else Fore.RED}{success}{Fore.RESET}",        # 检查结果
        ]

    table = [[f"{Fore.YELLOW}Device{Fore.RESET}", f"{Fore.GREEN}Success{Fore.RESET}"]]  # 创建一个包含设备名称和检查结果的表格，初始值为 "Device" 和 "Success"。
    if not device or "all" in device:    # 如果没有指定设备或指定了 "all"，则检查所有设备。
        device = devs   # 设备列表为所有设备。

    if "adc" in device:     # 如果指定了 "adc"，则检查 ADC。
        from kazu.hardwares import sensors  # 从 kazu.hardwares 模块中导入 sensors 对象，用于访问传感器。

        sensors.adc_io_open()   # 打开 ADC 和 IO。
        table.append(_shader("ADC", check_adc(sensors))) # 检查 ADC 并将结果添加到表格中。
        sensors.adc_io_close()  # 关闭 ADC 和 IO。
    if "io" in device:  # 如果指定了 "io"，则检查 IO。
        from kazu.hardwares import sensors  # 从 kazu.hardwares 模块中导入 sensors 对象，用于访问传感器。

        sensors.adc_io_open()   # 打开 ADC 和 IO。
        table.append(_shader("IO", check_io(sensors)))  # 检查 IO 并将结果添加到表格中。
        sensors.adc_io_close()  # 关闭 ADC 和 IO。
    if "mpu" in device:     # 如果指定了 "mpu"，则检查 MPU。
        from kazu.hardwares import sensors  # 从 kazu.hardwares 模块中导入 sensors 对象，用于访问传感器。

        sensors.MPU6500_Open()  # 打开 MPU。
        table.append(_shader("MPU", check_mpu(sensors)))    # 检查 MPU 并将结果添加到表格中。

    if "pow" in device:     # 如果指定了 "pow"，则检查电源。
        from kazu.hardwares import sensors   # 从 kazu.hardwares 模块中导入 sensors 对象，用于访问传感器。

        table.append(_shader("POWER", check_power(sensors)))    # 检查电源并将结果添加到表格中。

    if "cam" in device:     # 如果指定了 "cam"，则检查相机。
        from kazu.hardwares import inited_tag_detector  # 从 kazu.hardwares 模块中导入 inited_tag_detector 函数，用于初始化 AprilTag 检测器。

        tag_detector = inited_tag_detector(app_config)  # 初始化 AprilTag 检测器。
        table.append(_shader("CAMERA", check_camera(tag_detector)))     # 检查相机并将结果添加到表格中。
        tag_detector.release_camera()    # 释放相机资源。
    if "mot" in device:     # 如果指定了 "mot"，则检查电机。
        from kazu.hardwares import inited_controller    # 从 kazu.hardwares 模块中导入 inited_controller 函数，用于初始化控制器。
        from kazu.hardwares import sensors      # 从 kazu.hardwares 模块中导入 sensors 对象，用于访问传感器。
        from bdmc import CMD     # 从 bdmc 模块中导入 CMD 类，用于发送命令给控制器。

        controller = inited_controller(app_config)  # 初始化控制器。
        table.append(_shader("MOTOR", check_motor(controller)))     # 检查电机并将结果添加到表格中。
        controller.close()   # 关闭控制器。
    secho(SingleTable(table).table)     # 打印表格。


@main.command("read")
@click.help_option("-h", "--help")
@click.pass_obj
@click.pass_context
@click.argument(
    "device",
    type=click.Choice(["adc", "io", "mpu", "all"]),
    nargs=-1,
)
@click.option("-s", "--use-screen", is_flag=True, default=False, show_default=True, help="Print to onboard lcd screen")
@click.option("-i", "interval", type=click.FLOAT, default=0.5, show_default=True)
def read_sensors(ctx: click.Context, conf: _InternalConfig, interval: float, device: str, use_screen: bool): # IM123read_sensors 函数用于读取传感器数据并打印到终端。
    """
    Read sensors data and print to terminal
    """
    from pyuptech import make_mpu_table, make_io_table, make_adc_table, adc_io_display_on_lcd, Color # 从 pyuptech 模块中导入 make_mpu_table、make_io_table、make_adc_table 和 adc_io_display_on_lcd 函数，
    from kazu.hardwares import sensors, screen # 从 kazu.hardwares 模块中导入 sensors 和 screen 对象，用于访问传感器和屏幕。

    app_config: APPConfig = conf.app_config     # app_config 是一个 APPConfig 对象，用于存储应用程序的配置信息。
    device = set(device) or ("all",)    # 设备列表为指定设备或所有设备。
    sensor_config = app_config.sensor    # sensor_config 是一个 SensorConfig 对象，用于存储传感器的配置信息。
    (
        sensors.adc_io_open()    # 打开 ADC 和 IO。
        .MPU6500_Open()        # 打开 MPU。
        .set_all_io_mode(0)      # 设置所有 IO 的模式为输入。
        .mpu_set_gyro_fsr(sensor_config.gyro_fsr)    # 设置 MPU 的陀螺仪量程。
        .mpu_set_accel_fsr(sensor_config.accel_fsr)      # 设置 MPU 的加速度计量程。
    )

    if "all" in device:        # 如果指定了 "all"，则读取所有传感器数据。
        device = ("adc", "io", "mpu")    # 设备列表为所有传感器。

    packs = []

    adc_labels = {
        sensor_config.edge_fl_index: "EDG-FL",      # 左侧前边缘传感器
        sensor_config.edge_fr_index: "EDG-FR",      # 右侧前边缘传感器
        sensor_config.edge_rl_index: "EDG-RL",      # 左侧后侧传感器
        sensor_config.edge_rr_index: "EDG-RR",      # 右侧后侧传感器
        sensor_config.left_adc_index: "LEFT",       # 左侧传感器
        sensor_config.right_adc_index: "RIGHT",     # 右侧传感器
        sensor_config.front_adc_index: "FRONT",     # 前侧传感器
        sensor_config.rb_adc_index: "BACK",         # 后侧传感器
        sensor_config.gray_adc_index: "GRAY",       # 灰度传感器
    }

    io_labels = {
        sensor_config.fl_io_index: "FL",    # 左侧前 IO
        sensor_config.fr_io_index: "FR",    # 右侧前 IO
        sensor_config.rl_io_index: "RL",    # 左侧后 IO
        sensor_config.rr_io_index: "RR",    # 右侧后 IO
        sensor_config.reboot_button_index: "REBOOT",    # 复位按钮
        sensor_config.gray_io_left_index: "GRAY-L",     # 左侧灰度 IO
        sensor_config.gray_io_right_index: "GRAY-R",    # 右侧灰度 IO
    }
    for dev in device:    # 遍历设备列表。
        match dev:
            case "adc":
                packs.append(lambda: make_adc_table(sensors, adc_labels))    # 添加 ADC 数据生成函数到 packs 列表中。

            case "io":
                packs.append(lambda: make_io_table(sensors, io_labels))        # 添加 IO 数据生成函数到 packs 列表中。
            case "mpu":
                packs.append(lambda: make_mpu_table(sensors))            # 添加 MPU 数据生成函数到 packs 列表中。
            case _:
                raise ValueError(f"Invalid device: {dev}")          # 如果设备列表中包含无效设备，则抛出 ValueError 异常。
    try:
        if use_screen:  # 如果使用屏幕，则打开屏幕。
            screen.open(2)  # 打开屏幕。
        while 1:
            if use_screen:  # 如果使用屏幕，则显示 ADC 和 IO 数据。
                adc_io_display_on_lcd(sensors, screen, adc_labels, io_labels)    # 显示 ADC 和 IO 数据。
            stdout: str = "\n".join(pack() for pack in packs)    # 生成所有传感器数据并拼接成字符串。
            clear()     # 清空终端屏幕。
            echo(stdout)    # 打印传感器数据。
            sleep(interval)     # 等待指定时间。
    except KeyboardInterrupt:    # 如果用户按下 Ctrl+C，则中断读取传感器数据。
        _logger.info("Read sensors data interrupted.")  # 记录中断信息。
    finally:    # 最后，关闭传感器和屏幕。
        _logger.info("Closing sensors...")  # 记录关闭传感器信息。
        sensors.adc_io_close()  # 关闭 ADC 和 IO。
        if use_screen:  # 如果使用屏幕，则关闭屏幕。
            screen.fill_screen(Color.BLACK).refresh().close()    # 关闭屏幕。
        _logger.info("Exit reading successfully.")  # 记录成功退出信息。
        ctx.exit(0)      # 退出程序。


@main.command("viz")
@click.help_option("-h", "--help")
@click.pass_obj
@click.argument(
    "packname",
    type=click.Choice(
        [
            "all",
            "edge",
            "surr",
            "search",
            "fence",
            "boot",
            "scan",
            "stdbat",
            "bkstage",
            "rdwalk",
            "onstage",
            "angbat",
            "afgbat",
        ]
    ),
    nargs=-1,   # 允许传递多个参数。
)
@click.option(
    "-d",
    "--destination",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="./visualize",
    show_default=True,
    help="Destination path of the generated files",     # 生成文件的路径。
)
@click.option(
    "-r",
    "--run-config-path",
    show_default=True,  # 显示默认值。
    default=None,    # 默认值为 None。
    help=f"config file path, also can receive env {Env.KAZU_RUN_CONFIG_PATH}",  # 配置文件路径，也可以接收环境变量 KAZU_RUN_CONFIG_PATH。
    type=click.Path(dir_okay=False, readable=True, path_type=Path),     # 文件路径类型为 Path。
    envvar=Env.KAZU_RUN_CONFIG_PATH,     # 环境变量为 KAZU_RUN_CONFIG_PATH。
)
@click.option(
    "-e",
    "--render",
    show_default=True,   # 显示默认值。
    is_flag=True,        # 设置为标志选项。
    default=False,       # 默认值为 False。
    help="Render PlantUML files into SVG files",     # 将 PlantUML 文件渲染为 SVG 文件。
)
def visualize(
    conf: _InternalConfig,   # 内部配置对象。
    destination: Path,       # 目标路径。
    run_config_path: Optional[Path],     # 运行配置文件路径。
    render: bool,          # 是否渲染 PlantUML 文件为 SVG 文件。
    packname: Tuple[str, ...],   # 包名。
):
    """
    Visualize State-Transition Diagram of KAZU with PlantUML    # 使用 PlantUML 可视化 KAZU 的状态转移图。

    """
    from kazu.compile import (
        botix,
        make_edge_handler,
        make_reboot_handler,
        make_back_to_stage_handler,
        make_surrounding_handler,
        make_scan_handler,
        make_search_handler,
        make_rand_walk_handler,
        make_fence_handler,
        make_std_battle_handler,
        make_always_on_stage_battle_handler,
        make_always_off_stage_battle_handler,
    )
    from plantuml import PlantUML    # 导入 PlantUML 类。

    packname = packname or ("all",) # 如果没有传递参数，则默认为 "all"。
    puml_d = PlantUML(url="http://www.plantuml.com/plantuml/svg/")  # 创建 PlantUML 对象。

    destination.mkdir(parents=True, exist_ok=True)  # 创建目标目录。
    secho(f"Destination directory: {destination.absolute().as_posix()}", fg="yellow")    # 打印目标目录路径。
    app_config = conf.app_config    # 获取应用配置。
    run_config_path = load_run_config(run_config_path)  # 加载运行配置。

    handlers = {    
        "edge": make_edge_handler,   # 添加边生成函数到 handlers 字典中。
        "boot": make_reboot_handler,     # 添加重启生成函数到 handlers 字典中。
        "bkstage": make_back_to_stage_handler,   # 添加返回舞台生成函数到 handlers 字典中。
        "surr": make_surrounding_handler,    # 添加周围生成函数到 handlers 字典中。
        "scan": make_scan_handler,      # 添加扫描生成函数到 handlers 字典中。
        "search": make_search_handler,    # 添加搜索生成函数到 handlers 字典中。
        "fence": make_fence_handler,    # 添加围栏生成函数到 handlers 字典中。
        "rdwalk": make_rand_walk_handler,       # 添加随机行走生成函数到 handlers 字典中。
        "stdbat": make_std_battle_handler,    # 添加标准战斗生成函数到 handlers 字典中。
        "onstage": make_always_on_stage_battle_handler,  # 添加舞台上战斗生成函数到 handlers 字典中。
        "angbat": make_always_on_stage_battle_handler,  # 添加舞台上战斗生成函数到 handlers 字典中。
        "afgbat": make_always_off_stage_battle_handler,     # 添加舞台外战斗生成函数到 handlers 字典中。
    }

    # 如果packname是'all'，则导出所有；否则，仅导出指定的包
    packs_to_export = list(handlers.keys()) if "all" in packname else packname

    destination.mkdir(parents=True, exist_ok=True)  # 创建目标目录。

    for f_name in packs_to_export:       # IM123led灯设置
        # 假设每个处理函数返回一个可以被导出的数据结构
        # 这里简化处理，实际可能需要根据handler的不同调用不同的导出方法
        handler_func: Callable = handlers.get(f_name)    # 获取处理函数。
        with sig_light_registry:     # 使用信号灯注册器。
            (*_, handler_data) = handler_func(app_config=app_config, run_config=run_config_path)    # 调用处理函数并获取返回值。
        filename = f_name + ".puml"     # 设置文件名。
        destination_filename = (destination / filename).as_posix()  # 设置目标文件名。

        botix.export_structure(destination_filename, handler_data)  # 导出结构。

        if render:
            secho(f"Rendering {filename}", fg="green", bold=True)    # 打印渲染信息。
            puml_d.processes_file(destination_filename, destination_filename.replace(".puml", ".svg"))  # 渲染 PlantUML 文件为 SVG 文件。
        secho(f"Exported {filename}", fg="green", bold=True)    # 打印导出信息。


@main.command("cmd", context_settings={"ignore_unknown_options": True})     # 定义一个名为 "cmd" 的命令，并设置忽略未知选项。
@click.help_option("-h", "--help") # 添加帮助选项。
@click.pass_obj     # 传递对象。
@click.option("-s", "--shell", is_flag=True, help="Run in shell mode", default=False, show_default=True)     # 添加 shell 模式选项。
@click.option(
    "-p",
    "--port",
    type=click.STRING,  # 设置类型为字符串。
    help="Set the serial port temporarily",     # 设置帮助信息。
    default=None,    # 设置默认值为 None。
    show_default=True,   # 显示默认值。
    callback=set_port_callback,     # 设置回调函数。
)
@click.argument("duration", type=click.FLOAT, required=False)    # 添加 duration 参数，类型为浮点数，默认值为 None。
@click.argument("speeds", nargs=-1, type=click.INT, required=False)     # 添加 speeds 参数，类型为整数，默认值为 None。
def control_motor(conf: _InternalConfig, duration: Optional[float], speeds: Optional[list[int]], shell: bool, **_):     # IM123定义一个名为 "control_motor" 的命令，并设置参数。
    """
    Control motor by sending command.   # 通过发送命令控制电机。

    move the bot at <SPEEDS> for <DURATION> seconds, then stop.     # 在 <DURATION> 秒内以 <SPEEDS> 的速度移动机器人，然后停止。

    Args:

        DURATION: (float)    # 移动持续时间。

        SPEEDS: (int) | (int,int) | (int,int,int,int)    # 移动速度。
    """
    from kazu.compile import composer, botix    # 导入 composer 和 botix。
    from kazu.hardwares import inited_controller    # 导入 inited_controller。

    from mentabotix import MovingState, MovingTransition    # 导入 MovingState 和 MovingTransition。

    import threading    # 导入 threading 模块。

    controller = inited_controller(conf.app_config)     # 获取控制器。
    if not controller.seriald.is_open:  # 如果串口未打开，则打印错误信息并退出。
        secho(f"Serial client is not connected to {conf.app_config.motion.port}, exiting...", fg="red", bold=True)  # 打印错误信息。
        return

    supported_token_len = {2, 3, 5}     # 设置支持的命令长度。

    def _send_cmd(mov_duration, mov_speeds):     # 定义发送命令函数。
        try:
            states, transitions = (     # 使用 composer 初始化容器，并添加移动状态和移动过渡，然后导出结构。
                composer.init_container()   # 初始化容器。
                .add(state := MovingState(*mov_speeds))     # 添加移动状态。
                .add(MovingTransition(mov_duration))    # 添加移动过渡。
                .add(MovingState(0))    # 添加停止状态。
                .export_structure()      # 导出结构。
            )
        except ValueError as e:     # 如果发生 ValueError 异常，则打印错误信息并退出。
            secho(f"{e}", fg="red")
            return

        botix.token_pool = transitions  # 设置 botix 的 token_pool 属性为 transitions。

        secho(
            f"{Fore.RESET}Move as {Fore.YELLOW}{state.unwrap()}{Fore.RESET} for {Fore.YELLOW}{mov_duration}{Fore.RESET} seconds",    # 打印移动信息。
        )
        fi: Callable[[], None] = botix.compile(return_median=False)     # 获取编译函数。

        def _bar():        # 定义进度条函数。
            with click.progressbar(     # 创建进度条。
                range(int(mov_duration / 0.1)),     # 设置进度条长度。
                show_percent=True,    # 显示百分比。
                show_eta=True,      # 显示预计时间。
                label="Moving",        # 设置标签。
                color=True,        # 设置颜色。
                fill_char=f"{Fore.GREEN}█{Fore.RESET}",     # 设置填充字符。
                empty_char=f"{Fore.LIGHTWHITE_EX}█{Fore.RESET}",     # 设置空字符。
            ) as bar:    # 使用进度条。
                for _ in bar:    # 循环进度条。
                    sleep(0.1)  # 暂停 0.1 秒。

        t = threading.Thread(target=_bar, daemon=True)  # 创建线程，并设置目标函数为 _bar，并将守护线程设置为 True。
        t.start()    # 启动线程。
        fi()        # 调用编译函数。
        t.join()     # 等待线程结束。

    def _cmd_validator(raw_cmd: str) -> Tuple[float, list[int]] | Tuple[None, None]:     # 定义命令验证函数。
        tokens = raw_cmd.split()    # 将命令字符串按空格分割为列表。
        token_len = len(tokens)     # 获取命令长度。
        if token_len not in supported_token_len:     # 如果命令长度不在支持的长度中，则打印错误信息并返回 None。
            secho(f"Only support 2, 3 or 5 cmd tokens, got {token_len}", fg="red")  # 打印错误信息。
            return None, None    # 返回 None。

        try:
            conv_cmd = float(tokens.pop(0)), list(map(int, tokens))     # 将命令字符串转换为浮点数和整数列表。
        except ValueError:
            secho(f"Invalid cmd: {raw_cmd}", fg="red")  # 打印错误信息。
            return None, None

        return conv_cmd     # 返回转换后的命令。

    if shell:
        secho(f"Open shell mode, enter '{QUIT}' to exit", fg="green", bold=True)    # 打印提示信息。
        while 1:

            cmd = click.prompt(     # 提示用户输入命令。
                f"{Fore.GREEN}>> ",     # 设置提示符颜色为绿色。
                type=click.STRING,    # 设置输入类型为字符串。
                show_default=False,      # 不显示默认值。
                show_choices=False,      # 不显示选项。
                prompt_suffix=f"{Fore.MAGENTA}",     # 设置提示符后缀颜色为洋红色。
            )

            if cmd == QUIT:        # 如果用户输入的命令为 QUIT，则退出循环。
                break   
            duration, speeds = _cmd_validator(cmd)  # 调用命令验证函数，并将返回值赋值给 duration 和 speeds。

            if duration and speeds:     # 如果 duration 和 speeds 都不为 None，则调用发送命令函数。
                _send_cmd(duration, speeds)     # 调用发送命令函数。
    elif duration and speeds:    # 如果 duration 和 speeds 都不为 None，则调用发送命令函数。
        _send_cmd(duration, speeds)     # 调用发送命令函数。
    else:
        secho(
            "You should specify duration and speeds if you want to a single send cmd or add '-s' to open shell",
            fg="red",   # 设置颜色为红色。
        )
    controller.close()   # 关闭控制器。


@main.command("ports")
@click.help_option("-h", "--help")
@click.option("-c", "--check", is_flag=True, default=False, show_default=True, help="Check if ports are available") 
@click.option("-t", "--timeout", type=click.FLOAT, default=1.0, show_default=True, help="Check timeout, in seconds")
@click.pass_obj
def list_ports(conf: _InternalConfig, check: bool, timeout: float):     # 定义 list_ports 命令。
    """
    List serial ports and check if they are in use.     # 列出串行端口并检查它们是否在使用中。
    """
    import serial
    from bdmc import find_serial_ports  # 导入 serial 模块和 find_serial_ports 函数。
    from terminaltables import SingleTable  # 导入 SingleTable 类。
    from colorama import Fore, Style     # 导入 Fore 和 Style 类。
   
    def is_port_open(port_to_check):
        """检查端口是否开放（未被占用）"""
        try:
            with serial.Serial(port_to_check, timeout=timeout):     # 打开端口，设置超时时间。
                return True, "Available."   # 如果端口打开成功，则返回 True 和 "Available."。
        except (OSError, serial.SerialException):    # 如果端口打开失败，则返回 False 和 "Not available or Busy."。
            return False, "Not available or Busy."

    ports = sorted(find_serial_ports(), reverse=True)    # 获取所有串行端口，并按反向排序。
    data = [["Serial Ports", "Status"]]        # 创建数据列表，包含两个标题行。

    for port in ports:    # 遍历所有串行端口。
        if check:    # 如果 check 参数为 True，则检查端口是否开放。
            open_status, message = is_port_open(port)    # 调用 is_port_open 函数，将返回值赋值给 open_status 和 message。
            status_color = Fore.GREEN if open_status else Fore.RED  # 根据端口是否开放，设置状态颜色为绿色或红色。
            data.append([port, f"{status_color}{message}{Style.RESET_ALL}"])    # 将端口和状态添加到数据列表中。
        else:
            data.append([port, f"{Fore.YELLOW}---{Style.RESET_ALL}"])    # 如果 check 参数为 False，则将状态设置为 "---"。

    data.append(["Configured port", conf.app_config.motion.port])    # 将配置的端口添加到数据列表中。
    table = SingleTable(data) # 创建表格对象，将数据列表作为参数传入。
    table.inner_footing_row_border = True    # 设置表格底部边框为 True。
    table.inner_row_border = False  # 设置表格内部行边框为 False。
    table.justify_columns[1] = "right"  # 设置第二列对齐方式为右对齐。
    secho(table.table, bold=True)    # 打印表格。


@main.command("msg")
@click.help_option("-h", "--help")
@click.pass_obj
@click.pass_context
@click.option(
    "-p",
    "--port",
    type=click.STRING,  # 设置参数类型为字符串。
    help="Set the serial port temporarily",     # 设置参数帮助信息。
    default=None,        # 设置默认值为 None。
    show_default=True,    # 显示默认值。
    callback=set_port_callback,     # 设置回调函数为 set_port_callback。
)
def stream_send_msg(ctx: click.Context, conf: _InternalConfig, **_):
    """
    Sending msg in streaming input mode.    # 在流输入模式下发送消息。
    """
    from kazu.hardwares import inited_controller

    con = inited_controller(conf.app_config)    # 调用 inited_controller 函数，将返回值赋值给 con。
    if not con.seriald.is_open:     # 如果 con.seriald.is_open 为 False，则打印错误信息并退出。
        secho(f"Serial client is not connected to {conf.app_config.motion.port}, exiting...", fg="red", bold=True)
        return
    secho("Start reading thread", fg="green", bold=True)    # 打印开始读取线程的信息。

    def _ret_handler(msg: str):      # 定义返回处理函数，将返回值赋值给 msg。
        print(f"\n{Fore.YELLOW}< {msg}{Fore.RESET}")    # 打印返回的消息。

    secho(f"Start streaming input, enter '{QUIT}' to quit", fg="green", bold=True)  # 打印开始流输入的信息，并提示用户输入 QUIT 退出。

    while 1:
        cmd = click.prompt(     # 提示用户输入命令，并将返回值赋值给 cmd。
            f"{Fore.GREEN}> ",   # 设置提示符颜色为绿色。
            type=str,        # 设置输入类型为字符串。
            default="",        # 设置默认值为空字符串。
            prompt_suffix=f"{Fore.MAGENTA}",     # 设置提示符后缀颜色为洋红色。
            show_choices=False,      # 不显示选择项。
            show_default=False,        # 不显示默认值。
        )
        if cmd == QUIT:        # 如果用户输入的命令为 QUIT，则退出循环。
            break
        con.seriald.write(f"{cmd}\r".encode("ascii"))    # 将用户输入的命令发送给串行端口。

    con.close()     # 关闭串行端口。

    secho("Quit streaming", fg="green", bold=True)    # 打印退出流输入的信息。
    ctx.exit(0)        # 退出程序，返回值为 0。


@main.command("light")
@click.help_option("-h", "--help")
@click.pass_obj
@click.option("-s", "--shell", is_flag=True, default=False, callback=led_light_shell_callback)
@click.option("-g", "--sig-lights", is_flag=True, default=False)
def control_display(conf: _InternalConfig, sig_lights: bool, **_):    # 定义 control_display 命令。
    """
    Control LED display.    # 控制LED显示屏。
    """
    if sig_lights:   # 如果 sig_lights 参数为 True，则打印提示信息并退出。

        if not conf.app_config.debug.use_siglight:    # 如果 use_siglight 参数为 False，则打印警告信息并启用 use_siglight 参数。
            secho("Siglight is not enabled, temporarily enable it during the display", fg="yellow", bold=True)  
            conf.app_config.debug.use_siglight = True   # 启用 use_siglight 参数。
        from kazu.compile import make_std_battle_handler
        from kazu.config import RunConfig
        from kazu.signal_light import sig_light_registry
        from kazu.hardwares import screen, sensors
        from pyuptech import Color

        sensors.adc_io_open()   # 打开传感器接口。
        screen.open(2)   # 打开显示屏。
        with sig_light_registry:    # 使用 with 语句，确保 sig_light_registry 被正确关闭。
            _ = make_std_battle_handler(conf.app_config, RunConfig())    # 调用 make_std_battle_handler 函数，将返回值赋值给 _。

        secho("Press 'Enter' to show next.", fg="yellow", bold=True)    # 打印提示信息，提示用户按 Enter 键显示下一个。
        for color, purpose in sig_light_registry.mapping.items():    # 遍历 sig_light_registry.mapping 字典，将键和值分别赋值给 color 和 purpose。
            screen.fill_screen(Color.BLACK).print(purpose).refresh().set_all_leds_single(*color)    # 将显示屏填充为黑色，打印 purpose，刷新显示屏，并将所有 LED 设置为 color 颜色。

            color_names = sig_light_registry.get_key_color_name_colorful(color)     # 调用 get_key_color_name_colorful 函数，将返回值赋值给 color_names。
            out_string = f"<{color_names[0]}, {color_names[1]}>"    # 将 color_names 的第一个和第二个元素分别赋值给 out_string 的第一个和第二个位置。

            click.prompt(f"{out_string}|{purpose} ", prompt_suffix="", default="next", show_default=False)  # 提示用户输入，将返回值赋值给 _。

        _logger.info("All displayed")    # 打印所有显示的信息。
        screen.fill_screen(Color.BLACK).refresh().close().set_all_leds_same(Color.BLACK)    # 将显示屏填充为黑色，刷新显示屏，关闭显示屏，并将所有 LED 设置为黑色。
        sensors.adc_io_close()  # 关闭传感器接口。


@main.command("tag")
@click.help_option("-h", "--help")
@click.pass_obj
@click.pass_context
@click.option(
    "-c",
    "--camera-id",
    type=click.INT,
    help="Set the camera id temporarily",
    default=None,
    show_default=True,
    callback=set_camera_callback,
)
@click.option(
    "-m",
    "--camera-res-mul",
    type=click.FLOAT,
    help="Set the camera resolution multiplier temporarily",
    default=None,
    show_default=True,
    callback=set_res_multiplier_callback,
)
@click.option(
    "-i", "--interval", type=click.FLOAT, default=0.5, show_default=True, help="Set the interval of the tag detector"
)
def tag_test(ctx: click.Context, conf: _InternalConfig, interval: float, **_):  # IM123定义 tag_test 命令。
    """
    Use tag detector to test tag ID detection.  # 使用标签检测器测试标签ID检测。
    """
    from kazu.hardwares import inited_tag_detector
    from kazu.checkers import check_camera

    detector = inited_tag_detector(conf.app_config)     # 调用 inited_tag_detector 函数，将返回值赋值给 detector。
    if not check_camera(detector):   # 调用 check_camera 函数，如果返回值为 False，则打印错误信息并退出。
        secho("Camera is not ready, exiting...", fg="red", bold=True)
        return

    try:
        detector.apriltag_detect_start()    # 调用 apriltag_detect_start 函数，启动标签检测器。
        while 1:
            sleep(interval)     # 休眠 interval 秒。
            secho(f"\rTag: {detector.tag_id}", fg="green", bold=True, nl=False)     # 打印标签ID。

    except KeyboardInterrupt:
        _logger.info("KeyboardInterrupt, exiting...")    # 打印键盘中断信息，并退出。
    finally:
        _logger.info("Release camera...")
        detector.apriltag_detect_end()  # 调用 apriltag_detect_end 函数，停止标签检测器。
        detector.release_camera()    # 调用 release_camera 函数，释放摄像头资源。
        _logger.info("Released")
        ctx.exit(0)


@main.command("breaker")
@click.help_option("-h", "--help")
@click.pass_obj
@click.pass_context
@click.option(
    "-r",
    "--run-config-path",
    show_default=True,
    default=None,
    help=f"config file path, also can receive env {Env.KAZU_RUN_CONFIG_PATH}",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    envvar=Env.KAZU_RUN_CONFIG_PATH,
)
@click.option(
    "-i",
    "--interval",
    type=click.FLOAT,
    default=0.5,
    show_default=True,
    help="Set the interval of the refresh frequency",
)
@click.option("-s", "--use-screen", is_flag=True, default=False, show_default=True, help="Print to onboard lcd screen")
def breaker_test(ctx: click.Context, conf: _InternalConfig, run_config_path: Path, interval: float, use_screen: bool):
    """
    Use breaker detector to test breaker detection.     # 使用断路器检测器测试断路器检测。
    """
    from kazu.config import load_run_config
    from kazu.judgers import Breakers
    from kazu.constant import EdgeCodeSign, SurroundingCodeSign, ScanCodesign, FenceCodeSign, Activation
    from terminaltables import SingleTable
    from kazu.hardwares import sensors, controller, screen
    from kazu.config import ContextVar
    from pyuptech import Color, FontSize

    sensors.adc_io_open().MPU6500_Open()
    controller.context.update({ContextVar.recorded_pack.name: sensors.adc_all_channels()})
    run_config = load_run_config(run_config_path)
    config_pack = conf.app_config, run_config

    def _make_display_pack(     # 定义 _make_display_pack 函数，用于生成显示包。
        breaker: Callable[[], int | bool], codesign_enum: Type[Enum]) -> Callable[[], Tuple[str, int | bool]]:  # 定义 breaker 函数，用于生成断路器函数，并返回一个元组，包含断路器的名称和值。
        def _display():
            codesign = breaker()    # 调用 breaker 函数，将返回值赋值给 codesign。
            [matched] = [x.name for x in codesign_enum if x.value == codesign]  # 从 codesign_enum 中找到与 codesign 相等的枚举值，并将名称赋值给 matched。
            return matched, codesign    # 返回一个元组，包含断路器的名称和值。

        return _display     # 返回 _display 函数。

    data = []    # 定义一个空列表，用于存储数据。
    table: SingleTable = SingleTable(data)  # 定义一个 SingleTable 对象，用于存储数据。

    displays = [
        ("Edge", (_make_display_pack(Breakers.make_std_edge_full_breaker(*config_pack), EdgeCodeSign))),
        ("Surr", (_make_display_pack(Breakers.make_surr_breaker(*config_pack), SurroundingCodeSign))),
        ("Scan", (_make_display_pack(Breakers.make_std_scan_breaker(*config_pack), ScanCodesign))),
        ("Fence", (_make_display_pack(Breakers.make_std_fence_breaker(*config_pack), FenceCodeSign))),
        ("FrontE", (_make_display_pack(Breakers.make_std_edge_front_breaker(*config_pack), Activation))),
        ("RearE", (_make_display_pack(Breakers.make_std_edge_rear_breaker(*config_pack), Activation))),
        ("SAlignT", (_make_display_pack(Breakers.make_std_stage_align_breaker(*config_pack), Activation))),
        ("SAlignM", (_make_display_pack(Breakers.make_stage_align_breaker_mpu(*config_pack), Activation))),
        ("DAlignM", (_make_display_pack(Breakers.make_align_direction_breaker_mpu(*config_pack), Activation))),
        ("DAlignT", (_make_display_pack(Breakers.make_std_align_direction_breaker(*config_pack), Activation))),
        ("TTFront", (_make_display_pack(Breakers.make_std_turn_to_front_breaker(*config_pack), Activation))),
        ("ATK", (_make_display_pack(Breakers.make_std_atk_breaker(*config_pack), Activation))),
        ("ATKE", (_make_display_pack(Breakers.make_atk_breaker_with_edge_sensors(*config_pack), Activation))),
        ("NSTG", (_make_display_pack(Breakers.make_is_on_stage_breaker(*config_pack), Activation))),
        ("SDAWAY", (_make_display_pack(Breakers.make_back_stage_side_away_breaker(*config_pack), Activation))),
        ("LRBLK", (_make_display_pack(Breakers.make_lr_sides_blocked_breaker(*config_pack), Activation))),
    ]

    if use_screen:  # 如果使用屏幕
        screen.open(2).fill_screen(Color.BLACK).refresh().set_font_size(FontSize.FONT_6X8) # 打开屏幕，填充屏幕为黑色，刷新屏幕，设置字体大小为 6x8。
    try:
        while 1:
            data.clear()    # 清空数据列表。
            data.append(["Breaker", "CodeSign", "Value"])    # 添加表头。
            packs = [[name, *d()] for name, d in displays]  # 遍历 displays，将每个断路器的名称和值添加到 packs 列表中。
            data.extend(packs)  # 将 packs 列表添加到数据列表中。
            click.clear()   # 清屏。
            secho(table.table, bold=True)    # 打印表。
            if use_screen:  # 如果使用屏幕
                for pack, start_y in zip(packs, range(0, 80, 8)):    # 遍历 packs，将每个断路器的名称和值添加到屏幕上。
                    screen.put_string(0, start_y, "|".join(map(str, pack)))     # 将每个断路器的名称和值添加到屏幕上。
                screen.refresh()    # 刷新屏幕。
            sleep(interval)     # 等待一段时间。
    except KeyboardInterrupt:    # 如果按下 Ctrl+C
        _logger.info("KeyboardInterrupt, exiting...")    # 打印日志信息。

    except Exception as e:  # 如果发生异常
        _logger.critical(e)     # 打印异常信息。
    finally:

        _logger.info("Releasing resources.")    # 打印日志信息。
        if use_screen:    # 如果使用屏幕
            screen.fill_screen(0).refresh().close()     # 填充屏幕为黑色，刷新屏幕，关闭屏幕。
        sensors.adc_io_close()  # 关闭 ADC IO。
        _logger.info("Released")     # 打印日志信息。
        ctx.exit(0)        # 退出程序。


@main.command("bench")
@click.help_option("-h", "--help")
@click.option(
    "-a",
    "--add-up-to",
    type=click.IntRange(0, max_open=True),
    callback=bench_add_app,
    help="measure time cost adding up to N times",
)
@click.option(
    "-p", "--add-up-per-second", is_flag=True, default=False, callback=bench_aps, help="measure add-ups per second"
)
@click.option(
    "-c",
    "--sleep-precision",
    is_flag=True,
    default=False,
    callback=bench_sleep_precision,
    help="measure sleep precision",
)
@click.option(
    "-w",
    "--light-switch-freq",
    is_flag=True,
    default=False,
    callback=bench_siglight_switch_freq,
    help="measure light switch freq",
)
def bench(**_):
    """
    Benchmarks
    """

    echo("bench test done!")


@main.command("trac")
@click.pass_obj
@click.help_option("-h", "--help")
@click.option(
    "-r",
    "--run-config-path",
    show_default=True,
    default=None,
    help=f"config file path, also can receive env {Env.KAZU_RUN_CONFIG_PATH}",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    envvar=Env.KAZU_RUN_CONFIG_PATH,
)
@click.option(
    "-o",
    "--output-path",
    show_default=True,
    default="./profile.json",
    help=f"Viztracer profile dump path.",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "-s",
    "--salvo",
    show_default=True,
    default=10,
    help=f"How many salvo to run.",
    type=click.INT,
)
@click.option(
    "-d",
    "--disable-view-profile",
    is_flag=True,
    default=False,
    help=f"Disable view profile using vizviewer.",
)
@click.option(
    "-p",
    "--port",
    type=click.INT,
    help="Set the port of the render server",
    default=2024,
    show_default=True,
)
def trace(
    conf: _InternalConfig, run_config_path: Path, output_path: Path, salvo, disable_view_profile: bool, port: int, **_
):
    """
    Trace the std battle using viztracer    #使用 viztracer 跟踪 std battle
    """

    from viztracer import VizTracer        # 从 viztracer 模块导入 VizTracer
    from bdmc import CMD    # 从 bdmc 模块导入 CMD
    from kazu.hardwares import inited_controller, sensors, inited_tag_detector  # 从 kazu.hardwares 模块导入 inited_controller、sensors 和 inited_tag_detector 
    from kazu.signal_light import set_all_black     # 从 kazu.signal_light 模块导入 set_all_black
    from kazu.assembly import assembly_NGS_schema   # 从 kazu.assembly 模块导入 assembly_NGS_schema
    from kazu.compile import botix      # 从 kazu.compile 模块导入 botix

    output_path.parent.mkdir(parents=True, exist_ok=True)    # 创建输出路径的父目录

    traver = VizTracer()    # 创建 VizTracer 对象

    run_config = load_run_config(run_config_path)    # 加载运行配置

    app_config = conf.app_config    # 获取应用程序配置

    sensors.adc_io_open().MPU6500_Open()    # 打开 ADC IO，打开 MPU6500
    set_all_black()     # 设置所有信号灯为黑色
    tag_detector = inited_tag_detector(app_config).apriltag_detect_start()  # 初始化 AprilTag 检测器，开始 AprilTag 检测
    con = inited_controller(app_config)     # 初始化控制器
    con.context.update(ContextVar.export_context())     # 更新控制器的上下文

    botix.token_pool = assembly_NGS_schema(app_config, run_config)  # 组装 NGS 模式，并设置 botix 的 token_pool
    stage_func = botix.compile(function_name="std_battle")  # 编译 std_battle 函数，并设置 stage_func
    seq = (0,) * salvo  # 创建一个包含 salvo 个 0 的元组
    traver.start()    # 开始跟踪
    for _ in seq:    # 对于 seq 中的每个元素
        stage_func()     # 调用 stage_func
    traver.stop()    # 停止跟踪

    set_all_black()     # 设置所有信号灯为黑色
    tag_detector.apriltag_detect_end().release_camera()     # 停止 AprilTag 检测，释放相机
    con.send_cmd(CMD.RESET).close()     # 发送 RESET 命令，关闭控制器
    sensors.adc_io_close()  # 关闭 ADC IO
    traver.save(output_path.as_posix())     # 保存跟踪结果到输出路径

    if not disable_view_profile:     # 如果不禁用查看跟踪结果
        from kazu.static import get_local_ip     # 从 kazu.static 模块导入 get_local_ip
        from subprocess import DEVNULL, Popen    # 从 subprocess 模块导入 DEVNULL 和 Popen

        local_ip = get_local_ip()    # 获取本地 IP
        if local_ip is None:     # 如果获取本地 IP 失败
            secho("Cannot get local ip, vizviewer will not be opened", fg="red", bold=True)     # 输出错误信息
            return
        url = f"http://{local_ip}:{port}"    # 设置 URL
        with Popen(["vizviewer", "--server_only", "--port", str(port), output_path], stdout=DEVNULL) as process:     # 使用 subprocess.Popen 启动 vizviewer 
            secho(f"View profile at {url}", fg="green", bold=True)    # 输出 URL

            while True:
                line = click.prompt(f"Enter '{QUIT}' to quit")  # 提示用户输入
                if line == QUIT:     # 如果用户输入 QUIT
                    break
            process.kill()  # 终止进程


@main.command("view")
@click.help_option("-h", "--help")
@click.argument("profile", type=click.Path(dir_okay=False, readable=True, path_type=Path))
@click.option(
    "-p",
    "--port",
    type=click.INT,
    help="Set the port of the render server",
    default=2024,
    show_default=True,
)
@click.option(
    "-f",
    "--flamegraph",
    is_flag=True,
    help="If generate flamegraph",
    default=False,
    show_default=True,
)
def view_profile(port: int, flamegraph: Path, profile: Path, **_):
    """
    View the profile using vizviewer    # 使用 vizviewer 查看跟踪结果
    """
    from kazu.static import get_local_ip
    from subprocess import DEVNULL, Popen

    local_ip = get_local_ip()    # 获取本地 IP
    if local_ip is None:    # 如果获取本地 IP 失败
        secho("Cannot get local ip, vizviewer will not be opened", fg="red", bold=True)     # 输出错误信息
        return
    url = f"http://{local_ip}:{port}"    # 设置 URL

    args = ["vizviewer", "--server_only", "--port", str(port), profile.as_posix()]  # 设置 vizviewer 的参数
    if flamegraph:  # 如果需要生成火焰图
        args.append("--flamegraph")     # 添加生成火焰图的参数
    with Popen(args, stdout=DEVNULL) as process:     # 使用 subprocess.Popen 启动 vizviewer
        secho(f"View profile at {url}", fg="green", bold=True)  # 输出 URL

        while True:        # 循环等待用户输入 
            line = click.prompt(f"Enter '{QUIT}' to quit")  # 提示用户输入
            if line == QUIT:     # 如果用户输入 QUIT
                break
        process.kill()    # 终止进程


@main.command("record")
@click.help_option("-h", "--help")
@click.pass_obj
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="./record",
    show_default=True,
    help="Output directory",
)
@click.option("-i", "interval", type=click.FLOAT, default=0.1, show_default=True, help="Set the interval of the record")
@click.option(
    "-r",
    "--run-config-path",
    show_default=True,
    default=None,
    help=f"config file path, also can receive env {Env.KAZU_RUN_CONFIG_PATH}",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    envvar=Env.KAZU_RUN_CONFIG_PATH,
)
def record_data(conf: _InternalConfig, output_dir: Path, interval: float, run_config_path: Path):
    """
    Record data     # 记录数据
    """
    from kazu.hardwares import sensors, screen
    from kazu.signal_light import set_all_black, sig_light_registry, Color
    from kazu.judgers import Breakers
    from pandas import DataFrame

    with sig_light_registry as reg:     # 使用 sig_light_registry 注册信号灯
        set_red = reg.register_all("Record|Start Recording", Color.RED)     # 注册红色信号灯
        set_white = reg.register_all("Record|Waiting for Recording", Color.WHITE)    # 注册白色信号灯

    run_config = load_run_config(run_config_path)    # 加载运行配置
    is_pressed = Breakers.make_reboot_button_pressed_breaker(conf.app_config, run_config)    # 创建重启按钮按下中断器

    sensors.adc_io_open()    # 打开 ADC IO
    screen.open(2)  # 打开屏幕

    recorded_df = {}     # 创建一个空的字典，用于存储记录的数据
    recording_container: List[Tuple[int, ...]] = []     # 创建一个空的列表，用于存储记录的数据

    sensor_conf = conf.app_config.sensor    # 获取传感器配置

    def _conv_to_df(data_container: List[Tuple[int, ...]]):     # 定义一个函数，用于将数据转换为 DataFrame
        pack = list(zip(*data_container))    # 将数据打包
        col_names = ["Timestamp", "EDGE_FL", "EDGE_FR", "EDGE_RL", "EDGE_RR", "LEFT", "RIGHT", "FRONT", "BACK", "GRAY"]     # 设置列名
        if pack:
            temp_df = DataFrame(
                {
                    "Timestamp": pack[-1],    # 设置时间戳列
                    "EDGE_FL": pack[sensor_conf.edge_fl_index],     # 设置左前边缘传感器列
                    "EDGE_FR": pack[sensor_conf.edge_fr_index],     # 设置右前边缘传感器列
                    "EDGE_RL": pack[sensor_conf.edge_rl_index],     # 设置左后边缘传感器列
                    "EDGE_RR": pack[sensor_conf.edge_rr_index],     # 设置右后边缘传感器列
                    "LEFT": pack[sensor_conf.left_adc_index],    # 设置左传感器列
                    "RIGHT": pack[sensor_conf.right_adc_index],     # 设置右传感器列
                    "FRONT": pack[sensor_conf.front_adc_index],     # 设置前传感器列
                    "BACK": pack[sensor_conf.rb_adc_index],        # 设置后传感器列
                    "GRAY": pack[sensor_conf.gray_adc_index],        # 设置灰度传感器列
                }
            )
        else:
            temp_df = DataFrame(columns=col_names)  # 如果没有数据，则创建一个空的 DataFrame
        return temp_df  # 返回 DataFrame

    try:
        secho("Press the reboot button to start recording", fg="green", bold=True)  # 输出提示信息
        set_white()        # 设置白色信号灯
        while not is_pressed():      # 等待用户按下重启按钮
            pass
        while is_pressed():     # 等待用户松开重启按钮
            pass
        secho("Start recording|Salvo 1", fg="red", bold=True)    # 输出提示信息
        set_red()        # 设置红色信号灯
        while True:
            recording_container.append(sensors.adc_all_channels() + (get_timestamp(),))     # 将数据添加到记录容器中
            sleep(interval)     # 等待一段时间
            if is_pressed():     # 如果用户按下重启按钮
                while is_pressed():     # 等待用户松开重启按钮
                    pass
                secho(f"Start recording|Salvo {len(recorded_df)+2}", fg="red", bold=True)    # 输出提示信息
                recorded_df[f"record_{get_timestamp()}"] = _conv_to_df(recording_container)     # 将记录容器中的数据转换为 DataFrame，并添加到记录字典中  
                recording_container.clear()     # 清空记录容器
                continue
    except KeyboardInterrupt:
        _logger.info(f"Record interrupted, Exiting...")     # 输出提示信息
    finally:
        _logger.info(f"Recorded Salvo count: {len(recorded_df)}")    # 输出提示信息
        output_dir.mkdir(exist_ok=True, parents=True)    # 创建输出目录
        for k, v in recorded_df.items():     # 遍历记录字典，将每个 DataFrame 保存为 CSV 文件
            v.to_csv(output_dir / f"{k}.csv", index=False)  # 保存为 CSV 文件
        _logger.info(f"Recorded data saved to {output_dir}")    # 输出提示信息
        set_all_black()     # 设置所有信号灯为黑色
        screen.close()    # 关闭屏幕
        sensors.adc_io_close()  # 关闭 ADC IO
