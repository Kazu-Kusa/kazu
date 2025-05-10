from socket import socket, AF_INET, SOCK_DGRAM
from typing import Dict, Tuple

from mentabotix import MovingState

from kazu.config import ContextVar, TagGroup
from kazu.constant import SurroundingWeights

name = ContextVar.prev_salvo_speed.name     #这行代码获取 ContextVar.prev_salvo_speed 的名称，并将其赋值给变量 name。
continues_state = MovingState(  #创建一个 MovingState 对象，并将其赋值给变量 continues_state。
    speed_expressions=(f"{name}[0]", f"{name}[1]", f"{name}[2]", f"{name}[3]"),     #这行代码将 ContextVar.prev_salvo_speed 的名称作为 MovingState 对象的 speed_expressions 参数的值。
    used_context_variables=[ContextVar.prev_salvo_speed.name],  #这行代码将 ContextVar.prev_salvo_speed 的名称作为 MovingState 对象的 used_context_variables 参数的值。
)


def make_query_table(tag_group: TagGroup) -> Dict[Tuple[int, bool], int]:
    """


    Args:
        tag_group (TagGroup):   #这行代码定义了一个名为 tag_group 的参数，其类型为 TagGroup。

    Returns:

    """
    query_table: Dict[Tuple[int, bool], int] = {
        (tag_group.default_tag, True): SurroundingWeights.FRONT_ENEMY_CAR,  #这行代码将 (tag_group.default_tag, True) 作为键，将 SurroundingWeights.FRONT_ENEMY_CAR 作为值，添加到 query_table 字典中。
        (tag_group.default_tag, False): SurroundingWeights.NOTHING,        #这行代码将 (tag_group.default_tag, False) 作为键，将 SurroundingWeights.NOTHING 作为值，添加到 query_table
        (tag_group.allay_tag, True): SurroundingWeights.FRONT_ALLY_BOX,        #这行代码将 (tag_group.allay_tag, True) 作为键，将 SurroundingWeights.FRONT_ALLY_BOX 作为值，添加
        (tag_group.allay_tag, False): SurroundingWeights.FRONT_ALLY_BOX,    #这行代码将 (tag_group.allay_tag, False) 作为键，将 SurroundingWeights.FRONT_ALLY_BOX 作为值，添加到 query
        (tag_group.neutral_tag, True): SurroundingWeights.FRONT_NEUTRAL_BOX,    #这行代码将 (tag_group.neutral_tag, True) 作为键，将 SurroundingWeights.FRONT_NEUTRAL_BOX 作为值，添加
        (tag_group.neutral_tag, False): SurroundingWeights.NOTHING,        #这行代码将 (tag_group.neutral_tag, False) 作为键，将 SurroundingWeights.NOTHING 作为值，添加到 query
        (tag_group.enemy_tag, True): SurroundingWeights.FRONT_ENEMY_BOX,        #这行代码将 (tag_group.enemy_tag, True) 作为键，将 SurroundingWeights.FRONT_ENEMY_BOX 作为值，添加到 
        (tag_group.enemy_tag, False): SurroundingWeights.FRONT_ENEMY_BOX,       #这行代码将 (tag_group.enemy_tag, False) 作为键，将 SurroundingWeights.FRONT_ENEMY_BOX 作为值，添加到 query_table 字典中。
    }
    return query_table #这行代码返回 query_table 字典。


def get_local_ip() -> str | None:   #这行代码定义了一个名为 get_local_ip 的函数，它返回一个字符串或 None。
    """

    Returns:
        str|None : the local ip     #这行代码定义了函数的返回类型为字符串或 None。

    """
    s = socket(AF_INET, SOCK_DGRAM)     #这行代码创建了一个 socket 对象，并将其赋值给变量 s。
    try:
        # 尝试连接到一个有效的外部IP地址和端口，这里使用Google的DNS服务器
        s.connect(("8.8.8.8", 80))  #这行代码尝试连接到IP地址为 8.8.8.8，端口号为 80 的服务器。
        # 获取本地IP地址
        local_ip = s.getsockname()[0]   #这行代码获取本地IP地址，并将其赋值给变量 local_ip。
    except Exception as e:   #这行代码捕获所有异常，并将其赋值给变量 e。
        print(e)    #这行代码打印异常信息。
        return None
    finally:
        s.close()    #这行代码关闭 socket 对象。
    return local_ip     #这行代码返回本地IP地址。


def get_timestamp() -> str:
    """
    Returns a string representing the current timestamp in the format "YYYY-MM-DD-HH-MM-SS-ms".     #这行代码定义了函数的返回类型为字符串，并描述了该函数的功能。

    :return: A string representing the current timestamp.   #这行代码定义了函数的返回类型为字符串，并描述了该函数的返回值。
    :rtype: str     #这行代码定义了函数的返回类型为字符串。
    """
    import datetime

    # 获取当前时间
    now = datetime.datetime.now()   #这行代码获取当前时间，并将其赋值给变量 now。

    # 定义日期时间格式，包括毫秒
    timestamp_format = "%Y-%m-%d-%H-%M-%S-%f"

    # 格式化时间戳为字符串，去除最后三位微秒（保留毫秒）
    timestamp_str = now.strftime(timestamp_format)[:-3]

    # 返回格式化后的字符串
    return timestamp_str
