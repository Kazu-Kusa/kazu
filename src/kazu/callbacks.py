from pathlib import Path

import click
from click import secho

from .config import APPConfig, RunConfig


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
    if value:
        app_config: APPConfig = ctx.obj.app_config

        secho("Disable camera", fg="red", bold=True)
        app_config.vision.use_camera = False


def log_level_callback(ctx: click.Context, _, value: str):
    if value:
        app_config: APPConfig = ctx.obj.app_config

        secho(f"Change log level to {value}", fg="magenta", bold=True)
        app_config.logger.log_level = value


def team_color_callback(ctx: click.Context, _, value: str):
    if value:
        app_config: APPConfig = ctx.obj.app_config

        secho(f"Change team color to {value}", fg=value, bold=True)
        app_config.vision.team_color = value
