from enum import Enum, auto
from pathlib import Path
from typing import Tuple, List, Self, Literal, TextIO, Any, Dict, Type, Optional

from click import secho
from colorama import Fore
from pydantic import BaseModel, Field, NonNegativeInt, PositiveFloat, PositiveInt, NonNegativeFloat
from pydantic.fields import FieldInfo
from toml import dump, load
from tomlkit import document, comment, dumps, TOMLDocument, table, nl
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
    team_color: Literal["yellow", "blue", "online"] | str
    enemy_tag: Literal[0, 1, 2] = None
    allay_tag: Literal[0, 1, 2] = None
    neutral_tag: Literal[0] = 0
    default_tag: int = TagDetector.Config.default_tag_id

    def __init__(self, /, **data: Any):
        super().__init__(**data)

        match self.team_color:
            case "online":
                self.enemy_tag = 1
                self.allay_tag = 0
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
    lower_threshold: Tuple[float, float, float, float] = Field(
        default=(1740, 1819, 1819, 1740),
        description="Lower threshold values for edge detection.",
    )
    upper_threshold: Tuple[float, float, float, float] = Field(
        default=(2100, 2470, 2470, 2100), description="Upper threshold values for edge detection."
    )

    fallback_speed: PositiveInt = Field(default=2600, description="Speed when falling back.")
    fallback_duration: PositiveFloat = Field(default=0.2, description="Duration of the fallback action.")

    advance_speed: PositiveInt = Field(default=2400, description="Speed when advancing.")
    advance_duration: PositiveFloat = Field(default=0.35, description="Duration of the advance action.")

    turn_speed: PositiveInt = Field(default=2800, description="Speed when turning.")
    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")

    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)

    drift_speed: PositiveInt = Field(default=1500, description="Speed when drifting.")
    drift_duration: PositiveFloat = Field(default=0.13, description="Duration of the drift action.")

    use_gray_io: bool = Field(default=True, description="Whether to use gray IO for detection.")


class SurroundingConfig(BaseModel):
    io_encounter_object_value: int = Field(default=0, description="IO value when encountering an object.")

    left_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the left sensor.", gt=0, lt=4096
    )
    right_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the right sensor.", gt=0, lt=4096
    )

    front_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the front sensor.", gt=0, lt=4096
    )
    back_adc_lower_threshold: int = Field(
        default=1100, description="ADC lower threshold for the back sensor.", gt=0, lt=4096
    )

    atk_break_front_lower_threshold: int = Field(
        default=1500, description="Front ADC lower threshold for attack break.", gt=0, lt=4096
    )

    atk_break_use_edge_sensors: bool = Field(default=True, description="Whether to use edge sensors for attack break.")

    atk_speed_enemy_car: PositiveInt = Field(default=2300, description="Attack speed for enemy car.")
    atk_speed_enemy_box: PositiveInt = Field(default=2500, description="Attack speed for enemy box.")
    atk_speed_neutral_box: PositiveInt = Field(default=2500, description="Attack speed for neutral box.")
    fallback_speed_ally_box: PositiveInt = Field(default=2900, description="Fallback speed for ally box.")
    fallback_speed_edge: PositiveInt = Field(default=2400, description="Fallback speed for edge.")

    atk_enemy_car_duration: PositiveFloat = Field(default=4.2, description="Duration of attack on enemy car.")
    atk_enemy_box_duration: PositiveFloat = Field(default=3.6, description="Duration of attack on enemy box.")
    atk_neutral_box_duration: PositiveFloat = Field(default=3.6, description="Duration of attack on neutral box.")
    fallback_duration_ally_box: PositiveFloat = Field(default=0.3, description="Duration of fallback for ally box.")
    fallback_duration_edge: PositiveFloat = Field(default=0.2, description="Duration of fallback for edge.")

    turn_speed: NonNegativeInt = Field(default=2900, description="Speed when turning.")
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)

    turn_to_front_use_front_sensor: bool = Field(
        default=False, description="Whether to use the front sensor for turning to front."
    )

    rand_turn_speeds: List[NonNegativeInt] = Field(default=[1600, 2100, 3000], description="Random turn speeds.")
    rand_turn_speed_weights: List[float] = Field(default=[2, 3, 1], description="Weights for random turn speeds.")

    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")


class GradientConfig(BaseModel):
    max_speed: PositiveInt = Field(default=2800, description="Maximum speed for gradient move.")
    min_speed: NonNegativeInt = Field(default=500, description="Minimum speed for gradient move.")
    lower_bound: int = Field(default=2900, description="Lower bound for gradient move.", gt=0, lt=4096)
    upper_bound: int = Field(default=3700, description="Upper bound for gradient move.", gt=0, lt=4096)


class ScanConfig(BaseModel):

    front_max_tolerance: int = Field(default=760, description="Maximum tolerance for the front sensor.", gt=0, lt=4096)
    rear_max_tolerance: int = Field(default=760, description="Maximum tolerance for the rear sensor.", gt=0, lt=4096)
    left_max_tolerance: int = Field(default=760, description="Maximum tolerance for the left sensor.", gt=0, lt=4096)
    right_max_tolerance: int = Field(default=760, description="Maximum tolerance for the right sensor.", gt=0, lt=4096)

    io_encounter_object_value: int = Field(default=0, description="IO value when encountering an object.")

    scan_speed: PositiveInt = Field(default=300, description="Speed for scanning.")
    scan_duration: PositiveFloat = Field(default=4.5, description="Duration of the scan action.")
    scan_turn_left_prob: float = Field(
        default=0.5, description="Probability of turning left during scan.", ge=0, le=1.0
    )

    fall_back_speed: PositiveInt = Field(default=3250, description="Speed for falling back.")
    fall_back_duration: float = Field(default=0.2, description="Duration of the fall back action.")

    turn_speed: PositiveInt = Field(default=2700, description="Speed when turning.")
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)

    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")

    check_edge_before_scan: bool = Field(default=True, description="Whether to check edge before scanning.")
    check_gray_adc_before_scan: bool = Field(default=True, description="Whether to check gray ADC before scanning.")
    gray_adc_lower_threshold: int = Field(
        default=3100, description="Gray ADC lower threshold for scanning.", gt=0, lt=4096
    )


class RandTurn(BaseModel):

    turn_speed: PositiveInt = Field(default=2300, description="Speed when turning.")
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)
    full_turn_duration: PositiveFloat = Field(default=0.25, description="Duration of a full turn.")
    half_turn_duration: PositiveFloat = Field(default=0.15, description="Duration of a half turn.")

    use_turn_to_front: bool = Field(default=True, description="Whether to use turning to front.")


class SearchConfig(BaseModel):

    use_gradient_move: bool = Field(default=True, description="Whether to use gradient move.")
    gradient_move_weight: PositiveFloat = Field(default=100, description="Weight for gradient move.")
    use_scan_move: bool = Field(default=True, description="Whether to use scan move.")
    scan_move_weight: PositiveFloat = Field(default=1.96, description="Weight for scan move.")
    use_rand_turn: bool = Field(default=True, description="Whether to use random turn.")
    rand_turn_weight: PositiveFloat = Field(default=0.05, description="Weight for random turn.")

    gradient_move: GradientConfig = Field(default=GradientConfig(), description="Configuration for gradient move.")
    scan_move: ScanConfig = Field(default=ScanConfig(), description="Configuration for scan move.")
    rand_turn: RandTurn = Field(default=RandTurn(), description="Configuration for random turn.")


class RandWalk(BaseModel):

    use_straight: bool = Field(default=True, description="Whether to use straight movement.")
    straight_weight: PositiveFloat = Field(default=2, description="Weight for straight movement.")

    rand_straight_speeds: List[int] = Field(default=[-800, -500, 500, 800], description="Random straight speeds.")
    rand_straight_speed_weights: List[float] = Field(
        default=[1, 3, 3, 1], description="Weights for random straight speeds."
    )

    use_turn: bool = Field(default=True, description="Whether to use turning.")
    turn_weight: float = Field(default=1, description="Weight for turning.")
    rand_turn_speeds: List[int] = Field(default=[-1200, -800, 800, 1200], description="Random turn speeds.")
    rand_turn_speed_weights: List[float] = Field(default=[1, 3, 3, 1], description="Weights for random turn speeds.")

    walk_duration: PositiveFloat = Field(default=0.3, description="Duration of walking.")


class FenceConfig(BaseModel):
    front_adc_lower_threshold: int = Field(default=900, description="Front ADC lower threshold.")
    rear_adc_lower_threshold: int = Field(default=1100, description="Rear ADC lower threshold.")
    left_adc_lower_threshold: int = Field(default=900, description="Left ADC lower threshold.")
    right_adc_lower_threshold: int = Field(default=900, description="Right ADC lower threshold.")

    io_encounter_fence_value: int = Field(default=0, description="IO value when encountering a fence.")
    max_yaw_tolerance: PositiveFloat = Field(default=20.0, description="Maximum yaw tolerance.")

    use_mpu_align_stage: bool = Field(default=False, description="Whether to use MPU for aligning stage.")
    use_mpu_align_direction: bool = Field(default=False, description="Whether to use MPU for aligning direction.")

    stage_align_speed: PositiveInt = Field(default=850, description="Speed for aligning stage.")
    max_stage_align_duration: PositiveFloat = Field(default=4.5, description="Maximum duration for aligning stage.")
    stage_align_direction: Literal["l", "r", "rand"] = Field(
        default="rand", description='Turn direction for aligning stage, allow ["l", "r", "rand"].'
    )

    direction_align_speed: PositiveInt = Field(default=850, description="Speed for aligning direction.")
    max_direction_align_duration: PositiveFloat = Field(
        default=4.5, description="Maximum duration for aligning direction."
    )
    direction_align_direction: Literal["l", "r", "rand"] = Field(
        default="rand",
        description='Turn direction for aligning the parallel or vertical direction to the stage,  allow ["l", "r", "rand"].',
    )

    exit_corner_speed: PositiveInt = Field(default=1200, description="Speed for exiting corner.")
    max_exit_corner_duration: PositiveFloat = Field(default=1.5, description="Maximum duration for exiting corner.")

    rand_walk: RandWalk = Field(default=RandWalk(), description="Configuration for random walk.")


class StrategyConfig(BaseModel):
    use_edge_component: bool = Field(default=True, description="Whether to use edge component.")
    use_surrounding_component: bool = Field(default=True, description="Whether to use surrounding component.")
    use_normal_component: bool = Field(default=True, description="Whether to use normal component.")


class PerformanceConfig(BaseModel):
    checking_duration: NonNegativeFloat = Field(default=0.0, description="Duration for checking.")


class BootConfig(BaseModel):
    button_io_activate_case_value: int = Field(default=0, description="Button IO value for activating case.")

    time_to_stabilize: PositiveFloat = Field(default=0.1, description="Time to stabilize after activation.")

    max_holding_duration: PositiveFloat = Field(default=180.0, description="Maximum holding duration.")

    left_threshold: int = Field(default=1100, description="Threshold for left sensor.")
    right_threshold: int = Field(default=1100, description="Threshold for right sensor.")

    dash_speed: PositiveInt = Field(default=7000, description="Speed for dashing.")
    dash_duration: PositiveFloat = Field(default=0.55, description="Duration for dashing.")

    turn_speed: PositiveInt = Field(default=2150, description="Speed for turning.")
    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration for a full turn.")
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)


class BackStageConfig(BaseModel):
    time_to_stabilize: PositiveFloat = Field(default=0.1, description="Time to stabilize after activation.")

    small_advance_speed: PositiveInt = Field(default=1500, description="Speed for small advance.")
    small_advance_duration: PositiveFloat = Field(default=0.6, description="Duration for small advance.")

    dash_speed: PositiveInt = Field(default=7000, description="Speed for dashing.")
    dash_duration: PositiveFloat = Field(default=0.55, description="Duration for dashing.")

    turn_speed: PositiveInt = Field(default=2600, description="Speed for turning.")
    full_turn_duration: PositiveFloat = Field(default=0.35, description="Duration for a full turn.")
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)

    use_is_on_stage_check: bool = Field(default=True, description="Whether to check if on stage.")
    use_side_away_check: bool = Field(
        default=True, description="Whether to check side away after the is_on_stage check."
    )
    check_start_percent: PositiveFloat = Field(
        default=0.9,
        description="defining when does the is_on_stage check being brought on during the dashing. DO NOT set it too small!",
        lt=1.0,
    )

    side_away_degree_tolerance: PositiveFloat = Field(default=10.0, description="Degree tolerance for side away.")
    exit_side_away_speed: PositiveInt = Field(default=1300, description="Speed for exiting side away.")
    exit_side_away_duration: PositiveFloat = Field(default=0.6, description="Duration for exiting side away.")


class StageConfig(BaseModel):
    gray_adc_off_stage_upper_threshold: int = Field(default=2630, description="Upper threshold for gray ADC off stage.")
    gray_adc_on_stage_lower_threshold: int = Field(default=2830, description="Lower threshold for gray ADC on stage.")
    unclear_zone_tolerance:int = Field(default=90, description="Tolerance for judging if the car is on stage in unclear zone state.")
    unclear_zone_turn_speed: PositiveInt = Field(default=1500, description="Speed for turning in unclear zone.")
    unclear_zone_turn_duration: PositiveFloat = Field(default=0.6, description="Duration for turning in unclear zone.")
    unclear_zone_turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)
    gray_io_off_stage_case_value: int = Field(default=0, description="IO value for gray off stage.")


class RunConfig(CounterHashable):
    strategy: StrategyConfig = StrategyConfig()
    boot: BootConfig = BootConfig()
    backstage: BackStageConfig = BackStageConfig()
    stage: StageConfig = StageConfig()
    edge: EdgeConfig = EdgeConfig()
    surrounding: SurroundingConfig = SurroundingConfig()
    search: SearchConfig = SearchConfig()
    fence: FenceConfig = FenceConfig()

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
    def dump_config(cls, fp: TextIO, config: Self, with_desc: bool = True) -> None:
        """
        Dump the configuration data to a file object.

        Args:
            fp (TextIO): The file object to write the configuration data to.
            config (Config): The configuration data to be dumped.
            with_desc (bool): Whether to add descriptions to the dump file.
        Returns:
            None
        """
        if with_desc:
            # Extract description and raw data from the config
            desc_pack: Dict[str, Tuple[str | None, Dict | None]] = extract_description(config)
            raw_data = cls.model_dump(config)

            # Create a new TOML document
            data: TOMLDocument = document()
            import kazu
            import datetime

            data.add(comment(f"Exported by Kazu-v{kazu.__version__} at {datetime.datetime.now()}"))
            # Recursive function to inject descriptions into the TOML document

            # Inject the descriptions into the TOML document
            inject_description_into_toml(desc_pack, data, raw_data)

            fp.write(dumps(data))

        else:
            # If no description is needed, just use the raw data
            pure_data = cls.model_dump(config)
            dump(pure_data, fp)


class ContextVar(Enum):
    prev_salvo_speed: NonNegativeInt = auto()

    is_aligned: bool = auto()

    recorded_pack: tuple = auto()

    gradient_speed: NonNegativeInt = auto()

    unclear_zone_gray:int=auto()
    @property
    def default(self) -> Any:
        """
        Get the default value for the context variable.

        Returns:
            Any: The default value for the context variable.
        """
        defaults = {"prev_salvo_speed": (0, 0, 0, 0), "is_aligned": False, "recorded_pack": (), "gradient_speed": 0,
                    "unclear_zone_gray":0}
        assert self.name in defaults, "should always find a default value!"
        return defaults.get(self.name)

    @staticmethod
    def export_context() -> Dict[str, Any]:
        """
        Export the context variables and their default values as a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing the names of the context variables as keys and their default values as values.
        """
        return {a.name: a.default for a in ContextVar}


class MotionConfig(BaseModel):
    motor_fr: Tuple[int, int] = Field(default=(1, 1), description="Front-right motor configuration.")
    motor_fl: Tuple[int, int] = Field(default=(2, 1), description="Front-left motor configuration.")
    motor_rr: Tuple[int, int] = Field(default=(3, 1), description="Rear-right motor configuration.")
    motor_rl: Tuple[int, int] = Field(default=(4, 1), description="Rear-left motor configuration.")
    port: str = Field(default="/dev/ttyUSB0", description="Serial port for communication.")


class VisionConfig(BaseModel):
    team_color: Literal["yellow", "blue"] = Field(
        default="blue", description='Team color for vision, allow ["yellow", "blue"]'
    )
    resolution_multiplier: float = Field(default=1.0, description="Resolution multiplier for camera.")
    use_camera: bool = Field(default=True, description="Whether to use the camera.")
    camera_device_id: int = Field(default=0, description="Camera device ID.")


class DebugConfig(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description='Log level for debugging, allow ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].'
    )
    use_siglight: bool = Field(default=True, description="Whether to use signal light.")


class SensorConfig(BaseModel):
    gyro_fsr: Literal[250, 500, 1000, 2000] = Field(
        default=1000, description="Gyroscope full scale range, allows [250, 500, 1000, 2000]."
    )
    accel_fsr: Literal[2, 4, 8, 16] = Field(
        default=8, description="Accelerometer full scale range, allows [2, 4, 8, 16]."
    )

    adc_min_sample_interval: int = Field(default=5, description="Minimum ADC sample interval.")

    edge_fl_index: int = Field(default=3, description="Index for front-left edge sensor.")
    edge_fr_index: int = Field(default=0, description="Index for front-right edge sensor.")
    edge_rl_index: int = Field(default=2, description="Index for rear-left edge sensor.")
    edge_rr_index: int = Field(default=1, description="Index for rear-right edge sensor.")

    left_adc_index: int = Field(default=6, description="Index for left ADC sensor.")
    right_adc_index: int = Field(default=4, description="Index for right ADC sensor.")

    front_adc_index: int = Field(default=5, description="Index for front ADC sensor.")
    rb_adc_index: int = Field(default=7, description="Index for rear-back ADC sensor.")

    gray_adc_index: int = Field(default=8, description="Index for gray ADC sensor.")

    # ---------IO----------

    gray_io_left_index: int = Field(default=1, description="Index for left gray IO sensor.")
    gray_io_right_index: int = Field(default=0, description="Index for right gray IO sensor.")

    fl_io_index: int = Field(default=5, description="Index for front-left IO sensor.")
    fr_io_index: int = Field(default=2, description="Index for front-right IO sensor.")

    rl_io_index: int = Field(default=4, description="Index for rear-left IO sensor.")
    rr_io_index: int = Field(default=3, description="Index for rear-right IO sensor.")

    reboot_button_index: int = Field(default=6, description="Index for reboot button.")


class APPConfig(CounterHashable):
    motion: MotionConfig = MotionConfig()
    vision: VisionConfig = VisionConfig()
    debug: DebugConfig = DebugConfig()
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

        import toml

        return cls.model_validate(toml.load(fp))

    @classmethod
    def dump_config(cls, fp: TextIO, config: Self, with_desc: bool = True) -> None:
        """
        Dump the configuration data to a file object.

        Args:
            fp (TextIO): The file object to write the configuration data to.
            config (Config): The configuration data to be dumped.
            with_desc (bool): Whether to add descriptions to the dump file.
        Returns:
            None
        """
        if with_desc:
            # Extract description and raw data from the config
            desc_pack: Dict[str, Tuple[str | None, Dict | None]] = extract_description(config)
            raw_data = cls.model_dump(config)

            # Create a new TOML document
            data: TOMLDocument = document()
            import kazu
            import datetime

            data.add(comment(f"Exported by Kazu-v{kazu.__version__} at {datetime.datetime.now().timestamp()}"))

            # Recursive function to inject descriptions into the TOML document

            # Inject the descriptions into the TOML document
            inject_description_into_toml(desc_pack, data, raw_data)

            fp.write(dumps(data))

        else:
            # If no description is needed, just use the raw data
            pure_data = cls.model_dump(config)
            dump(pure_data, fp)


def inject_description_into_toml(
    desc_pack: Dict[str, Tuple[str | None, Dict | None]],
    toml_doc: TOMLDocument,
    raw_data: Dict[str, Any],
    path: List[str] = None,
):
    """
    Injects descriptions into a TOML document.

    This function recursively iterates through a dictionary containing description information and sub-model fields.
    It adds these descriptions as comments to the TOML document. If the current item is a sub-model (i.e., contains
    sub-fields), it recursively calls itself to handle the sub-model fields. For non-sub-model items, it adds the
    description as a comment and retrieves the corresponding value from the raw data to add to the TOML document.

    Parameters:
    - desc_pack: A dictionary where keys are field names and values are tuples containing the description of the field
      and sub-model fields (if any).
    - toml_doc: A TOMLDocument object representing the TOML document to be modified.
    - raw_data: A dictionary containing the source data from which to retrieve values.
    - path: A list representing the current path of the field being processed. Defaults to an empty list, used for
      recursive calls to build the complete path.

    Returns:
    No return value; the function modifies the provided `toml_doc` parameter directly.
    """

    def _nested_get(k_list: List[str], _dict: dict) -> Any:
        cur = _dict.get(k_list.pop(0))
        for k in k_list:
            cur = cur.get(k)

        return cur

    # Initialize the path if not provided
    if path is None:
        path = []

    # Iterate through the dictionary of description information and sub-model fields
    for key, (desc, sub_model_fields) in desc_pack.items():
        # Build the complete path for the current item
        cur_path = path + [key]

        # If the current item is a sub-model, add the description (if any) to the TOML document and create a new table
        # to handle the sub-model fields
        if sub_model_fields:
            toml_doc.add(comment("#" * 76 + " #"))
            if desc:
                toml_doc.add(comment(desc))
                toml_doc.add(nl())
            toml_doc[key] = (sub_table := table())
            # Recursively call itself to handle the sub-model fields
            inject_description_into_toml(sub_model_fields, sub_table, raw_data, cur_path)
            toml_doc.add(nl())

        else:
            # If the current item is not a sub-model, add the description
            toml_doc.add(comment(desc))
            # Retrieve the corresponding value from the raw data and add it to the TOML document
            toml_doc[key] = _nested_get(cur_path, raw_data)


class _InternalConfig(BaseModel):
    app_config: APPConfig = APPConfig()
    app_config_file_path: Path = Path(DEFAULT_APP_CONFIG_PATH)


def load_run_config(run_config_path: Path | None) -> RunConfig:
    """
    A function that loads the run configuration based on the provided run_config_path.

    Parameters:
        run_config_path (Path | None): The path to the run configuration file.

    Returns:
        RunConfig: The loaded run configuration.
    """
    if run_config_path and (r_conf := Path(run_config_path)).exists():
        secho(f'Loading run config from "{r_conf.absolute().as_posix()}"', fg="green", bold=True)
        with open(r_conf) as fp:
            run_config_path: RunConfig = RunConfig.read_config(fp)
    else:
        secho(f"Loading DEFAULT run config", fg="yellow", bold=True)
        run_config_path = RunConfig()
    return run_config_path


def load_app_config(app_config_path: Path | None) -> APPConfig:
    """
    A function that loads the application configuration based on the provided app_config_path.

    Parameters:
        app_config_path (Path | None): The path to the application configuration file.

    Returns:
        APPConfig: The loaded application configuration.
    """
    if app_config_path and app_config_path.exists():
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


def extract_description(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Recursively extracts description information from a given model.

    This function first extracts the information of all fields in the model (including field names and related info).
    It then iterates through each field, processing its information. For each field, if the associated model is None,
    it packs the field's description and None value into the result dictionary. Otherwise, it packs the field's
    description and the recursively extracted sub-model description information into the result dictionary.
    The function returns a dictionary where keys are field names and values are tuples containing the field's
    description and its associated model description (or None).

    Parameters:
        model: Type[BaseModel] - A class that inherits from BaseModel, representing some data structure or schema.

    Returns:
        Dict[str, Any] - A dictionary containing field names and their descriptions along with the associated model
                       description (or None).
    """

    def _extract(model_field: FieldInfo) -> Tuple[str, Optional[Type[BaseModel]]]:

        ano = model_field.annotation

        is_model = False

        try:
            is_model = issubclass(ano, BaseModel)
        except:
            pass

        return model_field.description, ano if is_model else None

    # Extract all fields and their related information from the model
    temp = {f_name: _extract(info) for f_name, info in model.model_fields.items()}
    # Initialize the final container dictionary to store processed field descriptions and related info
    fi_container = {}
    # Iterate through preprocessed field information
    for f_name, pack in temp.items():
        # Unpack the field information, including description and possible sub-model
        desc, model = pack
        # If the field does not have an associated sub-model, store the description and None value
        if model is None:
            fi_container[f_name] = pack
        else:
            # If the field has an associated sub-model, store the description and recursively extracted sub-model info
            fi_container[f_name] = desc, extract_description(model)

    return fi_container
