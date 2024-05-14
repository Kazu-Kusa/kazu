from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List, Self, Literal, TextIO, Optional

from pydantic import BaseModel
from toml import load, dump

DEFAULT_APP_CONFIG_PATH = f"{Path.home().as_posix()}/.kazu/config.toml"


class EdgeConfig(BaseModel):
    lower_threshold: float = 1700
    upper_threshold: float = 2200


class SurroundingConfig(BaseModel):
    lower_threshold: float = 1000
    upper_threshold: float = 2300


class NormalConfig(BaseModel): ...


class fenceConfig(BaseModel): ...


class RunConfig(BaseModel):
    edge: EdgeConfig = EdgeConfig()
    surrounding: SurroundingConfig = SurroundingConfig()
    normal: NormalConfig = NormalConfig()
    fence: fenceConfig = fenceConfig()
    # TODO fill the configs that still remain
    ...


class InitContext(BaseModel):

    on_stage: bool = False
    reset: bool = True
    # TODO fill the configs that still remain

    ...


@dataclass(frozen=True)
class Env:
    """
    KAZU_CONFIG_PATH: str = "KAZU_CONFIG_PATH"
    """

    KAZU_APP_CONFIG_PATH: str = "KAZU_APP_CONFIG_PATH"
    KAZU_RUN_CONFIG_PATH: str = "KAZU_CONFIG_PATH"
    KAZU_RUN_MODE: str = "KAZU_RUN_MODE"


@dataclass(frozen=True)
class RunMode:
    """
    run modes that suit for most use cases

    Attributes:
        AFG: [A]LWAYS O[F]F STA[G]E
        ANG: [A]LWAYS O[N] STA[G]E
        NGS: O[N] STA[G]E [S]TART
        FGS: O[F]F STA[G]E [S]TART

        FGDL: O[F]F STA[G]E [D]ASH [L]OOP
    """

    AFG: str = "AFG"
    ANG: str = "ANG"
    NGS: str = "NGS"
    FGS: str = "FGS"

    FGDL: str = "FGDL"

    @staticmethod
    def export() -> List[str]:
        return [RunMode.AFG, RunMode.ANG, RunMode.NGS, RunMode.FGS, RunMode.FGDL]


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
