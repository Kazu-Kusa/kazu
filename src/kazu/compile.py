from dataclasses import dataclass
from typing import Callable, List, Tuple, Dict

from bdmc import CloseLoopController
from mentabotix import (
    MovingChainComposer,
    Botix,
    Menta,
    MovingState,
    MovingTransition,
    SamplerUsage,
)
from pyuptech import OnBoardSensors

from .config import APPConfig, RunConfig, ContextVar
from .constant import EdgeWeights, EdgeCodeSign

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


@dataclass
class SamplerIndexes:
    adc_all: int = 0
    io_all: int = 1
    io_level_idx: int = 2
    io_mode_all: int = 3
    atti_all: int = 4
    gyro_all: int = 5
    acc_all: int = 6


def make_edge_handler(app_config: APPConfig, run_config: RunConfig) -> Tuple[List[MovingState], List[MovingTransition]]:
    lt_seq = run_config.edge.lower_threshold
    ut_seq = run_config.edge.upper_threshold

    edge_weight_seq = EdgeWeights.export_std_weight_seq()

    # build edge full breaker, which used to implement the branching logic. It uses CodeSign to distinguish the edge case
    edge_full_breaker: Callable[[], int] = menta.construct_inlined_function(
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
                for s_id, lt, ut, wt in zip(range(4), lt_seq, ut_seq, edge_weight_seq)
            )
            + ")"
        ),
        extra_context={"int": int},
        return_type_varname="int",
        return_raw=False,
    )

    # build edge front breaker, used to halt the bot as soon as the edge is detected at the front, using gray io and two front edge sensors
    edge_front_breaker: Callable[[], bool] = menta.construct_inlined_function(
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
        judging_source=f"ret=s0=={app_config.sensor.gray_io_off_stage_case} or s1=={app_config.sensor.gray_io_off_stage_case} or ({lt_seq[0]}>s2 or s2<{ut_seq[0]}) or ({lt_seq[-1]}>s3 or s3<{ut_seq[-1]})",
        extra_context={"bool": bool},
        return_type_varname="bool",
        return_raw=False,
    )
    edge_rear_breaker: Callable[[], bool] = menta.construct_inlined_function(
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

    stop_state = MovingState(0)

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

    transitions_pool: List[MovingTransition] = []

    case_dict: Dict = {EdgeCodeSign.O_O_O_O: continues_state.clone()}

    # <editor-fold desc="1-Activation">
    # fallback and full turn right
    states, transition = (
        composer.init_container()
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(right_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_O_O_O] = states[0]
    # -----------------------------------------------------------------------------
    # fallback and full turn left
    states, transition = (
        composer.init_container()
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(left_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.O_O_O_X] = states[0]
    # -----------------------------------------------------------------------------

    # advance and half turn right
    states, transition = (
        composer.init_container()
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.O_X_O_O] = states[0]
    # -----------------------------------------------------------------------------

    # advance and half turn left
    states, transition = (
        composer.init_container()
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.O_O_X_O] = states[0]
    # </editor-fold>

    # <editor-fold desc="2-Activation">
    # half turn right
    states, transition = (
        composer.init_container()
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_X_O_O] = states[0]
    # -----------------------------------------------------------------------------

    # half turn left
    states, transition = (
        composer.init_container()
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.O_O_X_X] = states[0]
    # -----------------------------------------------------------------------------

    # fallback and full turn left or right
    states, transition = (
        composer.init_container()
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(rand_lr_turn_state.clone())
        .add(full_turn_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_O_O_X] = states[0]
    # -----------------------------------------------------------------------------

    # advance
    states, transition = (
        composer.init_container()
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.O_X_X_O] = states[0]
    # -----------------------------------------------------------------------------

    # drift right back
    states, transition = (
        composer.init_container()
        .add(drift_right_back_state.clone())
        .add(drift_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_O_X_O] = states[0]
    # -----------------------------------------------------------------------------

    # drift left back
    states, transition = (
        composer.init_container()
        .add(drift_left_back_state.clone())
        .add(drift_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.O_X_O_X] = states[0]

    # </editor-fold>

    # <editor-fold desc="3-Activation">

    # half turn left and advance
    states, transition = (
        composer.init_container()
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.O_X_X_X] = states[0]
    # -----------------------------------------------------------------------------

    # half turn right and advance
    states, transition = (
        composer.init_container()
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(advance_state.clone())
        .add(advance_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_X_X_O] = states[0]
    # -----------------------------------------------------------------------------

    # half turn right and fallback
    states, transition = (
        composer.init_container()
        .add(right_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_O_X_X] = states[0]
    # -----------------------------------------------------------------------------

    # half turn left and fallback
    states, transition = (
        composer.init_container()
        .add(left_turn_state.clone())
        .add(half_turn_transition.clone())
        .add(fallback_state.clone())
        .add(fallback_transition.clone())
        .add(stop_state)
        .export_structure()
    )

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_X_O_X] = states[0]

    # </editor-fold>

    # <editor-fold desc="4-Activation">
    # just stop immediately, since such case are extremely rare in the normal race
    states, transition = composer.init_container().add(stop_state).export_structure()

    transitions_pool.extend(transition)

    case_dict[EdgeCodeSign.X_X_X_X] = states[0]
    # </editor-fold>

    head_state, head_trans = (
        composer.init_container()
        .add(continues_state)
        .add(MovingTransition(run_config.perf.min_sync_interval, breaker=edge_full_breaker, to_states=case_dict))
        .export_structure()
    )

    transitions_pool.extend(head_trans)
    botix.export_structure("strac.puml", transitions_pool)

    return


def make_surrounding_handler() -> Callable:
    raise NotImplementedError


def make_normal_handler() -> Callable:
    raise NotImplementedError


def make_fence_handler() -> Callable:
    raise NotImplementedError


def make_start_handler() -> Callable:
    raise NotImplementedError


def make_reboot_handler() -> Callable:
    raise NotImplementedError
