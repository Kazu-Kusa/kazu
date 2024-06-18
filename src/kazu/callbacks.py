from pathlib import Path
from typing import Optional

import click
from click import secho, echo

from kazu.config import APPConfig, RunConfig, _InternalConfig


def export_default_app_config(ctx: click.Context, _, path: Path):
    """
     Export the default application configuration to the specified path.
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
            APPConfig.dump_config(fp, APPConfig())
        secho(
            f"Exported DEFAULT app config file at {path.as_posix()}.",
            fg="yellow",
            bold=True,
        )
        ctx.exit(0)


def export_default_run_config(ctx: click.Context, _, path: Path):
    """
    Export the default run configuration to a file.
    Args:
        ctx (click.Context): The click context object.
        _ (Any): A placeholder parameter.
        path (Path): The path to the file where the default run configuration will be exported.
    Returns:
        None
    """
    if path:
        path.parent.mkdir(exist_ok=True, parents=True)
        with open(path, mode="w") as fp:
            RunConfig.dump_config(fp, RunConfig())
        secho(f"Exported DEFAULT run config file at {path.absolute().as_posix()}", fg="yellow")
        ctx.exit(0)


@click.pass_obj
def disable_cam_callback(conf: _InternalConfig, ctx: click.Context, _, value: str):
    """
    Disable the camera.
    """
    if value:

        secho("Disable camera", fg="red", bold=True)
        conf.app_config.vision.use_camera = False


def _set_all_log_level(level: int | str):
    import pyuptech
    import bdmc
    import mentabotix
    from kazu.logger import set_log_level

    pyuptech.set_log_level(level)
    mentabotix.set_log_level(level)
    bdmc.set_log_level(level)
    set_log_level(level)


@click.pass_obj
def log_level_callback(conf: _InternalConfig, ctx: click.Context, _, value: str):
    """
    Change the log level.
    """
    if value:

        secho(f"Change log level to {value}", fg="magenta", bold=True)
        conf.app_config.logger.log_level = value
        _set_all_log_level(value)


@click.pass_obj
def team_color_callback(conf: _InternalConfig, ctx: click.Context, _, value: str):
    """
    Change the team color.
    """
    if value:

        secho(f"Change team color to {value}", fg=value, bold=True)
        conf.app_config.vision.team_color = value


def bench_add_app(ctx: click.Context, _, add_up_to):
    """
    Benchmark the execution time of adding up to a given number.
    """
    if add_up_to is not None:
        import timeit

        def count_up():
            i = 0
            while i < add_up_to:
                i += 1

        # 测量执行100万次自增操作的耗时，这里repeat=5表示重复执行5次取平均值，number=1表示每次执行1次计数到100万的操作
        execution_time = timeit.timeit(count_up, number=1, globals=globals())
        echo(f"Execution time of add up to {add_up_to}: {execution_time:.6f} s")


def bench_aps(ctx: click.Context, _, add_up_per_second: bool):
    """
    Benchmark the execution time of adding up to a given number.
    """

    if add_up_per_second:
        import timeit
        from time import perf_counter_ns

        counter = 0

        end_time = perf_counter_ns() + 1000_000_000
        while perf_counter_ns() < end_time:  # 运行1秒
            counter += 1

        echo(f"Operations per second: {counter}\nAverage counts per ms: {counter / 1000}")


@click.pass_obj
def set_port_callback(conf: _InternalConfig, ctx, _, port: Optional[str]):
    """
    Set the port.
    """
    if port is not None:
        conf.app_config.motion.port = port
        secho(f"Set serial port to {port}", fg="blue", bold=True)


@click.pass_obj
def set_camera_callback(conf: _InternalConfig, ctx, _, camera: Optional[int]):
    """
    Set the Camera device id.
    """
    if camera is not None:
        conf.app_config.vision.camera_device_id = camera
        secho(f"Set camera device id to {camera}", fg="blue", bold=True)


@click.pass_obj
def set_res_multiplier_callback(conf: _InternalConfig, ctx, _, multiplier: Optional[int]):
    """
    Set the Camera device id.
    """
    if multiplier is not None:
        conf.app_config.vision.camera_device_id = multiplier
        secho(f"Set camera resolution multiplier to {multiplier}", fg="blue", bold=True)
