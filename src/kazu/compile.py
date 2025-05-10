from functools import lru_cache
from typing import Callable, List, Tuple, TypeVar, Optional

from mentabotix import (
    MovingChainComposer,
    CaseRegistry,
    Botix,
    MovingState,
    MovingTransition,
    SamplerUsage,
    make_weighted_selector,
)
from pyuptech import Color

from kazu.config import APPConfig, RunConfig, ContextVar
from kazu.constant import (
    EdgeCodeSign,
    SurroundingCodeSign,
    FenceCodeSign,
    ScanCodesign,
    SearchCodesign,
    StageCodeSign,
)
from kazu.hardwares import controller, tag_detector, menta, SamplerIndexes, sensors
from kazu.judgers import Breakers
from kazu.logger import _logger
from kazu.signal_light import sig_light_registry
from kazu.static import continues_state

botix = Botix(controller=controller)

composer = MovingChainComposer()

T = TypeVar("T")    # 定义一个类型变量T，用于泛型函数


def make_edge_handler(
    app_config: APPConfig,  # 应用配置，包含传感器和其它配置。
    run_config: RunConfig,  # 运行时配置，包含边缘检测的阈值和行为配置。
    start_state: MovingState = None,    # 开始的移动状态
    normal_exit: MovingState = None,    # 正常退出的移动状态
    abnormal_exit: MovingState = None,  # 异常退出的移动状态
) -> Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:  # 返回开始状态、正常退出状态、异常退出状态和状态转换列表
    """
    根据应用和运行配置创建边缘处理函数。

    Args:
        app_config (APPConfig):  应用配置，包含传感器和其它配置。
        run_config (RunConfig):  运行时配置，包含边缘检测的阈值和行为配置。
        start_state (MovingState):  开始的移动状态。
        normal_exit (MovingState):  正常退出的移动状态。
        abnormal_exit (MovingTransition):  异常退出的移动状态。

    Returns:
        start_state: 开始的移动状态。
        normal_exit: 正常退出的移动状态。
        abnormal_exit: 异常退出的移动状态。
        transitions_pool: 状态转换列表。
    """
    start_state = start_state or continues_state.clone()    # 如果没有提供开始状态，则使用默认的继续状态
    normal_exit = normal_exit or continues_state.clone() # 如果没有提供正常退出状态，则使用默认的继续状态
    abnormal_exit = abnormal_exit or MovingState.halt()     # 如果没有提供异常退出状态，则使用停止状态

    if app_config.debug.log_level == "DEBUG":   # 如果调试级别为DEBUG，则添加调试日志

        def _log_state():
            _logger.debug("Entering Edge State")    # 记录进入边缘状态

        start_state.after_exiting.append(_log_state)
    # <editor-fold desc="Breakers">
    # 创建不同类型的边缘中断器（breaker），用于处理边缘检测逻辑
    # 边缘全中断器：用于实施分支逻辑
    # build edge full breaker, which used to implement the branching logic.
    # It uses CodeSign to distinguish the edge case
    edge_full_breaker: Callable[[], int] = Breakers.make_std_edge_full_breaker(app_config, run_config)
    # 边缘前中断器：用于在检测到前方边缘时立即停止机器人
    # build edge front breaker, used to halt the bot as soon as the edge is detected at the front,
    # using gray io and two front edge sensors
    edge_front_breaker: Callable[[], bool] = Breakers.make_std_edge_front_breaker(app_config, run_config)
    # 边缘后中断器：用于在检测到后方边缘时停止机器人
    edge_rear_breaker: Callable[[], bool] = Breakers.make_std_edge_rear_breaker(app_config, run_config)
    # </editor-fold>

    # <editor-fold desc="Templates">

    # 定义不同移动状态，如停止、继续、后退等

    fallback_state = MovingState.straight(-run_config.edge.fallback_speed)  # 后退状态

    fallback_transition = MovingTransition(run_config.edge.fallback_duration, breaker=edge_rear_breaker)    # 后退转换

    advance_state = MovingState.straight(run_config.edge.advance_speed)     # 前进状态

    advance_transition = MovingTransition(run_config.edge.advance_duration, breaker=edge_front_breaker)     # 前进转换

    left_turn_state = MovingState.turn("l", run_config.edge.turn_speed)     # 左转状态

    right_turn_state = MovingState.turn("r", run_config.edge.turn_speed)        # 右转状态

    rand_lr_turn_state = MovingState.rand_dir_turn(
        controller, run_config.edge.turn_speed, turn_left_prob=run_config.edge.turn_left_prob   # 随机左右转状态
    )

    half_turn_transition = MovingTransition(run_config.edge.half_turn_duration)     # 半转转换

    full_turn_transition = MovingTransition(run_config.edge.full_turn_duration)     # 全转转换

    drift_left_back_state = MovingState.drift("rl", run_config.edge.drift_speed)    # 左侧后退状态

    drift_right_back_state = MovingState.drift("rr", run_config.edge.drift_speed)    # 右侧后退状态

    drift_transition = MovingTransition(run_config.edge.drift_duration)     # 后退转换
    # </editor-fold>

    # <editor-fold desc="Initialize Containers">
    transitions_pool: List[MovingTransition] = []   # 状态转换列表
    (
        abnormal_exit.after_exiting.append(sig_light_registry.register_all("Edge|Abnormal Exit", Color.PURPLE))     # 添加异常退出状态
        if app_config.debug.use_siglight    # 如果使用信号灯，则添加信号灯注册
        else None
    )
    (case_reg := CaseRegistry(EdgeCodeSign)).register(EdgeCodeSign.O_O_O_O, normal_exit)    # 添加正常退出状态
    # </editor-fold>

    # <editor-fold desc="1-Activation Cases">
    # fallback and full turn right
    [head_state, *_], transition = (    # 创建边缘处理函数
        composer.init_container()   # 初始化容器
        .add(fallback_state.clone())    # 添加后退状态
        .add(fallback_transition.clone())   # 添加后退转换
        .add(right_turn_state.clone())  # 添加右转状态
        .add(full_turn_transition.clone())  # 添加全转转换
        .add(abnormal_exit)     # 添加异常退出状态
        .export_structure()     # 导出结构
    )

    transitions_pool.extend(transition)     # 添加状态转换

    case_reg.register(EdgeCodeSign.X_O_O_O, head_state)     # 注册边缘处理函数

    # -----------------------------------------------------------------------------
    # fallback and full turn left   # 后退并全转左
    [head_state, *_], transition = (    # 创建边缘处理函数
        composer.init_container()   # 初始化容器
        .add(fallback_state.clone())    # 添加后退状态
        .add(fallback_transition.clone())   # 添加后退转换
        .add(left_turn_state.clone())   # 添加左转状态
        .add(full_turn_transition.clone())  # 添加全转转换
        .add(abnormal_exit)     # 添加异常退出状态
        .export_structure()     # 导出结构
    )

    transitions_pool.extend(transition)     # 添加状态转换

    case_reg.register(EdgeCodeSign.O_O_O_X, head_state)     # 注册边缘处理函数

    # -----------------------------------------------------------------------------

    # advance and half turn right   # 前进并右半转
    [head_state, *_], transition = (    # 创建边缘处理函数
        composer.init_container()   # 初始化容器
        .add(advance_state.clone())        # 添加前进状态
        .add(advance_transition.clone())    # 添加前进转换
        .add(right_turn_state.clone())  #   添加右转状态
        .add(half_turn_transition.clone())  # 添加半转转换
        .add(abnormal_exit)  # 添加异常退出状态
        .export_structure()     # 导出结构
    )

    transitions_pool.extend(transition)     # 添加状态转换

    case_reg.register(EdgeCodeSign.O_X_O_O, head_state)     # 注册边缘处理函数

    # -----------------------------------------------------------------------------

    # advance and half turn left    # 前进并左半转
    [head_state, *_], transition = (
        composer.init_container()
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.O_O_X_O, head_state)

    # </editor-fold>

    # <editor-fold desc="2-Activation Cases">
    # half turn right   # 半转右
    [head_state, *_], transition = (
        composer.init_container()
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_X_O_O, head_state)

    # -----------------------------------------------------------------------------

    # half turn left    # 半转左
    [head_state, *_], transition = (
        composer.init_container()
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.O_O_X_X, head_state)

    # -----------------------------------------------------------------------------

    # fallback and full turn left or right  # 后退并全转左右
    [head_state, *_], transition = (
        composer.init_container()
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(rand_lr_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_O_O_X, head_state)

    # -----------------------------------------------------------------------------

    # advance   # 前进
    [head_state, *_], transition = (
        composer.init_container()
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.O_X_X_O, head_state)

    # -----------------------------------------------------------------------------

    # drift right back  # 右后退
    [head_state, *_], transition = (
        composer.init_container()
        .add(drift_right_back_state.clone())
        .add(drift_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_O_X_O, head_state)

    # -----------------------------------------------------------------------------

    # drift left back   # 左后退
    [head_state, *_], transition = (
        composer.init_container()
        .add(drift_left_back_state.clone())
        .add(drift_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.O_X_O_X, head_state)

    # </editor-fold>

    # <editor-fold desc="3-Activation Cases">

    # half turn left and advance    # 左半转并前进
    [head_state, *_], transition = (
        composer.init_container()
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.O_X_X_X, head_state)

    # -----------------------------------------------------------------------------

    # half turn right and advance   # 右半转并前进
    [head_state, *_], transition = (
        composer.init_container()
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_X_X_O, head_state)

    # -----------------------------------------------------------------------------

    # half turn right and fallback   # 右半转并后退
    [head_state, *_], transition = (
        composer.init_container()
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_O_X_X, head_state)

    # -----------------------------------------------------------------------------

    # half turn left and fallback   # 左半转并后退
    [head_state, *_], transition = (
        composer.init_container()
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_X_O_X, head_state)

    # </editor-fold>

    # <editor-fold desc="4-Activation Cases">
    # just stop immediately, since such case are extremely rare in the normal race  # 立即停止，因为这种情况在正常比赛中极为罕见
    [head_state, *_], transition = composer.init_container().add(abnormal_exit).export_structure()

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_X_X_X, head_state)

    # </editor-fold>

    # <editor-fold desc="Assembly">     # 组装
    _, head_trans = (
        composer.init_container()
        .add(start_state)
        .add(
            MovingTransition(run_config.perf.checking_duration, breaker=edge_full_breaker, to_states=case_reg.export())
        )
        .export_structure()
    )

    transitions_pool.extend(head_trans)

    # </editor-fold>

    return start_state, normal_exit, abnormal_exit, transitions_pool


def make_surrounding_handler(   # 创建周围环境处理器
    app_config: APPConfig,
    run_config: RunConfig,
    start_state: MovingState = None,
    normal_exit: MovingState = None,
    abnormal_exit: MovingState = None,
) -> Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:
    """
    构造一个处理周围环境信息的策略处理器。

    Args:
        app_config: APPConfig, 应用配置对象，包含传感器和行为配置。
        run_config: RunConfig, 运行时配置对象，包含执行环境和策略细节。
        start_state: MovingState, 开始状态，默认为None。
        normal_exit: MovingState, 正常退出状态，默认为None。
        abnormal_exit: MovingState, 异常退出状态，默认为None。

    Returns:
        Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:
      一个四元组，包含开始状态、正常退出状态、异常退出状态和一系列可能的状态转换。
    """
    start_state = start_state or continues_state.clone()
    normal_exit = normal_exit or continues_state.clone()
    abnormal_exit = abnormal_exit or MovingState.halt()
    if app_config.vision.use_camera:    # 如果使用摄像头
        start_state.before_entering.append(tag_detector.resume_detection)   # 添加恢复检测
        normal_exit.before_entering.append(tag_detector.halt_detection)     # 添加停止检测
        abnormal_exit.before_entering.append(tag_detector.halt_detection)   # 添加停止检测

    if app_config.debug.log_level == "DEBUG":

        def _log_state():
            _logger.debug("Entering Surr State")

        start_state.after_exiting.append(_log_state)

    surr_conf = run_config.surrounding  # 获取周围环境配置
    # <editor-fold desc="Breakers">

    surr_full_breaker = Breakers.make_surr_breaker(app_config, run_config)  # 创建周围环境全中断器

    atk_breaker = (
        Breakers.make_atk_breaker_with_edge_sensors(app_config, run_config)     # 使用边缘传感器创建攻击中断器
        if surr_conf.atk_break_use_edge_sensors and any([_logger.info("Using edge sensors to end the atk"), True])  # 如果使用边缘传感器
        else Breakers.make_std_atk_breaker(app_config, run_config)  # 否则创建标准攻击中断器
    )

    edge_rear_breaker = Breakers.make_std_edge_rear_breaker(app_config, run_config)     # 创建边缘后中断器

    turn_to_front_breaker = Breakers.make_std_turn_to_front_breaker(app_config, run_config)     # 创建转向前中断器
    # </editor-fold>

    # <editor-fold desc="Templates">

    atk_enemy_car_state = MovingState.straight(surr_conf.atk_speed_enemy_car)   # 创建攻击敌人汽车状态
    atk_enemy_box_state = MovingState.straight(surr_conf.atk_speed_enemy_box)   # 创建攻击敌人盒子状态
    atk_neutral_box_state = MovingState.straight(surr_conf.atk_speed_neutral_box)   # 创建攻击中立盒子状态
    allay_fallback_state = MovingState.straight(-surr_conf.fallback_speed_ally_box)     # IM23创建盟友后退状态/创建炸弹后退状态
    edge_fallback_state = MovingState.straight(-surr_conf.fallback_speed_edge)      # 创建边缘后退状态
    if app_config.debug.use_siglight:   # 如果使用信号灯
        atk_enemy_car_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Attack enemy car", Color.PURPLE, Color.RED)   # 注册攻击敌人汽车信号灯
        )
        atk_enemy_box_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Attack enemy box", Color.PURPLE, Color.YELLOW)    # 注册攻击敌人盒子信号灯
        )

        atk_neutral_box_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Attack neutral box", Color.PURPLE, Color.WHITE)   # 注册攻击中立盒子信号灯
        )

        allay_fallback_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Ally fallback", Color.PURPLE, Color.GREEN)    # IM123注册盟友后退信号灯/注册炸弹后退信号灯
        )

        edge_fallback_state.after_exiting.append(sig_light_registry.register_all("Surr|Edge fallback", Color.CYAN))     # 注册边缘后退信号灯
    atk_enemy_car_transition = MovingTransition(surr_conf.atk_speed_enemy_car, breaker=atk_breaker)     # 创建攻击敌人汽车转换
    atk_enemy_box_transition = MovingTransition(surr_conf.atk_speed_enemy_box, breaker=atk_breaker)     # 创建攻击敌人盒子转换
    atk_neutral_box_transition = MovingTransition(surr_conf.atk_neutral_box_duration, breaker=atk_breaker)  # 创建攻击中立盒子转换
    allay_fallback_transition = MovingTransition(surr_conf.fallback_duration_ally_box, breaker=edge_rear_breaker)    # IM23创建盟友后退转换/创建炸弹后退转换
    edge_fallback_transition = MovingTransition(surr_conf.fallback_duration_edge, breaker=edge_rear_breaker)    # 创建边缘后退转换

    rand_turn_state = MovingState.rand_dir_turn(
        controller, surr_conf.turn_speed, turn_left_prob=surr_conf.turn_left_prob    # 创建随机转向状态
    )
    left_turn_state = MovingState.turn("l", surr_conf.turn_speed)    # 创建左转状态
    right_turn_state = MovingState.turn("r", surr_conf.turn_speed)  # 创建右转状态
    rand_spd_turn_left_state = MovingState.rand_spd_turn(       # 创建随机速度左转状态
        controller,     
        "l",
        surr_conf.rand_turn_speeds,     # 随机速度列表
        weights=surr_conf.rand_turn_speed_weights,  # 随机速度权重
    )
    rand_spd_turn_right_state = MovingState.rand_spd_turn(  # 创建随机速度右转状态
        controller,
        "r",
        surr_conf.rand_turn_speeds,
        weights=surr_conf.rand_turn_speed_weights,
    )

    full_turn_transition = MovingTransition(surr_conf.full_turn_duration, breaker=turn_to_front_breaker)    # 创建全转向转换
    half_turn_transition = MovingTransition(surr_conf.half_turn_duration, breaker=turn_to_front_breaker)    # 创建半转向转换
    # </editor-fold>

    # <editor-fold desc="Init Container">
    transitions_pool: List[MovingTransition] = []    # 创建转换池

    (case_reg := CaseRegistry(SurroundingCodeSign)).register(SurroundingCodeSign.NOTHING, normal_exit)  # 注册无周围环境状态
    # </editor-fold>

    # <editor-fold desc="Front enemy car">
    # ---------------------------------------------------------------------

    # atk and fallback and full random turn then stop
    [head_state, *_], transitions = (    # 创建攻击敌人汽车状态和转换
        composer.init_container()   # 初始化容器
        .add(atk_enemy_car_state.clone())    # 添加攻击敌人汽车状态
        .add(atk_enemy_car_transition.clone())  # 添加攻击敌人汽车转换
        .add(edge_fallback_state.clone())    # 添加边缘后退状态
        .add(edge_fallback_transition.clone())  # 添加边缘后退转换
        .add(rand_turn_state.clone())    # 添加随机转向状态
        .add(full_turn_transition.clone())  # 添加全转向转换
        .add(abnormal_exit)     # 添加异常退出
        .export_structure()     # 导出结构
    )

    transitions_pool.extend(transitions)    # 添加转换到转换池

    case_reg.batch_register(
        [
            SurroundingCodeSign.FRONT_ENEMY_CAR,    # 前方敌人汽车
            SurroundingCodeSign.FRONT_ENEMY_CAR_RIGHT_OBJECT,    # 前方敌人汽车右方物体
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_OBJECT,    # 前方敌人汽车左方物体
            SurroundingCodeSign.FRONT_ENEMY_CAR_BEHIND_OBJECT,  # 前方敌人汽车后方物体
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_RIGHT_OBJECTS,     # 前方敌人汽车左右方物体
            SurroundingCodeSign.FRONT_ENEMY_CAR_RIGHT_BEHIND_OBJECTS,    # 前方敌人汽车右后方物体
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_BEHIND_OBJECTS,     # 前方敌人汽车左后方物体
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_RIGHT_BEHIND_OBJECTS,  # 前方敌人汽车左右后方物体
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    # </editor-fold>

    # <editor-fold desc="Target switch">
    # ---------------------------------------------------------------------
    # full random turn atk and fallback and full random turn then stop
    [head_state, *_], transitions = (   # 创建全随机转向攻击状态和转换
        composer.init_container()
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(atk_enemy_car_state.clone())
        .add(atk_enemy_car_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transitions)    # 添加转换到转换池
    case_reg.batch_register(    # 注册目标切换状态
        [
            SurroundingCodeSign.BEHIND_OBJECT,  # 后方物体
            SurroundingCodeSign.LEFT_RIGHT_BEHIND_OBJECTS,  # 左右后方物体
            SurroundingCodeSign.FRONT_ENEMY_BOX_BEHIND_OBJECT,  #前方敌人盒子后方物体
            SurroundingCodeSign.FRONT_ALLY_BOX_BEHIND_OBJECT,   #前方友方盒子后方物体
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_BEHIND_OBJECT,        #前方中立盒子后方物体
            SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_RIGHT_BEHIND_OBJECTS,    #前方友方盒子左右后方物体
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_RIGHT_BEHIND_OBJECTS,    #前方中立盒子左右后方物体
            SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_RIGHT_BEHIND_OBJECTS,  #前方敌人盒子左右后方物体
        ],
        head_state,
    )  # ---------------------------------------------------------------------
    # half turn left atk and fallback and full random turn then stop    # 创建半转向左攻击状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(atk_enemy_car_state.clone())
        .add(atk_enemy_car_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transitions)    # 添加转换到转换池
    case_reg.batch_register(    # 注册半转向左状态
        [
            SurroundingCodeSign.LEFT_OBJECT,
            SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_OBJECT,
            SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_OBJECT,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_OBJECT,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    # half turn right atk and fallback and full random turn then stop    # 创建半转向右攻击状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(atk_enemy_car_state.clone())
        .add(atk_enemy_car_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            SurroundingCodeSign.RIGHT_OBJECT,
            SurroundingCodeSign.FRONT_ENEMY_BOX_RIGHT_OBJECT,
            SurroundingCodeSign.FRONT_ALLY_BOX_RIGHT_OBJECT,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_RIGHT_OBJECT,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    # half random turn atk and fallback and full random turn then stop  # 创建半随机转向攻击状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(rand_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(atk_enemy_car_state.clone())
        .add(atk_enemy_car_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            SurroundingCodeSign.LEFT_RIGHT_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_RIGHT_OBJECTS,
            SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_RIGHT_OBJECTS,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_RIGHT_OBJECTS,
        ],
        head_state,
    )

    # ---------------------------------------------------------------------
    # random spd turn left atk and fallback and full random turn then stop  # 创建随机速度转向左攻击状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(rand_spd_turn_left_state.clone())
        .add(full_turn_transition.clone())
        .add(atk_enemy_car_state.clone())
        .add(atk_enemy_car_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            SurroundingCodeSign.LEFT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_BEHIND_OBJECTS,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    # random spd turn right atk and fallback and full random turn then stop     # 创建随机速度转向右攻击状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(rand_spd_turn_right_state.clone())
        .add(full_turn_transition.clone())
        .add(atk_enemy_car_state.clone())
        .add(atk_enemy_car_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            SurroundingCodeSign.RIGHT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_BOX_RIGHT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ALLY_BOX_RIGHT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_RIGHT_BEHIND_OBJECTS,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    # </editor-fold>

    # <editor-fold desc="Front box only">
    # ---------------------------------------------------------------------
    # atk and fallback and full random turn then stop   # 创建攻击状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(atk_enemy_box_state.clone())
        .add(atk_enemy_box_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.register(SurroundingCodeSign.FRONT_ENEMY_BOX, head_state)
    # ---------------------------------------------------------------------
    # atk and fallback and full random turn then stop   # 创建攻击状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(atk_neutral_box_state.clone())
        .add(atk_neutral_box_transition.clone())
        .add(edge_fallback_state.clone())
        .add(edge_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )
    transitions_pool.extend(transitions)
    case_reg.register(SurroundingCodeSign.FRONT_NEUTRAL_BOX, head_state)
    # ---------------------------------------------------------------------
    # fallback and full random turn then stop   # 创建后退状态和转换
    [head_state, *_], transitions = (
        composer.init_container()
        .add(allay_fallback_state.clone())
        .add(allay_fallback_transition.clone())
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )
    transitions_pool.extend(transitions)
    case_reg.register(SurroundingCodeSign.FRONT_ALLY_BOX, head_state)

    # ---------------------------------------------------------------------
    # </editor-fold>

    # <editor-fold desc="Assembly">
    _, head_trans = (
        composer.init_container()
        .add(start_state)
        .add(
            MovingTransition(run_config.perf.checking_duration, breaker=surr_full_breaker, to_states=case_reg.export())
        )
        .export_structure()
    )
    # </editor-fold>

    # <editor-fold desc="Make Return">
    transitions_pool.extend(head_trans)

    return start_state, normal_exit, abnormal_exit, transitions_pool    # 返回起始状态、正常退出状态、异常退出状态和转换池
    # </editor-fold>


def make_scan_handler(  # 创建扫描处理程序
    app_config: APPConfig,
    run_config: RunConfig,
    end_state: MovingState = None,
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a scan handler for the given application configuration, run configuration, and optional end state.    #为给定的应用程序配置、运行配置和可选的结束状态生成扫描处理程序。

    Args:
        app_config (APPConfig): The application configuration.  #应用程序配置
        run_config (RunConfig): The run configuration.  #运行配置
        end_state (MovingState, optional): The optional end state. Defaults to MovingState(0).  #可选的结束状态。默认为MovingState(0)。

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.    #包含状态列表和转换列表的元组。
    """
    end_state = end_state or MovingState.halt()     #如果end_state为空，则将其设置为MovingState.halt()

    scan_breaker = Breakers.make_std_scan_breaker(app_config, run_config)   #创建扫描断路器
    rear_edge_breaker = Breakers.make_std_edge_rear_breaker(app_config, run_config)     #创建后边断路器
    turn_to_front_breaker = Breakers.make_std_turn_to_front_breaker(app_config, run_config)     #创建转向前断路器
    conf = run_config.search.scan_move  #获取扫描移动配置
    case_reg = CaseRegistry(to_cover=ScanCodesign)  #创建案例注册表

    scan_state = MovingState.rand_dir_turn(controller, conf.scan_speed, conf.scan_turn_left_prob)    #创建扫描状态
    (
        scan_state.after_exiting.append(    #在扫描状态退出后添加
            sig_light_registry.register_singles("Scan|Start Scanning", Color.RED, Color.GREEN)
        )
        if app_config.debug.use_siglight    #如果使用信号灯
        else None   #否则不执行任何操作
    )
    scan_state.before_entering.append(  #在扫描状态进入前添加
        controller.register_context_executor(
            sensors.adc_all_channels, output_keys=ContextVar.recorded_pack.name, function_name="update_recorded_pack"
        )
    )
    if app_config.debug.log_level == "DEBUG":   #如果日志级别为DEBUG

        def _log_state():
            _logger.debug("Entering Scan State")    #记录进入扫描状态

        scan_state.after_exiting.append(_log_state)     #在扫描状态退出后添加记录函数

    rand_turn_state = MovingState.rand_dir_turn(controller, conf.turn_speed, conf.turn_left_prob)   #创建随机转向状态

    turn_left_state = MovingState.turn("l", conf.turn_speed)    #创建左转状态
    turn_right_state = MovingState.turn("r", conf.turn_speed)    #创建右转状态

    full_turn_transition = MovingTransition(run_config.surrounding.full_turn_duration, breaker=turn_to_front_breaker)    #创建全转向转换
    half_turn_transition = MovingTransition(run_config.surrounding.half_turn_duration, breaker=turn_to_front_breaker)    #创建半转向转换

    fall_back_state = MovingState.straight(-conf.fall_back_speed)   #创建后退状态
    fall_back_transition = MovingTransition(conf.fall_back_duration, breaker=rear_edge_breaker)     #创建后退转换

    (
        end_state.after_exiting.append(sig_light_registry.register_all("Scan|End Scanning", Color.RED))     #在结束状态退出后添加信号灯注册
        if app_config.debug.use_siglight    #如果使用信号灯
        else None
    )
    transitions_pool: List[MovingTransition] = []    #创建转换池
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().add(end_state).export_structure()     #创建结束状态

    transitions_pool.extend(transitions)    #将转换添加到转换池
    case_reg.register(ScanCodesign.O_O_O_O, head_state)     #注册案例
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (   #创建头部状态
        composer.init_container()   #初始化容器
        .add(fall_back_state.clone())    #添加后退状态
        .add(fall_back_transition.clone())  #添加后退转换
        .add(end_state)     #添加结束状态
        .export_structure()     #导出结构
    )

    transitions_pool.extend(transitions)    #将转换添加到转换池
    case_reg.batch_register([ScanCodesign.X_O_O_O, ScanCodesign.X_O_X_X], head_state)    #注册案例
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (   #创建头部状态
        composer.init_container()
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)    #将转换添加到转换池
    case_reg.batch_register(    #注册案例
        [
            ScanCodesign.X_X_X_X,
            ScanCodesign.X_X_X_O,
            ScanCodesign.X_X_O_X,
            ScanCodesign.O_X_X_X,
            ScanCodesign.X_X_O_O,
            ScanCodesign.O_X_X_O,
            ScanCodesign.O_X_O_X,
            ScanCodesign.O_X_O_O,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (   #创建头部状态
        composer.init_container()
        .add(turn_left_state.clone())
        .add(half_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)    #将转换添加到转换池
    case_reg.batch_register(
        [
            ScanCodesign.O_O_X_O,
            ScanCodesign.X_O_X_O,
        ],
        head_state,
    )

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (   #创建头部状态
        composer.init_container()
        .add(turn_right_state.clone())
        .add(half_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)    #将转换添加到转换池
    case_reg.batch_register(
        [
            ScanCodesign.O_O_O_X,
            ScanCodesign.X_O_O_X,
        ],
        head_state,
    )

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (   #创建头部状态
        composer.init_container()
        .add(fall_back_state.clone())
        .add(fall_back_transition.clone())
        .add(rand_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )
    
    transitions_pool.extend(transitions)    #将转换添加到转换池
    case_reg.register(ScanCodesign.O_O_X_X, head_state)     #注册案例
    # ---------------------------------------------------------------------
    composer.init_container()   #初始化容器
    if conf.check_gray_adc_before_scan:        #IM123如果检查灰度ADC
        _logger.debug("Checking gray ADC before scan")  #调试信息
        check_gray_adc_breaker = Breakers.make_check_gray_adc_for_scan_breaker(app_config, run_config)  #创建灰度ADC检查断路器
        composer.add(MovingState.halt()).add(
            MovingTransition(0, breaker=check_gray_adc_breaker, to_states={True: make_salvo_end_state()})    #添加转换
        )
    if conf.check_edge_before_scan:        #如果检查边缘
        _logger.debug("Checking edge before scan")  #调试信息
        check_edge_breaker = Breakers.make_std_edge_full_breaker(app_config, run_config)    #创建边缘检查断路器

        def boolean_full_edge_breaker() -> bool:
            """
            converts the  edge breaker to a boolean edge breaker    #将边缘断路器转换为布尔边缘断路器
            Returns:    #返回

            """
            return bool(check_edge_breaker())   #返回布尔值

        composer.add(MovingState.halt(), register_case=False).add(  #添加状态
            MovingTransition(0, breaker=boolean_full_edge_breaker, to_states={True: make_salvo_end_state()})    #添加转换
        )

    states, transitions = (     #创建状态和转换
        composer.add(scan_state, register_case=False)    #添加扫描状态
        .add(MovingTransition(conf.scan_duration, breaker=scan_breaker, to_states=case_reg.export()))    #添加转换
        .export_structure()     #导出结构
    )

    transitions_pool.extend(transitions)    #将转换添加到转换池
    return states, transitions_pool     #将转换添加到转换池并返回状态和转换池


def make_rand_turn_handler(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a handler for a random turn action.   #生成一个随机转动的处理程序。

    Args:
        app_config (APPConfig): The application configuration.  #应用程序配置。
        run_config (RunConfig): The run configuration.  #运行配置。
        end_state (MovingState, optional): The state to transition to after the random turn. Defaults to MovingState.halt().    #随机转动后的状态转换。默认为MovingState.halt()。

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.    #包含状态列表和转换列表的元组。
    """

    end_state = end_state or MovingState.halt()     #如果end_state为空，则设置为MovingState.halt()

    conf = run_config.search.rand_turn  #获取随机转动的配置

    rand_lr_turn_state = MovingState.rand_dir_turn(controller, conf.turn_speed, turn_left_prob=conf.turn_left_prob)     #创建随机左右转动状态
    (
        rand_lr_turn_state.after_exiting.append(sig_light_registry.register_all("Rturn|Start Rturn", Color.YELLOW))     #注册信号灯
        if app_config.debug.use_siglight    #如果使用信号灯
        else None
    )
    breaker = (
        Breakers.make_std_turn_to_front_breaker(app_config, run_config)     #创建标准转向前断路器
        if conf.use_turn_to_front and any([_logger.info("RTurn uses TTF Breaker"), True])   #如果使用转向前
        else None
    )
    half_turn_transition = MovingTransition(conf.half_turn_duration, breaker=breaker)    #创建半转换

    states, transitions = composer.add(rand_lr_turn_state).add(half_turn_transition).add(end_state).export_structure()  #导出结构
    return states, transitions  #返回状态和转换


def make_gradient_move(     #生成梯度移动
    app_config: APPConfig, run_config: RunConfig, is_salvo_end: bool = True, fall_back: bool = False
) -> MovingState:
    """
    Generates a MovingState object for a gradient move in a search algorithm.   #在搜索算法中生成梯度移动的MovingState对象。

    Args:
        app_config (APPConfig): The application configuration.  #应用程序配置。
        run_config (RunConfig): The run configuration.  #运行配置。
        is_salvo_end (bool, optional): Indicates if this is the last gradient move in a salvo. Defaults to True.    #指示这是否是齐射中的最后一次梯度移动。默认为True。
        fall_back (bool): Indicates if the gradient move should be in the opposite direction.   #指示梯度移动是否应该朝相反方向。

    Returns:
        MovingState: The MovingState object representing the gradient move.     #表示梯度移动的MovingState对象。

    """
    conf = run_config.search.gradient_move  #获取梯度移动的配置

    sign = "-" if fall_back else ""     #如果反向，则设置为-，否则设置为空
    speed_range = conf.max_speed - conf.min_speed    #获取速度范围

    speed_calc_func = menta.construct_inlined_function(     #创建内联函数
        usages=[
            SamplerUsage(
                used_sampler_index=SamplerIndexes.adc_all, required_data_indexes=[app_config.sensor.gray_adc_index]     #获取灰度ADC索引
            )
        ],
        judging_source=f"ret={sign}({conf.min_speed}+int({speed_range}*(s0-{conf.min_speed})/({conf.max_speed}-{conf.min_speed})))",    #计算速度
        return_type=int,    #返回类型为int
        return_raw=False,   #返回原始值
        function_name="calc_gradient_speed",    #函数名为calc_gradient_speed
    )
    updaters = []   #创建更新器列表
    speed_updater = controller.register_context_executor(    #注册上下文执行器
        speed_calc_func, [ContextVar.gradient_speed.name], function_name="_update_gradient_speed"   #更新梯度速度
    )
    updaters.append(speed_updater)  #将更新器添加到列表中
    if is_salvo_end:    #如果is_salvo_end为真
        getter: Callable[[], int] = controller.register_context_getter(ContextVar.gradient_speed.name)  #注册上下文获取器

        def _update_salvo_end_speed() -> Tuple[int, int, int, int]:
            speed = getter()    #获取速度
            return speed, speed, speed, speed   #返回速度

        salvo_end_speed_updater = controller.register_context_executor(     #注册上下文执行器
            _update_salvo_end_speed, [ContextVar.prev_salvo_speed.name], function_name="_update_salvo_end_speed"    #更新齐射结束速度
        )
        updaters.append(salvo_end_speed_updater)    #将更新器添加到列表中

    return MovingState(
        speed_expressions=ContextVar.gradient_speed.name,   #速度表达式
        used_context_variables=[ContextVar.gradient_speed.name],    #使用的上下文变量
        before_entering=updaters,   #进入前
        after_exiting=(     #在退出后
            [sig_light_registry.register_all("GMove|Start gradient move", Color.BLUE)]  #注册信号灯
            if app_config.debug.use_siglight    #如果使用信号灯
            else []     #否则为空
        ),
    )


def make_search_handler(    #生成搜索处理程序
    app_config: APPConfig,  #应用程序配置
    run_config: RunConfig,  #运行配置
    start_state: MovingState = None,    #开始状态
    stop_state: MovingState = None,     #停止状态
) -> Tuple[List[MovingState], List[MovingTransition]]:  #返回状态和转换
    """
    Generates a search handler for the given application configuration, run configuration, and optional start and stop states.  #为给定的应用程序配置、运行配置和可选的开始和停止状态生成搜索处理程序。

    Args:
        app_config (APPConfig): The application configuration.  #应用程序配置。
        run_config (RunConfig): The run configuration.  #运行配置。
        start_state (MovingState, optional): The optional start state. Defaults to None.    #可选的开始状态。默认为None。
        stop_state (MovingState, optional): The stop state. Defaults to MovingState.halt().     #停止状态。默认为MovingState.halt()。

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.    #包含状态列表和转换列表的元组。
    """
    start_state = start_state or continues_state.clone()    #如果开始状态为空，则克隆continues_state
    stop_state = stop_state or MovingState.halt()   #如果停止状态为空，则设置为MovingState.halt()
    scan_states, scan_transitions = make_scan_handler(app_config, run_config, end_state=stop_state)     #生成扫描处理程序
    rand_turn_states, rand_turn_transitions = make_rand_turn_handler(app_config, run_config, end_state=stop_state)  #生成随机转向处理程序
    grad_move_state = make_gradient_move(app_config, run_config, is_salvo_end=True)     #生成梯度移动处理程序

    pool = []   #创建池
    w = []  #创建池和权重列表
    if run_config.search.use_gradient_move:     #如果使用梯度移动
        _logger.info(f"Using gradient move, weight: {run_config.search.gradient_move_weight}")  #记录日志
        pool.append(SearchCodesign.GRADIENT_MOVE)    #将梯度移动添加到池中
        w.append(run_config.search.gradient_move_weight)    #将权重添加到权重列表中
    if run_config.search.use_rand_turn:     #如果使用随机转向
        _logger.info(f"Using random turn, weight: {run_config.search.rand_turn_weight}")    #记录日志
        pool.append(SearchCodesign.RAND_TURN)   #将随机转向添加到池中
        w.append(run_config.search.rand_turn_weight)    #将权重添加到权重列表中
    if run_config.search.use_scan_move:     #如果使用扫描移动
        _logger.info(f"Using scan move, weight: {run_config.search.scan_move_weight}")  #记录日志
        pool.append(SearchCodesign.SCAN_MOVE)   #将扫描移动添加到池中
        w.append(run_config.search.scan_move_weight)    #将权重添加到权重列表中

    w_selector = make_weighted_selector(pool, w)    #创建权重选择器
    case_reg = CaseRegistry(SearchCodesign)     #创建案例注册表

    case_reg.register(SearchCodesign.GRADIENT_MOVE, grad_move_state)    #将梯度移动状态添加到案例注册表中
    case_reg.register(SearchCodesign.RAND_TURN, rand_turn_states[0])    #将随机转向状态添加到案例注册表中
    case_reg.register(SearchCodesign.SCAN_MOVE, scan_states[0])     #将扫描移动状态添加到案例注册表中

    trans = MovingTransition(0, breaker=w_selector, to_states=case_reg.export())    #创建转换
    states, transitions = composer.init_container().add(start_state).add(trans).export_structure()  #将开始状态和转换添加到容器中，并导出结构

    states_pool = [*states, *scan_states, *rand_turn_states, grad_move_state]    #将状态添加到状态池中
    transitions_pool = [*transitions, *scan_transitions, *rand_turn_transitions]    #将转换添加到转换池中
    return states_pool, transitions_pool    #返回状态池和转换池
   

def make_fence_handler(     #生成围栏处理程序
    app_config: APPConfig,  #应用程序配置
    run_config: RunConfig,  #运行配置
    start_state: MovingState = None,    #开始状态
    stop_state: MovingState = None,     #停止状态
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:    #返回开始状态、停止状态和转换列表
    """
    Generates a fence handler for a given app configuration, run configuration, and optional start state.   #为给定的应用程序配置、运行配置和可选的开始状态生成围栏处理程序。

    Args:
        app_config (APPConfig): The app configuration.   #应用程序配置。
        run_config (RunConfig): The run configuration.   #运行配置。
        start_state (MovingState, optional): The optional start state. Defaults to None.    #可选的开始状态。默认为None。
        stop_state (MovingState, optional): The stop state. Defaults to MovingState.halt().     #停止状态。默认为MovingState.halt()。

    Returns:
        Tuple[MovingState, MovingState, List[MovingTransition]]: A tuple containing the start state, stop state, and list of transitions.    #包含开始状态、停止状态和转换列表的元组。
    """

    start_state = start_state or continues_state.clone()    #如果开始状态为空，则克隆continues_state
    stop_state = stop_state or MovingState.halt()    #如果停止状态为空，则设置为MovingState.halt()
    transitions_pool: List[MovingTransition] = []       #创建转换池
    if app_config.debug.log_level == "DEBUG":

        def _log_state():
            _logger.debug("Entering Fence State")

        start_state.after_exiting.append(_log_state)    #将日志状态添加到开始状态的退出后列表中
    fence_breaker = Breakers.make_std_fence_breaker(app_config, run_config)     #创建围栏断路器

    align_stage_breaker = (
        Breakers.make_stage_align_breaker_mpu(app_config, run_config)    #创建舞台对齐断路器
        if run_config.fence.use_mpu_align_stage and any([_logger.info("Using MPU to align stage"), True])   #如果使用MPU对齐舞台，则记录日志并返回True
        else Breakers.make_std_stage_align_breaker(app_config, run_config)      #否则创建标准舞台对齐断路器
    )
    lr_blocked_breaker = Breakers.make_lr_sides_blocked_breaker(app_config, run_config)     #创建左右侧被阻挡断路器

    back_stage_states, back_stage_transitions, _, back_stage_trans_all = make_back_to_stage_handler(    #创建返回舞台处理程序
        app_config, run_config, stop_state
    )
    transitions_pool.extend(back_stage_trans_all)   #将返回舞台转换添加到转换池中
    back_stage_pack = (back_stage_states, back_stage_transitions)    #将返回舞台状态和转换打包
    rand_move_pack = make_rand_walk_handler(app_config, run_config, stop_state)     #创建随机行走处理程序

    rand_move_head_state = rand_move_pack[0][0]     #获取随机行走处理程序中的第一个状态
    align_direction_pack = make_align_direction_handler(app_config, run_config, rand_move_head_state, stop_state)    #创建对齐方向处理程序

    conf = run_config.fence     #获取围栏配置
    
    rear_exit_corner_state = MovingState.straight(-conf.exit_corner_speed)   #创建后退出角状态
    front_exit_corner_state = MovingState.straight(conf.exit_corner_speed)   #创建前退出角状态

    exit_duration = MovingTransition(conf.max_exit_corner_duration, breaker=lr_blocked_breaker)     #创建退出持续时间

    match conf.stage_align_direction:    #根据舞台对齐方向匹配
        case "rand":
            align_state = MovingState.rand_dir_turn(controller, conf.stage_align_speed)     #创建随机方向转向状态
        case "l":
            align_state = MovingState.turn("l", conf.stage_align_speed)     #创建左转向状态
        case "r":
            align_state = MovingState.turn("r", conf.stage_align_speed)     #创建右转向状态
        case _:
            raise ValueError(f"Invalid align direction: {conf.stage_align_direction}")  #如果对齐方向无效，则引发ValueError

    align_stage_transition = MovingTransition(
        conf.max_stage_align_duration, breaker=align_stage_breaker, to_states={False: rand_move_head_state}     #创建舞台对齐转换
    )

    case_reg = CaseRegistry(FenceCodeSign)  #创建案例注册表

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().concat(*back_stage_pack).export_structure()    #将返回舞台状态和转换打包
    transitions_pool.extend(transitions)    #将转换添加到转换池中
    case_reg.register(FenceCodeSign.X_O_O_O, head_state)    #注册案例

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (   #创建舞台对齐处理程序
        composer.init_container()   #初始化容器
        .add(align_state.clone())    #添加对齐状态
        .add(align_stage_transition.clone())    #添加舞台对齐转换
        .concat(*back_stage_pack, register_case=True)  # back to stage only when the check is passed    #当检查通过时，仅返回舞台
        .export_structure()        #导出结构
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(    #批量注册案例
        [
            FenceCodeSign.O_X_O_O,
            FenceCodeSign.O_O_X_O,
            FenceCodeSign.O_O_O_X,
            FenceCodeSign.O_O_X_X,
            FenceCodeSign.X_X_O_O,
        ],
        head_state,     #案例状态
    )
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (   #创建前退出角状态
        composer.init_container()
        .add(front_exit_corner_state.clone())
        .add(exit_duration.clone())
        .add(stop_state)
        .export_structure()
    )
    transitions_pool.extend(transitions)    #将转换添加到转换池中
    case_reg.batch_register([FenceCodeSign.O_X_O_X, FenceCodeSign.O_X_X_O], head_state)     #注册案例
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(rear_exit_corner_state.clone())
        .add(exit_duration.clone())
        .add(stop_state)
        .export_structure()
    )
    transitions_pool.extend(transitions)    #将转换添加到转换池中
    case_reg.batch_register([FenceCodeSign.X_O_O_X, FenceCodeSign.X_O_X_O], head_state)     #注册案例
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().concat(*align_direction_pack).export_structure()  #将对齐方向状态和转换打包
    transitions_pool.extend(transitions)    #将转换添加到转换池中
    case_reg.batch_register(    #批量注册案例
        [FenceCodeSign.O_X_X_X, FenceCodeSign.X_O_X_X, FenceCodeSign.X_X_O_X, FenceCodeSign.X_X_X_O], head_state
    )
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().concat(*rand_move_pack).export_structure()    #将随机行走状态和转换打包
    transitions_pool.extend(transitions)    #将转换添加到转换池中
    case_reg.batch_register([FenceCodeSign.O_O_O_O, FenceCodeSign.X_X_X_X], head_state)     #注册案例
    # ---------------------------------------------------------------------

    (
        start_state.after_exiting.append(sig_light_registry.register_all("Fence|Starting Fence finding", Color.ORANGE))     #注册所有案例
        if app_config.debug.use_siglight    #如果使用信号灯
        else None
    )
    # <editor-fold desc="Assembly">
    _, head_trans = (
        composer.init_container()
        .add(start_state)
        .add(MovingTransition(run_config.perf.checking_duration, breaker=fence_breaker, to_states=case_reg.export()))
        .export_structure()
    )
    # </editor-fold>

    # <editor-fold desc="Make Return">
    transitions_pool.extend(head_trans)

    return start_state, stop_state, list(set(transitions_pool))     #返回开始状态、停止状态和转换池
    # </editor-fold>


def make_align_direction_handler(   #创建对齐方向处理程序
    app_config: APPConfig,
    run_config: RunConfig,
    not_aligned_state: Optional[MovingState] = None,
    aligned_state: Optional[MovingState] = None,
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Constructs a state machine handler for aligning the direction.  #构建对齐方向状态机处理程序

    Parameters:
        app_config (APPConfig): The configuration object for the application.   #应用程序配置对象
        run_config (RunConfig): The runtime configuration object.   #运行时配置对象
        not_aligned_state (MovingState): The state to transition to when not aligned. Defaults to MovingState.halt().   #未对齐时的转换状态
        aligned_state (MovingState, optional): The state to transition to when aligned. Defaults to None.   #对齐时的转换状态

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and transitions.    #包含状态和转换的元组

    Raises:
        ValueError: If the align direction is invalid.  #如果对齐方向无效
    """

    conf = run_config.fence     #获取对齐方向配置

    match conf.direction_align_direction:   #根据对齐方向配置选择对齐状态
        case "rand":
            align_state = MovingState.rand_dir_turn(controller, conf.direction_align_speed)     #随机方向转动
        case "l":
            align_state = MovingState.turn("l", conf.direction_align_speed)     #左转
        case "r":
            align_state = MovingState.turn("r", conf.direction_align_speed)     #右转
        case _:
            raise ValueError(f"Invalid align direction: {conf.direction_align_direction}")  #无效的对齐方向 
    align_direction_breaker = (     #创建对齐方向断路器
        Breakers.make_align_direction_breaker_mpu(app_config, run_config)   #使用MPU对齐方向断路器
        if run_config.fence.use_mpu_align_direction and any([_logger.info("Using MPU to align direction"), True])   #如果使用MPU对齐方向
        else Breakers.make_std_align_direction_breaker(app_config, run_config)  #否则使用标准对齐方向断路器
    )
    if aligned_state and not_aligned_state:     #如果对齐状态和未对齐状态都存在
        branch = {True: aligned_state, False: not_aligned_state}
    elif aligned_state:     #如果只有对齐状态
        branch = {True: aligned_state}
    elif not_aligned_state:     #如果只有未对齐状态
        branch = {False: not_aligned_state}
    else:
        branch = {}     #否则为空
    align_direction_transition = MovingTransition(  #创建对齐方向转换
        conf.max_direction_align_duration,  #对齐方向最大持续时间
        breaker=align_direction_breaker,    #对齐方向断路器
        to_states=branch,   #对齐方向转换状态
    )

    composer.init_container().add(align_state).add(align_direction_transition)  #初始化容器并添加对齐状态和对齐方向转换
    return composer.export_structure() #导出结构


def make_back_to_stage_handler(     #IM123创建回到舞台处理程序
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None, **_ #创建回到舞台处理程序
) -> Tuple[List[MovingState], List[MovingTransition], List[MovingState], List[MovingTransition]]:   #返回状态和转换的元组
    """
    Creates a state machine handler for moving back to the stage.   #创建回到舞台状态机处理程序

    Args:
        app_config (APPConfig): The configuration object for the application.   #应用程序配置对象
        run_config (RunConfig): Runtime configuration object with parameters for movement actions. #运行时配置对象，包含移动动作的参数
        end_state (MovingState, optional): The final state of the state machine. Defaults to MovingState.halt().    #状态机的最终状态

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing lists of states and transitions.   #包含状态和转换的元组
    """

    end_state = end_state or MovingState.halt()     #如果最终状态为空，则设置为停止状态
    small_advance = MovingState(run_config.backstage.small_advance_speed)   #创建小前进状态
    small_advance_transition = MovingTransition(run_config.backstage.small_advance_duration)    #创建小前进转换
    stab_trans = MovingTransition(run_config.backstage.time_to_stabilize)    #创建稳定转换
    # waiting for a booting signal, and dash on to the stage once received  #等待启动信号，收到后 dashes 进入舞台

    (
        small_advance.after_exiting.append(sig_light_registry.register_all("BStage|Small move", Color.GREEN))    #将小前进状态添加到退出时
        if app_config.debug.use_siglight    #如果使用信号灯
        else None
    )
    (
        composer.init_container()
        .add(small_advance)
        .add(small_advance_transition)
        .add(MovingState.halt())
        .add(stab_trans.clone())
        .add(dash_state := MovingState.straight(-run_config.backstage.dash_speed))
    )
    concat_state = None
    if run_config.backstage.use_is_on_stage_check:  #如果使用舞台检查
        _logger.info("Using is_on_stage_check to restrict the behavior.")   #使用舞台检查来限制行为
        is_on_stage_breaker = Breakers.make_is_on_stage_breaker(app_config, run_config)     #创建舞台断路器

        dash_trans = MovingTransition(  #创建 dashes 转换
            run_config.backstage.dash_duration * run_config.backstage.check_start_percent,  # dashes 转换持续时间
        )  # during which the detection is disabled     #在此期间禁用检测

        checking_dash_trans = MovingTransition(     #创建检查 dashes 转换
            run_config.backstage.dash_duration * (1 - run_config.backstage.check_start_percent),    #检查 dashes 转换持续时间
            breaker=is_on_stage_breaker,    #舞台断路器
            to_states={False: (concat_state := MovingState.halt())},    #如果舞台断路器为假，则转换为 concat_state
        )
        (composer.add(dash_trans).add(dash_state.clone()).add(checking_dash_trans))     #添加 dashes 状态和转换
    else:
        dash_trans = MovingTransition(run_config.backstage.dash_duration)   #创建 dashes 转换
        (composer.add(dash_trans))  #. add(dash_state.clone())    #添加 dashes 状态和转换

    composer.add(MovingState.halt(), register_case=True).add(stab_trans.clone())    #添加停止状态和稳定转换

    # turn_section  # 转弯部分
    main_branch_states, main_branch_transitions = (     #创建主分支状态和转换
        composer.add(
            MovingState.rand_dir_turn(
                controller, run_config.backstage.turn_speed, turn_left_prob=run_config.backstage.turn_left_prob     #创建随机方向转弯状态
            ),
            register_case=True,     #注册案例
        )
        .add(MovingTransition(run_config.backstage.full_turn_duration))     #添加完整转弯转换
        .add(end_state)     #添加最终状态
        .export_structure()     #导出结构
    )

    all_states, all_transitions = list(main_branch_states), list(main_branch_transitions)   #将主分支状态和转换转换为列表
    if run_config.backstage.use_is_on_stage_check and run_config.backstage.use_side_away_check:     #如果使用舞台检查和侧移检查
        _logger.info("Using side_away_check to restrict the behavior.")     #使用侧移检查来限制行为
        side_away_breaker = Breakers.make_back_stage_side_away_breaker(app_config, run_config)  #创建侧移断路器
        extra_states, extra_transitions = (     #创建额外状态和转换
            composer.init_container()   #初始化容器
            .add(concat_state)
            .add(
                MovingTransition(
                    0,
                    breaker=side_away_breaker,  #舞台断路器
                    to_states={False: end_state},   #如果舞台断路器为假，则转换为最终状态
                )
            )
            .add(MovingState(run_config.backstage.exit_side_away_speed), register_case=True)
            .add(MovingTransition(run_config.backstage.exit_side_away_duration))
            .add(end_state)
            .export_structure()
        )
        all_states.extend(extra_states)     #将额外状态添加到所有状态
        all_transitions.extend(extra_transitions)   #将额外转换添加到所有转换

    return main_branch_states, main_branch_transitions, all_states, all_transitions     #返回主分支状态和转换，所有状态和转换


def make_reboot_handler(    #创建重启处理程序
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None     #创建重启处理程序
) -> Tuple[List[MovingState], List[MovingTransition]]:  #返回一个包含状态和转换的元组
    """
    Constructs a state machine handler for reboot sequences.    #构建一个用于重启序列的状态机处理程序

    Parameters:
        app_config: APPConfig, configuration object for application specifics including sensor details.     #应用程序配置对象，包括传感器详细信息
        run_config: RunConfig, runtime configuration object with parameters for bootup and movement actions.    #运行时配置对象，包含启动和移动动作的参数
        end_state: MovingState, the final state of the state machine, defaults to MovingState(0).   #状态机的最终状态，默认为 MovingState(0)

    Returns:
        Tuple[List[MovingState], List[MovingTransition]], a tuple containing lists of states and transitions.   #包含状态和转换列表的元组
    """
    end_state = end_state or MovingState.halt()     #如果最终状态为空，则设置为停止状态

    activation_breaker = menta.construct_inlined_function(  #创建激活断路器
        usages=[
            SamplerUsage(
                used_sampler_index=SamplerIndexes.adc_all,  #使用 adc_all 采样器
                required_data_indexes=[app_config.sensor.left_adc_index, app_config.sensor.right_adc_index],    #所需数据索引
            )
        ],
        judging_source=f"ret=s0>{run_config.boot.left_threshold} and s1>{run_config.boot.right_threshold}",     #判断源
        return_type=bool,   #返回类型
        return_raw=False,   #返回原始值
        function_name="reboot_breaker",     #函数名称
    )

    holding_transition = MovingTransition(run_config.boot.max_holding_duration, breaker=activation_breaker)     #创建保持转换
    # waiting for a booting signal, and dash on to the stage once received  #等待启动信号，一旦收到就冲上舞台
    states, transitions = (     #创建状态和转换
        composer.init_container()   #初始化容器
        .add(
            MovingState(
                0,
                before_entering=(
                    [sig_light_registry.register_singles("Reboot|Start rebooting", Color.G_RED, Color.R_GREEN)]     #注册单次信号灯
                    if app_config.debug.use_siglight    #如果使用信号灯
                    else []
                ),
            )
        )
        .add(holding_transition)
        .add(
            MovingState(
                -run_config.boot.dash_speed,
                after_exiting=(
                    [sig_light_registry.register_singles("Reboot|In rebooting", Color.DARKBLUE, Color.DARKGREEN)]   #注册单次信号灯
                    if app_config.debug.use_siglight
                    else []
                ),
            )
        )
        .add(MovingTransition(run_config.boot.dash_duration))
        .add(MovingState.halt())
        .add(MovingTransition(run_config.boot.time_to_stabilize))
        .add(
            MovingState.rand_dir_turn(
                controller, run_config.boot.turn_speed, turn_left_prob=run_config.boot.turn_left_prob   #随机方向转弯
            )
        )
        .add(MovingTransition(run_config.boot.full_turn_duration))
        .add(end_state)
        .export_structure()
    )

    return states, transitions  #返回状态和转换


def make_rand_walk_handler(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None, **_
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a random walk handler for the given run configuration and end state.  #为给定的运行配置和最终状态生成随机行走处理程序

    Args:
        app_config (APPConfig): The application configuration containing the sensor details.    #应用程序配置，包含传感器详细信息
        run_config (RunConfig): The run configuration containing the fence settings.    #运行配置，包含栅栏设置
        end_state (MovingState, optional): The end state to transition to after the random walk. Defaults to MovingState.halt().    #随机行走后的转换状态，默认为 MovingState.halt()
        **_: Additional keyword arguments.  #额外的关键字参数

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.    #包含状态列表和转换列表的元组

    Raises:
        None

    Description:
        This function generates a random walk handler based on the given run configuration. It creates a list of moves  #根据给定的运行配置生成随机行走处理程序。它创建一个移动列表  
        and their corresponding weights based on the fence settings in the run configuration. The moves can be either turns     #基于运行配置中的栅栏设置创建移动及其相应的权重。移动可以是转弯    
        or straight lines. The function then creates a random move state using the moves and weights, and a move transition     #或者直线。然后使用移动和权重创建随机移动状态和移动转换
        with the specified walk duration. Finally, it returns a tuple containing the random move state, move transition,    #并使用指定的行走持续时间。最后，它返回一个包含随机移动状态、移动转换和最终状态的元组 
        and the specified end state.    #并指定的最终状态

    """
    end_state = end_state or MovingState.halt()     #如果最终状态为空，则设置为停止状态
    conf = run_config.fence.rand_walk   #获取随机行走配置

    moves_seq = []  #移动序列
    weights = []    #权重
    if conf.use_turn:   #如果使用转弯
        for left_turn_spd, w in zip(conf.rand_turn_speeds, conf.rand_turn_speed_weights):   #遍历转弯速度和权重
            moves_seq.append((-left_turn_spd, -left_turn_spd, left_turn_spd, left_turn_spd))    #将转弯速度添加到移动序列中
            weights.append(w * conf.turn_weight)    #将权重添加到权重列表中
    if conf.use_straight:   #如果使用直线
        for straight_spd, w in zip(conf.rand_straight_speeds, conf.rand_straight_speed_weights):    #遍历直线速度和权重
            moves_seq.append((straight_spd, straight_spd, straight_spd, straight_spd))  #将直线速度添加到移动序列中
            weights.append(w * conf.straight_weight)    #将权重添加到权重列表中

    rand_move_state = MovingState.rand_move(controller, moves_seq, weights)     #创建随机移动状态
    (
        rand_move_state.after_exiting.append(sig_light_registry.register_all("Rwalk|Start rand walking", Color.WHITE))  #注册单次信号灯
        if app_config.debug.use_siglight    #如果使用信号灯
        else None
    )

    move_transition = MovingTransition(conf.walk_duration)  #创建移动转换
    return composer.init_container().add(rand_move_state).add(move_transition).add(end_state).export_structure()    #返回状态和转换


def make_std_battle_handler(    #生成标准战斗处理程序
    app_config: APPConfig,    #应用程序配置
    run_config: RunConfig,    #运行配置
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:    #返回起始状态、结束状态和转换池
    """
    Generates a standard battle handler for a given app configuration, run configuration, and optional tag group.    #为给定的应用程序配置、运行配置和可选的标签组生成标准战斗处理程序

    Args:
        app_config (APPConfig): The application configuration.  #应用程序配置
        run_config (RunConfig): The run configuration.  #运行配置

    Returns:
        Tuple[MovingState, MovingState, List[MovingTransition]]: A tuple containing the start state, end state, and transition pool.    #包含起始状态、结束状态和转换池的元组
            - start_state (MovingState): The starting state of the battle handler.          #战斗处理程序的起始状态
            - end_state (MovingState): The end state of the battle handler.     #战斗处理程序的结束状态
            - transition_pool (List[MovingTransition]): The list of transition objects for the battle handler.  #战斗处理程序的转换对象列表
    """
    end_state: MovingState = make_salvo_end_state()     #创建结束状态
    start_state = continues_state.clone()   #创建起始状态

    stage_breaker = Breakers.make_std_stage_breaker(app_config, run_config)     #创建阶段中断器

    reboot_states_pack, reboot_transitions_pack = make_reboot_handler(  #创建重启处理程序
        app_config, run_config, end_state=end_state.clone()     #将结束状态作为参数传递
    )
    [reboot_start_state, *_] = reboot_states_pack   #获取重启起始状态
    fence_start_state, _, fence_pack = make_fence_handler(app_config, run_config, stop_state=end_state.clone())     #创建栅栏处理程序
    on_stage_start_state, stage_pack = make_on_stage_handler(   #创建舞台处理程序
        app_config,     #应用程序配置
        run_config,     #运行配置
        abnormal_exit=end_state.clone(),    #将结束状态作为参数传递
    )

    unclear_zone_start_state,_,unclear_zone_pack = make_unclear_zone_handler(app_config, run_config,normal_exit=end_state.clone())  #创建不明区域处理程序

    case_reg = CaseRegistry(StageCodeSign)  #创建案例注册表
    transition_pool = [*reboot_transitions_pack, *fence_pack, *stage_pack,*unclear_zone_pack]   #将重启、栅栏、舞台和不明区域处理程序的转换添加到转换池中

    (
        case_reg.batch_register(
            [StageCodeSign.ON_STAGE_REBOOT, StageCodeSign.OFF_STAGE_REBOOT,StageCodeSign.UNCLEAR_ZONE_REBOOT],  #注册重启状态
            reboot_start_state,     #重启起始状态
        )
        .register(StageCodeSign.ON_STAGE, on_stage_start_state)     #注册舞台起始状态
        .register(StageCodeSign.OFF_STAGE, fence_start_state)   #注册栅栏起始状态
        .register(StageCodeSign.UNCLEAR_ZONE,unclear_zone_start_state)  #注册不明区域起始状态
    )

    check_trans = MovingTransition(
        run_config.perf.checking_duration, breaker=stage_breaker, to_states=case_reg.export()   #创建检查转换
    )

    _, trans = composer.init_container().add(start_state).add(check_trans).export_structure()   #将起始状态和检查转换添加到容器中，并导出结构
    transition_pool.extend(trans)   #将转换添加到转换池中
    return start_state, end_state, transition_pool  #返回起始状态、结束状态和转换池


def make_on_stage_handler(
    app_config: APPConfig,  # 应用程序配置
    run_config: RunConfig,  # 运行配置
    start_state: MovingState = None,    # 起始状态
    abnormal_exit: MovingState = None,  # 异常退出状态
) -> Tuple[MovingState, List[MovingTransition]]:    #返回起始状态和转换池
    """
    创建一个舞台处理程序，用于管理机器人的移动状态和过渡。

    Parameters:
        app_config: 应用配置对象，包含通用的应用配置信息。
        run_config: 运行配置对象，包含与运行时相关的配置信息。
        start_state: 移动状态的初始状态，默认为继续状态的克隆。
        abnormal_exit: 移动状态的异常退出状态，默认为停止状态。

    Returns:
        边缘处理状态；
        异常退出状态；
        包含所有边缘、环绕和搜索处理状态转换的列表。
    """

    conf = run_config.strategy  # 获取策略配置
    start_state = start_state or continues_state.clone()    # 如果没有提供起始状态，则使用继续状态的克隆
    abnormal_exit = abnormal_exit or MovingState.halt()     # 如果没有提供异常退出状态，则使用停止状态

    transitions = []    # 创建一个空列表来存储转换
    concat_state = start_state  # 将起始状态赋值给concat_state
    if conf.use_edge_component:        # 如果策略配置中启用了边缘组件
        _logger.info("Using edge component.")    # 打印日志信息
        edge_pack = make_edge_handler(
            app_config, run_config, start_state=concat_state, abnormal_exit=abnormal_exit.clone()   # 创建边缘处理程序
        )
        transitions.extend(edge_pack[-1])    # 将边缘处理程序的转换添加到转换列表中
        concat_state = edge_pack[1]        # 将concat_state更新为边缘处理程序的结束状态
    if conf.use_surrounding_component:  # 如果策略配置中启用了环绕组件
        _logger.info("Using surrounding component.")    # 打印日志信息
        surr_pack = make_surrounding_handler(    # 创建环绕处理程序
            app_config, run_config, start_state=concat_state, abnormal_exit=abnormal_exit.clone()   # 将起始状态和异常退出状态作为参数传递
        )
        transitions.extend(surr_pack[-1])    # 将环绕处理程序的转换添加到转换列表中
        concat_state = surr_pack[1]        # 将concat_state更新为环绕处理程序的结束状态
    if conf.use_normal_component:   # 如果策略配置中启用了普通组件
        _logger.info("Using normal component.")     # 打印日志信息
        search_pack = make_search_handler(
            app_config, run_config, start_state=concat_state, stop_state=abnormal_exit.clone()  # 创建搜索处理程序
        )
        transitions.extend(search_pack[-1])     # 将搜索处理程序的转换添加到转换列表中
    if not any(transitions):
        _logger.warning(
            f"No transition is generated for on stage handler, since the strategy config does not use any component."   # 打印警告信息
        )
    return start_state, transitions     # 返回起始状态和转换列表


def make_always_on_stage_battle_handler(
    app_config: APPConfig,
    run_config: RunConfig,
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    """
    Generates a handler for an always-on stage battle.  #生成一个始终开启的舞台战斗处理程序。

    Args:
        app_config (APPConfig): The application configuration.  #应用程序配置
        run_config (RunConfig): The run configuration.  #运行配置

    Returns:
        Tuple[MovingState, MovingState, List[MovingTransition]]: A tuple containing the start state, end state, and transition pool.    #一个包含起始状态、结束状态和转换池的元组。
    """ 
    end_state: MovingState = make_salvo_end_state()     # 创建一个停止状态
    start_state = continues_state.clone()            # 创建一个继续状态的克隆

    stage_breaker = Breakers.make_always_on_stage_breaker(app_config, run_config)    # 创建一个始终开启的舞台断路器

    on_stage_start_state, stage_pack = make_on_stage_handler(app_config, run_config, abnormal_exit=end_state)    # 创建一个舞台处理程序

    transition_pool = stage_pack    # 将舞台处理程序的转换添加到转换池中

    check_trans = MovingTransition(
        run_config.perf.checking_duration, breaker=stage_breaker, to_states=on_stage_start_state    # 创建一个检查转换
    )

    _, trans = composer.init_container().add(start_state).add(check_trans).export_structure()    # 将起始状态和检查转换添加到容器中，并导出结构
    transition_pool.extend(trans)    # 将转换添加到转换池中
    return start_state, end_state, transition_pool  # 返回起始状态、结束状态和转换池


def make_always_off_stage_battle_handler(   
    app_config: APPConfig,
    run_config: RunConfig,
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    """
    Generates a battle handler for when the stage is always off.    #生成一个舞台始终关闭时的战斗处理程序。

    Args:
        app_config (APPConfig): The application configuration.  #应用程序配置
        run_config (RunConfig): The run configuration.  #运行配置

    Returns:
        start_state (MovingState): The starting state of the battle handler.    #战斗处理程序的起始状态
        end_state (MovingState): The end state of the battle handler.    #战斗处理程序的结束状态
        transition_pool (List[MovingTransition]): The list of transition objects for the battle handler.    #战斗处理程序的转换对象列表

    """
    end_state = make_salvo_end_state()  # 创建一个停止状态
    start_state = continues_state.clone()    # 创建一个继续状态的克隆

    stage_breaker = Breakers.make_always_off_stage_breaker(app_config, run_config)  # 创建一个始终关闭的舞台断路器

    reboot_pack = make_reboot_handler(app_config, run_config, end_state=end_state)  # 创建一个重启处理程序
    fence_pack = make_fence_handler(app_config, run_config, stop_state=end_state)    # 创建一个围栏处理程序

    transition_pool = [*reboot_pack[-1], *fence_pack[-1]]    # 将重启处理程序和围栏处理程序的转换添加到转换池中

    check_trans = MovingTransition(     # 创建一个检查转换
        run_config.perf.checking_duration,  # 检查持续时间
        breaker=stage_breaker,  # 断路器
        to_states={StageCodeSign.OFF_STAGE: fence_pack[0], StageCodeSign.OFF_STAGE_REBOOT: reboot_pack[0][0]},  # 转换状态
    )

    _, trans = composer.init_container().add(start_state).add(check_trans).export_structure()    # 将起始状态和检查转换添加到容器中，并导出结构
    transition_pool.extend(trans)    # 将转换添加到转换池中
    return start_state, end_state, transition_pool  # 返回起始状态、结束状态和转换池


@lru_cache(1)
def make_salvo_end_state() -> MovingState:
    """
    创建并返回一个表示循环轮结束状态的移动状态。

    这个状态在进入时会将之前的循环轮速度重置为零，以准备下一次循环轮。

    返回:
        MovingState: 一个配置了速度重置执行器的移动状态，用于循环轮结束时的状态转换。
    """
    end_state: MovingState = MovingState.halt()
    zero_salvo_speed_updater = controller.register_context_executor(
        lambda: (0, 0, 0, 0), output_keys=[ContextVar.prev_salvo_speed.name], function_name="zero_salvo_speed_updater"
    )
    end_state.before_entering.append(zero_salvo_speed_updater)
    return end_state



def make_unclear_zone_handler(
        app_config: APPConfig,
        run_config: RunConfig,
        normal_exit:Optional[MovingState]=None
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    """
    Generate a handler for the unclear zone.    #生成一个不明区域处理程序。

    Args:
        app_config: Application configuration containing sensor information.    #应用程序配置包含传感器信息。
        run_config: Runtime configuration with operational parameters.  #运行配置包含操作参数。
        normal_exit: Optional normal exit state. Defaults to None.  #可选的正常退出状态。默认为无。

    Returns:
        A tuple containing: initial state, normal exit state, and a list of moving transitions.     #一个包含：初始状态、正常退出状态和移动转换列表的元组。
    """

    # Get stage configuration from runtime config   #从运行时配置中获取舞台配置
    conf = run_config.stage

    # Create the initial state: random direction turn   #创建初始状态：随机方向转向
    start_state = MovingState.rand_dir_turn(controller, turn_speed=conf.unclear_zone_turn_speed,
                                            turn_left_prob=conf.unclear_zone_turn_left_prob)

    # Create the normal exit state: halt movement   #创建正常退出状态：停止移动
    normal_exit = normal_exit or MovingState.halt()

    # Register context executor to update gray value    #注册上下文执行器以更新灰度值
    updater = controller.register_context_executor(
        menta.construct_inlined_function(
            usages=[SamplerUsage(used_sampler_index=SamplerIndexes.adc_all,
                                required_data_indexes=[app_config.sensor.gray_adc_index])],  # Specify ADC sample index     #指定ADC采样索引
            judging_source="ret=s0",  # Gray value stored in s0
            return_type=int,    
            function_name="get_unclear_zone_gray"   #函数名称
        ),
        output_keys=[ContextVar.unclear_zone_gray.name],
        function_name="update_unclear_zone_gray"
    )

    # Register context getter for gray value    #注册灰度值上下文获取器
    getter = controller.register_context_getter(ContextVar.unclear_zone_gray.name)

    # Construct function to judge if in unclear zone    #构建判断是否在不明区域的函数
    judge = menta.construct_inlined_function(
        usages=[SamplerUsage(used_sampler_index=SamplerIndexes.adc_all,
                            required_data_indexes=[app_config.sensor.gray_adc_index])],
        extra_context={"getter": getter},
        judging_source=f"ret=abs(s0-getter())>{conf.unclear_zone_tolerance}",  # Check if gray value difference exceeds tolerance   #检查灰度值差异是否超过容差
        return_type=bool,
        function_name="judge_unclear_zone"
    )

    # Append updater to actions after exiting initial state     #在初始状态退出后追加更新器
    start_state.after_exiting.append(updater)

    # Build state transition structure
    [_, transitions] = (composer
                        .init_container()
                        .add(start_state)
                        .add(MovingTransition(conf.unclear_zone_turn_duration, breaker=judge))  # Add transition condition  #添加转换条件
                        .add(normal_exit)
                        .export_structure())

    # Return initial state, normal exit state, and transition list  #返回初始状态、正常退出状态和转换列表
    return start_state, normal_exit, transitions
