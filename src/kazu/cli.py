from enum import Enum
from functools import partial
from pathlib import Path
from time import sleep
from typing import Callable, Optional, Tuple, List, Type

import click
from click import secho, echo, clear
from colorama import Fore

from kazu import __version__, __command__
from kazu.callbacks import (
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
from kazu.constant import Env, RunMode, QUIT
from kazu.logger import _logger
from kazu.signal_light import sig_light_registry
from kazu.visualize import print_colored_toml


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
@click.option(
    "-l",
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Change log level temporarily.",
    default=None,
    show_default=True,
)
def main(ctx: click.Context, app_config_path: Path, log_level: str):
    """A Dedicated Robots Control System"""
    app_config = load_app_config(app_config_path)

    ctx.obj = _InternalConfig(app_config=app_config, app_config_file_path=app_config_path)

    log_level_callback(ctx=ctx, _=None, value=log_level)


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
def run(conf: _InternalConfig, run_config_path: Path | None, mode: str, **_):
    """
    Run command for the main group.
    """
    from kazu.compile import botix
    from bdmc import CMD

    run_config = load_run_config(run_config_path)

    app_config = conf.app_config

    from kazu.hardwares import inited_controller, sensors, inited_tag_detector
    from kazu.signal_light import set_all_black

    sensors.adc_io_open().MPU6500_Open()
    tag_detector = inited_tag_detector(app_config)
    con = inited_controller(app_config)
    con.context.update(ContextVar.export_context())
    _logger.info(f"Run Mode: {mode}")
    try:
        match mode:
            case RunMode.FGS:
                # O[F]F STA[G]E [S]TART
                from kazu.assembly import assembly_FGS_schema

                boot_pool, stage_pool = assembly_FGS_schema(app_config, run_config)
                botix.token_pool = boot_pool
                boot_func = botix.compile()
                botix.token_pool = stage_pool
                stage_func = botix.compile()
                boot_func()
                while 1:
                    stage_func()
            case RunMode.NGS:
                # O[N] STA[G]E [S]TART
                from kazu.assembly import assembly_NGS_schema

                botix.token_pool = assembly_NGS_schema(app_config, run_config)
                stage_func = botix.compile()
                while 1:
                    stage_func()
            case RunMode.AFG:
                # [A]LWAYS O[F]F STA[G]E
                from kazu.assembly import assembly_AFG_schema

                botix.token_pool = assembly_AFG_schema(app_config, run_config)
                off_stage_func = botix.compile()
                while 1:
                    off_stage_func()
            case RunMode.ANG:
                # [A]LWAYS O[N] STA[G]E
                from kazu.assembly import assembly_ANG_schema

                botix.token_pool = assembly_ANG_schema(app_config, run_config)
                on_stage_func = botix.compile()
                while 1:
                    on_stage_func()
            case RunMode.FGDL:
                # O[F]F STA[G]E [D]ASH [L]OOP
                from kazu.assembly import assembly_FGDL_schema

                botix.token_pool = assembly_FGDL_schema(app_config, run_config)
                boot_func = botix.compile()
                while 1:
                    boot_func()
    except KeyboardInterrupt:
        _logger.info("KAZU stopped by keyboard interrupt.")
    finally:
        _logger.info(f"Releasing hardware resources...")
        set_all_black()
        sensors.adc_io_close()
        tag_detector.release_camera()
        con.send_cmd(CMD.FULL_STOP).send_cmd(CMD.RESET).stop_msg_sending()
        _logger.info(f"KAZU stopped.")


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
def test(conf: _InternalConfig, device: str, **_):
    """
    Check devices' normal functions
    """
    app_config: APPConfig = conf.app_config

    from kazu.checkers import check_io, check_camera, check_adc, check_motor, check_power, check_mpu
    from terminaltables import SingleTable

    def _shader(dev_name: str, success: bool) -> List[str]:
        return [
            f"{Fore.LIGHTYELLOW_EX if success else Fore.RED}{dev_name}{Fore.RESET}",
            f"{Fore.GREEN if success else Fore.RED}{success}{Fore.RESET}",
        ]

    table = [[f"{Fore.YELLOW}Device{Fore.RESET}", f"{Fore.GREEN}Success{Fore.RESET}"]]
    if not device or "all" in device:
        device = devs

    if "adc" in device:
        from kazu.hardwares import sensors

        sensors.adc_io_open()
        table.append(_shader("ADC", check_adc(sensors)))
        sensors.adc_io_close()
    if "io" in device:
        from kazu.hardwares import sensors

        sensors.adc_io_open()
        table.append(_shader("IO", check_io(sensors)))
        sensors.adc_io_close()
    if "mpu" in device:
        from kazu.hardwares import sensors

        sensors.MPU6500_Open()
        table.append(_shader("MPU", check_mpu(sensors)))

    if "pow" in device:
        from kazu.hardwares import sensors

        table.append(_shader("POWER", check_power(sensors)))

    if "cam" in device:
        from kazu.hardwares import inited_tag_detector

        tag_detector = inited_tag_detector(app_config)
        table.append(_shader("CAMERA", check_camera(tag_detector)))
        tag_detector.release_camera()
    if "mot" in device:
        from kazu.hardwares import inited_controller
        from kazu.hardwares import sensors
        from bdmc import CMD

        controller = inited_controller(app_config)
        table.append(_shader("MOTOR", check_motor(controller)))
        controller.stop_msg_sending()
    secho(SingleTable(table).table)


@main.command("read")
@click.help_option("-h", "--help")
@click.pass_obj
@click.argument(
    "device",
    type=click.Choice(["adc", "io", "mpu", "all"]),
    nargs=-1,
)
@click.option("-i", "interval", type=click.FLOAT, default=0.5, show_default=True)
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
    sensor_config = app_config.sensor
    (
        sensors.adc_io_open()
        .MPU6500_Open()
        .set_all_io_mode(0)
        .mpu_set_gyro_fsr(sensor_config.gyro_fsr)
        .mpu_set_accel_fsr(sensor_config.accel_fsr)
    )

    if "all" in device:
        device = ("adc", "io", "mpu")

    packs = []

    adc_labels = {
        sensor_config.edge_fl_index: "EDG-FL",
        sensor_config.edge_fr_index: "EDG-FR",
        sensor_config.edge_rl_index: "EDG-RL",
        sensor_config.edge_rr_index: "EDG-RR",
        sensor_config.left_adc_index: "LEFT",
        sensor_config.right_adc_index: "RIGHT",
        sensor_config.front_adc_index: "FRONT",
        sensor_config.rb_adc_index: "BACK",
        sensor_config.gray_adc_index: "GRAY",
    }

    io_labels = {
        sensor_config.fl_io_index: "FL",
        sensor_config.fr_io_index: "FR",
        sensor_config.rl_io_index: "RL",
        sensor_config.rr_io_index: "RR",
        sensor_config.reboot_button_index: "REBOOT",
        sensor_config.gray_io_left_index: "GRAY-LEFT",
        sensor_config.gray_io_right_index: "GRAY-RIGHT",
    }
    for dev in device:
        match dev:
            case "adc":
                packs.append(lambda: make_adc_table(sensors, adc_labels))

            case "io":
                packs.append(lambda: make_io_table(sensors, io_labels))
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
        _logger.info("Read sensors data interrupted.")
    finally:
        _logger.info("Closing sensors...")
        sensors.adc_io_close()
        _logger.info("Exit reading successfully.")


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
@click.option(
    "-r",
    "--render",
    show_default=True,
    is_flag=True,
    default=False,
    help="Render PlantUML files into SVG files",
)
def visualize(
    conf: _InternalConfig,
    destination: Path,
    run_config: Optional[Path],
    render: bool,
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
    from plantuml import PlantUML

    puml_d = PlantUML(url="http://www.plantuml.com/plantuml/svg/")

    destination.mkdir(parents=True, exist_ok=True)
    secho(f"Destination directory: {destination.absolute().as_posix()}", fg="yellow")
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
        with sig_light_registry:
            (*_, handler_data) = handler_func(app_config=app_config, run_config=run_config)
        filename = f_name + ".puml"
        destination_filename = (destination / filename).as_posix()

        botix.export_structure(destination_filename, handler_data)

        if render:
            secho(f"Rendering {filename}", fg="green", bold=True)
            puml_d.processes_file(destination_filename, destination_filename.replace(".puml", ".svg"))
        secho(f"Exported {filename}", fg="green", bold=True)


@main.command("cmd", context_settings={"ignore_unknown_options": True})
@click.help_option("-h", "--help")
@click.pass_obj
@click.option("-s", "--shell", is_flag=True, help="Run in shell mode", default=False, show_default=True)
@click.option(
    "-p",
    "--port",
    type=click.STRING,
    help="Set the serial port temporarily",
    default=None,
    show_default=True,
    callback=set_port_callback,
)
@click.argument("duration", type=click.FLOAT, required=False)
@click.argument("speeds", nargs=-1, type=click.INT, required=False)
def control_motor(conf: _InternalConfig, duration: Optional[float], speeds: Optional[list[int]], shell: bool, **_):
    """
    Control motor by sending command.

    move the bot at <SPEEDS> for <DURATION> seconds, then stop.

    Args:

        DURATION: (float)

        SPEEDS: (int) | (int,int) | (int,int,int,int)
    """
    from kazu.compile import composer, botix
    from kazu.hardwares import inited_controller

    from mentabotix import MovingState, MovingTransition

    import threading

    controller = inited_controller(conf.app_config)
    if not controller.serial_client.is_connected:
        secho(f"Serial client is not connected to {conf.app_config.motion.port}, exiting...", fg="red", bold=True)
        return

    supported_token_len = {2, 3, 5}

    def _send_cmd(mov_duration, mov_speeds):
        try:
            states, transitions = (
                composer.init_container()
                .add(state := MovingState(*mov_speeds))
                .add(MovingTransition(mov_duration))
                .add(MovingState(0))
                .export_structure()
            )
        except ValueError as e:
            secho(f"{e}", fg="red")
            return

        botix.token_pool = transitions

        secho(
            f"{Fore.RESET}Move as {Fore.YELLOW}{state.unwrap()}{Fore.RESET} for {Fore.YELLOW}{mov_duration}{Fore.RESET} seconds",
        )
        fi: Callable[[], None] = botix.compile(return_median=False)

        def _bar():
            with click.progressbar(
                range(int(mov_duration / 0.1)),
                show_percent=True,
                show_eta=True,
                label="Moving",
                color=True,
                fill_char=f"{Fore.GREEN}█{Fore.RESET}",
                empty_char=f"{Fore.LIGHTWHITE_EX}█{Fore.RESET}",
            ) as bar:
                for _ in bar:
                    sleep(0.1)

        t = threading.Thread(target=_bar, daemon=True)
        t.start()
        fi()
        t.join()

    def _cmd_validator(raw_cmd: str) -> Tuple[float, list[int]] | Tuple[None, None]:
        tokens = raw_cmd.split()
        token_len = len(tokens)
        if token_len not in supported_token_len:
            secho(f"Only support 2, 3 or 5 cmd tokens, got {token_len}", fg="red")
            return None, None

        try:
            conv_cmd = float(tokens.pop(0)), list(map(int, tokens))
        except ValueError:
            secho(f"Invalid cmd: {raw_cmd}", fg="red")
            return None, None

        return conv_cmd

    if shell:
        secho(f"Open shell mode, enter '{QUIT}' to exit", fg="green", bold=True)
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
            duration, speeds = _cmd_validator(cmd)

            if duration and speeds:
                _send_cmd(duration, speeds)
    elif duration and speeds:
        _send_cmd(duration, speeds)
    else:
        secho(
            "You should specify duration and speeds if you want to a single send cmd or add '-s' to open shell",
            fg="red",
        )
    controller.stop_msg_sending()


@main.command("ports")
@click.help_option("-h", "--help")
@click.option("-c", "--check", is_flag=True, default=False, show_default=True, help="Check if ports are available")
@click.option("-t", "--timeout", type=click.FLOAT, default=1.0, show_default=True, help="Check timeout, in seconds")
@click.pass_obj
def list_ports(conf: _InternalConfig, check: bool, timeout: float):
    """
    List serial ports and check if they are in use.
    """
    import serial
    from bdmc import find_serial_ports
    from terminaltables import SingleTable
    from colorama import Fore, Style

    def is_port_open(port_to_check):
        """检查端口是否开放（未被占用）"""
        try:
            with serial.Serial(port_to_check, timeout=timeout) as ser:
                return True, "Available."
        except (OSError, serial.SerialException):
            return False, "Not available or Busy."

    ports = sorted(find_serial_ports(), reverse=True)
    data = [["Serial Ports", "Status"]]

    for port in ports:
        if check:
            open_status, message = is_port_open(port)
            status_color = Fore.GREEN if open_status else Fore.RED
            data.append([port, f"{status_color}{message}{Style.RESET_ALL}"])
        else:
            data.append([port, f"{Fore.YELLOW}---{Style.RESET_ALL}"])

    data.append(["Configured port", conf.app_config.motion.port])
    table = SingleTable(data)
    table.inner_footing_row_border = True
    table.inner_row_border = False
    table.justify_columns[1] = "right"
    secho(table.table, bold=True)


@main.command("msg")
@click.help_option("-h", "--help")
@click.pass_obj
@click.option(
    "-p",
    "--port",
    type=click.STRING,
    help="Set the serial port temporarily",
    default=None,
    show_default=True,
    callback=set_port_callback,
)
def stream_send_msg(conf: _InternalConfig, **_):
    """
    Sending msg in streaming input mode.
    """
    from kazu.hardwares import inited_controller

    con = inited_controller(conf.app_config)
    if not con.serial_client.is_connected:
        secho(f"Serial client is not connected to {conf.app_config.motion.port}, exiting...", fg="red", bold=True)
        return
    secho("Start reading thread", fg="green", bold=True)

    def _ret_handler(msg: str):
        print(f"\n{Fore.YELLOW}< {msg}{Fore.RESET}")

    con.serial_client.start_read_thread(_ret_handler)

    secho(f"Start streaming input, enter '{QUIT}' to quit", fg="green", bold=True)

    while 1:
        cmd = click.prompt(
            f"{Fore.GREEN}> ",
            type=str,
            default="",
            prompt_suffix=f"{Fore.MAGENTA}",
            show_choices=False,
            show_default=False,
        )
        if cmd == QUIT:
            break
        con.cmd_queue.put(f"{cmd}\r".encode("ascii"))

    con.stop_msg_sending()
    con.serial_client.stop_read_thread()

    secho("Quit streaming", fg="green", bold=True)


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


@main.command("tag")
@click.help_option("-h", "--help")
@click.pass_obj
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
def tag_test(conf: _InternalConfig, interval: float, **_):
    """
    Use tag detector to test tag ID detection.
    """
    from kazu.hardwares import inited_tag_detector
    from kazu.checkers import check_camera

    detector = inited_tag_detector(conf.app_config)
    if not check_camera(detector):
        secho("Camera is not ready, exiting...", fg="red", bold=True)
        return

    try:
        detector.apriltag_detect_start()
        while 1:
            sleep(interval)
            secho(f"\rTag: {detector.tag_id}", fg="green", bold=True, nl=False)

    except KeyboardInterrupt:
        _logger.info("KeyboardInterrupt, exiting...")
    finally:
        _logger.info("Release camera...")
        detector.apriltag_detect_end()
        detector.release_camera()
        _logger.info("Done")


@main.command("breaker")
@click.help_option("-h", "--help")
@click.pass_obj
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
def breaker_test(
    conf: _InternalConfig,
    run_config_path: Path,
    interval: float,
):
    """
    Use breaker detector to test breaker detection.
    """
    from kazu.config import load_run_config
    from kazu.judgers import Breakers
    from kazu.constant import EdgeCodeSign, SurroundingCodeSign, ScanCodesign, FenceCodeSign
    from terminaltables import SingleTable
    from kazu.hardwares import sensors, controller
    from kazu.config import ContextVar

    controller.context.update(ContextVar.export_context())
    sensors.adc_io_open().MPU6500_Open()
    run_config = load_run_config(run_config_path)
    config_pack = conf.app_config, run_config

    def _make_display_pack(breaker: Callable[[], int], codesign_enum: Type[Enum]) -> Callable[[], Tuple[str, int]]:
        def _display():
            codesign = breaker()
            [matched] = [x.name for x in codesign_enum if x.value == codesign]
            return matched, codesign

        return _display

    data = []
    table: SingleTable = SingleTable(data)

    edge_breaker_display = _make_display_pack(Breakers.make_std_edge_full_breaker(*config_pack), EdgeCodeSign)

    tag_group = TagGroup(team_color=conf.app_config.vision.team_color)

    surr_breaker_maker = (
        Breakers.make_cam_surr_breaker if conf.app_config.vision.use_camera else Breakers.make_nocam_surr_breaker
    )

    surr_breaker_display = _make_display_pack(
        surr_breaker_maker(*config_pack, tag_group=tag_group), SurroundingCodeSign
    )

    scan_breaker_display = _make_display_pack(Breakers.make_std_scan_breaker(*config_pack), ScanCodesign)

    fence_breaker_display = _make_display_pack(Breakers.make_std_fence_breaker(*config_pack), FenceCodeSign)

    displays = [
        ("Edge", edge_breaker_display),
        ("Surr", surr_breaker_display),
        ("Scan", scan_breaker_display),
        ("Fence", fence_breaker_display),
    ]
    try:
        while 1:
            data.clear()
            for name, d in displays:
                data.append([name, *d()])
            click.clear()
            secho(table.table, bold=True)
            sleep(interval)
    finally:
        sensors.adc_io_close()
        secho("Exit breaker test.")


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
def bench(**_):
    """
    Benchmarks
    """
    echo("bench test done!")
