from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


@dataclass(frozen=True)
class Env:
    """
    KAZU_CONFIG_PATH: str = "KAZU_CONFIG_PATH"
    """

    KAZU_APP_CONFIG_PATH: str = "KAZU_APP_CONFIG_PATH"
    KAZU_RUN_CONFIG_PATH: str = "KAZU_RUN_CONFIG_PATH"
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
class SurroundingWeights:
    # region SURROUNDING KEYS
    LEFT_OBJECT = 1
    RIGHT_OBJECT = 2
    BEHIND_OBJECT = 4
    # endregion

    # region BASIC KEYS
    FRONT_ENEMY_CAR = 400
    FRONT_ENEMY_BOX = 300
    FRONT_NEUTRAL_BOX = 200
    FRONT_ALLY_BOX = 100
    NOTHING = 0

    # endregion


class EdgeCodeSign(Enum):
    """
    fl           fr
        O-----O
           |
        O-----O
    rl           rr

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


class SurroundingCodeSign(Enum):
    """
    fl           fr
        O-----O
           |
        O-----O
    rl           rr
    Notes:
        Usually the bigger the number, the more dangerous the situation is
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
    def __add__(self, other: "SurroundingCodeSign"):
        return self.value + other.value

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


class FenceCodeSign(Enum):
    """
          front:0
          O-----O
    left:2   |   right:3
          O-----O
          rear:1

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
