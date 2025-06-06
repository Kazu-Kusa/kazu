from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import List, Tuple

QUIT: str = "q"


class Activation(Enum):
    Activate: bool = True
    Deactivate: bool = False


@dataclass(frozen=True)
class Attitude:
    pitch: int = 0
    roll: int = 1
    yaw: int = 2


@dataclass(frozen=True)
class Axis:
    x: int = 0
    y: int = 1
    z: int = 2


@dataclass(frozen=True)
class Env:
    """KAZU_CONFIG_PATH: str = "KAZU_CONFIG_PATH"."""

    KAZU_APP_CONFIG_PATH: str = "KAZU_APP_CONFIG_PATH"
    KAZU_RUN_CONFIG_PATH: str = "KAZU_RUN_CONFIG_PATH"
    KAZU_RUN_MODE: str = "KAZU_RUN_MODE"


@dataclass(frozen=True)
class RunMode:
    """run modes that suit for most use cases.

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


@dataclass(frozen=True)
class EdgeWeights:
    FL: int = 1
    FR: int = 2
    RL: int = 4
    RR: int = 8

    @staticmethod
    def export_std_weight_seq() -> Tuple[int, int, int, int]:
        return EdgeWeights.FL, EdgeWeights.RL, EdgeWeights.RR, EdgeWeights.FR


@dataclass(frozen=True)
class FenceWeights:
    Front: int = 1
    Rear: int = 2

    Left: int = 4
    Right: int = 8


@dataclass(frozen=True)
class ScanWeights:
    Front: int = 1
    Rear: int = 2

    Left: int = 4
    Right: int = 8


@dataclass(frozen=True)
class SurroundingWeights:
    # region SURROUNDING KEYS
    LEFT_OBJECT: int = 1
    RIGHT_OBJECT: int = 2
    BEHIND_OBJECT: int = 4
    # endregion

    # region BASIC KEYS
    FRONT_ENEMY_CAR: int = 400
    FRONT_ENEMY_BOX: int = 300
    FRONT_NEUTRAL_BOX: int = 200
    FRONT_ALLY_BOX: int = 100
    NOTHING: int = 0

    # endregion


class EdgeCodeSign(IntEnum):
    """fl           fr
        O-----O
           |
        O-----O
    rl           rr.

    Notes:
        Usually the bigger the number, the more likely it is to be an edge
    """

    O_O_O_O = 0

    X_O_O_O = EdgeWeights.FL  # Front-Left encounter edge
    O_O_O_X = EdgeWeights.FR  # Front-Right encounter edge
    O_X_O_O = EdgeWeights.RL  # Rear-Left encounter edge
    O_O_X_O = EdgeWeights.RR  # Rear-Right encounter edge

    # A bunches of combinations
    X_X_O_O = EdgeWeights.FL + EdgeWeights.RL
    O_O_X_X = EdgeWeights.RR + EdgeWeights.FR
    X_O_X_O = EdgeWeights.FL + EdgeWeights.RR
    X_O_O_X = EdgeWeights.FR + EdgeWeights.FL
    O_X_X_O = EdgeWeights.RL + EdgeWeights.RR
    O_X_O_X = EdgeWeights.RL + EdgeWeights.FR

    X_X_X_O = EdgeWeights.FL + EdgeWeights.RL + EdgeWeights.RR
    X_X_O_X = EdgeWeights.FL + EdgeWeights.FR + EdgeWeights.RL
    X_O_X_X = EdgeWeights.FL + EdgeWeights.RR + EdgeWeights.FR
    O_X_X_X = EdgeWeights.RL + EdgeWeights.RR + EdgeWeights.FR

    X_X_X_X = EdgeWeights.FL + EdgeWeights.RL + EdgeWeights.RR + EdgeWeights.FR


class SurroundingCodeSign(IntEnum):
    """fl           fr
        O-----O
           |
        O-----O
    rl           rr
    Notes:
        Usually the bigger the number, the more dangerous the situation is.
    """

    # region SURROUNDING KEYS
    LEFT_OBJECT = SurroundingWeights.LEFT_OBJECT
    RIGHT_OBJECT = SurroundingWeights.RIGHT_OBJECT
    BEHIND_OBJECT = SurroundingWeights.BEHIND_OBJECT
    LEFT_RIGHT_OBJECTS = SurroundingWeights.LEFT_OBJECT + SurroundingWeights.RIGHT_OBJECT
    LEFT_BEHIND_OBJECTS = SurroundingWeights.LEFT_OBJECT + SurroundingWeights.BEHIND_OBJECT
    RIGHT_BEHIND_OBJECTS = SurroundingWeights.RIGHT_OBJECT + SurroundingWeights.BEHIND_OBJECT
    LEFT_RIGHT_BEHIND_OBJECTS = (
        SurroundingWeights.LEFT_OBJECT + SurroundingWeights.RIGHT_OBJECT + SurroundingWeights.BEHIND_OBJECT
    )
    # endregion

    # region BASIC KEYS
    FRONT_ENEMY_CAR = SurroundingWeights.FRONT_ENEMY_CAR
    FRONT_ENEMY_BOX = SurroundingWeights.FRONT_ENEMY_BOX
    FRONT_NEUTRAL_BOX = SurroundingWeights.FRONT_NEUTRAL_BOX
    FRONT_ALLY_BOX = SurroundingWeights.FRONT_ALLY_BOX
    NOTHING = SurroundingWeights.NOTHING

    # endregion

    # region ALLY BOX AND SURROUNDINGS
    FRONT_ALLY_BOX_LEFT_OBJECT = FRONT_ALLY_BOX + LEFT_OBJECT

    FRONT_ALLY_BOX_RIGHT_OBJECT = FRONT_ALLY_BOX + RIGHT_OBJECT

    FRONT_ALLY_BOX_BEHIND_OBJECT = FRONT_ALLY_BOX + BEHIND_OBJECT

    FRONT_ALLY_BOX_LEFT_RIGHT_OBJECTS = FRONT_ALLY_BOX + LEFT_RIGHT_OBJECTS

    FRONT_ALLY_BOX_LEFT_BEHIND_OBJECTS = FRONT_ALLY_BOX + LEFT_BEHIND_OBJECTS

    FRONT_ALLY_BOX_RIGHT_BEHIND_OBJECTS = FRONT_ALLY_BOX + RIGHT_BEHIND_OBJECTS

    FRONT_ALLY_BOX_LEFT_RIGHT_BEHIND_OBJECTS = FRONT_ALLY_BOX + LEFT_RIGHT_BEHIND_OBJECTS
    # endregion

    # region ENEMY BOX AND SURROUNDINGS
    FRONT_ENEMY_BOX_LEFT_OBJECT = FRONT_ENEMY_BOX + LEFT_OBJECT

    FRONT_ENEMY_BOX_RIGHT_OBJECT = FRONT_ENEMY_BOX + RIGHT_OBJECT

    FRONT_ENEMY_BOX_BEHIND_OBJECT = FRONT_ENEMY_BOX + BEHIND_OBJECT

    FRONT_ENEMY_BOX_LEFT_RIGHT_OBJECTS = FRONT_ENEMY_BOX + LEFT_RIGHT_OBJECTS

    FRONT_ENEMY_BOX_LEFT_BEHIND_OBJECTS = FRONT_ENEMY_BOX + LEFT_BEHIND_OBJECTS

    FRONT_ENEMY_BOX_RIGHT_BEHIND_OBJECTS = FRONT_ENEMY_BOX + RIGHT_BEHIND_OBJECTS

    FRONT_ENEMY_BOX_LEFT_RIGHT_BEHIND_OBJECTS = FRONT_ENEMY_BOX + LEFT_RIGHT_BEHIND_OBJECTS
    # endregion

    # region NEUTRAL BOX AND SURROUNDINGS
    FRONT_NEUTRAL_BOX_LEFT_OBJECT = FRONT_NEUTRAL_BOX + LEFT_OBJECT

    FRONT_NEUTRAL_BOX_RIGHT_OBJECT = FRONT_NEUTRAL_BOX + RIGHT_OBJECT

    FRONT_NEUTRAL_BOX_BEHIND_OBJECT = FRONT_NEUTRAL_BOX + BEHIND_OBJECT

    FRONT_NEUTRAL_BOX_LEFT_RIGHT_OBJECTS = FRONT_NEUTRAL_BOX + LEFT_RIGHT_OBJECTS

    FRONT_NEUTRAL_BOX_LEFT_BEHIND_OBJECTS = FRONT_NEUTRAL_BOX + LEFT_BEHIND_OBJECTS

    FRONT_NEUTRAL_BOX_RIGHT_BEHIND_OBJECTS = FRONT_NEUTRAL_BOX + RIGHT_BEHIND_OBJECTS

    FRONT_NEUTRAL_BOX_LEFT_RIGHT_BEHIND_OBJECTS = FRONT_NEUTRAL_BOX + LEFT_RIGHT_BEHIND_OBJECTS

    # endregion

    # region ENEMY CAR AND SURROUNDINGS
    FRONT_ENEMY_CAR_LEFT_OBJECT = FRONT_ENEMY_CAR + LEFT_OBJECT

    FRONT_ENEMY_CAR_RIGHT_OBJECT = FRONT_ENEMY_CAR + RIGHT_OBJECT

    FRONT_ENEMY_CAR_BEHIND_OBJECT = FRONT_ENEMY_CAR + BEHIND_OBJECT

    FRONT_ENEMY_CAR_LEFT_RIGHT_OBJECTS = FRONT_ENEMY_CAR + LEFT_RIGHT_OBJECTS

    FRONT_ENEMY_CAR_LEFT_BEHIND_OBJECTS = FRONT_ENEMY_CAR + LEFT_BEHIND_OBJECTS

    FRONT_ENEMY_CAR_RIGHT_BEHIND_OBJECTS = FRONT_ENEMY_CAR + RIGHT_BEHIND_OBJECTS

    FRONT_ENEMY_CAR_LEFT_RIGHT_BEHIND_OBJECTS = FRONT_ENEMY_CAR + LEFT_RIGHT_BEHIND_OBJECTS
    # endregion


@dataclass(frozen=True)
class StageWeight:
    STAGE: int = 1
    REBOOT: int = 2
    UNCLEAR: int = 4


class StageCodeSign(IntEnum):
    ON_STAGE = 0
    OFF_STAGE = StageWeight.STAGE
    ON_STAGE_REBOOT = StageWeight.REBOOT
    OFF_STAGE_REBOOT = StageWeight.STAGE + StageWeight.REBOOT
    UNCLEAR_ZONE = StageWeight.UNCLEAR
    UNCLEAR_ZONE_REBOOT = StageWeight.UNCLEAR + StageWeight.REBOOT


class FenceCodeSign(IntEnum):
    """front:0
          O-----O
    left:2   |   right:3
          O-----O
          rear:1.

    Notes:
        Usually the bigger the number, the more likely it is to be an edge
        Beware that though the CodeSign is somehow similar to that of the 'EdgeCodeSign', the meaning of the two are
        completely different.
    """

    O_O_O_O = 0  # Front,Rear,Left,Right all four direction are not encountering edge

    X_O_O_O = FenceWeights.Front  # Front encounter Fence
    O_X_O_O = FenceWeights.Rear  # Rear encounter Fence
    O_O_X_O = FenceWeights.Left  # Right encounter Fence
    O_O_O_X = FenceWeights.Right  # Left encounter Fence

    # A bunches of combinations
    X_X_O_O = FenceWeights.Front + FenceWeights.Rear
    X_O_X_O = FenceWeights.Front + FenceWeights.Left
    X_O_O_X = FenceWeights.Front + FenceWeights.Right
    O_X_X_O = FenceWeights.Rear + FenceWeights.Left
    O_X_O_X = FenceWeights.Rear + FenceWeights.Right
    O_O_X_X = FenceWeights.Left + FenceWeights.Right

    X_X_X_O = FenceWeights.Front + FenceWeights.Rear + FenceWeights.Left
    X_X_O_X = FenceWeights.Front + FenceWeights.Rear + FenceWeights.Right
    X_O_X_X = FenceWeights.Front + FenceWeights.Left + FenceWeights.Right
    O_X_X_X = FenceWeights.Rear + FenceWeights.Left + FenceWeights.Right

    X_X_X_X = FenceWeights.Front + FenceWeights.Rear + FenceWeights.Left + FenceWeights.Right


class ScanCodesign(IntEnum):
    O_O_O_O = 0

    X_O_O_O = ScanWeights.Front
    O_X_O_O = ScanWeights.Rear
    O_O_X_O = ScanWeights.Left
    O_O_O_X = ScanWeights.Right

    # A bunches of combinations
    X_X_O_O = ScanWeights.Front + ScanWeights.Rear
    X_O_X_O = ScanWeights.Front + ScanWeights.Left
    X_O_O_X = ScanWeights.Front + ScanWeights.Right
    O_X_X_O = ScanWeights.Rear + ScanWeights.Left
    O_X_O_X = ScanWeights.Rear + ScanWeights.Right
    O_O_X_X = ScanWeights.Left + ScanWeights.Right

    X_X_X_O = ScanWeights.Front + ScanWeights.Rear + ScanWeights.Left
    X_X_O_X = ScanWeights.Front + ScanWeights.Rear + ScanWeights.Right
    X_O_X_X = ScanWeights.Front + ScanWeights.Left + ScanWeights.Right
    O_X_X_X = ScanWeights.Rear + ScanWeights.Left + ScanWeights.Right

    X_X_X_X = ScanWeights.Front + ScanWeights.Rear + ScanWeights.Left + ScanWeights.Right


class SearchCodesign(IntEnum):
    GRADIENT_MOVE: int = auto()
    SCAN_MOVE: int = auto()
    RAND_TURN: int = auto()
