from dataclasses import dataclass
from typing import Callable, List, Tuple, Dict, Set

from bdmc import CloseLoopController
from mentabotix import MovingChainComposer, Botix, Menta, MovingState, MovingTransition, SamplerUsage
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
    sensor_name = [f"s{i}" for i in range(4)]

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
                f"({lt}>{s_name} or {s_name}<{ut})*{wt}"
                for s_name, lt, ut, wt in zip(sensor_name, lt_seq, ut_seq, edge_weight_seq)
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

    half_turn_transition = MovingTransition(run_config.edge.half_turn_duration)

    full_turn_transition = MovingTransition(run_config.edge.full_turn_duration)

    states_pool: Set[MovingState] = {stop_state, continues_state}

    transitions_pool: List[MovingTransition] = []

    case_dict: Dict = {}

    case_dict[EdgeCodeSign.O_O_O_O] = continues_state.clone()

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

    states_pool.update(states)
    transition.extend(transitions_pool)

    case_dict[EdgeCodeSign.X_O_O_O] = states[0]

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

    states_pool.update(states)
    transition.extend(transitions_pool)

    case_dict[EdgeCodeSign.O_O_O_X] = states[0]

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

    states_pool.update(states)
    transition.extend(transitions_pool)

    case_dict[EdgeCodeSign.O_X_O_O] = states[0]

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

    states_pool.update(states)
    transition.extend(transitions_pool)

    case_dict[EdgeCodeSign.O_O_X_O] = states[0]

    head = (
        composer.init_container()
        .add(continues_state)
        .add(MovingTransition(run_config.perf.min_sync_interval, breaker=edge_full_breaker, to_states=case_dict))
        .export_structure()
    )

    botix.export_structure("strac.puml", head[-1])

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
