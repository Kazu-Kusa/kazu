from pathlib import Path
from time import sleep
from typing import Callable, Optional, Tuple

import bdmc
import click
import mentabotix
import pyuptech
from click import secho
from mentabotix import MovingState, MovingTransition

from . import __version__, __command__
from .compile import botix, make_edge_handler, make_reboot_handler, make_back_to_stage_handler
from .config import DEFAULT_APP_CONFIG_PATH, APPConfig, _InternalConfig, RunConfig
from .constant import Env, RunMode
from .logger import set_log_level
from .visualize import print_colored_toml


def _set_all_log_level(level: int | str):
    pyuptech.set_log_level(level)
    mentabotix.set_log_level(level)
    bdmc.set_log_level(level)
    set_log_level(level)


@click.group(
    epilog=r"For more details, Check at https://github.com/Kazu-Kusa/kazu",
)
@click.help_option("-h", "--help")
@click.version_option(__version__, "-v", "--version", prog_name=__command__)
@click.pass_context
@click.option(
    "-a",
    "--app-config-path",
    envvar=Env.KAZU_APP_CONFIG_PATH,
    default=DEFAULT_APP_CONFIG_PATH,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help=f"config file path, also can receive env {Env.KAZU_APP_CONFIG_PATH}",
)
def main(ctx: click.Context, app_config_path):
    """A Dedicated Robots Control System"""
    if (config_path := Path(app_config_path)).exists():
        with open(app_config_path, encoding="utf-8") as fp:
            app_config = APPConfig.read_config(fp)
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        app_config = APPConfig()
        with open(app_config_path, "w", encoding="utf-8") as fp:
            APPConfig.dump_config(fp, app_config)

    ctx.obj = _InternalConfig(app_config=app_config, app_config_file_path=app_config_path)
    _set_all_log_level(ctx.obj.app_config.logger.log_level)


def reset_config(ctx: click.Context, *_):
    ctx.obj.app_config = APPConfig()
    with open(ctx.obj.app_config_file_path, "w") as fp:
        APPConfig.dump_config(fp, ctx.obj.app_config)
    secho(f"Reset config file at {Path(ctx.obj.app_config_file_path).absolute().as_posix()} to default.", fg="yellow")
    ctx.exit(0)


def export_default_runconfig(ctx: click.Context, _, path: Path):
    if path:
        path = Path(path)
        path.parent.mkdir(exist_ok=True, parents=True)
        with open(path, mode="w") as fp:
            RunConfig.dump_config(fp, RunConfig())
        secho(f"Exported config file at {path.absolute().as_posix()}", fg="yellow")
    ctx.exit(0)


@main.command("config")
@click.help_option("-h", "--help")
@click.option(
    "-e",
    "--export-path",
    help=f"Path of the exported config template file",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    callback=export_default_runconfig,
)
@click.option(
    "-r",
    "--reset",
    is_flag=True,
    default=False,
    required=False,
    show_default=True,
    help="Reset config",
    callback=reset_config,
)
@click.pass_context
@click.argument("kv", type=(str, str), required=False)
def configure(context: click.Context, kv: Optional[Tuple[str, str]] = None):
    """
    Configure KAZU
    """
    config: _InternalConfig = context.obj
    app_config = config.app_config
    if kv is None:
        from toml import dumps

        secho(f"Config file at {Path(config.app_config_file_path).absolute().as_posix()}", fg="green", bold=True)
        print_colored_toml(dumps(APPConfig.model_dump(app_config)))
        return
    key, value = kv
    try:
        exec(f"app_config.{key} = '{value}'")
    except Exception as e:
        print(e)
    finally:
        with open(config.app_config_file_path, "w") as fp:
            APPConfig.dump_config(fp, app_config)


@main.command("run")
@click.pass_context
@click.help_option("-h", "--help")
@click.option("-e", "--use-camera", is_flag=True, default=True, show_default=True, help="If use camera")
@click.option(
    "-t",
    "--team-color",
    default="blue",
    show_default=True,
    type=click.Choice(["blue", "yellow"]),
    help="Change allay team color temporarily.",
)
@click.option(
    "-c",
    "--run-config",
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
def run(ctx: click.Context, use_camera: bool, team_color: str, run_config: Path | None, mode: str):
    """
    Run command for the main group.
    """

    internal_config: _InternalConfig = ctx.obj
    if run_config and (r_conf := Path(run_config)).exists():
        secho(f'Loading run config from "{r_conf.absolute().as_posix()}"', fg="green", bold=True)
        with open(r_conf) as fp:
            run_config: RunConfig = RunConfig.read_config(fp)
    else:
        secho(f"Loading DEFAULT run config", fg="yellow", bold=True)
        run_config = RunConfig()

    edge_pack = make_edge_handler(internal_config.app_config, run_config)

    boot_pack = make_reboot_handler(internal_config.app_config, run_config)

    backstage_pack = make_back_to_stage_handler(run_config)
    botix.export_structure("edge.puml", edge_pack[-1])
    botix.export_structure("boot.puml", boot_pack[-1])
    botix.export_structure("backstage.puml", backstage_pack[-1])
    print(use_camera, team_color, run_config, mode)


@main.command("check")
@click.help_option("-h", "--help")
@click.pass_context
@click.argument(
    "device",
    type=click.Choice(devs := ["mot", "cam", "adc", "io", "mpu", "pow", "all"]),
    nargs=-1,
)
def test(ctx: click.Context, device: str = ("all",)):
    """
    Check devices' normal functions
    """
    app_config: APPConfig = ctx.obj.app_config

    from .checkers import check_io, check_camera, check_adc, check_motor, check_power, check_mpu
    from terminaltables import SingleTable
    from colorama import Fore

    shader = lambda dev_name, success: [
        f"{Fore.LIGHTYELLOW_EX if success else Fore.RED}{dev_name}{Fore.RESET}",
        f"{Fore.GREEN if success else Fore.RED}{success}{Fore.RESET}",
    ]

    table = [[f"{Fore.YELLOW}Device{Fore.RESET}", f"{Fore.GREEN}Success{Fore.RESET}"]]
    if "all" in device or device == ():
        from bdmc import CMD
        from cv2 import VideoCapture
        from .compile import controller, sensors

        controller.serial_client.port = app_config.motion.port

        controller.serial_client.open()
        controller.start_msg_sending().send_cmd(CMD.RESET)
        table.append(shader("IO", check_io(sensors)))
        table.append(shader("ADC", check_adc(sensors)))
        table.append(shader("MPU", check_mpu(sensors)))
        table.append(shader("POWER", check_power(sensors)))
        table.append(shader("MOTOR", check_motor(controller)))
        table.append(shader("CAMERA", check_camera(VideoCapture(app_config.vision.camera_device_id))))
        secho(
            SingleTable(table).table,
            fg="green",
        )
        controller.stop_msg_sending()
        return

    if "adc" in device:
        from .compile import sensors

        table.append(shader("ADC", check_adc(sensors)))

    if "io" in device:
        from .compile import sensors

        table.append(shader("IO", check_io(sensors)))

    if "mpu" in device:
        from .compile import sensors

        table.append(shader("MPU", check_mpu(sensors)))

    if "pow" in device:
        from .compile import sensors

        table.append(shader("POWER", check_power(sensors)))

    if "cam" in device:
        from cv2 import VideoCapture

        table.append(shader("CAMERA", check_camera(VideoCapture(app_config.vision.camera_device_id))))

    if "mot" in device:
        from .compile import controller, sensors
        from bdmc import CMD

        controller.serial_client.port = app_config.motion.port

        controller.serial_client.open()
        controller.start_msg_sending().send_cmd(CMD.RESET)
        table.append(shader("MOTOR", check_motor(controller)))

    secho(
        SingleTable(table).table,
    )


@main.command("cmd")
@click.help_option("-h", "--help")
@click.pass_context
@click.argument("duration", type=click.FLOAT, required=True)
@click.argument("speeds", nargs=-1, type=click.INT, required=True)
def control_motor(ctx: click.Context, duration: float, speeds: list[int]):
    """
    Control motor by sending command.

    move the bot at <SPEEDS> for <DURATION> seconds, then stop.

    Args:

        SPEEDS: (int) | (int,int) | (int,int,int,int)

        DURATION: (float)
    """
    from .compile import composer, botix, controller
    from colorama import Fore

    internal_conf: _InternalConfig = ctx.obj
    controller.serial_client.port = internal_conf.app_config.motion.port
    controller.serial_client.open()
    controller.start_msg_sending()
    try:
        states, transitions = (
            composer.init_container()
            .add(state := MovingState(*speeds))
            .add(MovingTransition(duration))
            .add(MovingState(0))
            .export_structure()
        )
    except ValueError as e:
        secho(f"{e}", fg="red")
        return

    botix.token_pool = transitions

    secho(
        f"Move as {Fore.YELLOW}{state.unwrap()}{Fore.RESET} for {Fore.YELLOW}{duration}{Fore.RESET} seconds",
    )
    fi: Callable[[], None] = botix.compile(return_median=False)

    def _bar():
        with click.progressbar(
            range(int(duration / 0.1)), show_percent=True, show_eta=True, label="Moving", color=True
        ) as bar:
            for _ in bar:
                sleep(0.1)

    import threading

    t = threading.Thread(target=_bar, daemon=True)
    t.start()
    fi()
    controller.stop_msg_sending()