from pathlib import Path
from typing import Optional, Tuple

import click
from click import echo, secho
from colorama import Fore

from kazu.config import APPConfig, RunConfig, _InternalConfig, load_app_config, load_run_config
from kazu.constant import QUIT


def export_default_app_config(ctx: click.Context, _, path: Path) -> None:
    """Export the default application configuration to the specified path.

    Args:
        ctx (click.Context): The click context object.
        _ (Any): Ignored parameter.
        path (str): The path to export the default application configuration to.

    Returns:
        None: If the path is not provided.
    """
    if path:
        path.parent.mkdir(exist_ok=True, parents=True)
        with open(path, "w") as fp:
            APPConfig.dump_config(fp, load_app_config(path))
        secho(
            f"Exported app config file at {path.as_posix()}.",
            fg="yellow",
            bold=True,
        )
        ctx.exit(0)


def export_default_run_config(ctx: click.Context, _, path: Path) -> None:
    """Export the default run configuration to a file.

    Args:
        ctx (click.Context): The click context object.
        _ (Any): A placeholder parameter.
        path (Path): The path to the file where the default run configuration will be exported.

    Returns:
        None.
    """
    if path:
        path.parent.mkdir(exist_ok=True, parents=True)
        with open(path, mode="w") as fp:
            RunConfig.dump_config(fp, load_run_config(path))
        secho(f"Exported run config file at {path.absolute().as_posix()}", fg="yellow")

        ctx.exit(0)


@click.pass_obj
def disable_cam_callback(conf: _InternalConfig, ctx: click.Context, _, value: str) -> None:
    """Disable the camera."""
    if value:
        secho("Disable camera", fg="red", bold=True)
        conf.app_config.vision.use_camera = False


@click.pass_obj
def disable_siglight_callback(conf: _InternalConfig, ctx: click.Context, _, value: str) -> None:
    """Disable the siglight."""
    if value:
        secho("Disable siglight", fg="red", bold=True)
        conf.app_config.debug.use_siglight = False


def _set_all_log_level(level: int | str) -> None:
    import bdmc
    import mentabotix
    import pyuptech

    from kazu.logger import set_log_level

    pyuptech.set_log_level(level)
    mentabotix.set_log_level(level)
    bdmc.set_log_level(level)
    set_log_level(level)


@click.pass_obj
def log_level_callback(conf: _InternalConfig, ctx: click.Context, _, value: str) -> None:
    """Change the log level."""
    if value:
        secho(f"Change log level to {value}", fg="magenta", bold=True)
        conf.app_config.debug.log_level = value
        _set_all_log_level(value)


@click.pass_obj
def team_color_callback(conf: _InternalConfig, ctx: click.Context, _, value: str) -> None:
    """Change the team color."""
    if value:
        secho(f"Change team color to {value}", fg=value, bold=True)
        conf.app_config.vision.team_color = value


def bench_add_app(ctx: click.Context, _, add_up_to) -> None:
    """Benchmark the execution time of adding up to a given number."""
    if add_up_to is not None:
        import timeit

        def count_up() -> None:
            i = 0
            while i < add_up_to:
                i += 1

        # 测量执行100万次自增操作的耗时，这里repeat=5表示重复执行5次取平均值，number=1表示每次执行1次计数到100万的操作
        execution_time = timeit.timeit(count_up, number=1, globals=globals())
        echo(f"Execution time of add up to {add_up_to}: {execution_time:.6f} s")


def bench_aps(ctx: click.Context, _, add_up_per_second: bool) -> None:
    """Benchmark the execution time of adding up to a given number."""
    if add_up_per_second:
        from time import perf_counter_ns

        counter = 0

        end_time = perf_counter_ns() + 1000_000_000
        while perf_counter_ns() < end_time:  # 运行1秒
            counter += 1

        echo(f"Operations per second: {counter}\nAverage counts per ms: {counter / 1000}")


@click.pass_obj
def set_port_callback(conf: _InternalConfig, ctx, _, port: Optional[str]) -> None:
    """Set the port."""
    if port is not None:
        conf.app_config.motion.port = port
        secho(f"Set serial port to {port}", fg="blue", bold=True)


@click.pass_obj
def set_camera_callback(conf: _InternalConfig, ctx, _, camera: Optional[int]) -> None:
    """Set the Camera device id."""
    if camera is not None:
        conf.app_config.vision.camera_device_id = camera
        secho(f"Set camera device id to {camera}", fg="blue", bold=True)


@click.pass_obj
def set_res_multiplier_callback(conf: _InternalConfig, ctx, _, multiplier: Optional[int]) -> None:
    """Set the Camera device id."""
    if multiplier is not None:
        conf.app_config.vision.camera_device_id = multiplier
        secho(f"Set camera resolution multiplier to {multiplier}", fg="blue", bold=True)


def bench_sleep_precision(ctx, _, enable: bool) -> None:
    """Measure the precision of the sleep function by comparing intended sleep duration
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

    # Ensure termcolor is installed, if not, install it using pip: `pip install termcolor`

    # Define the range of intervals and the step
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
                [f"{intended_duration * 1000:.3f}", f"{actual_duration * 1000:.3f}", f"{precision_offset * 1000:.3f}"]
            )
    data = [["Intended", "Actual", "Offset"], *data_trunk]
    table = SingleTable(data)
    table.inner_column_border = False
    table.inner_heading_row_border = True
    secho(f"{table.table}", bold=True)


def led_light_shell_callback(ctx: click.Context, _, shell) -> None:
    """Callback function for the LED light shell.

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
    if not shell:
        return
    from pyuptech import Color

    from kazu.hardwares import screen, sensors

    def _validate_cmd(cmd_string: str) -> Tuple[int, int, int] | None:
        cmd_tokens = cmd_string.split()
        length = len(cmd_tokens)
        if length not in {1, 3}:
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
            secho("Bad token(s), not accept!", fg="red")
            return None

        return (numbers[0],) * 3 if length == 1 else tuple(numbers)

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


def bench_siglight_switch_freq(ctx: click.Context, _, enable) -> None:
    """Callback function for the bench_siglight_switch_freq shell. Will test to acquire the signal light switch freq per second
    Args:
        ctx:
        _:
        enable:

    Returns:

    """
    if not enable:
        return

    from time import perf_counter

    from pyuptech import Color

    from kazu.hardwares import screen, sensors
    from kazu.signal_light import sig_light_registry

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
