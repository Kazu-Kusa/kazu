from io import TextIOWrapper
from pathlib import Path
from typing import Callable

import bdmc
import click
import mentabotix
import pyuptech
from mentabotix import MovingState, MovingTransition

from . import __version__, __command__
from .config import Env, RunMode, DEFAULT_APP_CONFIG_PATH, APPConfig, _InternalConfig
from .logger import set_log_level


def _set_all_log_level(level: int | str):
    pyuptech.set_log_level(level)
    mentabotix.set_log_level(level)
    bdmc.set_log_level(level)
    set_log_level(level)


@click.group()
@click.pass_context
@click.version_option(__version__, "-v", "--version", prog_name=__command__)
@click.help_option("-h", "--help")
@click.option(
    "-a",
    "--app-config-path",
    envvar=Env.KAZU_APP_CONFIG_PATH,
    default=DEFAULT_APP_CONFIG_PATH,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help=f"config file path, also can receive env {Env.KAZU_APP_CONFIG_PATH}",
)
def main(ctx: click.Context, app_config_path):
    """
    A Dedicated Robots Control System
    """
    if (config_path := Path(app_config_path)).exists():
        with open(app_config_path) as fp:
            app_config = APPConfig.read_config(fp)
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        app_config = APPConfig()
        with open(app_config_path, "w") as fp:
            APPConfig.dump_config(fp, app_config)

    ctx.obj = _InternalConfig(app_config=app_config, app_config_file_path=app_config_path)
    _set_all_log_level(ctx.obj.app_config.logger.log_level)


@main.command("config")
@click.help_option("-h", "--help")
@click.pass_context
@click.argument("key")
@click.argument("value")
def configure(context: click.Context, key: str, value: str):
    """
    Configure KAZU
    """
    config: _InternalConfig = context.obj
    app_config = config.app_config
    try:
        exec(f"app_config.{key} = '{value}'")
    except Exception as e:
        print(e)
    finally:
        with open(config.app_config_file_path, "w") as fp:
            APPConfig.dump_config(fp, app_config)


@main.command("run")
@click.help_option("-h", "--help")
@click.option("-e", "--use-camera", is_flag=True, default=True, help="use camera")
@click.option("-t", "--team-color", default="blue", type=click.Choice(["blue", "yellow"]), help="team color")
@click.option(
    "-c",
    "--run-config",
    default=None,
    help=f"config file path, also can receive env {Env.KAZU_RUN_CONFIG_PATH}",
    type=click.File("r", encoding="utf-8"),
    envvar=Env.KAZU_RUN_CONFIG_PATH,
)
@click.option(
    "-m",
    "--mode",
    default=RunMode.FGS,
    type=click.Choice(RunMode.export()),
    help=f"run mode, also can receive env {Env.KAZU_RUN_MODE}",
    envvar=Env.KAZU_RUN_MODE,
)
def run(use_camera: bool, team_color: str, run_config: TextIOWrapper | None, mode: str):
    """
    Run command for the main group.
    """
    print(use_camera, team_color, run_config, mode)


@main.command("check")
@click.help_option("-h", "--help")
@click.argument("device", type=click.Choice(["mot", "cam", "led", "lcd", "adc", "io", "mpu", "pow"]))
def test(device: str):
    """
    Check devices.
    """
    print(device)


@main.command("cmd")
@click.argument("duration", type=click.FLOAT)
@click.argument("speeds", nargs=-1, type=click.INT)
def control_motor(duration: float, speeds: list[int]):
    """
    Control motor by sending command.
    """
    from .compile import composer, botix

    states, transitions = (
        composer.init_container()
        .add(MovingState(*speeds))
        .add(MovingTransition(duration))
        .add(MovingState(0))
        .export_structure()
    )
    botix.token_pool = transitions

    fi: Callable[[], None] = botix.compile(return_median=False)
    fi()
