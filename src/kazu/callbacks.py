from pathlib import Path

import click
from click import secho, echo

from kazu.config import APPConfig, RunConfig


def export_default_app_config(ctx: click.Context, _, path):
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
        ctx.obj.app_config = APPConfig()
        with open(ctx.obj.app_config_file_path, "w") as fp:
            APPConfig.dump_config(fp, ctx.obj.app_config)
        secho(
            f"Exported DEFAULT app config file at {Path(ctx.obj.app_config_file_path).absolute().as_posix()} to default.",
            fg="yellow",
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


def disable_cam_callback(ctx: click.Context, _, value: bool):
    """
    Disable the camera.
    """
    if value:
        app_config: APPConfig = ctx.obj.app_config

        secho("Disable camera", fg="red", bold=True)
        app_config.vision.use_camera = False


def log_level_callback(ctx: click.Context, _, value: str):
    """
    Change the log level.
    """
    if value:
        app_config: APPConfig = ctx.obj.app_config

        secho(f"Change log level to {value}", fg="magenta", bold=True)
        app_config.logger.log_level = value


def team_color_callback(ctx: click.Context, _, value: str):
    """
    Change the team color.
    """
    if value:
        app_config: APPConfig = ctx.obj.app_config

        secho(f"Change team color to {value}", fg=value, bold=True)
        app_config.vision.team_color = value


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
