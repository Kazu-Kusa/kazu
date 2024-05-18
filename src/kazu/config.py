from enum import Enum, auto
from pathlib import Path
from typing import Tuple, List, Self, Literal, TextIO, Optional, Any, Dict

from pydantic import BaseModel
from toml import load, dump

DEFAULT_APP_CONFIG_PATH = f"{Path.home().as_posix()}/.kazu/config.toml"


class EdgeConfig(BaseModel):
    lower_threshold: List[float] = [1700] * 4
    upper_threshold: List[float] = [2200] * 4

    fallback_speed: int = 6000
    fallback_duration: float = 0.5

    advance_speed: int = 6000
    advance_duration: float = 0.5

    turn_speed: int = 5000
    full_turn_duration: float = 0.9
    half_turn_duration: float = 0.5

    turn_left_prob: float = 0.5

    drift_speed: int = 6000
    drift_duration: float = 0.5


class SurroundingConfig(BaseModel):
    lower_threshold: List[float] = [1000] * 4
    upper_threshold: List[float] = [2300] * 4

    action_speed: float = 3000


class NormalConfig(BaseModel):

    use_gradient_speed: bool = True


class fenceConfig(BaseModel):
    lower_threshold: List[float] = [1700] * 4
    upper_threshold: List[float] = [2200] * 4


class StrategyConfig(BaseModel):
    use_edge_component: bool = True
    use_surrounding_component: bool = True
    use_normal_component: bool = True
    use_fence_component: bool = True


class PerformanceConfig(BaseModel):
    min_sync_interval: float = 0.007


class RunConfig(BaseModel):

    edge: EdgeConfig = EdgeConfig()
    surrounding: SurroundingConfig = SurroundingConfig()
    normal: NormalConfig = NormalConfig()
    fence: fenceConfig = fenceConfig()

    strategy: StrategyConfig = StrategyConfig()
    perf: PerformanceConfig = PerformanceConfig()
    # TODO fill the configs that still remain
    ...

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

    on_stage: bool = auto()
    reset: bool = auto()
    prev_salvo_speed: int = auto()
    had_encountered_edge: bool = auto()

    @property
    def default(self) -> Any:
        defaults = {
            "on_stage": False,
            "reset": True,
            "prev_salvo_speed": 0,
            "had_encountered_edge": False,
        }
        assert self.name in defaults, "should always find a default value!"
        return defaults.get(self.name)

    @staticmethod
    def export_context() -> Dict[str, Any]:
        return {a.name: a.default for a in ContextVar}


class MotionConfig(BaseModel):
    motor_fr: Tuple[int, int] = (1, 1)
    motor_fl: Tuple[int, int] = (1, 1)
    motor_rr: Tuple[int, int] = (1, 1)
    motor_rl: Tuple[int, int] = (1, 1)
    port: str = "/dev/ttyACM0"


class VisionConfig(BaseModel):
    team_color: Literal["yellow", "blue"] = "blue"
    use_camera: bool = True
    camera_device_id: int = 0


class LoggerConfig(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class SensorConfig(BaseModel):

    adc_min_sample_interval: int = 5
    edge_fl_index: int = 0
    edge_fr_index: int = 1
    edge_rl_index: int = 2
    edge_rr_index: int = 3

    gray_io_off_stage_case: int = 0
    gray_io_left_index: int = 0
    gray_io_right_index: int = 1

    gray_adc_index: int = 8
    ...
    # TODO fill the configs that still remain


class APPConfig(BaseModel):
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
    run_config: Optional[RunConfig] = None
