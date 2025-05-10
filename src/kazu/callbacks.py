from pathlib import Path
from typing import Optional, Tuple

import click
from click import secho, echo
from colorama import Fore

from kazu.config import APPConfig, RunConfig, _InternalConfig, load_run_config, load_app_config
from kazu.constant import QUIT


def export_default_app_config(ctx: click.Context, _, path: Path):   #将默认应用程序配置导出到指定路径。
    """
     Export the default application configuration to the specified path.    #将默认应用程序配置导出到指定路径。
    Args:
        ctx (click.Context): The click context object.  #点击上下文对象。
        _ (Any): Ignored parameter.     #忽略参数。
        path (str): The path to export the default application configuration to.    #将默认应用程序配置导出到的路径。
    Returns:
        None: If the path is not provided.  #如果未提供路径，则返回None。
    """
    if path:
        path.parent.mkdir(exist_ok=True, parents=True)  # 创建路径的父目录，如果不存在则创建。
        with open(path, "w") as fp:     #以写入模式打开文件。
            APPConfig.dump_config(fp, load_app_config(path))    # 将默认应用程序配置导出到文件中。
        secho(
            f"Exported app config file at {path.as_posix()}.",  # 将应用程序配置文件导出到指定路径。
            fg="yellow",    # 设置输出颜色为黄色。
            bold=True,  # 设置输出为粗体。
        )
        ctx.exit(0)


def export_default_run_config(ctx: click.Context, _, path: Path):   #将默认运行配置导出到指定路径。
    """
    Export the default run configuration to a file.     #将默认运行配置导出到文件中。
    Args:
        ctx (click.Context): The click context object.  #点击上下文对象。
        _ (Any): A placeholder parameter.   #占位参数。
        path (Path): The path to the file where the default run configuration will be exported.     #将默认运行配置导出到文件的路径。
    Returns:
        None
    """
    if path:
        path.parent.mkdir(exist_ok=True, parents=True)  # 创建路径的父目录，如果不存在则创建。
        with open(path, mode="w") as fp:    #以写入模式打开文件。
            RunConfig.dump_config(fp, load_run_config(path))    # 将默认运行配置导出到文件中。
        secho(f"Exported run config file at {path.absolute().as_posix()}", fg="yellow")     # 将运行配置文件导出到指定路径。

        ctx.exit(0)


@click.pass_obj
def disable_cam_callback(conf: _InternalConfig, ctx: click.Context, _, value: str):     #禁用摄像头回调函数。
    """
    Disable the camera.     #禁用摄像头。
    """
    if value:

        secho("Disable camera", fg="red", bold=True)    #禁用摄像头。
        conf.app_config.vision.use_camera = False   #禁用摄像头。


@click.pass_obj
def disable_siglight_callback(conf: _InternalConfig, ctx: click.Context, _, value: str):    #禁用siglight回调函数。
    """
    Disable the siglight.   #禁用siglight。
    """
    if value:

        secho("Disable siglight", fg="red", bold=True)
        conf.app_config.debug.use_siglight = False


def _set_all_log_level(level: int | str):   #设置所有日志级别。
    import pyuptech
    import bdmc
    import mentabotix
    from kazu.logger import set_log_level

    pyuptech.set_log_level(level)   #设置pyuptech日志级别。
    mentabotix.set_log_level(level)     #设置mentabotix日志级别。
    bdmc.set_log_level(level)   #设置bdmc日志级别。
    set_log_level(level)    #设置kazu日志级别。


@click.pass_obj
def log_level_callback(conf: _InternalConfig, ctx: click.Context, _, value: str):   #设置日志级别回调函数。
    """
    Change the log level.
    """
    if value:

        secho(f"Change log level to {value}", fg="magenta", bold=True)
        conf.app_config.debug.log_level = value
        _set_all_log_level(value)


@click.pass_obj
def team_color_callback(conf: _InternalConfig, ctx: click.Context, _, value: str):  # 设置团队颜色回调函数。
    """
    Change the team color.
    """
    if value:

        secho(f"Change team color to {value}", fg=value, bold=True)     # 设置团队颜色。
        conf.app_config.vision.team_color = value   # 设置团队颜色。


def bench_add_app(ctx: click.Context, _, add_up_to):
    """
    Benchmark the execution time of adding up to a given number.    #测量将数字加到给定数字的执行时间。
    """
    if add_up_to is not None:   #如果给定的数字不为空。
        import timeit

        def count_up():
            i = 0
            while i < add_up_to:
                i += 1

        # 测量执行100万次自增操作的耗时，这里repeat=5表示重复执行5次取平均值，number=1表示每次执行1次计数到100万的操作
        execution_time = timeit.timeit(count_up, number=1, globals=globals())   #测量将数字加到给定数字的执行时间。
        echo(f"Execution time of add up to {add_up_to}: {execution_time:.6f} s")    #输出执行时间。


def bench_aps(ctx: click.Context, _, add_up_per_second: bool):  #测量每秒执行次数。
    """
    Benchmark the execution time of adding up to a given number.    #测量将数字加到给定数字的执行时间。
    """

    if add_up_per_second:   #如果每秒执行次数不为空。
        import timeit
        from time import perf_counter_ns

        counter = 0

        end_time = perf_counter_ns() + 1000_000_000
        while perf_counter_ns() < end_time:  # 运行1秒
            counter += 1

        echo(f"Operations per second: {counter}\nAverage counts per ms: {counter / 1000}")


@click.pass_obj
def set_port_callback(conf: _InternalConfig, ctx, _, port: Optional[str]):  # 设置端口回调函数。
    """
    Set the port.
    """
    if port is not None:
        conf.app_config.motion.port = port
        secho(f"Set serial port to {port}", fg="blue", bold=True)


@click.pass_obj
def set_camera_callback(conf: _InternalConfig, ctx, _, camera: Optional[int]):  # 设置摄像头回调函数。
    """
    Set the Camera device id.
    """
    if camera is not None:
        conf.app_config.vision.camera_device_id = camera
        secho(f"Set camera device id to {camera}", fg="blue", bold=True)


@click.pass_obj
def set_res_multiplier_callback(conf: _InternalConfig, ctx, _, multiplier: Optional[int]):  # 设置分辨率回调函数。
    """
    Set the Camera device id.
    """
    if multiplier is not None:
        conf.app_config.vision.camera_device_id = multiplier
        secho(f"Set camera resolution multiplier to {multiplier}", fg="blue", bold=True)


def bench_sleep_precision(ctx, _, enable: bool):    #测量睡眠精度。
    """
    Measure the precision of the sleep function by comparing intended sleep duration
    with the actual elapsed time using a high-resolution timer.

    Args:
        ctx: Context object, potentially used for additional configuration or logging.
        _: Placeholder argument, typically not used.
        enable: A boolean flag to control whether the benchmark should run.

    Returns:
        None, but prints out the precision measurement if enabled.
    """
    if not enable:
        return
    from time import perf_counter, sleep
    from terminaltables import SingleTable

    # Ensure termcolor is installed, if not, install it using pip: `pip install termcolor`  #确保安装了termcolor，如果没有，使用pip安装：`pip install termcolor`

    # Define the range of intervals and the step    #定义间隔范围和步长。
    start_interval = 0.001  # 1 ms
    end_interval = 1.0  # 1 second
    step_interval = 0.050  # 50 ms
    data_trunk = []
    with click.progressbar(
        [i * step_interval for i in range(int((end_interval - start_interval) / step_interval) + 1)],
        show_percent=True,
        show_eta=True,
        label="Measuring precision",
        color=True,
        fill_char=f"{Fore.GREEN}█{Fore.RESET}",
        empty_char=f"{Fore.LIGHTWHITE_EX}█{Fore.RESET}",
    ) as bar:
        for intended_duration in bar:
            start_time = perf_counter()
            sleep(intended_duration)
            end_time = perf_counter()

            actual_duration = end_time - start_time
            precision_offset = actual_duration - intended_duration

            data_trunk.append(
                [f"{intended_duration*1000:.3f}", f"{actual_duration*1000:.3f}", f"{precision_offset*1000:.3f}"]
            )
    data = [["Intended", "Actual", "Offset"]] + data_trunk
    table = SingleTable(data)
    table.inner_column_border = False
    table.inner_heading_row_border = True
    secho(f"{table.table}", bold=True)


def led_light_shell_callback(ctx: click.Context, _, shell):     #LED灯壳回调函数。
    """
    Callback function for the LED light shell.

    Args:
        ctx (click.Context): The click context.
        _ (Any): Unused parameter.
        shell (bool): Flag indicating whether the shell is enabled.

    Returns:
        None: If the shell is not enabled.

    Raises:
        None.

    Description:
        This function is a callback for the LED light shell. It initializes the necessary hardware
        modules and enters a loop to prompt the user for commands. The valid commands are either a
        single number or three numbers separated by spaces. The function validates the input and
        sets the LED lights to the specified color. The loop continues until the user enters the
        "QUIT" command.

        The function also handles the cleanup of the hardware modules and exits the context.

    """
    if not shell:   #如果shell标志为False，则返回
        return
    from kazu.hardwares import screen, sensors
    from pyuptech import Color

    def _validate_cmd(cmd_string: str) -> Tuple[int, int, int] | None:
        cmd_tokens = cmd_string.split()
        length = len(cmd_tokens)
        if length != 1 and length != 3:
            secho(f"Accept only 1 or 3 tokens, got {length}!", fg="red")
            return None

        def _conv(n: str):
            n = int(n)
            if n < 0:
                n = 0
            elif n > 255:
                n = 255
            return n

        try:
            numbers = list(map(_conv, cmd_tokens))
        except ValueError:
            secho(f"Bad token(s), not accept!", fg="red")
            return None

        channels = (numbers[0],) * 3 if length == 1 else tuple(numbers)
        return channels

    sensors.adc_io_open()
    screen.open(2)

    while 1:
        cmd = click.prompt(
            f"{Fore.GREEN}>> ",
            type=click.STRING,
            show_default=False,
            show_choices=False,
            prompt_suffix=f"{Fore.MAGENTA}",
        )
        if cmd == QUIT:
            break
        channel = _validate_cmd(cmd)
        if channel is None:
            continue

        c = Color.new_color(*channel)
        (
            screen.fill_screen(Color.BLACK)
            .set_all_leds_same(c)
            .print(f"R:{channel[0]}\nG:{channel[1]}\nB:{channel[2]}")
            .refresh()
        )
    screen.fill_screen(Color.BLACK).refresh().close().set_all_leds_same(Color.BLACK)
    sensors.adc_io_close()
    ctx.exit(0)


def bench_siglight_switch_freq(ctx: click.Context, _, enable):
    """
    Callback function for the bench_siglight_switch_freq shell. Will test to acquire the signal light switch freq per second    #测试获取信号灯开关每秒频率的回调函数。
    Args:
        ctx:
        _:
        enable:

    Returns:

    """
    if not enable:
        return

    from kazu.signal_light import sig_light_registry
    from time import perf_counter
    from kazu.hardwares import sensors, screen
    from pyuptech import Color

    sensors.adc_io_open()
    screen.set_all_leds_same(Color.BLACK)
    setter_a = sig_light_registry.register_singles("bench", Color.RED, Color.GREEN)
    setter_b = sig_light_registry.register_singles("bench", Color.BLUE, Color.RED)

    DURATION = 10
    counter = 0
    end_time = perf_counter() + DURATION
    while perf_counter() < end_time:
        setter_a()
        setter_b()
        counter += 1

    freq = counter / DURATION
    secho(f"Signal light switch freq: {freq}")
    screen.set_all_leds_same(Color.BLACK)

    sensors.adc_io_close()
