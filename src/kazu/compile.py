from enum import Enum
from typing import Callable, List, Tuple, Dict, Optional, Iterable, TypeVar, Type

from mentabotix import (
    MovingChainComposer,
    CaseRegistry,
    Botix,
    MovingState,
    MovingTransition,
    SamplerUsage,
    make_weighted_selector,
)

from kazu.config import APPConfig, RunConfig, ContextVar, TagGroup
from kazu.constant import (
    EdgeCodeSign,
    SurroundingWeights,
    SurroundingCodeSign,
    FenceCodeSign,
    ScanCodesign,
    SearchCodesign,
    StageCodeSign,
)
from kazu.hardwares import controller, tag_detector, menta, SamplerIndexes
from kazu.judgers import Breakers
from kazu.static import continues_state

botix = Botix(controller=controller)

composer = MovingChainComposer()

T = TypeVar("T")


def check_all_case_defined(branch_dict: Dict[T, MovingState], case_list: Iterable[T] | Type[Enum]) -> None:
    """
    Check if all cases in the `case_list` are defined in the `branch_dict`.

    Args:
        branch_dict (Dict[T, MovingState]): A dictionary mapping cases to their corresponding MovingState.
        case_list (Iterable[T] | Type[Enum]): An iterable of cases or an Enum class.

    Raises:
        ValueError: If any case in the `case_list` is not defined in the `branch_dict`.

    Returns:
        None
    """
    if issubclass(case_list, Enum):
        undefined_cases = list(filter(lambda x: x.value not in branch_dict, case_list))
    else:
        undefined_cases = list(filter(lambda x: x not in branch_dict, case_list))
    if undefined_cases:
        raise ValueError(f"Case not defined: {undefined_cases}")


def make_edge_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    start_state: Optional[MovingState] = None,
    normal_exit: Optional[MovingState] = None,
    abnormal_exit: Optional[MovingState] = MovingState.halt(),
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
    start_state = start_state or continues_state.clone()
    normal_exit = normal_exit or continues_state.clone()

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
    case_dict: Dict = {EdgeCodeSign.O_O_O_O.value: normal_exit}
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

    case_dict[EdgeCodeSign.X_O_O_O.value] = head_state

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

    case_dict[EdgeCodeSign.O_O_O_X.value] = head_state

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

    case_dict[EdgeCodeSign.O_X_O_O.value] = head_state

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

    case_dict[EdgeCodeSign.O_O_X_O.value] = head_state

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

    case_dict[EdgeCodeSign.X_X_O_O.value] = head_state

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

    case_dict[EdgeCodeSign.O_O_X_X.value] = head_state

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

    case_dict[EdgeCodeSign.X_O_O_X.value] = head_state

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

    case_dict[EdgeCodeSign.O_X_X_O.value] = head_state

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

    case_dict[EdgeCodeSign.X_O_X_O.value] = head_state

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

    case_dict[EdgeCodeSign.O_X_O_X.value] = head_state

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

    case_dict[EdgeCodeSign.O_X_X_X.value] = head_state

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

    case_dict[EdgeCodeSign.X_X_X_O.value] = head_state

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

    case_dict[EdgeCodeSign.X_O_X_X.value] = head_state

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

    case_dict[EdgeCodeSign.X_X_O_X.value] = head_state

    # </editor-fold>

    # <editor-fold desc="4-Activation Cases">
    # just stop immediately, since such case are extremely rare in the normal race
    [head_state, *_], transition = composer.init_container().add(abnormal_exit).export_structure()

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_X_X_X.value] = head_state

    # </editor-fold>

    # <editor-fold desc="Assembly">
    _, head_trans = (
        composer.init_container()
        .add(start_state)
        .add(MovingTransition(run_config.perf.min_sync_interval, breaker=edge_full_breaker, to_states=case_dict))
        .export_structure()
    )

    transitions_pool.extend(head_trans)

    botix.export_structure("strac.puml", transitions_pool)

    # </editor-fold>

    check_all_case_defined(branch_dict=case_dict, case_list=EdgeCodeSign)
    return start_state, normal_exit, abnormal_exit, transitions_pool


def make_surrounding_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    tag_group: Optional[TagGroup] = None,
    start_state: Optional[MovingState] = None,
    normal_exit: Optional[MovingState] = None,
    abnormal_exit: Optional[MovingState] = MovingState.halt(),
) -> Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:
    """
    构造一个处理周围环境信息的策略处理器。

    Args:
        app_config: APPConfig, 应用配置对象，包含传感器和行为配置。
        run_config: RunConfig, 运行时配置对象，包含执行环境和策略细节。
        tag_group: TagGroup, 标签组对象，用于识别不同物体标签，默认为None。
        start_state: MovingState, 开始状态，默认为None。
        normal_exit: MovingState, 正常退出状态，默认为None。
        abnormal_exit: MovingState, 异常退出状态，默认为None。

    Returns:
        Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:
      一个四元组，包含开始状态、正常退出状态、异常退出状态和一系列可能的状态转换。
    """

    # <editor-fold desc="Breakers">
    if app_config.vision.use_camera:

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

        surr_full_breaker = menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        app_config.sensor.fl_io_index,  # s0
                        app_config.sensor.fr_io_index,  # s1
                        app_config.sensor.rl_io_index,  # s2
                        app_config.sensor.rr_io_index,  # s3
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.front_adc_index,  # s4
                        app_config.sensor.left_adc_index,  # s5
                        app_config.sensor.right_adc_index,  # s6
                        app_config.sensor.rb_adc_index,  # s7
                    ],
                ),
            ],
            judging_source=(
                f"ret=q_tb.get((tag_d.tag_id, bool(s0 or s1 or s4>{run_config.surrounding.front_adc_lower_threshold})))"
                f"+(s5>{run_config.surrounding.left_adc_lower_threshold})*{SurroundingWeights.LEFT_OBJECT}"
                f"+(s6>{run_config.surrounding.right_adc_lower_threshold})*{SurroundingWeights.RIGHT_OBJECT}"
                f"+s2 or s3 or s7>{run_config.surrounding.right_adc_lower_threshold}*{SurroundingWeights.BEHIND_OBJECT}"
            ),
            return_type_varname="int",
            extra_context={"int": int, "tag_d": tag_detector, "q_tb": query_table},
            return_raw=False,
        )

    else:
        raise NotImplementedError

    atk_breaker = Breakers.make_std_atk_breaker(app_config, run_config)

    edge_rear_breaker = Breakers.make_std_edge_rear_breaker(app_config, run_config)

    turn_to_front_breaker = Breakers.make_std_turn_to_front_breaker(app_config, run_config)
    # </editor-fold>

    # <editor-fold desc="Templates">
    start_state = start_state or continues_state.clone()
    normal_exit = normal_exit or continues_state.clone()

    atk_enemy_car_state = MovingState.straight(run_config.surrounding.atk_speed_enemy_car)
    atk_enemy_box_state = MovingState.straight(run_config.surrounding.atk_speed_enemy_box)
    atk_neutral_box_state = MovingState.straight(run_config.surrounding.atk_speed_neutral_box)
    allay_fallback_state = MovingState.straight(-run_config.surrounding.fallback_speed_ally_box)
    edge_fallback_state = MovingState.straight(-run_config.surrounding.fallback_speed_edge)

    atk_enemy_car_transition = MovingTransition(run_config.surrounding.atk_speed_enemy_car, breaker=atk_breaker)
    atk_enemy_box_transition = MovingTransition(run_config.surrounding.atk_speed_enemy_box, breaker=atk_breaker)
    atk_neutral_box_transition = MovingTransition(run_config.surrounding.atk_neutral_box_duration, breaker=atk_breaker)
    allay_fallback_transition = MovingTransition(
        run_config.surrounding.fallback_duration_ally_box, breaker=edge_rear_breaker
    )
    edge_fallback_transition = MovingTransition(
        run_config.surrounding.fallback_duration_edge, breaker=edge_rear_breaker
    )

    rand_turn_state = MovingState.rand_dir_turn(
        controller, run_config.surrounding.turn_speed, turn_left_prob=run_config.surrounding.turn_left_prob
    )
    left_turn_state = MovingState.turn("l", run_config.surrounding.turn_speed)
    right_turn_state = MovingState.turn("r", run_config.surrounding.turn_speed)
    rand_spd_turn_left_state = MovingState.rand_spd_turn(
        controller,
        "l",
        run_config.surrounding.rand_turn_speeds,
        weights=run_config.surrounding.rand_turn_speed_weights,
    )
    rand_spd_turn_right_state = MovingState.rand_spd_turn(
        controller,
        "r",
        run_config.surrounding.rand_turn_speeds,
        weights=run_config.surrounding.rand_turn_speed_weights,
    )

    full_turn_transition = MovingTransition(run_config.surrounding.full_turn_duration, breaker=turn_to_front_breaker)
    half_turn_transition = MovingTransition(run_config.surrounding.half_turn_duration, breaker=turn_to_front_breaker)
    # </editor-fold>

    # <editor-fold desc="Init Container">
    transitions_pool: List[MovingTransition] = []

    case_dict: Dict[int, MovingState] = {SurroundingCodeSign.NOTHING.value: normal_exit}
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
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR_RIGHT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR_BEHIND_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_RIGHT_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR_RIGHT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_CAR_LEFT_RIGHT_BEHIND_OBJECTS.value] = head_state
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
    case_dict[SurroundingCodeSign.BEHIND_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.LEFT_RIGHT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX_BEHIND_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX_BEHIND_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX_BEHIND_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_RIGHT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_RIGHT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_RIGHT_BEHIND_OBJECTS.value] = head_state
    # ---------------------------------------------------------------------
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
    case_dict[SurroundingCodeSign.LEFT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_OBJECT.value] = head_state
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
    case_dict[SurroundingCodeSign.RIGHT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX_RIGHT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX_RIGHT_OBJECT.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX_RIGHT_OBJECT.value] = head_state
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
    case_dict[SurroundingCodeSign.LEFT_RIGHT_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_RIGHT_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_RIGHT_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_RIGHT_OBJECTS.value] = head_state

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
    case_dict[SurroundingCodeSign.LEFT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX_LEFT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX_LEFT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX_LEFT_BEHIND_OBJECTS.value] = head_state
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
    case_dict[SurroundingCodeSign.RIGHT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX_RIGHT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX_RIGHT_BEHIND_OBJECTS.value] = head_state
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX_RIGHT_BEHIND_OBJECTS.value] = head_state
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
    case_dict[SurroundingCodeSign.FRONT_ENEMY_BOX.value] = head_state
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
    case_dict[SurroundingCodeSign.FRONT_NEUTRAL_BOX.value] = head_state
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
    case_dict[SurroundingCodeSign.FRONT_ALLY_BOX.value] = head_state
    # ---------------------------------------------------------------------
    # </editor-fold>

    # <editor-fold desc="Assembly">
    _, head_trans = (
        composer.init_container()
        .add(start_state)
        .add(MovingTransition(run_config.perf.min_sync_interval, breaker=surr_full_breaker, to_states=case_dict))
        .export_structure()
    )
    # </editor-fold>

    # <editor-fold desc="Make Return">
    transitions_pool.extend(head_trans)

    check_all_case_defined(case_dict, SurroundingCodeSign)
    return start_state, normal_exit, abnormal_exit, transitions_pool
    # </editor-fold>


def make_scan_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    end_state: Optional[MovingState] = MovingState.halt(),
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Generates a scan handler for the given application configuration, run configuration, and optional end state.

    Args:
        app_config (APPConfig): The application configuration.
        run_config (RunConfig): The run configuration.
        end_state (Optional[MovingState], optional): The optional end state. Defaults to MovingState(0).

    Returns:
        Tuple[List[MovingState], List[MovingTransition]]: A tuple containing the list of states and the list of transitions.
    """
    scan_breaker = Breakers.make_std_scan_breaker(app_config, run_config)
    rear_edge_breaker = Breakers.make_std_edge_rear_breaker(app_config, run_config)
    turn_to_front_breaker = Breakers.make_std_turn_to_front_breaker(app_config, run_config)
    conf = run_config.search.scan_move
    case_reg = CaseRegistry(to_cover=ScanCodesign)

    scan_state = MovingState.rand_dir_turn(controller, conf.scan_speed, conf.scan_turn_left_prob)

    rand_turn_state = MovingState.rand_dir_turn(controller, conf.turn_speed, conf.turn_left_prob)

    turn_left_state = MovingState.turn("l", conf.turn_speed)
    turn_right_state = MovingState.turn("r", conf.turn_speed)

    full_turn_transition = MovingTransition(run_config.surrounding.full_turn_duration, breaker=turn_to_front_breaker)
    half_turn_transition = MovingTransition(run_config.surrounding.half_turn_duration, breaker=turn_to_front_breaker)

    fall_back_state = MovingState.straight(-conf.fall_back_speed)
    fall_back_transition = MovingTransition(conf.fall_back_duration, breaker=rear_edge_breaker)

    transitions_pool: List[MovingTransition] = []
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().add(end_state).export_structure()

    transitions_pool.extend(transitions)
    case_reg.register(ScanCodesign.O_O_O_O, head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container().add(fall_back_state).add(fall_back_transition).add(end_state).export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.register(ScanCodesign.X_O_O_O, head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container().add(rand_turn_state).add(full_turn_transition).add(end_state).export_structure()
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
        composer.init_container().add(turn_left_state).add(half_turn_transition).add(end_state).export_structure()
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
        composer.init_container().add(turn_right_state).add(half_turn_transition).add(end_state).export_structure()
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
        composer.init_container().add(fall_back_state).add(fall_back_transition).add(end_state).export_structure()
    )

    transitions_pool.extend(transitions)
    case_reg.register(ScanCodesign.X_O_X_X, head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(fall_back_state)
        .add(fall_back_transition)
        .add(rand_turn_state)
        .add(half_turn_transition)
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

    return states, transitions


def make_rand_turn_handler(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = MovingState.halt()
) -> Tuple[List[MovingState], List[MovingTransition]]:

    conf = run_config.search.rand_turn

    rand_lr_turn_state = MovingState.rand_dir_turn(controller, conf.turn_speed, turn_left_prob=conf.turn_left_prob)

    half_turn_transition = MovingTransition(conf.half_turn_duration)

    states, transitions = composer.add(rand_lr_turn_state).add(half_turn_transition).add(end_state).export_structure()
    return states, transitions


def make_gradient_move(
    app_config: APPConfig, run_config: RunConfig, end_state: MovingState = MovingState.halt()
) -> MovingState:
    conf = run_config.search.gradient_move

    speed_range = conf.max_speed - conf.min_speed

    speed_calc_func = menta.construct_inlined_function(
        usages=[
            SamplerUsage(
                used_sampler_index=SamplerIndexes.adc_all, required_data_indexes=[app_config.sensor.gray_adc_index]
            )
        ],
        judging_source=f"ret={conf.min_speed}+int({speed_range}*(s0-{conf.min_speed})/({conf.max_speed}-{conf.min_speed}))",
        return_type_varname="int",
        extra_context={"int": int},
        return_raw=False,
    )
    speed_updater = controller.register_context_executor(speed_calc_func, [ContextVar.gradient_speed.name])
    return MovingState(
        speed_expressions=ContextVar.gradient_speed.name,
        used_context_variables=[ContextVar.gradient_speed.name],
        before_entering=[speed_updater],
    )


def make_search_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    start_state: Optional[MovingState] = None,
) -> Tuple[List[MovingState], List[MovingTransition]]:
    start_state = start_state or continues_state.clone()
    scan_states, scan_transitions = make_scan_handler(app_config, run_config)
    rand_turn_states, rand_turn_transitions = make_rand_turn_handler(app_config, run_config)
    grad_move_state = make_gradient_move(app_config, run_config)

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
    start_state: Optional[MovingState] = None,
    end_state: Optional[MovingState] = MovingState.halt(),
    abnormal_exit: MovingState = MovingState.halt(),
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:
    is_align_setter_true = controller.register_context_executor(lambda: True, ContextVar.is_aligned.name)
    is_align_setter_false = controller.register_context_executor(lambda: False, ContextVar.is_aligned.name)
    is_align_getter = controller.register_context_getter(ContextVar.is_aligned.name)

    fence_breaker = Breakers.make_std_fence_breaker(app_config, run_config)

    align_stage_breaker = Breakers.make_stage_align_breaker_mpu(app_config, run_config)

    back_stage_pack = make_back_to_stage_handler(run_config, end_state)
    rand_move_pack = make_rand_walk_handler(run_config, abnormal_exit)

    align_direction_pack = make_align_direction_handler(app_config, run_config, rand_move_pack[0][0])

    conf = run_config.fence

    start_state = start_state or continues_state.clone()

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

    align_stage_transition = MovingTransition(conf.max_stage_align_duration, breaker=align_stage_breaker)

    transitions_pool: List[MovingTransition] = []

    case_reg = CaseRegistry(FenceCodeSign)

    # ---------------------------------------------------------------------
    # TODO impl
    [head_state, *_], transitions = composer.init_container().concat(*back_stage_pack).export_structure()
    transitions_pool.extend(transitions)
    case_reg.register(FenceCodeSign.X_O_O_O, head_state)

    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(align_state.clone())
        .add(align_stage_transition.clone())
        .concat(*back_stage_pack)
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
        .add(MovingState.halt())
        .export_structure()
    )
    transitions_pool.extend(transitions)
    case_reg.batch_register([FenceCodeSign.O_X_O_X, FenceCodeSign.O_X_X_O], head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container()
        .add(rear_exit_corner_state.clone())
        .add(exit_duration.clone())
        .add(MovingState.halt())
        .export_structure()
    )
    transitions_pool.extend(transitions)
    case_reg.batch_register([FenceCodeSign.X_O_O_X, FenceCodeSign.X_O_X_O], head_state)
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = (
        composer.init_container().concat(*align_direction_pack).add(MovingState.halt(), True).export_structure()
    )
    transitions_pool.extend(transitions)
    case_reg.batch_register(
        [FenceCodeSign.O_X_X_X, FenceCodeSign.X_O_X_X, FenceCodeSign.X_X_O_X, FenceCodeSign.X_X_X_O], head_state
    )
    # ---------------------------------------------------------------------
    [head_state, *_], transitions = composer.init_container().concat(*rand_move_pack).export_structure()
    transitions_pool.extend(transitions)
    case_reg.batch_register([FenceCodeSign.O_O_O_O, FenceCodeSign.X_X_X_X], head_state)
    # ---------------------------------------------------------------------

    # <editor-fold desc="Assembly">
    _, head_trans = (
        composer.init_container()
        .add(start_state)
        .add(MovingTransition(run_config.perf.min_sync_interval, breaker=fence_breaker, to_states=case_reg.export()))
        .export_structure()
    )
    # </editor-fold>

    # <editor-fold desc="Make Return">
    transitions_pool.extend(head_trans)

    return start_state, end_state, list(set(transitions_pool))
    # </editor-fold>


def make_align_direction_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    not_aligned_state: Optional[MovingState] = MovingState.halt(),
    aligned_state: Optional[MovingState] = None,
) -> Tuple[List[MovingState], List[MovingTransition]]:
    # TODO impl
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
    align_direction_transition = MovingTransition(
        conf.max_direction_align_duration, breaker=align_direction_breaker, to_states={False: not_aligned_state}
    )

    composer.init_container().add(align_state).add(align_direction_transition)
    composer.add(aligned_state, True) if aligned_state else None
    return composer.export_structure()


def make_back_to_stage_handler(
    run_config: RunConfig, end_state: Optional[MovingState] = MovingState.halt()
) -> Tuple[List[MovingState], List[MovingTransition]]:
    small_advance = MovingState(run_config.backstage.small_advance_speed)
    small_advance_transition = MovingTransition(run_config.backstage.small_advance_duration)
    stab_trans = MovingTransition(run_config.backstage.time_to_stabilize)
    # waiting for a booting signal, and dash on to the stage once received
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
    app_config: APPConfig, run_config: RunConfig, end_state: Optional[MovingState] = MovingState.halt()
) -> Tuple[List[MovingState], List[MovingTransition]]:
    """
    Constructs a state machine handler for reboot sequences.

    Parameters:
        app_config: APPConfig, configuration object for application specifics including sensor details.
        run_config: RunConfig, runtime configuration object with parameters for bootup and movement actions.
        end_state: Optional[MovingState], the final state of the state machine, defaults to MovingState(0).

    Returns:
        Tuple[List[MovingState], List[MovingTransition]], a tuple containing lists of states and transitions.
    """
    activation_breaker = menta.construct_inlined_function(
        usages=[
            SamplerUsage(
                used_sampler_index=SamplerIndexes.adc_all,
                required_data_indexes=[app_config.sensor.left_adc_index, app_config.sensor.right_adc_index],
            )
        ],
        judging_source=f"ret=s0>{run_config.boot.left_threshold} and s1>{run_config.boot.right_threshold}",
        return_type_varname="bool",
        extra_context={"bool": bool},
        return_raw=False,
    )

    holding_transition = MovingTransition(run_config.boot.max_holding_duration, breaker=activation_breaker)
    # waiting for a booting signal, and dash on to the stage once received
    states, transitions = (
        composer.init_container()
        .add(MovingState.halt())
        .add(holding_transition)
        .add(MovingState.straight(-run_config.boot.dash_speed))
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
    run_config: RunConfig, end_state: MovingState = MovingState.halt()
) -> Tuple[List[MovingState], List[MovingTransition]]:
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
    move_transition = MovingTransition(conf.walk_duration)
    return composer.init_container().add(rand_move_state).add(move_transition).add(end_state).export_structure()


def make_stage_handler(
    app_config: APPConfig,
    run_config: RunConfig,
    end_state: MovingState = MovingState.halt(),
    tag_group: Optional[TagGroup] = None,
) -> List[MovingTransition]:

    start_state = continues_state.clone()

    stage_breaker = Breakers.make_std_stage_breaker(app_config, run_config)

    reboot_pack = make_reboot_handler(app_config, run_config)
    fence_pack = make_fence_handler(app_config, run_config)
    edge_pack = make_edge_handler(app_config, run_config)
    surr_pack = make_surrounding_handler(app_config, run_config, tag_group, start_state=edge_pack[1])
    search_pack = make_search_handler(app_config, run_config, start_state=surr_pack[1])

    print(f"edge n end {edge_pack[1]}")
    case_reg = CaseRegistry(StageCodeSign)
    transition_pool = [*reboot_pack[-1], *edge_pack[-1], *fence_pack[-1], *surr_pack[-1], *search_pack[-1]]

    (
        case_reg.batch_register(
            [StageCodeSign.ON_STAGE_REBOOT, StageCodeSign.OFF_STAGE_REBOOT],
            reboot_pack[0][0],
        )
        .register(StageCodeSign.ON_STAGE, edge_pack[0])
        .register(StageCodeSign.OFF_STAGE, fence_pack[0])
    )

    check_trans = MovingTransition(
        run_config.perf.min_sync_interval, breaker=stage_breaker, to_states=case_reg.export()
    )

    _, trans = composer.init_container().add(start_state).add(check_trans).export_structure()
    transition_pool.extend(trans)
    return transition_pool
