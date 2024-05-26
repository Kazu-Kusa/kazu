from pathlib import Path
from time import sleep
from typing import Callable, Optional, Tuple

import bdmc
import click
import mentabotix
import pyuptech
from bdmc import MotorInfo, CMD
from click import secho, echo, clear
from mentabotix import MovingState, MovingTransition

from . import __version__, __command__
from .callbacks import (
    export_default_app_config,
    export_default_run_config,
    disable_cam_callback,
    log_level_callback,
    team_color_callback,
)
from .compile import (
    botix,
    make_edge_handler,
    make_reboot_handler,
    make_back_to_stage_handler,
    make_surrounding_handler,
    make_scan_handler,
    make_search_handler,
)
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


@main.command("config")
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
def configure(
    context: click.Context,
    kv: Optional[Tuple[str, str]],
    **_,
):
    """
    Configure KAZU
    """
    config: _InternalConfig = context.obj
    app_config = config.app_config
    print(f"kv: {kv}")
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
@click.option(
    "-e",
    "--disable-camera",
    is_flag=True,
    default=False,
    show_default=True,
    help="Run with the camera disabled.",
    callback=disable_cam_callback,
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
    "-l",
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Change log level temporarily.",
    default=None,
    show_default=True,
    callback=log_level_callback,
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
def run(ctx: click.Context, run_config: Path | None, mode: str, **_):
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

    app_config = internal_config.app_config

    from .hardwares import controller

    controller.motor_infos = (
        MotorInfo(*app_config.motion.motor_fl),
        MotorInfo(*app_config.motion.motor_rl),
        MotorInfo(*app_config.motion.motor_rr),
        MotorInfo(*app_config.motion.motor_fr),
    )
    controller.serial_client.port = app_config.motion.port
    controller.serial_client.open()
    controller.start_msg_sending().send_cmd(CMD.RESET)

    if app_config.vision.use_camera:
        from .hardwares import tag_detector
        from .config import TagGroup

        secho(f"Open Camera-{app_config.vision.camera_device_id}", fg="yellow", bold=True)
        tag_detector.open_camera(app_config.vision.camera_device_id)
        success, _ = tag_detector.camera_device.read()
        if success:
            secho("Camera opened successfully", fg="green", bold=True)
            tag_group = TagGroup(team_color=app_config.vision.team_color)
            secho(f"Team color: {tag_group.team_color}", fg=tag_group.team_color, bold=True)
            secho(f"Enemy tag: {tag_group.enemy_tag}", fg="red", bold=True)
            secho(f"Allay tag: {tag_group.allay_tag}", fg="green", bold=True)
            secho(f"Neutral tag: {tag_group.neutral_tag}", fg="cyan", bold=True)
        else:
            from .config import TagGroup

            # TODO remove this debug code
            tag_group = TagGroup(team_color=app_config.vision.team_color)
            secho(f"Failed to open Camera-{app_config.vision.camera_device_id}", fg="red", bold=True)
            app_config.vision.use_camera = False
    # TODO remove this debug code below
    app_config.vision.use_camera = True

    edge_pack = make_edge_handler(app_config, run_config)

    boot_pack = make_reboot_handler(app_config, run_config)

    backstage_pack = make_back_to_stage_handler(run_config)

    surr_pack = make_surrounding_handler(app_config, run_config, tag_group)
    scan_pack = make_scan_handler(app_config, run_config)

    search_pack = make_search_handler(app_config, run_config)
    botix.export_structure("edge.puml", edge_pack[-1])
    botix.export_structure("boot.puml", boot_pack[-1])
    botix.export_structure("backstage.puml", backstage_pack[-1])
    botix.export_structure("surr.puml", surr_pack[-1])
    botix.export_structure("scan.puml", scan_pack[-1])
    botix.export_structure("search.puml", search_pack[-1])


@main.command("check")
@click.help_option("-h", "--help")
@click.pass_context
@click.argument(
    "device",
    type=click.Choice(["mot", "cam", "adc", "io", "mpu", "pow", "all"]),
    nargs=-1,
)
def test(ctx: click.Context, device: str):
    """
    Check devices' normal functions
    """
    app_config: APPConfig = ctx.obj.app_config

    from .checkers import check_io, check_camera, check_adc, check_motor, check_power, check_mpu
    from terminaltables import SingleTable
    from colorama import Fore

    device = device or ("all",)
    shader = lambda dev_name, success: [
        f"{Fore.LIGHTYELLOW_EX if success else Fore.RED}{dev_name}{Fore.RESET}",
        f"{Fore.GREEN if success else Fore.RED}{success}{Fore.RESET}",
    ]

    table = [[f"{Fore.YELLOW}Device{Fore.RESET}", f"{Fore.GREEN}Success{Fore.RESET}"]]
    if "all" in device:
        from bdmc import CMD
        from .hardwares import tag_detector
        from .hardwares import controller
        from .hardwares import sensors

        sensors.adc_io_open().MPU6500_Open()
        controller.serial_client.port = app_config.motion.port
        tag_detector.open_camera(app_config.vision.camera_device_id)
        controller.serial_client.open()
        controller.start_msg_sending().send_cmd(CMD.RESET)
        table.append(shader("IO", check_io(sensors)))
        table.append(shader("ADC", check_adc(sensors)))
        table.append(shader("MPU", check_mpu(sensors)))
        table.append(shader("CAMERA", check_camera(tag_detector)))
        table.append(shader("MOTOR", check_motor(controller)))
        table.append(shader("POWER", check_power(sensors)))
        secho(SingleTable(table).table)
        controller.stop_msg_sending()
        sensors.adc_io_close()
        return

    if "adc" in device:
        from .hardwares import sensors

        sensors.adc_io_open()
        table.append(shader("ADC", check_adc(sensors)))
        sensors.adc_io_close()
    if "io" in device:
        from .hardwares import sensors

        sensors.adc_io_open()
        table.append(shader("IO", check_io(sensors)))
        sensors.adc_io_close()
    if "mpu" in device:
        from .hardwares import sensors

        sensors.MPU6500_Open()
        table.append(shader("MPU", check_mpu(sensors)))

    if "pow" in device:
        from .hardwares import sensors

        table.append(shader("POWER", check_power(sensors)))

    if "cam" in device:
        from .hardwares import tag_detector

        tag_detector.open_camera(app_config.vision.camera_device_id)
        table.append(shader("CAMERA", check_camera(tag_detector)))

    if "mot" in device:
        from .hardwares import controller
        from .hardwares import sensors
        from bdmc import CMD

        controller.serial_client.port = app_config.motion.port

        controller.serial_client.open()
        controller.start_msg_sending().send_cmd(CMD.RESET)
        table.append(shader("MOTOR", check_motor(controller)))

    secho(SingleTable(table).table)


@main.command("read")
@click.help_option("-h", "--help")
@click.pass_context
@click.argument(
    "device",
    type=click.Choice(["adc", "io", "mpu", "all"]),
    nargs=-1,
)
@click.option("-i", "interval", type=click.FLOAT, default=0.1, show_default=True)
def read_sensors(ctx: click.Context, interval: float, device: str):
    """
    Read sensors data and print to terminal
    """
    from pyuptech import (
        make_mpu_table,
        make_io_table,
        make_adc_table,
    )
    from .hardwares import sensors

    app_config: APPConfig = ctx.obj.app_config
    device = set(device) or ("all",)
    (
        sensors.adc_io_open()
        .MPU6500_Open()
        .set_all_io_mode(0)
        .mpu_set_gyro_fsr(app_config.sensor.gyro_fsr)
        .mpu_set_accel_fsr(app_config.sensor.accel_fsr)
    )

    if "all" in device:
        device = ("adc", "io", "mpu")

    packs = []
    for dev in device:
        match dev:
            case "adc":
                packs.append(lambda: make_adc_table(sensors))

            case "io":
                packs.append(lambda: make_io_table(sensors))
            case "mpu":
                packs.append(lambda: make_mpu_table(sensors))

    try:
        while 1:
            stdout: str = "\n".join(pack() for pack in packs)
            clear()
            echo(stdout)
            sleep(interval)
    except KeyboardInterrupt:
        echo("Exit reading.")

    sensors.adc_io_close()


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
    from .compile import composer, botix
    from .hardwares import controller
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


@main.command("light")
@click.help_option("-h", "--help")
@click.argument("channel", type=click.IntRange(0, 255), nargs=3, required=True)
def control_display(channel: Tuple[int, int, int]):
    """
    Control LED display.
    """
    from .hardwares import screen, sensors
    from pyuptech import Color

    sensors.adc_io_open()
    c = Color.new_color(*channel)
    (
        screen.set_led_0(c)
        .set_led_1(c)
        .open(2)
        .set_back_color(c)
        .print(f"R:{channel[0]}\nG:{channel[1]}\nB:{channel[2]}")
        .refresh()
    )
