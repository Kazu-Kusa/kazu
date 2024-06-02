from functools import partial
from pathlib import Path
from time import sleep
from typing import Callable, Optional, Tuple

import bdmc
import click
import mentabotix
import pyuptech
from bdmc import CMD
from click import secho, echo, clear
from mentabotix import MovingState, MovingTransition

from kazu import __version__, __command__
from kazu.callbacks import (
    export_default_app_config,
    export_default_run_config,
    disable_cam_callback,
    log_level_callback,
    team_color_callback,
    bench_add_app,
    bench_aps,
)
from kazu.config import (
    DEFAULT_APP_CONFIG_PATH,
    APPConfig,
    _InternalConfig,
    ContextVar,
    TagGroup,
    load_run_config,
    load_app_config,
)
from kazu.constant import Env, RunMode
from kazu.logger import set_log_level
from kazu.visualize import print_colored_toml


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
def main(ctx: click.Context, app_config_path: Path):
    """A Dedicated Robots Control System"""
    app_config = load_app_config(app_config_path)

    ctx.obj = _InternalConfig(app_config=app_config, app_config_file_path=app_config_path)
    _set_all_log_level(ctx.obj.app_config.logger.log_level)


@main.command("config")
@click.pass_obj
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
    config: _InternalConfig,
    kv: Optional[Tuple[str, str]],
    **_,
):
    """
    Configure KAZU
    """

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
        secho(e, fg="red", bold=True)
    finally:
        with open(config.app_config_file_path, "w") as fp:
            APPConfig.dump_config(fp, app_config)


@main.command("run")
@click.pass_obj
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
def run(conf: _InternalConfig, run_config: Path | None, mode: str, **_):
    """
    Run command for the main group.
    """
    from kazu.compile import botix

    run_config = load_run_config(run_config)

    app_config = conf.app_config

    from kazu.hardwares import inited_controller

    con = inited_controller(app_config)
    con.context.update(ContextVar.export_context())
    try:
        match mode:
            case RunMode.FGS:
                from kazu.assembly import assmbly_FGS_schema

                boot_pool, stage_pool = assmbly_FGS_schema(app_config, run_config)
                botix.token_pool = boot_pool
                boot_func = botix.compile()
                botix.token_pool = stage_pool
                stage_func = botix.compile()
                boot_func()
                while 1:
                    stage_func()
            case RunMode.NGS:
                from kazu.assembly import assmbly_NGS_schema

                botix.token_pool = assmbly_NGS_schema(app_config, run_config)
                stage_func = botix.compile()
                while 1:
                    stage_func()
            case RunMode.AFG:
                from kazu.assembly import assmbly_AFG_schema

                botix.token_pool = assmbly_AFG_schema(app_config, run_config)
                afg_func = botix.compile()
                while 1:
                    afg_func()
            case RunMode.ANG:
                from kazu.assembly import assmbly_ANG_schema

                botix.token_pool = assmbly_ANG_schema(app_config, run_config)
                ang_func = botix.compile()
                while 1:
                    ang_func()
            case RunMode.FGDL:
                from kazu.assembly import assmbly_FGDL_schema

                botix.token_pool = assmbly_FGDL_schema(app_config, run_config)
                boot_func = botix.compile()
                while 1:
                    boot_func()
    except KeyboardInterrupt:
        secho(f"Exited by user.", fg="red")
    finally:
        con.send_cmd(CMD.FULL_STOP).send_cmd(CMD.RESET).stop_msg_sending()
        secho(f"KAZU stopped.", fg="green")


@main.command("check")
@click.help_option("-h", "--help")
@click.pass_obj
@click.argument(
    "device",
    type=click.Choice(["mot", "cam", "adc", "io", "mpu", "pow", "all"]),
    nargs=-1,
)
def test(conf: _InternalConfig, device: str):
    """
    Check devices' normal functions
    """
    app_config: APPConfig = conf.app_config

    from kazu.checkers import check_io, check_camera, check_adc, check_motor, check_power, check_mpu
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
        from kazu.hardwares import tag_detector, controller, sensors

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
        from kazu.hardwares import sensors

        sensors.adc_io_open()
        table.append(shader("ADC", check_adc(sensors)))
        sensors.adc_io_close()
    if "io" in device:
        from kazu.hardwares import sensors

        sensors.adc_io_open()
        table.append(shader("IO", check_io(sensors)))
        sensors.adc_io_close()
    if "mpu" in device:
        from kazu.hardwares import sensors

        sensors.MPU6500_Open()
        table.append(shader("MPU", check_mpu(sensors)))

    if "pow" in device:
        from kazu.hardwares import sensors

        table.append(shader("POWER", check_power(sensors)))

    if "cam" in device:
        from kazu.hardwares import tag_detector

        tag_detector.open_camera(app_config.vision.camera_device_id)
        table.append(shader("CAMERA", check_camera(tag_detector)))

    if "mot" in device:
        from kazu.hardwares import controller
        from kazu.hardwares import sensors
        from bdmc import CMD

        controller.serial_client.port = app_config.motion.port

        controller.serial_client.open()
        controller.start_msg_sending().send_cmd(CMD.RESET)
        table.append(shader("MOTOR", check_motor(controller)))

    secho(SingleTable(table).table)


@main.command("read")
@click.help_option("-h", "--help")
@click.pass_obj
@click.argument(
    "device",
    type=click.Choice(["adc", "io", "mpu", "all"]),
    nargs=-1,
)
@click.option("-i", "interval", type=click.FLOAT, default=0.1, show_default=True)
def read_sensors(conf: _InternalConfig, interval: float, device: str):
    """
    Read sensors data and print to terminal
    """
    from pyuptech import (
        make_mpu_table,
        make_io_table,
        make_adc_table,
    )
    from kazu.hardwares import sensors

    app_config: APPConfig = conf.app_config
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
            case _:
                raise ValueError(f"Invalid device: {dev}")
    try:
        while 1:
            stdout: str = "\n".join(pack() for pack in packs)
            clear()
            echo(stdout)
            sleep(interval)
    except KeyboardInterrupt:
        echo("Exit reading.")

    sensors.adc_io_close()


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
    nargs=-1,
)
@click.option(
    "-d",
    "--destination",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="./visualize",
    show_default=True,
    help="Destination path of the generated files",
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
def visualize(
    conf: _InternalConfig,
    destination: Path,
    run_config: Optional[Path],
    packname: str = ("all",),
):
    """
    Visualize State-Transition Diagram of KAZU with PlantUML

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

    destination.mkdir(parents=True, exist_ok=True)

    app_config = conf.app_config
    run_config = load_run_config(run_config)

    tag_group = TagGroup(team_color=app_config.vision.team_color)
    handlers = {
        "edge": make_edge_handler,
        "boot": make_reboot_handler,
        "bkstage": make_back_to_stage_handler,
        "surr": partial(make_surrounding_handler, tag_group=tag_group),
        "scan": make_scan_handler,
        "search": make_search_handler,
        "fence": make_fence_handler,
        "rdwalk": make_rand_walk_handler,
        "stdbat": partial(make_std_battle_handler, tag_group=tag_group),
        "onstage": partial(make_always_on_stage_battle_handler, tag_group=tag_group),
        "angbat": partial(make_always_on_stage_battle_handler, tag_group=tag_group),
        "afgbat": make_always_off_stage_battle_handler,
    }

    # 如果packname是'all'，则导出所有；否则，仅导出指定的包
    packs_to_export = list(handlers.keys()) if "all" in packname else packname

    destination.mkdir(parents=True, exist_ok=True)

    for f_name in packs_to_export:
        # 假设每个处理函数返回一个可以被导出的数据结构
        # 这里简化处理，实际可能需要根据handler的不同调用不同的导出方法
        handler_func: Callable = handlers.get(f_name)

        (*_, handler_data) = handler_func(app_config=app_config, run_config=run_config)
        filename = f_name + ".puml"
        destination_filename = (destination / filename).as_posix()
        secho(f"Exporting {filename}", fg="green", bold=True)
        botix.export_structure(destination_filename, handler_data)


@main.command("cmd", context_settings={"ignore_unknown_options": True})
@click.help_option("-h", "--help")
@click.pass_obj
@click.argument("duration", type=click.FLOAT, required=True)
@click.argument("speeds", nargs=-1, type=click.INT, required=True)
def control_motor(conf: _InternalConfig, duration: float, speeds: list[int]):
    """
    Control motor by sending command.

    move the bot at <SPEEDS> for <DURATION> seconds, then stop.

    Args:

        SPEEDS: (int) | (int,int) | (int,int,int,int)

        DURATION: (float)
    """
    from kazu.compile import composer, botix
    from kazu.hardwares import inited_controller
    from colorama import Fore

    app_config = conf.app_config
    controller = inited_controller(app_config)
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
            range(int(duration / 0.1) - 1),
            show_percent=True,
            show_eta=True,
            label="Moving",
            color=True,
            fill_char=f"{Fore.GREEN}█{Fore.RESET}",
            empty_char=f"{Fore.LIGHTWHITE_EX}█{Fore.RESET}",
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
    from kazu.hardwares import screen, sensors
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
def bench(**_):
    """
    Benchmarks
    """
    echo("bench test done!")
