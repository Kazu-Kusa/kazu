from enum import Enum
from pathlib import Path
from time import sleep
from typing import Callable, List, Optional, Tuple, Type

import click
from click import clear, echo, secho
from colorama import Fore

from kazu import __command__, __version__
from kazu.callbacks import (
    bench_add_app,
    bench_aps,
    bench_siglight_switch_freq,
    bench_sleep_precision,
    disable_cam_callback,
    disable_siglight_callback,
    export_default_app_config,
    export_default_run_config,
    led_light_shell_callback,
    log_level_callback,
    set_camera_callback,
    set_port_callback,
    set_res_multiplier_callback,
    team_color_callback,
)
from kazu.config import (
    DEFAULT_APP_CONFIG_PATH,
    APPConfig,
    ContextVar,
    _InternalConfig,
    load_app_config,
    load_run_config,
)
from kazu.constant import QUIT, Env, RunMode
from kazu.logger import _logger
from kazu.signal_light import sig_light_registry
from kazu.static import get_timestamp
from kazu.visualize import print_colored_toml


@click.group(
    epilog=r"For more details, Check at https://github.com/Kazu-Kusa/kazu",
)
@click.help_option("-h", "--help")
@click.version_option(
    __version__,
    "-v",
    "--version",
    message=rf"""
{Fore.MAGENTA}______ __
___  //_/_____ __________  __
__  ,<  _  __ `/__  /_  / / /
_  /| | / /_/ /__  /_/ /_/ /
/_/ |_| \__,_/ _____/\__,_/
{Fore.RESET}
{Fore.YELLOW}Kazu: A Dedicated Robots Control System
{Fore.GREEN}Version: {__command__}-v{__version__}{Fore.RESET}
                             """,
)
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
@click.option(
    "-s",
    "--disable-siglight",
    is_flag=True,
    default=False,
    help="Disable signal light",
)
def main(ctx: click.Context, app_config_path: Path, log_level: str, disable_siglight: bool) -> None:
    """A Dedicated Robots Control System."""
    app_config = load_app_config(app_config_path)

    ctx.obj = _InternalConfig(app_config=app_config, app_config_file_path=app_config_path)

    log_level_callback(ctx=ctx, _=None, value=log_level)
    disable_siglight_callback(ctx=ctx, _=None, value=disable_siglight)


@main.command("config")
@click.pass_obj
@click.pass_context
@click.help_option("-h", "--help")
@click.option(
    "-r",
    "--export-run-conf-path",
    help="Path of the exported run config template file",
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
    ctx: click.Context,
    config: _InternalConfig,
    kv: Optional[Tuple[str, str]],
    **_,
) -> None:
    """Configure KAZU."""
    app_config = config.app_config
    if kv is None:
        from tomlkit import dumps

        secho(
            f"Config file at {Path(config.app_config_file_path).absolute().as_posix()}",
            fg="green",
            bold=True,
        )
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
        ctx.exit(0)


@main.command("run")
@click.pass_obj
@click.pass_context
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
    type=click.Choice(["blue", "yellow", "online"]),
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
def run(
    ctx: click.Context,
    conf: _InternalConfig,
    run_config_path: Path | None,
    mode: str,
    **_,
) -> None:
    """Run command for the main group.

    Executes the robot control system in different operational modes with hardware initialization
    and proper resource management.

    Args:
        ctx (click.Context): Click context object for command execution.
        conf (_InternalConfig): Internal configuration object containing app configuration.
        run_config_path (Path | None): Path to the run configuration file. If None, uses default.
        mode (str): Operational mode to run the system in. Must be one of the RunMode values.
        **_: Additional keyword arguments (ignored).

    Returns:
        None

    Raises:
        KeyboardInterrupt: When the program is interrupted by user (Ctrl+C).
        Exception: Any other exception that occurs during execution.

    Description:
        This function initializes all hardware components including sensors, camera, and motor
        controller, then runs the robot in one of several operational modes:

        - FGS (Off Stage Start): Runs boot sequence once, then stage sequence in loop
        - NGS (On Stage Start): Runs only stage sequence in continuous loop
        - AFG (Always Off Stage): Runs off-stage sequence continuously
        - ANG (Always On Stage): Runs on-stage sequence continuously
        - FGDL (Off Stage Dash Loop): Runs boot sequence continuously in loop

        The function ensures proper resource cleanup in the finally block, including:
        - Stopping motors and resetting controller
        - Releasing camera resources
        - Closing sensor connections
        - Turning off signal lights

    Note:
        This function will run indefinitely until interrupted or an error occurs.
        All hardware resources are properly initialized before execution and cleaned up
        after termination.
    """
    from bdmc import CMD

    from kazu.compile import botix

    run_config = load_run_config(run_config_path)

    app_config = conf.app_config

    from kazu.hardwares import inited_controller, inited_tag_detector, sensors
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
    except Exception as e:
        _logger.critical(e)
    finally:
        _logger.info("Releasing hardware resources...")
        set_all_black()
        con.send_cmd(CMD.FULL_STOP).send_cmd(CMD.RESET).close()
        tag_detector.apriltag_detect_end()
        tag_detector.release_camera()
        sensors.adc_io_close()
        _logger.info("KAZU stopped.")
        ctx.exit(0)


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
def test(conf: _InternalConfig, device: str, **_) -> None:
    """Check devices' normal functions.

    Tests the functionality of various hardware devices connected to the robot system.
    Each device is tested individually and results are displayed in a formatted table.

    Args:
        conf (_InternalConfig): Internal configuration object containing app configuration
            and file paths for system setup.
        device (str): Device type(s) to test. Can be one or more of:
            - "mot": Motor controller
            - "cam": Camera/tag detector
            - "adc": Analog-to-digital converter sensors
            - "io": Input/output sensors
            - "mpu": Motion processing unit (gyroscope/accelerometer)
            - "pow": Power monitoring
            - "all": Test all available devices
        **_: Additional keyword arguments (ignored).

    Returns:
        None

    Description:
        This function performs hardware diagnostics by testing specified devices:

        - ADC: Tests analog sensor readings by opening ADC interface and checking
          sensor connectivity
        - IO: Tests digital input/output functionality by checking IO channels
        - MPU: Tests motion processing unit (gyroscope and accelerometer) by
          initializing MPU6500 and verifying sensor data
        - POWER: Tests power monitoring system and battery status
        - CAMERA: Tests camera initialization, tag detection capabilities, and
          image capture functionality
        - MOTOR: Tests motor controller communication, initialization, and
          basic movement commands

        Each test result is displayed in a color-coded table:
        - Device names appear in yellow (success) or red (failure)
        - Test results show as green "True" (pass) or red "False" (fail)

        The function automatically handles resource management, ensuring proper
        initialization and cleanup of hardware interfaces for each test.

    Note:
        - If no device is specified or "all" is included, all devices are tested
        - Hardware resources are properly opened and closed for each test
        - Some tests may require specific hardware connections to pass
        - Camera and motor tests use the application configuration for setup
    """
    app_config: APPConfig = conf.app_config

    from terminaltables import SingleTable

    from kazu.checkers import (
        check_adc,
        check_camera,
        check_io,
        check_motor,
        check_mpu,
        check_power,
    )

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
        from kazu.hardwares import inited_controller, sensors

        controller = inited_controller(app_config)
        table.append(_shader("MOTOR", check_motor(controller)))
        controller.close()
    secho(SingleTable(table).table)


@main.command("read")
@click.help_option("-h", "--help")
@click.pass_obj
@click.pass_context
@click.argument(
    "device",
    type=click.Choice(["adc", "io", "mpu", "all"]),
    nargs=-1,
)
@click.option(
    "-s",
    "--use-screen",
    is_flag=True,
    default=False,
    show_default=True,
    help="Print to onboard lcd screen",
)
@click.option("-i", "interval", type=click.FLOAT, default=0.5, show_default=True)
def read_sensors(
    ctx: click.Context,
    conf: _InternalConfig,
    interval: float,
    device: str,
    use_screen: bool,
) -> None:
    """Read sensors data and print to terminal.

    Continuously reads and displays sensor data from various hardware components
    in real-time with configurable refresh intervals and display options.

    Args:
        ctx (click.Context): Click context object for command execution and exit handling.
        conf (_InternalConfig): Internal configuration object containing app configuration
            and sensor mapping definitions.
        interval (float): Time interval between sensor readings in seconds.
        device (str): Device type(s) to read from. Can be one or more of:
            - "adc": Analog-to-digital converter sensors (edge sensors, distance sensors)
            - "io": Digital input/output sensors (buttons, switches)
            - "mpu": Motion processing unit (gyroscope, accelerometer, attitude)
            - "all": Read from all available sensor types
        use_screen (bool): If True, displays sensor data on the onboard LCD screen
            in addition to terminal output.

    Returns:
        None

    Raises:
        KeyboardInterrupt: When the program is interrupted by user (Ctrl+C).
        ValueError: If an invalid device type is specified.

    Description:
        This function initializes and continuously reads from the specified sensor types:

        - ADC Sensors: Reads analog values from edge detection sensors (front-left,
          front-right, rear-left, rear-right), directional distance sensors (left,
          right, front, back), and grayscale sensors
        - IO Sensors: Reads digital input states from corner sensors, reboot button,
          and grayscale digital sensors
        - MPU Sensors: Reads motion data including gyroscope, accelerometer, and
          attitude information from the MPU6500 unit

        The function configures sensor parameters based on the application config:
        - Sets gyroscope full-scale range (FSR)
        - Sets accelerometer full-scale range (FSR)
        - Configures all IO pins to input mode (0)

        Display features:
        - Terminal output: Refreshes sensor tables in terminal every interval
        - LCD output: Shows ADC and IO sensor data on onboard screen when enabled
        - Labeled sensor data with human-readable names for easy identification

        The function ensures proper resource management by:
        - Opening necessary sensor interfaces before reading
        - Properly closing ADC/IO interfaces in the finally block
        - Closing and clearing the LCD screen if used
        - Graceful exit handling through click context

    Note:
        - The function runs indefinitely until interrupted
        - All sensor interfaces are properly initialized and cleaned up
        - LCD screen is cleared and closed when exiting if it was used
        - Sensor labels are mapped from configuration for consistent naming
    """
    from pyuptech import (
        Color,
        adc_io_display_on_lcd,
        make_adc_table,
        make_io_table,
        make_mpu_table,
    )

    from kazu.hardwares import screen, sensors

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
        sensor_config.gray_io_left_index: "GRAY-L",
        sensor_config.gray_io_right_index: "GRAY-R",
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
        if use_screen:
            screen.open(2)
        while 1:
            if use_screen:
                adc_io_display_on_lcd(sensors, screen, adc_labels, io_labels)
            stdout: str = "\n".join(pack() for pack in packs)
            clear()
            echo(stdout)
            sleep(interval)
    except KeyboardInterrupt:
        _logger.info("Read sensors data interrupted.")
    finally:
        _logger.info("Closing sensors...")
        sensors.adc_io_close()
        if use_screen:
            screen.fill_screen(Color.BLACK).refresh().close()
        _logger.info("Exit reading successfully.")
        ctx.exit(0)


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
    "-r",
    "--run-config-path",
    show_default=True,
    default=None,
    help=f"config file path, also can receive env {Env.KAZU_RUN_CONFIG_PATH}",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    envvar=Env.KAZU_RUN_CONFIG_PATH,
)
@click.option(
    "-e",
    "--render",
    show_default=True,
    is_flag=True,
    default=False,
    help="Render PlantUML files into SVG files",
)
def visualize(
    conf: _InternalConfig,
    destination: Path,
    run_config_path: Optional[Path],
    render: bool,
    packname: Tuple[str, ...],
) -> None:
    """Visualize State-Transition Diagram of KAZU with PlantUML.

    Generates PlantUML state-transition diagrams for various robot behavioral handlers
    and optionally renders them to SVG format for visualization and documentation.

    Args:
        conf (_InternalConfig): Internal configuration object containing app configuration
            and system settings for handler initialization.
        destination (Path): Output directory path where generated PlantUML files will be saved.
            Directory will be created if it doesn't exist.
        run_config_path (Optional[Path]): Path to the run configuration file. If None,
            uses default configuration. Contains runtime behavior parameters.
        render (bool): If True, renders generated PlantUML files to SVG format using
            online PlantUML service. If False, only generates .puml files.
        packname (Tuple[str, ...]): Tuple of handler package names to visualize. Can include:
            - "edge": Edge detection handler
            - "boot": System reboot handler
            - "bkstage": Back to stage handler
            - "surr": Surrounding detection handler
            - "scan": Area scanning handler
            - "search": Target search handler
            - "fence": Fence detection handler
            - "rdwalk": Random walk handler
            - "stdbat": Standard battle handler
            - "onstage": Always on-stage battle handler
            - "angbat": Always on-stage battle handler (alias)
            - "afgbat": Always off-stage battle handler
            - "all": Generate diagrams for all available handlers

    Returns:
        None

    Description:
        This function creates visual state-transition diagrams for robot behavioral handlers
        using PlantUML markup language. The process involves:

        1. Handler Selection: Determines which handlers to visualize based on packname parameter
        2. Configuration Loading: Loads app and run configurations for handler initialization
        3. Handler Execution: Executes each selected handler to extract state structure
        4. PlantUML Generation: Exports handler structure to PlantUML format (.puml files)
        5. Optional Rendering: Converts PlantUML files to SVG using online service

        Each handler represents a different robot behavior pattern:
        - Edge handlers manage boundary detection and avoidance
        - Battle handlers control combat and competition strategies
        - Navigation handlers manage movement and positioning
        - System handlers control initialization and recovery

        The generated diagrams show:
        - State nodes and their relationships
        - Transition conditions between states
        - Decision points and branching logic
        - Handler flow and execution paths

        Signal light registry is used during handler execution to ensure proper
        resource management and visual feedback during diagram generation.

    Note:
        - Requires internet connection for SVG rendering via PlantUML web service
        - Generated .puml files can be opened in PlantUML-compatible editors
        - SVG files provide ready-to-use documentation diagrams
        - Handler execution is performed in controlled environment with signal registry
        - All specified handlers must exist in the system or will be skipped
    """
    from plantuml import PlantUML

    from kazu.compile import (
        botix,
        make_always_off_stage_battle_handler,
        make_always_on_stage_battle_handler,
        make_back_to_stage_handler,
        make_edge_handler,
        make_fence_handler,
        make_rand_walk_handler,
        make_reboot_handler,
        make_scan_handler,
        make_search_handler,
        make_std_battle_handler,
        make_surrounding_handler,
    )

    packname = packname or ("all",)
    puml_d = PlantUML(url="http://www.plantuml.com/plantuml/svg/")

    destination.mkdir(parents=True, exist_ok=True)
    secho(f"Destination directory: {destination.absolute().as_posix()}", fg="yellow")
    app_config = conf.app_config
    run_config_path = load_run_config(run_config_path)

    handlers = {
        "edge": make_edge_handler,
        "boot": make_reboot_handler,
        "bkstage": make_back_to_stage_handler,
        "surr": make_surrounding_handler,
        "scan": make_scan_handler,
        "search": make_search_handler,
        "fence": make_fence_handler,
        "rdwalk": make_rand_walk_handler,
        "stdbat": make_std_battle_handler,
        "onstage": make_always_on_stage_battle_handler,
        "angbat": make_always_on_stage_battle_handler,
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
            (*_, handler_data) = handler_func(app_config=app_config, run_config=run_config_path)
        filename = f_name + ".puml"
        destination_filename = (destination / filename).as_posix()

        botix.export_structure(destination_filename, handler_data)

        if render:
            secho(f"Rendering {filename}", fg="green", bold=True)
            puml_d.processes_file(destination_filename, destination_filename.replace(".puml", ".svg"))
        secho(f"Exported {filename}", fg="green", bold=True)


@click.help_option("-h", "--help")
@click.pass_obj
@click.option(
    "-s",
    "--shell",
    is_flag=True,
    help="Run in shell mode",
    default=False,
    show_default=True,
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
@click.argument("duration", type=click.FLOAT, required=False)
@click.argument("speeds", nargs=-1, type=click.INT, required=False)
def control_motor(
    conf: _InternalConfig,
    duration: Optional[float],
    speeds: Optional[list[int]],
    shell: bool,
    **_,
) -> None:
    """Control motor by sending command.

    Sends movement commands to the robot's motor controller to move at specified speeds
    for a given duration, with support for both single commands and interactive shell mode.

    Args:
        conf (_InternalConfig): Internal configuration object containing app configuration
            and motor controller settings for hardware initialization.
        duration (Optional[float]): Duration in seconds to run the motors. Required for
            single command mode, ignored in shell mode.
        speeds (Optional[list[int]]): List of motor speeds. Can be:
            - Single value: Applied to all motors
            - Two values: [left_side, right_side] speeds
            - Four values: [front_left, rear_left, rear_right, front_right] speeds
        shell (bool): If True, enters interactive shell mode for continuous command input.
            If False, executes a single movement command.
        **_: Additional keyword arguments (ignored).

    Returns:
        None

    Raises:
        ValueError: When invalid speed values or command format is provided.
        SerialException: When motor controller connection fails.

    Description:
        This function provides two operational modes for motor control:

        1. Single Command Mode (shell=False):
           - Requires both duration and speeds parameters
           - Executes one movement command and exits
           - Shows a progress bar during movement execution
           - Automatically stops motors after the specified duration

        2. Interactive Shell Mode (shell=True):
           - Enters a continuous command prompt loop
           - Accepts commands in format: "<duration> <speed1> [speed2] [speed3] [speed4]"
           - Validates each command before execution
           - Continues until 'quit' command is entered

        Command Format:
        - 2 tokens: "<duration> <speed>" - All motors at same speed
        - 3 tokens: "<duration> <left_speed> <right_speed>" - Differential drive
        - 5 tokens: "<duration> <fl> <rl> <rr> <fr>" - Individual motor control

        The function initializes the motor controller using the application configuration,
        validates the serial connection, and ensures proper resource cleanup by closing
        the controller connection when finished.

        Progress visualization includes a colored progress bar with ETA display during
        movement execution, running in a separate daemon thread to avoid blocking
        the motor control commands.

    Note:
        - Motor controller must be properly connected and configured
        - All motor speeds are validated before sending commands
        - Serial connection is automatically closed on function exit
        - Progress bar updates every 0.1 seconds during movement
        - Invalid commands in shell mode are rejected with error messages
    """
    import threading

    from mentabotix import MovingState, MovingTransition

    from kazu.compile import botix, composer
    from kazu.hardwares import inited_controller

    controller = inited_controller(conf.app_config)
    if not controller.seriald.is_open:
        secho(
            f"Serial client is not connected to {conf.app_config.motion.port}, exiting...",
            fg="red",
            bold=True,
        )
        return

    supported_token_len = {2, 3, 5}

    def _send_cmd(mov_duration, mov_speeds) -> None:
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

        def _bar() -> None:
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
    controller.close()


@main.command("ports")
@click.help_option("-h", "--help")
@click.option(
    "-c",
    "--check",
    is_flag=True,
    default=False,
    show_default=True,
    help="Check if ports are available",
)
@click.option(
    "-t",
    "--timeout",
    type=click.FLOAT,
    default=1.0,
    show_default=True,
    help="Check timeout, in seconds",
)
@click.pass_obj
def list_ports(conf: _InternalConfig, check: bool, timeout: float) -> None:
    """List serial ports and check if they are in use.

    Scans the system for available serial ports and displays them in a formatted table,
    with optional checking of port availability status.

    Args:
        conf (_InternalConfig): Internal configuration object containing app configuration
            and current motor controller port settings.
        check (bool): If True, attempts to open each port to verify availability.
            If False, only lists the ports without checking.
        timeout (float): Timeout in seconds for port checking operations when
            attempting to open serial connections.

    Returns:
        None

    Description:
        This function performs the following operations:

        1. Port Discovery: Detects all available serial ports on the system using
           the bdmc.find_serial_ports utility

        2. Optional Port Checking: When check=True, attempts to open each port
           with the specified timeout to determine if it's available or in use

        3. Status Display: Shows a color-coded table with:
           - All detected serial ports (sorted in reverse order)
           - Availability status (if check=True)
           - The currently configured port from application settings

        Status colors indicate:
        - Green: Port is available and can be opened
        - Red: Port is in use or cannot be opened
        - Yellow: Status not checked (when check=False)

        The configured port is displayed at the bottom of the table for
        easy reference and comparison.

    Note:
        - Serial ports may require special permissions on some systems
        - Busy ports cannot be opened and will show as "Not available"
        - The function does not modify any configuration settings
        - Useful for diagnostics when configuring hardware connections
    """
    import serial
    from bdmc import find_serial_ports
    from colorama import Fore, Style
    from terminaltables import SingleTable

    def is_port_open(port_to_check):
        """Check if a serial port is available (not in use).

        Args:
            port_to_check (str): Serial port path to check.

        Returns:
            tuple: (is_open, message) where is_open is a boolean indicating
                   availability and message is a status string.
        """
        try:
            with serial.Serial(port_to_check, timeout=timeout):
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
@click.pass_context
@click.option(
    "-p",
    "--port",
    type=click.STRING,
    help="Set the serial port temporarily",
    default=None,
    show_default=True,
    callback=set_port_callback,
)
def stream_send_msg(ctx: click.Context, conf: _InternalConfig, **_) -> None:
    """Send messages to the motor controller in streaming input mode.

    Establishes a bidirectional serial communication channel with the motor controller
    for sending custom commands and receiving immediate responses.

    Args:
        ctx (click.Context): Click context object for command execution and exit handling.
        conf (_InternalConfig): Internal configuration object containing app configuration
            with serial port settings for controller communication.
        **_: Additional keyword arguments (ignored).

    Returns:
        None

    Raises:
        SerialException: When the serial connection cannot be established.

    Description:
        This function provides an interactive console for direct communication with
        the motor controller over the serial port. It operates as follows:

        1. Connection Setup: Initializes the motor controller with configured port settings
           and verifies that the serial connection is open and ready

        2. Interactive Console: Enters a command loop that:
           - Prompts the user for input with a colored command prompt
           - Sends each command to the controller with carriage return termination
           - Displays the controller's response with distinct formatting
           - Continues until the user enters the quit command

        3. Resource Cleanup: Ensures the serial connection is properly closed when
           exiting the command loop

        The function supports direct access to the controller's command interface,
        allowing for custom commands that may not be available through the higher-level
        API. This is particularly useful for debugging, testing new commands, or
        exploring the controller's capabilities.

    Note:
        - Commands are sent as ASCII with carriage return termination
        - The quit command is defined by the QUIT constant (typically "quit")
        - Messages received from the controller are displayed raw
        - Serial connection is automatically closed when exiting
        - Useful for diagnosing communication issues or testing custom commands
    """
    from kazu.hardwares import inited_controller

    con = inited_controller(conf.app_config)
    if not con.seriald.is_open:
        secho(
            f"Serial client is not connected to {conf.app_config.motion.port}, exiting...",
            fg="red",
            bold=True,
        )
        return
    secho("Start reading thread", fg="green", bold=True)

    def _ret_handler(msg: str) -> None:
        pass

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
        con.seriald.write(f"{cmd}\r".encode("ascii"))

        secho(f"Receive: {con.seriald.readline()}", fg="magenta", bold=True)

    con.close()

    secho("Quit streaming", fg="green", bold=True)
    ctx.exit(0)


@main.command("light")
@click.help_option("-h", "--help")
@click.pass_obj
@click.option("-s", "--shell", is_flag=True, default=False, callback=led_light_shell_callback)
@click.option("-g", "--sig-lights", is_flag=True, default=False)
def control_display(conf: _InternalConfig, sig_lights: bool, **_) -> None:
    """Control LED display and signal lights on the robot.

    Provides interfaces for controlling the onboard LED display and visualizing
    registered signal light patterns with their associated purposes.

    Args:
        conf (_InternalConfig): Internal configuration object containing app configuration
            and signal light settings.
        sig_lights (bool): If True, displays all registered signal light patterns and
            their purposes sequentially. If False, enters LED shell mode based on
            the shell option.
        **_: Additional keyword arguments (ignored).

    Returns:
        None

    Description:
        This function provides two operational modes:

        1. Signal Light Display Mode (-g/--sig-lights):
           - Temporarily enables signal lights if they are disabled in configuration
           - Initializes the standard battle handler to register all signal patterns
           - Displays each registered signal light pattern on the robot's LEDs
           - Shows the pattern's purpose on the onboard LCD screen
           - Presents a color-coded representation of the pattern in the terminal
           - Advances to the next pattern when the user presses Enter

        2. LED Shell Mode (-s/--shell) [handled by callback]:
           - When the shell option is provided, the led_light_shell_callback is triggered
           - This provides an interactive shell for directly controlling LEDs

        In Signal Light Display Mode, each registered pattern is shown with:
        - The actual LED lights displaying the pattern on the robot
        - The LCD screen showing the pattern's purpose/meaning
        - Terminal output showing color names in their actual colors
        - Interactive progression through all patterns

        The function ensures proper hardware initialization and cleanup:
        - Opens and configures the onboard LCD screen
        - Opens the ADC/IO interface for LED control
        - Properly closes all hardware interfaces when finished
        - Resets all LEDs to black/off state

    Note:
        - Signal light patterns are defined in the signal_light_registry
        - Each pattern is associated with a specific robot behavior or state
        - The LCD screen shows textual descriptions of each pattern's purpose
        - All hardware resources are properly initialized and cleaned up
        - LED patterns include color combinations for both sides of the robot
    """
    if sig_lights:
        if not conf.app_config.debug.use_siglight:
            secho(
                "Siglight is not enabled, temporarily enable it during the display",
                fg="yellow",
                bold=True,
            )
            conf.app_config.debug.use_siglight = True
        from pyuptech import Color

        from kazu.compile import make_std_battle_handler
        from kazu.config import RunConfig
        from kazu.hardwares import screen, sensors
        from kazu.signal_light import sig_light_registry

        sensors.adc_io_open()
        screen.open(2)
        with sig_light_registry:
            _ = make_std_battle_handler(conf.app_config, RunConfig())

        secho("Press 'Enter' to show next.", fg="yellow", bold=True)
        for color, purpose in sig_light_registry.mapping.items():
            screen.fill_screen(Color.BLACK).print(purpose).refresh().set_all_leds_single(*color)

            color_names = sig_light_registry.get_key_color_name_colorful(color)
            out_string = f"<{color_names[0]}, {color_names[1]}>"

            click.prompt(
                f"{out_string}|{purpose} ",
                prompt_suffix="",
                default="next",
                show_default=False,
            )

        _logger.info("All displayed")
        screen.fill_screen(Color.BLACK).refresh().close().set_all_leds_same(Color.BLACK)
        sensors.adc_io_close()


@main.command("tag")
@click.help_option("-h", "--help")
@click.pass_obj
@click.pass_context
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
    "-i",
    "--interval",
    type=click.FLOAT,
    default=0.5,
    show_default=True,
    help="Set the interval of the tag detector",
)
def tag_test(ctx: click.Context, conf: _InternalConfig, interval: float, **_) -> None:
    """Use tag detector to test tag ID detection.

    Continuously monitors and displays AprilTag detection results from the camera
    with configurable refresh interval.

    Args:
        ctx (click.Context): Click context object for command execution and exit handling.
        conf (_InternalConfig): Internal configuration object containing app configuration
            with camera settings.
        interval (float): Time interval in seconds between tag detection checks.
            Lower values provide more responsive detection but higher CPU usage.
        **_: Additional keyword arguments (ignored).

    Returns:
        None

    Raises:
        KeyboardInterrupt: When the program is interrupted by user (Ctrl+C).

    Description:
        This function provides a real-time AprilTag detection testing environment:

        1. Camera Initialization: Sets up the tag detector with the configured camera,
           verifying camera readiness before proceeding.

        2. Detection Loop: Continuously performs the following operations:
           - Reads frames from the camera at specified intervals
           - Processes frames for AprilTag detection
           - Updates the terminal with the detected tag ID in real-time
           - Maintains a non-blocking interface with inline output

        3. Resource Cleanup: Ensures camera resources are properly released when exiting,
           including stopping the tag detection thread and closing the camera interface.

        The function is useful for:
        - Testing camera positioning and focus
        - Verifying tag detection capabilities
        - Debugging tag recognition issues
        - Checking detection range and reliability

    Note:
        - Terminal output updates in-place with carriage return
        - Camera must be properly connected and configured
        - Detection performance depends on camera quality and lighting
        - Tag ID will show as -1 when no tag is detected
        - All camera resources are properly released on exit
    """
    from kazu.checkers import check_camera
    from kazu.hardwares import inited_tag_detector

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
        _logger.info("Released")
        ctx.exit(0)


@main.command("breaker")
@click.help_option("-h", "--help")
@click.pass_obj
@click.pass_context
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
@click.option(
    "-s",
    "--use-screen",
    is_flag=True,
    default=False,
    show_default=True,
    help="Print to onboard lcd screen",
)
def breaker_test(
    ctx: click.Context,
    conf: _InternalConfig,
    run_config_path: Path,
    interval: float,
    use_screen: bool,
) -> None:
    """Test and monitor various breaker detectors in real-time.

    Continuously monitors and displays the state of multiple robot behavior triggers
    (breakers) with configurable refresh intervals and display options.

    Args:
        ctx (click.Context): Click context object for command execution and exit handling.
        conf (_InternalConfig): Internal configuration object containing app configuration
            and sensor threshold settings.
        run_config_path (Path): Path to the run configuration file with behavior parameters.
        interval (float): Time interval in seconds between breaker state updates.
            Lower values provide more responsive detection but higher CPU usage.
        use_screen (bool): If True, displays breaker states on the onboard LCD screen
            in addition to terminal output.

    Returns:
        None

    Raises:
        KeyboardInterrupt: When the program is interrupted by user (Ctrl+C).
        Exception: Any other exception that occurs during execution.

    Description:
        This function initializes and continuously monitors multiple breaker detectors:

        - Edge Breakers: Detect boundaries and edges in different directions
        - Surrounding Breakers: Detect obstacles around the robot
        - Scanning Breakers: Detect scan conditions and patterns
        - Fence Breakers: Detect boundary fences and barriers
        - Alignment Breakers: Detect proper robot alignment conditions
        - Stage Breakers: Detect on/off stage conditions
        - Attack Breakers: Detect attack opportunities

        The function configures sensor interfaces and initializes the breakers using
        the provided application and run configurations. It then continuously updates
        and displays the state of each breaker in a formatted table.

        Display features:
        - Terminal output: Refreshes breaker state tables at specified intervals
        - LCD output: Shows breaker states on onboard screen when enabled
        - Color-coded formatting for better readability

        The function ensures proper resource management by:
        - Opening necessary sensor interfaces before reading
        - Properly closing hardware interfaces in the finally block
        - Clearing the LCD screen if used
        - Graceful exit handling through click context

    Note:
        - The function runs indefinitely until interrupted by Ctrl+C
        - All breaker states are displayed with their corresponding enum value names
        - LCD screen display is compact with 8 pixel line spacing
        - This tool is useful for debugging robot behavior conditions and sensor thresholds
    """
    from pyuptech import Color, FontSize
    from terminaltables import SingleTable

    from kazu.config import ContextVar, load_run_config
    from kazu.constant import (
        Activation,
        EdgeCodeSign,
        FenceCodeSign,
        ScanCodesign,
        SurroundingCodeSign,
    )
    from kazu.hardwares import controller, screen, sensors
    from kazu.judgers import Breakers

    sensors.adc_io_open().MPU6500_Open()
    controller.context.update({ContextVar.recorded_pack.name: sensors.adc_all_channels()})
    run_config = load_run_config(run_config_path)
    config_pack = conf.app_config, run_config

    def _make_display_pack(
        breaker: Callable[[], int | bool], codesign_enum: Type[Enum]
    ) -> Callable[[], Tuple[str, int | bool]]:
        def _display():
            codesign = breaker()
            [matched] = [x.name for x in codesign_enum if x.value == codesign]
            return matched, codesign

        return _display

    data = []
    table: SingleTable = SingleTable(data)

    displays = [
        (
            "Edge",
            (_make_display_pack(Breakers.make_std_edge_full_breaker(*config_pack), EdgeCodeSign)),
        ),
        (
            "Surr",
            (_make_display_pack(Breakers.make_surr_breaker(*config_pack), SurroundingCodeSign)),
        ),
        (
            "Scan",
            (_make_display_pack(Breakers.make_std_scan_breaker(*config_pack), ScanCodesign)),
        ),
        (
            "Fence",
            (_make_display_pack(Breakers.make_std_fence_breaker(*config_pack), FenceCodeSign)),
        ),
        (
            "FrontE",
            (_make_display_pack(Breakers.make_std_edge_front_breaker(*config_pack), Activation)),
        ),
        (
            "RearE",
            (_make_display_pack(Breakers.make_std_edge_rear_breaker(*config_pack), Activation)),
        ),
        (
            "SAlignT",
            (_make_display_pack(Breakers.make_std_stage_align_breaker(*config_pack), Activation)),
        ),
        (
            "SAlignM",
            (_make_display_pack(Breakers.make_stage_align_breaker_mpu(*config_pack), Activation)),
        ),
        (
            "DAlignM",
            (_make_display_pack(Breakers.make_align_direction_breaker_mpu(*config_pack), Activation)),
        ),
        (
            "DAlignT",
            (_make_display_pack(Breakers.make_std_align_direction_breaker(*config_pack), Activation)),
        ),
        (
            "TTFront",
            (_make_display_pack(Breakers.make_std_turn_to_front_breaker(*config_pack), Activation)),
        ),
        (
            "ATK",
            (_make_display_pack(Breakers.make_std_atk_breaker(*config_pack), Activation)),
        ),
        (
            "ATKE",
            (
                _make_display_pack(
                    Breakers.make_atk_breaker_with_edge_sensors(*config_pack),
                    Activation,
                )
            ),
        ),
        (
            "NSTG",
            (_make_display_pack(Breakers.make_is_on_stage_breaker(*config_pack), Activation)),
        ),
        (
            "SDAWAY",
            (_make_display_pack(Breakers.make_back_stage_side_away_breaker(*config_pack), Activation)),
        ),
        (
            "LRBLK",
            (_make_display_pack(Breakers.make_lr_sides_blocked_breaker(*config_pack), Activation)),
        ),
    ]

    if use_screen:
        screen.open(2).fill_screen(Color.BLACK).refresh().set_font_size(FontSize.FONT_6X8)
    try:
        while 1:
            data.clear()
            data.append(["Breaker", "CodeSign", "Value"])
            packs = [[name, *d()] for name, d in displays]
            data.extend(packs)
            click.clear()
            secho(table.table, bold=True)
            if use_screen:
                for pack, start_y in zip(packs, range(0, 80, 8), strict=False):
                    screen.put_string(0, start_y, "|".join(map(str, pack)))
                screen.refresh()
            sleep(interval)
    except KeyboardInterrupt:
        _logger.info("KeyboardInterrupt, exiting...")

    except Exception as e:
        _logger.critical(e)
    finally:
        _logger.info("Releasing resources.")
        if use_screen:
            screen.fill_screen(0).refresh().close()
        sensors.adc_io_close()
        _logger.info("Released")
        ctx.exit(0)


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
    "-p",
    "--add-up-per-second",
    is_flag=True,
    default=False,
    callback=bench_aps,
    help="measure add-ups per second",
)
@click.option(
    "-c",
    "--sleep-precision",
    is_flag=True,
    default=False,
    callback=bench_sleep_precision,
    help="measure sleep precision",
)
@click.option(
    "-w",
    "--light-switch-freq",
    is_flag=True,
    default=False,
    callback=bench_siglight_switch_freq,
    help="measure light switch freq",
)
def bench(**_) -> None:
    """Benchmarks."""
    echo("bench test done!")


@main.command("trac")
@click.pass_obj
@click.help_option("-h", "--help")
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
    "-o",
    "--output-path",
    show_default=True,
    default="./profile.json",
    help="Viztracer profile dump path.",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "-s",
    "--salvo",
    show_default=True,
    default=10,
    help="How many salvo to run.",
    type=click.INT,
)
@click.option(
    "-d",
    "--disable-view-profile",
    is_flag=True,
    default=False,
    help="Disable view profile using vizviewer.",
)
@click.option(
    "-p",
    "--port",
    type=click.INT,
    help="Set the port of the render server",
    default=2024,
    show_default=True,
)
def trace(
    conf: _InternalConfig,
    run_config_path: Path,
    output_path: Path,
    salvo,
    disable_view_profile: bool,
    port: int,
    **_,
) -> None:
    """Trace the std battle using viztracer."""
    from bdmc import CMD
    from viztracer import VizTracer

    from kazu.assembly import assembly_NGS_schema
    from kazu.compile import botix
    from kazu.hardwares import inited_controller, inited_tag_detector, sensors
    from kazu.signal_light import set_all_black

    output_path.parent.mkdir(parents=True, exist_ok=True)

    traver = VizTracer()

    run_config = load_run_config(run_config_path)

    app_config = conf.app_config

    sensors.adc_io_open().MPU6500_Open()
    set_all_black()
    tag_detector = inited_tag_detector(app_config).apriltag_detect_start()
    con = inited_controller(app_config)
    con.context.update(ContextVar.export_context())

    botix.token_pool = assembly_NGS_schema(app_config, run_config)
    stage_func = botix.compile(function_name="std_battle")
    seq = (0,) * salvo
    traver.start()
    for _ in seq:
        stage_func()
    traver.stop()

    set_all_black()
    tag_detector.apriltag_detect_end().release_camera()
    con.send_cmd(CMD.RESET).close()
    sensors.adc_io_close()
    traver.save(output_path.as_posix())

    if not disable_view_profile:
        from subprocess import DEVNULL, Popen

        from kazu.static import get_local_ip

        local_ip = get_local_ip()
        if local_ip is None:
            secho("Cannot get local ip, vizviewer will not be opened", fg="red", bold=True)
            return
        url = f"http://{local_ip}:{port}"
        with Popen(
            ["vizviewer", "--server_only", "--port", str(port), output_path],
            stdout=DEVNULL,
        ) as process:
            secho(f"View profile at {url}", fg="green", bold=True)

            while True:
                line = click.prompt(f"Enter '{QUIT}' to quit")
                if line == QUIT:
                    break
            process.kill()


@main.command("view")
@click.help_option("-h", "--help")
@click.argument("profile", type=click.Path(dir_okay=False, readable=True, path_type=Path))
@click.option(
    "-p",
    "--port",
    type=click.INT,
    help="Set the port of the render server",
    default=2024,
    show_default=True,
)
@click.option(
    "-f",
    "--flamegraph",
    is_flag=True,
    help="If generate flamegraph",
    default=False,
    show_default=True,
)
def view_profile(port: int, flamegraph: Path, profile: Path, **_) -> None:
    """View the profile using vizviewer."""
    from subprocess import DEVNULL, Popen

    from kazu.static import get_local_ip

    local_ip = get_local_ip()
    if local_ip is None:
        secho("Cannot get local ip, vizviewer will not be opened", fg="red", bold=True)
        return
    url = f"http://{local_ip}:{port}"

    args = ["vizviewer", "--server_only", "--port", str(port), profile.as_posix()]
    if flamegraph:
        args.append("--flamegraph")
    with Popen(args, stdout=DEVNULL) as process:
        secho(f"View profile at {url}", fg="green", bold=True)

        while True:
            line = click.prompt(f"Enter '{QUIT}' to quit")
            if line == QUIT:
                break
        process.kill()


@main.command("record")
@click.help_option("-h", "--help")
@click.pass_obj
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="./record",
    show_default=True,
    help="Output directory",
)
@click.option(
    "-i",
    "interval",
    type=click.FLOAT,
    default=0.1,
    show_default=True,
    help="Set the interval of the record",
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
def record_data(conf: _InternalConfig, output_dir: Path, interval: float, run_config_path: Path) -> None:
    """Record data."""
    from pandas import DataFrame

    from kazu.hardwares import screen, sensors
    from kazu.judgers import Breakers
    from kazu.signal_light import Color, set_all_black, sig_light_registry

    with sig_light_registry as reg:
        set_red = reg.register_all("Record|Start Recording", Color.RED)
        set_white = reg.register_all("Record|Waiting for Recording", Color.WHITE)

    run_config = load_run_config(run_config_path)
    is_pressed = Breakers.make_reboot_button_pressed_breaker(conf.app_config, run_config)

    sensors.adc_io_open()
    screen.open(2)

    recorded_df = {}
    recording_container: List[Tuple[int, ...]] = []

    sensor_conf = conf.app_config.sensor

    def _conv_to_df(data_container: List[Tuple[int, ...]]):
        pack = list(zip(*data_container, strict=False))
        col_names = [
            "Timestamp",
            "EDGE_FL",
            "EDGE_FR",
            "EDGE_RL",
            "EDGE_RR",
            "LEFT",
            "RIGHT",
            "FRONT",
            "BACK",
            "GRAY",
        ]
        if pack:
            temp_df = DataFrame(
                {
                    "Timestamp": pack[-1],
                    "EDGE_FL": pack[sensor_conf.edge_fl_index],
                    "EDGE_FR": pack[sensor_conf.edge_fr_index],
                    "EDGE_RL": pack[sensor_conf.edge_rl_index],
                    "EDGE_RR": pack[sensor_conf.edge_rr_index],
                    "LEFT": pack[sensor_conf.left_adc_index],
                    "RIGHT": pack[sensor_conf.right_adc_index],
                    "FRONT": pack[sensor_conf.front_adc_index],
                    "BACK": pack[sensor_conf.rb_adc_index],
                    "GRAY": pack[sensor_conf.gray_adc_index],
                }
            )
        else:
            temp_df = DataFrame(columns=col_names)
        return temp_df

    try:
        secho("Press the reboot button to start recording", fg="green", bold=True)
        set_white()
        while not is_pressed():
            pass
        while is_pressed():
            pass
        secho("Start recording|Salvo 1", fg="red", bold=True)
        set_red()
        while True:
            recording_container.append((*sensors.adc_all_channels(), get_timestamp()))
            sleep(interval)
            if is_pressed():
                while is_pressed():
                    pass
                secho(f"Start recording|Salvo {len(recorded_df) + 2}", fg="red", bold=True)
                recorded_df[f"record_{get_timestamp()}"] = _conv_to_df(recording_container)
                recording_container.clear()
                continue
    except KeyboardInterrupt:
        _logger.info("Record interrupted, Exiting...")
    finally:
        _logger.info(f"Recorded Salvo count: {len(recorded_df)}")
        output_dir.mkdir(exist_ok=True, parents=True)
        for k, v in recorded_df.items():
            v.to_csv(output_dir / f"{k}.csv", index=False)
        _logger.info(f"Recorded data saved to {output_dir}")
        set_all_black()
        screen.close()
        sensors.adc_io_close()
