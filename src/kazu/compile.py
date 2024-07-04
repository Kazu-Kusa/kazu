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

T = TypeVar("T")


def make_edge_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    start_state: MovingState = None,
    normal_exit: MovingState = None,
    abnormal_exit: MovingState = None,
) -> Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:
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
    start_state = start_state or continues_state.clone()
    normal_exit = normal_exit or continues_state.clone()
    abnormal_exit = abnormal_exit or MovingState.halt()

    if app_config.debug.log_level == "DEBUG":

        def _log_state():
            _logger.debug("Entering Edge State")

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

    fallback_state = MovingState.straight(-run_config.edge.fallback_speed)

    fallback_transition = MovingTransition(run_config.edge.fallback_duration, breaker=edge_rear_breaker)

    advance_state = MovingState.straight(run_config.edge.advance_speed)

    advance_transition = MovingTransition(run_config.edge.advance_duration, breaker=edge_front_breaker)

    left_turn_state = MovingState.turn("l", run_config.edge.turn_speed)

    right_turn_state = MovingState.turn("r", run_config.edge.turn_speed)

    rand_lr_turn_state = MovingState.rand_dir_turn(
        controller, run_config.edge.turn_speed, turn_left_prob=run_config.edge.turn_left_prob
    )

    half_turn_transition = MovingTransition(run_config.edge.half_turn_duration)

    full_turn_transition = MovingTransition(run_config.edge.full_turn_duration)

    drift_left_back_state = MovingState.drift("rl", run_config.edge.drift_speed)

    drift_right_back_state = MovingState.drift("rr", run_config.edge.drift_speed)

    drift_transition = MovingTransition(run_config.edge.drift_duration)
    # </editor-fold>

    # <editor-fold desc="Initialize Containers">
    transitions_pool: List[MovingTransition] = []
    (
        abnormal_exit.after_exiting.append(sig_light_registry.register_all("Edge|Abnormal Exit", Color.PURPLE))
        if app_config.debug.use_siglight
        else None
    )
    (case_reg := CaseRegistry(EdgeCodeSign)).register(EdgeCodeSign.O_O_O_O, normal_exit)
    # </editor-fold>

    # <editor-fold desc="1-Activation Cases">
    # fallback and full turn right
    [head_state, *_], transition = (
        composer.init_container()
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(right_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_O_O_O, head_state)

    # -----------------------------------------------------------------------------
    # fallback and full turn left
    [head_state, *_], transition = (
        composer.init_container()
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(left_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.O_O_O_X, head_state)

    # -----------------------------------------------------------------------------

    # advance and half turn right
    [head_state, *_], transition = (
        composer.init_container()
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(abnormal_exit)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.O_X_O_O, head_state)

    # -----------------------------------------------------------------------------

    # advance and half turn left
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
    # half turn right
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

    # half turn left
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

    # fallback and full turn left or right
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

    # advance
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

    # drift right back
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

    # drift left back
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

    # half turn left and advance
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

    # half turn right and advance
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

    # half turn right and fallback
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

    # half turn left and fallback
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
    # just stop immediately, since such case are extremely rare in the normal race
    [head_state, *_], transition = composer.init_container().add(abnormal_exit).export_structure()

    transitions_pool.extend(transition)

    case_reg.register(EdgeCodeSign.X_X_X_X, head_state)

    # </editor-fold>

    # <editor-fold desc="Assembly">
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


def make_surrounding_handler(
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
    if app_config.vision.use_camera:
        start_state.before_entering.append(tag_detector.resume_detection)
        normal_exit.before_entering.append(tag_detector.halt_detection)
        abnormal_exit.before_entering.append(tag_detector.halt_detection)

    if app_config.debug.log_level == "DEBUG":

        def _log_state():
            _logger.debug("Entering Surr State")

        start_state.after_exiting.append(_log_state)

    surr_conf = run_config.surrounding
    # <editor-fold desc="Breakers">

    surr_full_breaker = Breakers.make_surr_breaker(app_config, run_config)

    atk_breaker = (
        Breakers.make_atk_breaker_with_edge_sensors(app_config, run_config)
        if surr_conf.atk_break_use_edge_sensors
        else Breakers.make_std_atk_breaker(app_config, run_config)
    )

    edge_rear_breaker = Breakers.make_std_edge_rear_breaker(app_config, run_config)

    turn_to_front_breaker = Breakers.make_std_turn_to_front_breaker(app_config, run_config)
    # </editor-fold>

    # <editor-fold desc="Templates">

    atk_enemy_car_state = MovingState.straight(surr_conf.atk_speed_enemy_car)
    atk_enemy_box_state = MovingState.straight(surr_conf.atk_speed_enemy_box)
    atk_neutral_box_state = MovingState.straight(surr_conf.atk_speed_neutral_box)
    allay_fallback_state = MovingState.straight(-surr_conf.fallback_speed_ally_box)
    edge_fallback_state = MovingState.straight(-surr_conf.fallback_speed_edge)
    if app_config.debug.use_siglight:
        atk_enemy_car_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Attack enemy car", Color.PURPLE, Color.RED)
        )
        atk_enemy_box_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Attack enemy box", Color.PURPLE, Color.YELLOW)
        )

        atk_neutral_box_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Attack neutral box", Color.PURPLE, Color.WHITE)
        )

        allay_fallback_state.after_exiting.append(
            sig_light_registry.register_singles("Surr|Ally fallback", Color.PURPLE, Color.GREEN)
        )

        edge_fallback_state.after_exiting.append(sig_light_registry.register_all("Surr|Edge fallback", Color.CYAN))
    atk_enemy_car_transition = MovingTransition(surr_conf.atk_speed_enemy_car, breaker=atk_breaker)
    atk_enemy_box_transition = MovingTransition(surr_conf.atk_speed_enemy_box, breaker=atk_breaker)
    atk_neutral_box_transition = MovingTransition(surr_conf.atk_neutral_box_duration, breaker=atk_breaker)
    allay_fallback_transition = MovingTransition(surr_conf.fallback_duration_ally_box, breaker=edge_rear_breaker)
    edge_fallback_transition = MovingTransition(surr_conf.fallback_duration_edge, breaker=edge_rear_breaker)

    rand_turn_state = MovingState.rand_dir_turn(
        controller, surr_conf.turn_speed, turn_left_prob=surr_conf.turn_left_prob
    )
    left_turn_state = MovingState.turn("l", surr_conf.turn_speed)
    right_turn_state = MovingState.turn("r", surr_conf.turn_speed)
    rand_spd_turn_left_state = MovingState.rand_spd_turn(
        controller,
        "l",
        surr_conf.rand_turn_speeds,
        weights=surr_conf.rand_turn_speed_weights,
    )
    rand_spd_turn_right_state = MovingState.rand_spd_turn(
        controller,
        "r",
        surr_conf.rand_turn_speeds,
        weights=surr_conf.rand_turn_speed_weights,
    )

    full_turn_transition = MovingTransition(surr_conf.full_turn_duration, breaker=turn_to_front_breaker)
    half_turn_transition = MovingTransition(surr_conf.half_turn_duration, breaker=turn_to_front_breaker)
    # </editor-fold>

    # <editor-fold desc="Init Container">
    transitions_pool: List[MovingTransition] = []

    (case_reg := CaseRegistry(SurroundingCodeSign)).register(SurroundingCodeSign.NOTHING, normal_exit)
    # </editor-fold>

    # <editor-fold desc="Front enemy car">
    # ---------------------------------------------------------------------

    # atk and fallback and full random turn then stop
    [head_state, *_], transitions = (
        composer.init_container()
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
            SurroundingCodeSign.FRONT_ENEMY_CAR,
            SurroundingCodeSign.FRONT_ENEMY_CAR_RIGHT_OBJECT,
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_OBJECT,
            SurroundingCodeSign.FRONT_ENEMY_CAR_BEHIND_OBJECT,
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_RIGHT_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_CAR_RIGHT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_RIGHT_BEHIND_OBJECTS,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    # </editor-fold>

    # <editor-fold desc="Target switch">
    # ---------------------------------------------------------------------
    # full random turn atk and fallback and full random turn then stop
    [head_state, *_], transitions = (
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

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            SurroundingCodeSign.BEHIND_OBJECT,
            SurroundingCodeSign.LEFT_RIGHT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_BOX_BEHIND_OBJECT,
            SurroundingCodeSign.FRONT_ALLY_BOX_BEHIND_OBJECT,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_BEHIND_OBJECT,
            SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_RIGHT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_RIGHT_BEHIND_OBJECTS,
            SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_RIGHT_BEHIND_OBJECTS,
        ],
        head_state,
    )  # ---------------------------------------------------------------------
    # half turn left atk and fallback and full random turn then stop
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

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            SurroundingCodeSign.LEFT_OBJECT,
            SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_OBJECT,
            SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_OBJECT,
            SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_OBJECT,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    # half turn right atk and fallback and full random turn then stop
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
    # half random turn atk and fallback and full random turn then stop
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
    # random spd turn left atk and fallback and full random turn then stop
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
    # random spd turn right atk and fallback and full random turn then stop
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
    # atk and fallback and full random turn then stop
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
    # atk and fallback and full random turn then stop
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
    # fallback and full random turn then stop
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

    return start_state, normal_exit, abnormal_exit, transitions_pool
    # </editor-fold>


def make_scan_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    end_state: MovingState = None,
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a scan handler for the given application configuration, run configuration, and optional end state.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.
        end_state (MovingState, optional): The optional end state. Defaults to MovingState(0).

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.
    """
    end_state = end_state or MovingState.halt()

    scan_breaker = Breakers.make_std_scan_breaker(app_config, run_config)
    rear_edge_breaker = Breakers.make_std_edge_rear_breaker(app_config, run_config)
    turn_to_front_breaker = Breakers.make_std_turn_to_front_breaker(app_config, run_config)
    conf = run_config.search.scan_move
    case_reg = CaseRegistry(to_cover=ScanCodesign)

    scan_state = MovingState.rand_dir_turn(controller, conf.scan_speed, conf.scan_turn_left_prob)
    (
        scan_state.after_exiting.append(
            sig_light_registry.register_singles("Scan|Start Scanning", Color.RED, Color.GREEN)
        )
        if app_config.debug.use_siglight
        else None
    )
    scan_state.before_entering.append(
        controller.register_context_executor(
            sensors.adc_all_channels, output_keys=ContextVar.recorded_pack.name, function_name="update_recorded_pack"
        )
    )
    if app_config.debug.log_level == "DEBUG":

        def _log_state():
            _logger.debug("Entering Scan State")

        scan_state.after_exiting.append(_log_state)

    rand_turn_state = MovingState.rand_dir_turn(controller, conf.turn_speed, conf.turn_left_prob)

    turn_left_state = MovingState.turn("l", conf.turn_speed)
    turn_right_state = MovingState.turn("r", conf.turn_speed)

    full_turn_transition = MovingTransition(run_config.surrounding.full_turn_duration, breaker=turn_to_front_breaker)
    half_turn_transition = MovingTransition(run_config.surrounding.half_turn_duration, breaker=turn_to_front_breaker)

    fall_back_state = MovingState.straight(-conf.fall_back_speed)
    fall_back_transition = MovingTransition(conf.fall_back_duration, breaker=rear_edge_breaker)

    (
        end_state.after_exiting.append(sig_light_registry.register_all("Scan|End Scanning", Color.RED))
        if app_config.debug.use_siglight
        else None
    )
    transitions_pool: List[MovingTransition] = []
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().add(end_state).export_structure()

    transitions_pool.extend(transitions)
    case_reg.register(ScanCodesign.O_O_O_O, head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(fall_back_state.clone())
        .add(fall_back_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register([ScanCodesign.X_O_O_O, ScanCodesign.X_O_X_X], head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(rand_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
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
    [head_state, *_], transitions = (
        composer.init_container()
        .add(turn_left_state.clone())
        .add(half_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            ScanCodesign.O_O_X_O,
            ScanCodesign.X_O_X_O,
        ],
        head_state,
    )

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(turn_right_state.clone())
        .add(half_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            ScanCodesign.O_O_O_X,
            ScanCodesign.X_O_O_X,
        ],
        head_state,
    )

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(fall_back_state.clone())
        .add(fall_back_transition.clone())
        .add(rand_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(end_state)
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.register(ScanCodesign.O_O_X_X, head_state)
    # ---------------------------------------------------------------------

    states, transitions = (
        composer.init_container()
        .add(scan_state)
        .add(MovingTransition(conf.scan_duration, breaker=scan_breaker, to_states=case_reg.export()))
        .export_structure()
    )

    transitions_pool.extend(transitions)
    return states, transitions_pool


def make_rand_turn_handler(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a handler for a random turn action.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.
        end_state (MovingState, optional): The state to transition to after the random turn. Defaults to MovingState.halt().

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.
    """

    end_state = end_state or MovingState.halt()

    conf = run_config.search.rand_turn

    rand_lr_turn_state = MovingState.rand_dir_turn(controller, conf.turn_speed, turn_left_prob=conf.turn_left_prob)
    (
        rand_lr_turn_state.after_exiting.append(sig_light_registry.register_all("Rturn|Start Rturn", Color.YELLOW))
        if app_config.debug.use_siglight
        else None
    )
    half_turn_transition = MovingTransition(conf.half_turn_duration)

    states, transitions = composer.add(rand_lr_turn_state).add(half_turn_transition).add(end_state).export_structure()
    return states, transitions


def make_gradient_move(app_config: APPConfig, run_config: RunConfig, is_salvo_end: bool = True) -> MovingState:
    """
    Generates a MovingState object for a gradient move in a search algorithm.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.
        is_salvo_end (bool, optional): Indicates if this is the last gradient move in a salvo. Defaults to True.

    Returns:
        MovingState: The MovingState object representing the gradient move.

    """
    conf = run_config.search.gradient_move

    speed_range = conf.max_speed - conf.min_speed

    speed_calc_func = menta.construct_inlined_function(
        usages=[
            SamplerUsage(
                used_sampler_index=SamplerIndexes.adc_all, required_data_indexes=[app_config.sensor.gray_adc_index]
            )
        ],
        judging_source=f"ret={conf.min_speed}+int({speed_range}*(s0-{conf.min_speed})/({conf.max_speed}-{conf.min_speed}))",
        return_type=int,
        return_raw=False,
        function_name="calc_gradient_speed",
    )
    updaters = []
    speed_updater = controller.register_context_executor(
        speed_calc_func, [ContextVar.gradient_speed.name], function_name="_update_gradient_speed"
    )
    updaters.append(speed_updater)
    if is_salvo_end:
        getter: Callable[[], int] = controller.register_context_getter(ContextVar.gradient_speed.name)

        def _update_salvo_end_speed() -> Tuple[int, int, int, int]:
            speed = getter()
            return speed, speed, speed, speed

        salvo_end_speed_updater = controller.register_context_executor(
            _update_salvo_end_speed, [ContextVar.prev_salvo_speed.name], function_name="_update_salvo_end_speed"
        )
        updaters.append(salvo_end_speed_updater)

    return MovingState(
        speed_expressions=ContextVar.gradient_speed.name,
        used_context_variables=[ContextVar.gradient_speed.name],
        before_entering=updaters,
        after_exiting=(
            [sig_light_registry.register_all("GMove|Start gradient move", Color.BLUE)]
            if app_config.debug.use_siglight
            else []
        ),
    )


def make_search_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    start_state: MovingState = None,
    stop_state: MovingState = None,
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a search handler for the given application configuration, run configuration, and optional start and stop states.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.
        start_state (MovingState, optional): The optional start state. Defaults to None.
        stop_state (MovingState, optional): The stop state. Defaults to MovingState.halt().

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.
    """
    start_state = start_state or continues_state.clone()
    stop_state = stop_state or MovingState.halt()
    scan_states, scan_transitions = make_scan_handler(app_config, run_config, end_state=stop_state)
    rand_turn_states, rand_turn_transitions = make_rand_turn_handler(app_config, run_config, end_state=stop_state)
    grad_move_state = make_gradient_move(app_config, run_config, is_salvo_end=True)

    pool = []
    w = []
    if run_config.search.use_gradient_move:
        pool.append(SearchCodesign.GRADIENT_MOVE)
        w.append(run_config.search.gradient_move_weight)
    if run_config.search.use_rand_turn:
        pool.append(SearchCodesign.RAND_TURN)
        w.append(run_config.search.rand_turn_weight)
    if run_config.search.use_scan_move:
        pool.append(SearchCodesign.SCAN_MOVE)
        w.append(run_config.search.scan_move_weight)

    w_selector = make_weighted_selector(pool, w)
    case_reg = CaseRegistry(SearchCodesign)

    case_reg.register(SearchCodesign.GRADIENT_MOVE, grad_move_state)
    case_reg.register(SearchCodesign.RAND_TURN, rand_turn_states[0])
    case_reg.register(SearchCodesign.SCAN_MOVE, scan_states[0])

    trans = MovingTransition(0, breaker=w_selector, to_states=case_reg.export())
    states, transitions = composer.init_container().add(start_state).add(trans).export_structure()

    states_pool = [*states, *scan_states, *rand_turn_states, grad_move_state]
    transitions_pool = [*transitions, *scan_transitions, *rand_turn_transitions]
    return states_pool, transitions_pool


def make_fence_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    start_state: MovingState = None,
    stop_state: MovingState = None,
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    """
    Generates a fence handler for a given app configuration, run configuration, and optional start state.

    Args:
        app_config (APPConfig): The app configuration.
        run_config (RunConfig): The run configuration.
        start_state (MovingState, optional): The optional start state. Defaults to None.
        stop_state (MovingState, optional): The stop state. Defaults to MovingState.halt().

    Returns:
        Tuple[MovingState, MovingState, List[MovingTransition]]: A tuple containing the start state, stop state, and list of transitions.
    """

    start_state = start_state or continues_state.clone()
    stop_state = stop_state or MovingState.halt()
    if app_config.debug.log_level == "DEBUG":

        def _log_state():
            _logger.debug("Entering Fence State")

        start_state.after_exiting.append(_log_state)
    fence_breaker = Breakers.make_std_fence_breaker(app_config, run_config)

    align_stage_breaker = (
        Breakers.make_stage_align_breaker_mpu(app_config, run_config)
        if run_config.fence.use_mpu_align
        else Breakers.make_std_stage_align_breaker(app_config, run_config)
    )

    back_stage_pack = make_back_to_stage_handler(app_config, run_config, stop_state)
    rand_move_pack = make_rand_walk_handler(app_config, run_config, stop_state)

    rand_move_head_state = rand_move_pack[0][0]
    align_direction_pack = make_align_direction_handler(app_config, run_config, rand_move_head_state, stop_state)

    conf = run_config.fence

    rear_exit_corner_state = MovingState.straight(-conf.exit_corner_speed)
    front_exit_corner_state = MovingState.straight(conf.exit_corner_speed)

    exit_duration = MovingTransition(conf.max_exit_corner_duration)

    match conf.stage_align_direction:
        case "rand":
            align_state = MovingState.rand_dir_turn(controller, conf.stage_align_speed)
        case "l":
            align_state = MovingState.turn("l", conf.stage_align_speed)
        case "r":
            align_state = MovingState.turn("r", conf.stage_align_speed)
        case _:
            raise ValueError(f"Invalid align direction: {conf.stage_align_direction}")

    align_stage_transition = MovingTransition(
        conf.max_stage_align_duration, breaker=align_stage_breaker, to_states={False: rand_move_head_state}
    )

    transitions_pool: List[MovingTransition] = []

    case_reg = CaseRegistry(FenceCodeSign)

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().concat(*back_stage_pack).export_structure()
    transitions_pool.extend(transitions)
    case_reg.register(FenceCodeSign.X_O_O_O, head_state)

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(align_state.clone())
        .add(align_stage_transition.clone())
        .concat(*back_stage_pack, register_case=True)  # back to stage only when the check is passed
        .export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [
            FenceCodeSign.O_X_O_O,
            FenceCodeSign.O_O_X_O,
            FenceCodeSign.O_O_O_X,
            FenceCodeSign.O_O_X_X,
            FenceCodeSign.X_X_O_O,
        ],
        head_state,
    )
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(front_exit_corner_state.clone())
        .add(exit_duration.clone())
        .add(stop_state)
        .export_structure()
    )
    transitions_pool.extend(transitions)
    case_reg.batch_register([FenceCodeSign.O_X_O_X, FenceCodeSign.O_X_X_O], head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(rear_exit_corner_state.clone())
        .add(exit_duration.clone())
        .add(stop_state)
        .export_structure()
    )
    transitions_pool.extend(transitions)
    case_reg.batch_register([FenceCodeSign.X_O_O_X, FenceCodeSign.X_O_X_O], head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().concat(*align_direction_pack).export_structure()
    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [FenceCodeSign.O_X_X_X, FenceCodeSign.X_O_X_X, FenceCodeSign.X_X_O_X, FenceCodeSign.X_X_X_O], head_state
    )
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().concat(*rand_move_pack).export_structure()
    transitions_pool.extend(transitions)
    case_reg.batch_register([FenceCodeSign.O_O_O_O, FenceCodeSign.X_X_X_X], head_state)
    # ---------------------------------------------------------------------

    (
        start_state.after_exiting.append(sig_light_registry.register_all("Fence|Starting Fence finding", Color.ORANGE))
        if app_config.debug.use_siglight
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

    return start_state, stop_state, list(set(transitions_pool))
    # </editor-fold>


def make_align_direction_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    not_aligned_state: Optional[MovingState] = None,
    aligned_state: Optional[MovingState] = None,
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Constructs a state machine handler for aligning the direction.

    Parameters:
        app_config (APPConfig): The configuration object for the application.
        run_config (RunConfig): The runtime configuration object.
        not_aligned_state (MovingState): The state to transition to when not aligned. Defaults to MovingState.halt().
        aligned_state (MovingState, optional): The state to transition to when aligned. Defaults to None.

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and transitions.

    Raises:
        ValueError: If the align direction is invalid.
    """

    conf = run_config.fence

    match conf.direction_align_direction:
        case "rand":
            align_state = MovingState.rand_dir_turn(controller, conf.direction_align_speed)
        case "l":
            align_state = MovingState.turn("l", conf.direction_align_speed)
        case "r":
            align_state = MovingState.turn("r", conf.direction_align_speed)
        case _:
            raise ValueError(f"Invalid align direction: {conf.direction_align_direction}")
    align_direction_breaker = Breakers.make_align_direction_breaker(app_config, run_config)
    if aligned_state and not_aligned_state:
        branch = {True: aligned_state, False: not_aligned_state}
    elif aligned_state:
        branch = {True: aligned_state}
    elif not_aligned_state:
        branch = {False: not_aligned_state}
    else:
        branch = {}
    align_direction_transition = MovingTransition(
        conf.max_direction_align_duration,
        breaker=align_direction_breaker,
        to_states=branch,
    )

    composer.init_container().add(align_state).add(align_direction_transition)
    return composer.export_structure()


def make_back_to_stage_handler(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None, **_
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Creates a state machine handler for moving back to the stage.

    Args:
        app_config (APPConfig): The configuration object for the application.
        run_config (RunConfig): Runtime configuration object with parameters for movement actions.
        end_state (MovingState, optional): The final state of the state machine. Defaults to MovingState.halt().

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing lists of states and transitions.
    """

    end_state = end_state or MovingState.halt()
    small_advance = MovingState(run_config.backstage.small_advance_speed)
    small_advance_transition = MovingTransition(run_config.backstage.small_advance_duration)
    stab_trans = MovingTransition(run_config.backstage.time_to_stabilize)
    # waiting for a booting signal, and dash on to the stage once received
    (
        small_advance.after_exiting.append(sig_light_registry.register_all("BStage|Small move", Color.GREEN))
        if app_config.debug.use_siglight
        else None
    )
    states, transitions = (
        composer.init_container()
        .add(small_advance)
        .add(small_advance_transition)
        .add(MovingState.halt())
        .add(stab_trans.clone())
        .add(MovingState.straight(-run_config.boot.dash_speed))
        .add(MovingTransition(run_config.boot.dash_duration))
        .add(MovingState.halt())
        .add(stab_trans.clone())
        .add(
            MovingState.rand_dir_turn(
                controller, run_config.boot.turn_speed, turn_left_prob=run_config.boot.turn_left_prob
            )
        )
        .add(MovingTransition(run_config.backstage.full_turn_duration))
        .add(end_state)
        .export_structure()
    )

    return states, transitions


def make_reboot_handler(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Constructs a state machine handler for reboot sequences.

    Parameters:
        app_config: APPConfig, configuration object for application specifics including sensor details.
        run_config: RunConfig, runtime configuration object with parameters for bootup and movement actions.
        end_state: MovingState, the final state of the state machine, defaults to MovingState(0).

    Returns:
        Tuple[List[MovingState], List[MovingTransition]], a tuple containing lists of states and transitions.
    """
    end_state = end_state or MovingState.halt()

    activation_breaker = menta.construct_inlined_function(
        usages=[
            SamplerUsage(
                used_sampler_index=SamplerIndexes.adc_all,
                required_data_indexes=[app_config.sensor.left_adc_index, app_config.sensor.right_adc_index],
            )
        ],
        judging_source=f"ret=s0>{run_config.boot.left_threshold} and s1>{run_config.boot.right_threshold}",
        return_type=bool,
        return_raw=False,
        function_name="reboot_breaker",
    )

    holding_transition = MovingTransition(run_config.boot.max_holding_duration, breaker=activation_breaker)
    # waiting for a booting signal, and dash on to the stage once received
    states, transitions = (
        composer.init_container()
        .add(
            MovingState(
                0,
                before_entering=(
                    [sig_light_registry.register_singles("Reboot|Start rebooting", Color.G_RED, Color.R_GREEN)]
                    if app_config.debug.use_siglight
                    else []
                ),
            )
        )
        .add(holding_transition)
        .add(
            MovingState(
                -run_config.boot.dash_speed,
                after_exiting=(
                    [sig_light_registry.register_singles("Reboot|In rebooting", Color.DARKBLUE, Color.DARKGREEN)]
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
                controller, run_config.boot.turn_speed, turn_left_prob=run_config.boot.turn_left_prob
            )
        )
        .add(MovingTransition(run_config.boot.full_turn_duration))
        .add(end_state)
        .export_structure()
    )

    return states, transitions


def make_rand_walk_handler(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = None, **_
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a random walk handler for the given run configuration and end state.

    Args:
        app_config (APPConfig): The application configuration containing the sensor details.
        run_config (RunConfig): The run configuration containing the fence settings.
        end_state (MovingState, optional): The end state to transition to after the random walk. Defaults to MovingState.halt().
        **_: Additional keyword arguments.

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.

    Raises:
        None

    Description:
        This function generates a random walk handler based on the given run configuration. It creates a list of moves
        and their corresponding weights based on the fence settings in the run configuration. The moves can be either turns
        or straight lines. The function then creates a random move state using the moves and weights, and a move transition
        with the specified walk duration. Finally, it returns a tuple containing the random move state, move transition,
        and the specified end state.

    """
    end_state = end_state or MovingState.halt()
    conf = run_config.fence.rand_walk

    moves_seq = []
    weights = []
    if conf.use_turn:
        for left_turn_spd, w in zip(conf.rand_turn_speeds, conf.rand_turn_speed_weights):
            moves_seq.append((-left_turn_spd, -left_turn_spd, left_turn_spd, left_turn_spd))
            weights.append(w * conf.turn_weight)
    if conf.use_straight:
        for straight_spd, w in zip(conf.rand_straight_speeds, conf.rand_straight_speed_weights):
            moves_seq.append((straight_spd, straight_spd, straight_spd, straight_spd))
            weights.append(w * conf.straight_weight)

    rand_move_state = MovingState.rand_move(controller, moves_seq, weights)
    (
        rand_move_state.after_exiting.append(sig_light_registry.register_all("Rwalk|Start rand walking", Color.WHITE))
        if app_config.debug.use_siglight
        else None
    )

    move_transition = MovingTransition(conf.walk_duration)
    return composer.init_container().add(rand_move_state).add(move_transition).add(end_state).export_structure()


def make_std_battle_handler(
    app_config: APPConfig,
    run_config: RunConfig,
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    """
    Generates a standard battle handler for a given app configuration, run configuration, and optional tag group.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.

    Returns:
        Tuple[MovingState, MovingState, List[MovingTransition]]: A tuple containing the start state, end state, and transition pool.
            - start_state (MovingState): The starting state of the battle handler.
            - end_state (MovingState): The end state of the battle handler.
            - transition_pool (List[MovingTransition]): The list of transition objects for the battle handler.
    """
    end_state: MovingState = make_salvo_end_state()
    start_state = continues_state.clone()

    stage_breaker = Breakers.make_std_stage_breaker(app_config, run_config)

    reboot_states_pack, reboot_transitions_pack = make_reboot_handler(
        app_config, run_config, end_state=end_state.clone()
    )
    [reboot_start_state, *_] = reboot_states_pack
    fence_start_state, _, fence_pack = make_fence_handler(app_config, run_config, stop_state=end_state.clone())
    on_stage_start_state, stage_pack = make_on_stage_handler(
        app_config,
        run_config,
        abnormal_exit=end_state.clone(),
    )

    case_reg = CaseRegistry(StageCodeSign)
    transition_pool = [*reboot_transitions_pack, *fence_pack, *stage_pack]

    (
        case_reg.batch_register(
            [StageCodeSign.ON_STAGE_REBOOT, StageCodeSign.OFF_STAGE_REBOOT],
            reboot_start_state,
        )
        .register(StageCodeSign.ON_STAGE, on_stage_start_state)
        .register(StageCodeSign.OFF_STAGE, fence_start_state)
    )

    check_trans = MovingTransition(
        run_config.perf.checking_duration, breaker=stage_breaker, to_states=case_reg.export()
    )

    _, trans = composer.init_container().add(start_state).add(check_trans).export_structure()
    transition_pool.extend(trans)
    return start_state, end_state, transition_pool


def make_on_stage_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    start_state: MovingState = None,
    abnormal_exit: MovingState = None,
) -> Tuple[MovingState, List[MovingTransition]]:
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

    conf = run_config.strategy
    start_state = start_state or continues_state.clone()
    abnormal_exit = abnormal_exit or MovingState.halt()

    transitions = []
    concat_state = start_state
    if conf.use_edge_component:
        edge_pack = make_edge_handler(
            app_config, run_config, start_state=concat_state, abnormal_exit=abnormal_exit.clone()
        )
        transitions.extend(edge_pack[-1])
        concat_state = edge_pack[1]
    if conf.use_surrounding_component:
        surr_pack = make_surrounding_handler(
            app_config, run_config, start_state=concat_state, abnormal_exit=abnormal_exit.clone()
        )
        transitions.extend(surr_pack[-1])
        concat_state = surr_pack[1]
    if conf.use_normal_component:
        search_pack = make_search_handler(
            app_config, run_config, start_state=concat_state, stop_state=abnormal_exit.clone()
        )
        transitions.extend(search_pack[-1])
    if not any(transitions):
        _logger.warning(
            f"No transition is generated for on stage handler, since the strategy config does not use any component."
        )
    return start_state, transitions


def make_always_on_stage_battle_handler(
    app_config: APPConfig,
    run_config: RunConfig,
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    """
    Generates a handler for an always-on stage battle.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.

    Returns:
        Tuple[MovingState, MovingState, List[MovingTransition]]: A tuple containing the start state, end state, and transition pool.
    """
    end_state: MovingState = make_salvo_end_state()
    start_state = continues_state.clone()

    stage_breaker = Breakers.make_always_on_stage_breaker(app_config, run_config)

    on_stage_start_state, stage_pack = make_on_stage_handler(app_config, run_config, abnormal_exit=end_state)

    transition_pool = stage_pack

    check_trans = MovingTransition(
        run_config.perf.checking_duration, breaker=stage_breaker, to_states=on_stage_start_state
    )

    _, trans = composer.init_container().add(start_state).add(check_trans).export_structure()
    transition_pool.extend(trans)
    return start_state, end_state, transition_pool


def make_always_off_stage_battle_handler(
    app_config: APPConfig,
    run_config: RunConfig,
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    """
    Generates a battle handler for when the stage is always off.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.

    Returns:
        start_state (MovingState): The starting state of the battle handler.
        end_state (MovingState): The end state of the battle handler.
        transition_pool (List[MovingTransition]): The list of transition objects for the battle handler.

    """
    end_state = make_salvo_end_state()
    start_state = continues_state.clone()

    stage_breaker = Breakers.make_always_off_stage_breaker(app_config, run_config)

    reboot_pack = make_reboot_handler(app_config, run_config, end_state=end_state)
    fence_pack = make_fence_handler(app_config, run_config, stop_state=end_state)

    transition_pool = [*reboot_pack[-1], *fence_pack[-1]]

    check_trans = MovingTransition(
        run_config.perf.checking_duration,
        breaker=stage_breaker,
        to_states={StageCodeSign.OFF_STAGE: fence_pack[0], StageCodeSign.OFF_STAGE_REBOOT: reboot_pack[0][0]},
    )

    _, trans = composer.init_container().add(start_state).add(check_trans).export_structure()
    transition_pool.extend(trans)
    return start_state, end_state, transition_pool


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
