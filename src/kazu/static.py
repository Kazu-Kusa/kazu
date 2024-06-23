from typing import Dict, Tuple

from mentabotix import MovingState

from kazu.config import ContextVar, TagGroup
from kazu.constant import SurroundingWeights

name = ContextVar.prev_salvo_speed.name
continues_state = MovingState(
    speed_expressions=(f"{name}[0]", f"{name}[1]", f"{name}[2]", f"{name}[3]"),
    used_context_variables=[ContextVar.prev_salvo_speed.name],
)


def make_query_table(tag_group: TagGroup) -> Dict[Tuple[int, bool], int]:
    """


    Args:
        tag_group (TagGroup):

    Returns:

    """
    query_table: Dict[Tuple[int, bool], int] = {
        (tag_group.default_tag, True): SurroundingWeights.FRONT_ENEMY_CAR,
        (tag_group.default_tag, False): SurroundingWeights.NOTHING,
        (tag_group.allay_tag, True): SurroundingWeights.FRONT_ALLY_BOX,
        (tag_group.allay_tag, False): SurroundingWeights.FRONT_ALLY_BOX,
        (tag_group.neutral_tag, True): SurroundingWeights.FRONT_NEUTRAL_BOX,
        (tag_group.neutral_tag, False): SurroundingWeights.NOTHING,
        (tag_group.enemy_tag, True): SurroundingWeights.FRONT_ENEMY_BOX,
        (tag_group.enemy_tag, False): SurroundingWeights.FRONT_ENEMY_BOX,
    }
    return query_table
