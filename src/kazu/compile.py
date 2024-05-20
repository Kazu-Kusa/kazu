from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, List, Tuple, Dict, Optional

from bdmc import CloseLoopController
from mentabotix import MovingChainComposer, Botix, Menta, MovingState, MovingTransition, SamplerUsage
from pyuptech import OnBoardSensors, Screen
from upic import TagDetector

from .config import APPConfig, RunConfig, ContextVar, TagGroup
from .constant import EdgeWeights, EdgeCodeSign, SurroundingWeights

sensors = OnBoardSensors()
menta = Menta(
    samplers=[
        sensors.adc_all_channels,
        sensors.io_all_channels,
        sensors.get_io_level,
        sensors.get_all_io_mode,
        sensors.atti_all,
        sensors.gyro_all,
        sensors.acc_all,
    ]
)
controller = CloseLoopController()

botix = Botix(controller=controller)

composer = MovingChainComposer()

tag_detector = TagDetector()
screen = Screen()


@dataclass
class SamplerIndexes:
    adc_all: int = 0
    io_all: int = 1
    io_level_idx: int = 2
    io_mode_all: int = 3
    atti_all: int = 4
    gyro_all: int = 5
    acc_all: int = 6


class Breakers:

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_rear_breaker(app_config: APPConfig, run_config: RunConfig):
        lt_seq = run_config.edge.lower_threshold
        ut_seq = run_config.edge.upper_threshold
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.edge_rl_index,
                        app_config.sensor.edge_rr_index,
                    ],
                )
            ],
            judging_source=f"ret= ({lt_seq[1]}>s0 or s0<{ut_seq[1]}) or ({lt_seq[2]}>s1 or s1<{ut_seq[2]})",
            extra_context={"bool": bool},
            return_type_varname="bool",
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_front_breaker(app_config: APPConfig, run_config: RunConfig):
        lt_seq = run_config.edge.lower_threshold
        ut_seq = run_config.edge.upper_threshold
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[app_config.sensor.gray_io_left_index, app_config.sensor.gray_io_right_index],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.edge_fl_index,
                        app_config.sensor.edge_fr_index,
                    ],
                ),
            ],
            judging_source=f"ret=s0=={app_config.sensor.gray_io_off_stage_case} "
            f"or s1=={app_config.sensor.gray_io_off_stage_case} "
            f"or ({lt_seq[0]}>s2 or s2<{ut_seq[0]}) "
            f"or ({lt_seq[-1]}>s3 or s3<{ut_seq[-1]})",
            extra_context={"bool": bool},
            return_type_varname="bool",
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_full_breaker(app_config: APPConfig, run_config: RunConfig):
        lt_seq = run_config.edge.lower_threshold
        ut_seq = run_config.edge.upper_threshold
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.edge_fl_index,
                        app_config.sensor.edge_rl_index,
                        app_config.sensor.edge_rr_index,
                        app_config.sensor.edge_fr_index,
                    ],
                )
            ],
            judging_source=(
                "ret=sum("
                + ",".join(
                    f"({lt}>s{s_id} or {s_id}<{ut})*{wt}"
                    for s_id, lt, ut, wt in zip(range(4), lt_seq, ut_seq, EdgeWeights.export_std_weight_seq())
                )
                + ")"
            ),
            extra_context={"int": int},
            return_type_varname="int",
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_turn_to_front_breaker(app_config: APPConfig, run_config: RunConfig):
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_level_idx,
                    required_data_indexes=[
                        app_config.sensor.fl_io_index,  # s0
                        app_config.sensor.fr_io_index,  # s1
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.front_adc_index,  # s2
                    ],
                ),
            ],
            judging_source=f"ret=bool(s0 or s1 or s2>{run_config.surrounding.front_adc_lower_threshold})",
            extra_context={"bool": bool},
            return_type_varname="bool",
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_scanning_breaker(app_config: APPConfig, run_config: RunConfig):
        # TODO impl
        raise NotImplementedError


def make_edge_handler(
    app_config: APPConfig, run_config: RunConfig
) -> Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:
    """
    根据应用和运行配置创建边缘处理函数。

    Args:
        app_config: APPConfig 类型，应用配置，包含传感器和其它配置。
        run_config: RunConfig 类型，运行时配置，包含边缘检测的阈值和行为配置。

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

    # <editor-fold desc="Case Setter">
    # 创建上下文更新器（case setter），用于设置遇到边缘的上下文变量
    edge_setter_true = controller.register_context_updater(
        lambda: True,
        input_keys=[],
        output_keys=[ContextVar.had_encountered_edge.name],
    )

    edge_setter_false = controller.register_context_updater(
        lambda: False,
        input_keys=[],
        output_keys=[ContextVar.had_encountered_edge.name],
    )
    # </editor-fold>

    # <editor-fold desc="Templates">

    # 定义不同移动状态，如停止、继续、后退等
    stop_state = MovingState(0, after_exiting=[edge_setter_true])

    continues_state = MovingState(
        speed_expressions=ContextVar.prev_salvo_speed.name, used_context_variables=[ContextVar.prev_salvo_speed.name]
    )

    fallback_state = MovingState.straight(-run_config.edge.fallback_speed)

    fallback_transition = MovingTransition(run_config.edge.fallback_duration, breaker=edge_rear_breaker)

    advance_state = MovingState.straight(run_config.edge.advance_speed)

    advance_transition = MovingTransition(run_config.edge.advance_duration, breaker=edge_front_breaker)

    left_turn_state = MovingState.turn("l", run_config.edge.turn_speed)

    right_turn_state = MovingState.turn("r", run_config.edge.turn_speed)

    rand_lr_turn_state = MovingState.rand_turn(
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
    case_dict: Dict = {EdgeCodeSign.O_O_O_O.value: (normal_exit := continues_state.clone())}
    normal_exit.after_exiting.append(edge_setter_false)
    # </editor-fold>

    # <editor-fold desc="1-Activation Cases">
    # fallback and full turn right
    [head_state, *_], transition = (
        composer.init_container()
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(right_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
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
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_X_O_X.value] = head_state

    # </editor-fold>

    # <editor-fold desc="4-Activation Cases">
    # just stop immediately, since such case are extremely rare in the normal race
    [head_state, *_], transition = composer.init_container().add(stop_state).export_structure()

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_X_X_X.value] = head_state

    # </editor-fold>

    # <editor-fold desc="Assembly">
    _, head_trans = (
        composer.init_container()
        .add(continues_state)
        .add(MovingTransition(run_config.perf.min_sync_interval, breaker=edge_full_breaker, to_states=case_dict))
        .export_structure()
    )

    transitions_pool.extend(head_trans)

    botix.export_structure("strac.puml", transitions_pool)
    start_state = continues_state
    abnormal_exit = stop_state
    # </editor-fold>
    return start_state, normal_exit, abnormal_exit, transitions_pool


def make_surrounding_handler(
    app_config: APPConfig, run_config: RunConfig, tag_group: Optional[TagGroup] = None
) -> Tuple[MovingState, MovingState, MovingState, List[MovingTransition]]:
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

    dash_breaker = menta.construct_inlined_function(
        usages=[
            SamplerUsage(
                used_sampler_index=SamplerIndexes.io_all,
                required_data_indexes=[
                    app_config.sensor.gray_io_left_index,  # s0
                    app_config.sensor.gray_io_right_index,  # s1
                    app_config.sensor.fl_io_index,  # s2
                    app_config.sensor.fr_io_index,  # s3
                ],
            ),
            SamplerUsage(
                used_sampler_index=SamplerIndexes.adc_all,
                required_data_indexes=[app_config.sensor.front_adc_index],  # s4
            ),
        ],
        judging_source=f"ret=not s0 or not s1  "  # use gray scaler, indicating the edge is encountered
        f"or not any( (s2 , s3 , s4>{run_config.surrounding.dash_break_front_lower_threshold}))",  # indicating front is empty
        return_type_varname="bool",
        extra_context={"bool": bool},
        return_raw=False,
    )

    edge_rear_breaker = Breakers.make_std_edge_rear_breaker(app_config, run_config)


def make_normal_handler() -> Callable:
    raise NotImplementedError


def make_fence_handler() -> Callable:
    raise NotImplementedError


def make_back_to_stage_handler(run_config: RunConfig) -> Tuple[MovingState, MovingState, List[MovingTransition]]:

    small_advance = MovingState(run_config.backstage.small_advance_speed)
    small_advance_transition = MovingTransition(run_config.backstage.small_advance_duration)
    # waiting for a booting signal, and dash on to the stage once received
    states, transitions = (
        composer.init_container()
        .add(small_advance)
        .add(small_advance_transition)
        .add(MovingState(0))
        .add(stab_trans := MovingTransition(run_config.backstage.time_to_stabilize))
        .add(MovingState.straight(-run_config.boot.dash_speed))
        .add(MovingTransition(run_config.boot.dash_duration))
        .add(MovingState(0))
        .add(stab_trans.clone())
        .add(
            MovingState.rand_turn(controller, run_config.boot.turn_speed, turn_left_prob=run_config.boot.turn_left_prob)
        )
        .export_structure()
    )

    return states[0], states[-1], transitions


def make_reboot_handler(
    app_config: APPConfig, run_config: RunConfig
) -> Tuple[MovingState, MovingState, List[MovingTransition]]:

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
        .add(MovingState(0))
        .add(holding_transition)
        .add(MovingState.straight(-run_config.boot.dash_speed))
        .add(MovingTransition(run_config.boot.dash_duration))
        .add(MovingState(0))
        .add(MovingTransition(run_config.boot.time_to_stabilize))
        .add(
            MovingState.rand_turn(controller, run_config.boot.turn_speed, turn_left_prob=run_config.boot.turn_left_prob)
        )
        .add(MovingTransition(run_config.boot.full_turn_duration))
        .add(MovingState(0))
        .export_structure()
    )

    return states[0], states[-1], transitions
