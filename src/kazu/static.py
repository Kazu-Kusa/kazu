from socket import socket, AF_INET, SOCK_DGRAM
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


def get_local_ip() -> str | None:
    """

    Returns:
        str|None : the local ip

    """
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        # 尝试连接到一个有效的外部IP地址和端口，这里使用Google的DNS服务器
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        local_ip = s.getsockname()[0]
    except Exception as e:
        print(e)
        return None
    finally:
        s.close()
    return local_ip
