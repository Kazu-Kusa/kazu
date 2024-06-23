from enum import Enum, auto
from pathlib import Path
from typing import Tuple, List, Self, Literal, TextIO, Any, Dict

from click import secho
from colorama import Fore
from pydantic import BaseModel
from toml import load, dump
from upic import TagDetector

from kazu.logger import _logger

DEFAULT_APP_CONFIG_PATH = f"{Path.home().as_posix()}/.kazu/config.toml"


class CounterHashable(BaseModel):

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other) -> bool:
        return id(self) == id(other)

    def __int__(self) -> int:
        return id(self)


class TagGroup(BaseModel):

    team_color: Literal["yellow", "blue"] | str
    enemy_tag: Literal[1, 2] = None
    allay_tag: Literal[1, 2] = None
    neutral_tag: Literal[0] = 0
    default_tag: int = TagDetector.Config.default_tag_id

    def __init__(self, /, **data: Any):
        super().__init__(**data)

        match self.team_color:
            case "yellow":
                self.enemy_tag = 1
                self.allay_tag = 2
            case "blue":
                self.enemy_tag = 2
                self.allay_tag = 1
            case _:
                raise ValueError(f"Invalid team_color, got {self.team_color}")
        _logger.debug(f"{Fore.MAGENTA}Team color: {self.team_color}{Fore.RESET}")


class EdgeConfig(BaseModel):
    lower_threshold: List[float] = [1400, 1500, 1500, 1400]
    upper_threshold: List[float] = [2100, 2200, 2200, 2100]

    fallback_speed: int = 2100
    fallback_duration: float = 0.7

    advance_speed: int = 2100
    advance_duration: float = 0.7

    turn_speed: int = 5000
    full_turn_duration: float = 0.45
    half_turn_duration: float = 0.225

    turn_left_prob: float = 0.5

    drift_speed: int = 6000
    drift_duration: float = 0.18


class SurroundingConfig(BaseModel):
    io_encounter_object_value: int = 0

    left_adc_lower_threshold: int = 1300
    right_adc_lower_threshold: int = 1300

    front_adc_lower_threshold: int = 1300
    back_adc_lower_threshold: int = 1500
    atk_break_front_lower_threshold: int = 1700

    atk_speed_enemy_car: int = 2300
    atk_speed_enemy_box: int = 1600
    atk_speed_neutral_box: int = 1300
    fallback_speed_ally_box: int = 4000
    fallback_speed_edge: int = 3000

    atk_enemy_car_duration: float = 6.0
    atk_enemy_box_duration: float = 6.0
    atk_neutral_box_duration: float = 6.0
    fallback_duration_ally_box: float = 0.3
    fallback_duration_edge: float = 0.2

    turn_speed: int = 5000
    turn_left_prob: float = 0.5

    rand_turn_speeds: List[int] = [3000, 5000]
    rand_turn_speed_weights: List[float] = [1, 3]

    full_turn_duration: float = 0.45
    half_turn_duration: float = 0.225


class GradientConfig(BaseModel):

    max_speed: int = 3000
    min_speed: int = 500
    lower_bound: int = 2800
    upper_bound: int = 3700


class ScanConfig(BaseModel):

    front_max_tolerance: int = 1000
    rear_max_tolerance: int = 1300
    left_max_tolerance: int = 1000
    right_max_tolerance: int = 1000

    io_encounter_object_value: int = 0

    scan_speed: int = 300
    scan_duration: float = 3.5
    scan_turn_left_prob: float = 0.5

    fall_back_speed: int = 1500
    fall_back_duration: float = 0.2

    turn_speed: int = 5000
    turn_left_prob: float = 0.5

    full_turn_duration: float = 0.45
    half_turn_duration: float = 0.225


class RandTurn(BaseModel):

    turn_speed: int = 5000
    turn_left_prob: float = 0.5
    full_turn_duration: float = 0.45
    half_turn_duration: float = 0.225


class SearchConfig(BaseModel):

    use_gradient_move: bool = True
    gradient_move_weight: float = 8
    gradient_move: GradientConfig = GradientConfig()

    use_scan_move: bool = True
    scan_move_weight: float = 1
    scan_move: ScanConfig = ScanConfig()

    use_rand_turn: bool = True
    rand_turn_weight: float = 0.5
    rand_turn: RandTurn = RandTurn()


class RandWalk(BaseModel):

    use_straight: bool = True
    straight_weight: float = 3

    rand_straight_speeds: List[int] = [1300, 1600]
    rand_straight_speed_weights: List[int | float] = [1, 3]

    use_turn: bool = True
    turn_weight: float = 1
    rand_turn_speeds: List[int] = [3000, 5000]
    rand_turn_speed_weights: List[int | float] = [1, 3]

    walk_duration: float = 0.5


class fenceConfig(BaseModel):
    front_adc_lower_threshold: int = 1200
    rear_adc_lower_threshold: int = 1300
    left_adc_lower_threshold: int = 1300
    right_adc_lower_threshold: int = 1300

    io_encounter_fence_value: int = 0
    max_yaw_tolerance: float = 20.0

    stage_align_speed: int = 1000
    max_stage_align_duration: float = 3.0
    stage_align_direction: Literal["l", "r", "rand"] = "rand"

    direction_align_speed: int = 1000
    max_direction_align_duration: float = 3.0
    direction_align_direction: Literal["l", "r", "rand"] = "rand"

    exit_corner_speed: int = 2500
    max_exit_corner_duration: float = 3.0

    rand_walk: RandWalk = RandWalk()


class StrategyConfig(BaseModel):
    use_edge_component: bool = True
    use_surrounding_component: bool = True
    use_normal_component: bool = True
    use_fence_component: bool = True


class PerformanceConfig(BaseModel):
    min_sync_interval: float = 0.007

    gray_adc_lower_threshold: int = 2000


class BootConfig(BaseModel):
    button_io_activate_case_value: int = 0

    time_to_stabilize: float = 0.1

    max_holding_duration: float = 180.0

    left_threshold: int = 1100
    right_threshold: int = 1100

    dash_speed: int = 6000
    dash_duration: float = 0.6

    turn_speed: int = 5000
    full_turn_duration: float = 0.45
    turn_left_prob: float = 0.5


class BackStageConfig(BaseModel):
    time_to_stabilize: float = 0.1

    small_advance_speed: int = 3000
    small_advance_duration: float = 0.3

    dash_speed: int = 6000
    dash_duration: float = 0.6

    turn_speed: int = 5000
    full_turn_duration: float = 0.45
    turn_left_prob: float = 0.5


class StageConfig(BaseModel):
    gray_adc_upper_threshold: int = 2850
    gray_io_off_stage_case_value: int = 0


class RunConfig(CounterHashable):

    stage: StageConfig = StageConfig()
    edge: EdgeConfig = EdgeConfig()
    surrounding: SurroundingConfig = SurroundingConfig()
    search: SearchConfig = SearchConfig()
    fence: fenceConfig = fenceConfig()

    boot: BootConfig = BootConfig()
    backstage: BackStageConfig = BackStageConfig()

    strategy: StrategyConfig = StrategyConfig()
    perf: PerformanceConfig = PerformanceConfig()

    @classmethod
    def read_config(cls, fp: TextIO) -> Self:
        """
        Reads a configuration from a file object and returns an instance of the class.

        Args:
            fp (TextIOWrapper): A file object containing the configuration data.

        Returns:
            Self: An instance of the class with the configuration data loaded from the file.

        Raises:
            ValidationError: If the loaded configuration data fails validation.
        """
        return cls.model_validate(load(fp))

    @classmethod
    def dump_config(cls, fp: TextIO, config: Self) -> None:
        """
        Dump the configuration data to a file object.

        Args:
            fp (TextIOWrapper): The file object to write the configuration data to.
            config (Self): The configuration data to be dumped.

        Returns:
            None
        """
        dump(cls.model_dump(config), fp)


class ContextVar(Enum):

    prev_salvo_speed: int = auto()

    is_aligned: bool = auto()

    recorded_pack: tuple = auto()

    gradient_speed: int = auto()

    @property
    def default(self) -> Any:
        defaults = {"prev_salvo_speed": (0, 0, 0, 0), "is_aligned": False, "recorded_pack": (), "gradient_speed": 0}
        assert self.name in defaults, "should always find a default value!"
        return defaults.get(self.name)

    @staticmethod
    def export_context() -> Dict[str, Any]:
        return {a.name: a.default for a in ContextVar}


class MotionConfig(BaseModel):
    motor_fr: Tuple[int, int] = (1, 1)
    motor_fl: Tuple[int, int] = (2, 1)
    motor_rr: Tuple[int, int] = (3, 1)
    motor_rl: Tuple[int, int] = (4, 1)
    port: str = "/dev/ttyUSB0"


class VisionConfig(BaseModel):
    team_color: Literal["yellow", "blue"] = "blue"
    resolution_multiplier: float = 1.0
    use_camera: bool = True
    camera_device_id: int = 0


class LoggerConfig(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class SensorConfig(BaseModel):

    gyro_fsr: Literal[250, 500, 1000, 2000] = 1000
    accel_fsr: Literal[2, 4, 8, 16] = 8

    adc_min_sample_interval: int = 5

    edge_fl_index: int = 0
    edge_fr_index: int = 1
    edge_rl_index: int = 2
    edge_rr_index: int = 3

    left_adc_index: int = 4
    right_adc_index: int = 5

    front_adc_index: int = 6
    rb_adc_index: int = 7

    gray_adc_index: int = 8
    # ---------IO----------

    gray_io_left_index: int = 0
    gray_io_right_index: int = 1

    fl_io_index: int = 2
    fr_io_index: int = 3

    rl_io_index: int = 4
    rr_io_index: int = 5

    reboot_button_index: int = 7


class APPConfig(CounterHashable):
    motion: MotionConfig = MotionConfig()
    vision: VisionConfig = VisionConfig()
    logger: LoggerConfig = LoggerConfig()
    sensor: SensorConfig = SensorConfig()

    @classmethod
    def read_config(cls, fp: TextIO) -> Self:
        """
        Reads a configuration from a file object and returns an instance of the class.

        Args:
            fp (TextIOWrapper): A file object containing the configuration data.

        Returns:
            Self: An instance of the class with the configuration data loaded from the file.

        Raises:
            ValidationError: If the loaded configuration data fails validation.
        """
        return cls.model_validate(load(fp))

    @classmethod
    def dump_config(cls, fp: TextIO, config: Self) -> None:
        """
        Dump the configuration data to a file object.

        Args:
            fp (TextIOWrapper): The file object to write the configuration data to.
            config (Self): The configuration data to be dumped.

        Returns:
            None
        """
        dump(cls.model_dump(config), fp)


class _InternalConfig(BaseModel):
    app_config: APPConfig = APPConfig()
    app_config_file_path: Path = Path(DEFAULT_APP_CONFIG_PATH)


def load_run_config(run_config_path: Path | None) -> RunConfig:
    if run_config_path and (r_conf := Path(run_config_path)).exists():
        secho(f'Loading run config from "{r_conf.absolute().as_posix()}"', fg="green", bold=True)
        with open(r_conf) as fp:
            run_config_path: RunConfig = RunConfig.read_config(fp)
    else:
        secho(f"Loading DEFAULT run config", fg="yellow", bold=True)
        run_config_path = RunConfig()
    return run_config_path


def load_app_config(app_config_path) -> APPConfig:
    if app_config_path.exists():
        secho(f"Load app config from {app_config_path.absolute().as_posix()}", fg="yellow")
        with open(app_config_path, encoding="utf-8") as fp:
            app_config = APPConfig.read_config(fp)
    else:
        secho(f"Create and load default app config at {app_config_path.absolute().as_posix()}", fg="yellow")
        app_config_path.parent.mkdir(parents=True, exist_ok=True)
        app_config = APPConfig()
        with open(app_config_path, "w", encoding="utf-8") as fp:
            APPConfig.dump_config(fp, app_config)
    return app_config
