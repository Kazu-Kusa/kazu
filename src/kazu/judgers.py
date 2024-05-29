from functools import lru_cache
from typing import Callable, Tuple

from mentabotix import SamplerUsage

from kazu.config import APPConfig, RunConfig, ContextVar
from kazu.constant import EdgeWeights, Attitude, ScanWeights, StageWeight
from kazu.hardwares import controller, menta, SamplerIndexes


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
            judging_source=f"ret=s0=={app_config.sensor.io_activating_value} "
            f"or s1=={app_config.sensor.io_activating_value} "
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

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_atk_breaker(app_config: APPConfig, run_config: RunConfig):
        return menta.construct_inlined_function(
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
            f"or not any( (s2 , s3 , s4>{run_config.surrounding.atk_break_front_lower_threshold}))",
            # indicating front is empty
            return_type_varname="bool",
            extra_context={"bool": bool},
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_stage_align_breaker(app_config: APPConfig, run_config: RunConfig):
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_level_idx,
                    required_data_indexes=[
                        app_config.sensor.fl_io_index,  # s0
                        app_config.sensor.fr_io_index,  # s1
                        app_config.sensor.rl_io_index,  # s2
                        app_config.sensor.rr_io_index,  # s3
                    ],
                ),
            ],
            judging_source=f"ret=bool(s0 or s1 and not s2 and not s3)",
            return_type_varname="bool",
            extra_context={"bool": bool},
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_stage_align_breaker_mpu(app_config: APPConfig, run_config: RunConfig):
        invalid_lower_bound, invalid_upper_bound = (
            run_config.fence.max_yaw_tolerance,
            90 - run_config.fence.max_yaw_tolerance,
        )
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.atti_all,
                    required_data_indexes=[
                        Attitude.yaw,  # s0
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_level_idx,
                    required_data_indexes=[
                        app_config.sensor.fl_io_index,  # s1
                        app_config.sensor.fr_io_index,  # s2
                    ],
                ),
            ],
            judging_source=f"ret=bool(not ({invalid_lower_bound}<abs(s0)//90<{invalid_upper_bound}) and (s1 or s2))",
            return_type_varname="bool",
            extra_context={"bool": bool},
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_on_stage_breaker(app_config: APPConfig, run_config: RunConfig):
        from kazu.constant import StageWeight

        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        app_config.sensor.reboot_button_index,  # s0
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.gray_adc_index,  # s1
                    ],
                ),
            ],
            judging_source=f"ret={StageWeight.REBOOT}*(s0=={app_config.sensor.io_activating_value})"
            f"+{StageWeight.OFF}*(s1<{run_config.perf.gray_adc_lower_threshold})",
            return_type_varname="int",
            extra_context={"int": int},
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_fence_breaker(app_config: APPConfig, run_config: RunConfig):
        from kazu.constant import FenceWeights

        conf = run_config.fence
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.front_adc_index,  # s0
                        app_config.sensor.rb_adc_index,  # s1
                        app_config.sensor.left_adc_index,  # s2
                        app_config.sensor.right_adc_index,  # s3
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        app_config.sensor.fl_io_index,  # s4
                        app_config.sensor.fr_io_index,  # s5
                        app_config.sensor.rl_io_index,  # s6
                        app_config.sensor.rr_io_index,  # s7
                    ],
                ),
            ],
            judging_source=f"ret={FenceWeights.Front}*(s0>{conf.front_adc_lower_threshold} or s4 == {conf.io_activated_value} or s5 == {conf.io_activated_value})"
            f"+{FenceWeights.Rear}*(s1>{conf.rear_adc_lower_threshold} or s6 == {conf.io_activated_value} or s7 == {conf.io_activated_value})"
            f"+{FenceWeights.Left}*(s2>{conf.left_adc_lower_threshold})"
            f"+{FenceWeights.Rear}*(s3>{conf.right_adc_lower_threshold})",
            return_type_varname="int",
            extra_context={"int": int},
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_align_direction_breaker(app_config: APPConfig, run_config: RunConfig):
        from kazu.constant import Attitude

        invalid_lower_bound, invalid_upper_bound = (
            run_config.fence.max_yaw_tolerance,
            90 - run_config.fence.max_yaw_tolerance,
        )
        return menta.construct_inlined_function(
            usages=[SamplerUsage(used_sampler_index=SamplerIndexes.atti_all, required_data_indexes=[Attitude.yaw])],
            judging_source=["diff=abs(s0)//90", f"ret={invalid_lower_bound}>diff or diff>{invalid_upper_bound}"],
            return_type_varname="bool",
            extra_context={"bool": bool},
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_scan_breaker(app_config: APPConfig, run_config: RunConfig):

        adc_pack_getter: Callable[[], Tuple] = controller.register_context_getter(ContextVar.recorded_pack.name)
        conf = run_config.search.scan_move
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.front_adc_index,  # s0
                        app_config.sensor.rb_adc_index,  # s1
                        app_config.sensor.left_adc_index,  # s2
                        app_config.sensor.right_adc_index,  # s3
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        app_config.sensor.fl_io_index,  # s4
                        app_config.sensor.fr_io_index,  # s5
                        app_config.sensor.rl_io_index,  # s6
                        app_config.sensor.rr_io_index,  # s7
                    ],
                ),
            ],
            judging_source=[  # activate once the deviation surpluses the tolerance
                "pack=adc_pack_getter()",
                f"front=pack[{app_config.sensor.front_adc_index}]",
                f"rear=pack[{app_config.sensor.rb_adc_index}]",
                f"left=pack[{app_config.sensor.left_adc_index}]",
                f"right=pack[{app_config.sensor.right_adc_index}]",
                f"ret={ScanWeights.Front}*(s0-front>{conf.front_max_tolerance} or s4 == {conf.io_activated_value} or s5 == {conf.io_activated_value})"
                f"+{ScanWeights.Rear}*(s1-rear>{conf.rear_max_tolerance} or s6 == {conf.io_activated_value} or s7 == {conf.io_activated_value})"
                f"+{ScanWeights.Left}*(s2-left>{conf.left_max_tolerance})"
                f"+{ScanWeights.Rear}*(s3-right>{conf.right_max_tolerance})",
            ],
            return_type_varname="int",
            extra_context={"int": int, "adc_pack_getter": adc_pack_getter},
            return_raw=False,
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_stage_breaker(app_config: APPConfig, run_config: RunConfig):
        conf = run_config.stage
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.gray_adc_index,  # s0
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        app_config.sensor.reboot_button_index,  # s1
                    ],
                ),
            ],
            judging_source=f"ret={StageWeight.STAGE}*(s0<{conf.gray_adc_upper_threshold})"
            f"+{StageWeight.REBOOT}*(s1=={app_config.sensor.io_activating_value})",
            return_type_varname="int",
            extra_context={"int": int},
            return_raw=False,
        )
