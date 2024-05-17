from dataclasses import dataclass
from enum import Enum
from typing import List


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

    X_O_O_O = 1  # Front-Left encounter edge
    O_O_O_X = 2  # Front-Right encounter edge
    O_X_O_O = 4  # Rear-Left encounter edge
    O_O_X_O = 8  # Rear-Right encounter edge

    # A bunches of combinations
    X_X_O_O = 5
    X_O_X_O = 9
    X_O_O_X = 3
    O_X_X_O = 12
    O_X_O_X = 6
    O_O_X_X = 10

    X_X_X_O = 13
    X_X_O_X = 7
    X_O_X_X = 11
    O_X_X_X = 14

    X_X_X_X = 15


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
    LEFT_OBJECT = 1

    RIGHT_OBJECT = 2

    BEHIND_OBJECT = 4

    LEFT_RIGHT_OBJECTS = 3

    LEFT_BEHIND_OBJECTS = 5

    RIGHT_BEHIND_OBJECTS = 6

    LEFT_RIGHT_BEHIND_OBJECTS = 7
    # endregion

    # region BASIC KEYS
    FRONT_ENEMY_CAR = 400

    FRONT_ENEMY_BOX = 300

    FRONT_NEUTRAL_BOX = 200

    FRONT_ALLY_BOX = 100

    NOTHING = 0

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

    X_O_O_O = 1  # Front encounter Fence
    O_X_O_O = 4  # Rear encounter Fence
    O_O_X_O = 8  # Right encounter Fence
    O_O_O_X = 2  # Left encounter Fence

    # A bunches of combinations
    X_X_O_O = 5
    X_O_X_O = 9
    X_O_O_X = 3
    O_X_X_O = 12
    O_X_O_X = 6
    O_O_X_X = 10

    X_X_X_O = 13
    X_X_O_X = 7
    X_O_X_X = 11
    O_X_X_X = 14

    X_X_X_X = 15
