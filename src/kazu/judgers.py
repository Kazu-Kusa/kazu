from functools import lru_cache
from typing import Callable, Tuple, Dict

from mentabotix import SamplerUsage

from kazu.config import APPConfig, RunConfig, ContextVar, TagGroup
from kazu.constant import EdgeWeights, Attitude, ScanWeights, StageWeight, SurroundingWeights
from kazu.hardwares import controller, menta, SamplerIndexes, tag_detector
from kazu.logger import _logger


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
            return_type=bool,
            return_raw=False,
            function_name="std_edge_rear_breaker",
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
            return_type=bool,
            return_raw=False,
            function_name="std_edge_front_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_full_breaker(app_config: APPConfig, run_config: RunConfig):
        lt_seq = run_config.edge.lower_threshold
        ut_seq = run_config.edge.upper_threshold

        source = [
            "ret=sum(["
            + ",".join(
                f"({lt}>s{s_id} or {s_id}<{ut})*{wt}"
                for s_id, lt, ut, wt in zip(range(4), lt_seq, ut_seq, EdgeWeights.export_std_weight_seq())
            )
            + "])"
        ]
        ctx = {}
        if app_config.logger.log_level == "DEBUG":

            ctx["_logger"] = _logger
            source.append('_logger.debug(f"Edge Code: {ret}")')

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
            judging_source=source,
            extra_context=ctx,
            return_type=int,
            return_raw=False,
            function_name="std_edge_full_breaker",
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
            return_type=bool,
            return_raw=False,
            function_name="std_turn_to_front_breaker",
        )

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
            return_type=bool,
            return_raw=False,
            function_name="atk_breaker",
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
            return_type=bool,
            return_raw=False,
            function_name="stage_align_breaker",
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
            return_type=bool,
            return_raw=False,
            function_name="stage_align_breaker_mpu",
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
            f"+{StageWeight.STAGE}*(s1<{run_config.perf.gray_adc_lower_threshold})",
            return_type=int,
            return_raw=False,
            function_name="std_on_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_fence_breaker(app_config: APPConfig, run_config: RunConfig):
        from kazu.constant import FenceWeights

        conf = run_config.fence
        source = [
            f"ret={FenceWeights.Front}*(s0>{conf.front_adc_lower_threshold} or s4 == {conf.io_activated_value} or s5 == {conf.io_activated_value})"
            f"+{FenceWeights.Rear}*(s1>{conf.rear_adc_lower_threshold} or s6 == {conf.io_activated_value} or s7 == {conf.io_activated_value})"
            f"+{FenceWeights.Left}*(s2>{conf.left_adc_lower_threshold})"
            f"+{FenceWeights.Rear}*(s3>{conf.right_adc_lower_threshold})"
        ]

        ctx = {}
        if app_config.logger.log_level == "DEBUG":
            source.append('_logger.debug(f"Fence Code: {ret}")')
            ctx["_logger"] = _logger

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
            judging_source=source,
            extra_context=ctx,
            return_type=int,
            return_raw=False,
            function_name="std_fence_breaker",
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
            return_type=bool,
            return_raw=False,
            function_name="align_direction_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_scan_breaker(app_config: APPConfig, run_config: RunConfig):

        adc_pack_getter: Callable[[], Tuple] = controller.register_context_getter(ContextVar.recorded_pack.name)
        conf = run_config.search.scan_move
        source = [  # activate once the deviation surpluses the tolerance
            "pack=adc_pack_getter()",
            f"front=pack[{app_config.sensor.front_adc_index}]",
            f"rear=pack[{app_config.sensor.rb_adc_index}]",
            f"left=pack[{app_config.sensor.left_adc_index}]",
            f"right=pack[{app_config.sensor.right_adc_index}]",
            f"ret={ScanWeights.Front}*(s0-front>{conf.front_max_tolerance} or s4 == {conf.io_activated_value} or s5 == {conf.io_activated_value})"
            f"+{ScanWeights.Rear}*(s1-rear>{conf.rear_max_tolerance} or s6 == {conf.io_activated_value} or s7 == {conf.io_activated_value})"
            f"+{ScanWeights.Left}*(s2-left>{conf.left_max_tolerance})"
            f"+{ScanWeights.Rear}*(s3-right>{conf.right_max_tolerance})",
        ]
        ctx = {"adc_pack_getter": adc_pack_getter}

        if app_config.logger.log_level == "DEBUG":
            source.append('_logger.debug(f"Scan Code: {ret}")')
            ctx["_logger"] = _logger

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
            judging_source=source,
            return_type=int,
            extra_context=ctx,
            return_raw=False,
            function_name="std_scan_breaker",
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
            return_type=int,
            return_raw=False,
            function_name="std_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_always_on_stage_breaker(app_config: APPConfig, run_config: RunConfig):
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
            judging_source=[  # true ret is reserved to emulate the performance consumption
                f"true_ret={StageWeight.STAGE}*(s0<{conf.gray_adc_upper_threshold})"
                f"+{StageWeight.REBOOT}*(s1=={app_config.sensor.io_activating_value})",
                "ret=0",
            ],
            return_type=int,
            return_raw=False,
            function_name="always_on_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_always_off_stage_breaker(app_config: APPConfig, run_config: RunConfig):
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
            judging_source=[
                "temp_data=s0",
                f"ret={StageWeight.STAGE}*(True)"
                f"+{StageWeight.REBOOT}*(s1=={app_config.sensor.io_activating_value})",
            ],
            return_type=int,
            return_raw=False,
            function_name="always_off_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_cam_surr_breaker(app_config: APPConfig, run_config: RunConfig, query_table: Dict[Tuple[int, bool], int]):
        source = [
            (
                f"ret=q_tb.get((tag_d.tag_id, bool(s0 or s1 or s4>{run_config.surrounding.front_adc_lower_threshold})))"
                f"+(s5>{run_config.surrounding.left_adc_lower_threshold})*{SurroundingWeights.LEFT_OBJECT}"
                f"+(s6>{run_config.surrounding.right_adc_lower_threshold})*{SurroundingWeights.RIGHT_OBJECT}"
                f"+s2 or s3 or s7>{run_config.surrounding.right_adc_lower_threshold}*{SurroundingWeights.BEHIND_OBJECT}"
            )
        ]
        ctx = {"tag_d": tag_detector, "q_tb": query_table}
        if app_config.logger.log_level == "DEBUG":
            source.append('_logger.debug(f"Surrounding Code: {ret}")')
            ctx["_logger"] = _logger

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
            judging_source=source,
            return_type=int,
            extra_context=ctx,
            return_raw=False,
            function_name="surrounding_breaker_with_cam",
        )
        return surr_full_breaker

    @staticmethod
    @lru_cache(maxsize=None)
    def make_nocam_surr_breaker(
        app_config: APPConfig, run_config: RunConfig, query_table: Dict[Tuple[int, bool], int], tag_group: TagGroup
    ):
        source = [
            (
                f"ret=q_tb.get(({tag_group.default_tag}, bool(s0 or s1 or s4>{run_config.surrounding.front_adc_lower_threshold})))"
                f"+(s5>{run_config.surrounding.left_adc_lower_threshold})*{SurroundingWeights.LEFT_OBJECT}"
                f"+(s6>{run_config.surrounding.right_adc_lower_threshold})*{SurroundingWeights.RIGHT_OBJECT}"
                f"+s2 or s3 or s7>{run_config.surrounding.right_adc_lower_threshold}*{SurroundingWeights.BEHIND_OBJECT}"
            )
        ]
        ctx = {"q_tb": query_table}

        if app_config.logger.log_level == "DEBUG":
            source.append('_logger.debug(f"Surrounding Code: {ret}")')
            ctx["_logger"] = _logger
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
            judging_source=source,
            return_type=int,
            extra_context=ctx,
            return_raw=False,
            function_name="surrounding_breaker_without_cam",
        )
        return surr_full_breaker
