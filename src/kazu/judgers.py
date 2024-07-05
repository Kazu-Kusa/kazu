from functools import lru_cache
from typing import Callable, Tuple

from mentabotix import SamplerUsage

from kazu.config import APPConfig, RunConfig, ContextVar, TagGroup
from kazu.constant import EdgeWeights, Attitude, ScanWeights, StageWeight, SurroundingWeights, FenceWeights
from kazu.hardwares import controller, menta, SamplerIndexes, tag_detector
from kazu.logger import _logger
from kazu.static import make_query_table


class Breakers:

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_rear_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect edge at the rear direction,

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.
        """
        # Retrieve lower and upper threshold sequences
        lt_seq = run_config.edge.lower_threshold
        ut_seq = run_config.edge.upper_threshold

        # Constructs and returns an inlined function to judge the rear brake status
        # The function leverages the ADC for all channels and focuses on specific sensor indices
        # The judgment logic is based on whether sensor data exceeds set thresholds
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
            judging_source=f"ret= ({lt_seq[1]}>s0 or s0 > {ut_seq[1]}) or ({lt_seq[2]}>s1 or s1 > {ut_seq[2]})",
            return_type=bool,
            return_raw=False,
            function_name="std_edge_rear_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_front_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect edge at the front direction,

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.
        """
        lt_seq = run_config.edge.lower_threshold
        ut_seq = run_config.edge.upper_threshold
        activate = run_config.stage.gray_io_off_stage_case_value
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
            judging_source=f"ret=s0=={activate} "
            f"or s1=={activate} "
            f"or ({lt_seq[0]}>s2 or s2 > {ut_seq[0]}) "
            f"or ({lt_seq[-1]}>s3 or s3 > {ut_seq[-1]})",
            return_type=bool,
            return_raw=False,
            function_name="std_edge_front_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_full_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Constructs a standard function to detect edge at both front and rear directions,

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.
        """
        lt_seq = run_config.edge.lower_threshold
        ut_seq = run_config.edge.upper_threshold
        if run_config.edge.use_gray_io:
            _logger.info("Using gray io for edge full detection")
            fl_lt, rl_lt, rr_lt, fr_lt = lt_seq
            fl_ut, rl_ut, rr_ut, fr_ut = ut_seq
            fl_wt, rl_wt, rr_wt, fr_wt = EdgeWeights.export_std_weight_seq()

            fl_id, rl_id, rr_id, fr_id = list(range(4))

            activate = run_config.stage.gray_io_off_stage_case_value
            source = [
                f"ret=sum(["
                f"(s{fl_id}<{fl_lt} or s{fl_id}>{fl_ut} or s4=={activate} )*{fl_wt}, "
                f"(s{rl_id}<{rl_lt} or s{rl_id}>{rl_ut})*{rl_wt}, "
                f"(s{rr_id}<{rr_lt} or s{rr_id}>{rr_ut})*{rr_wt}, "
                f"(s{fr_id}<{fr_lt} or s{fr_id}>{fr_ut} or s5=={activate})*{fr_wt}"
                f"])"
            ]
        else:
            source = [
                "ret=sum(["
                + ",".join(
                    f"({lt}>s{s_id} or {ut}<s{s_id})*{wt}"
                    for s_id, lt, ut, wt in zip(range(4), lt_seq, ut_seq, EdgeWeights.export_std_weight_seq())
                )
                + "])"
            ]
        ctx = {}
        if app_config.debug.log_level == "DEBUG":

            ctx["_logger"] = _logger
            source.append('_logger.debug(f"Edge Code: {ret}")')

        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.edge_fl_index,  # s0
                        app_config.sensor.edge_rl_index,  # s1
                        app_config.sensor.edge_rr_index,  # s2
                        app_config.sensor.edge_fr_index,  # s3
                    ],
                )
            ]
            + (
                [
                    SamplerUsage(
                        used_sampler_index=SamplerIndexes.io_all,
                        required_data_indexes=[
                            app_config.sensor.gray_io_left_index,  # s4
                            app_config.sensor.gray_io_right_index,  # s5
                        ],
                    )
                ]
                if run_config.edge.use_gray_io
                else []
            ),
            judging_source=source,
            extra_context=ctx,
            return_type=int,
            return_raw=False,
            function_name="std_edge_full_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_turn_to_front_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect the timing to stop the turning action, impl by checking the front obstacles

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.
        """
        activate = run_config.surrounding.io_encounter_object_value
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
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
            judging_source=f"ret=bool(s0=={activate} "
            f"or s1=={activate} "
            f"or s2>{run_config.surrounding.front_adc_lower_threshold})",
            return_type=bool,
            return_raw=False,
            function_name="std_turn_to_front_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_atk_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect the timing to stop the atk action,
        impl by checking both the front obstacles and the edge of the stage

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.

        Notes:
            edge detection uses only the gray_io on the shovel
        """
        off_stage_activate = run_config.stage.gray_io_off_stage_case_value
        surr_obj_activate = run_config.surrounding.io_encounter_object_value

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
            judging_source=f"ret=bool(s0=={off_stage_activate} or s1=={off_stage_activate}  "  # use gray scaler, indicating the edge is encountered
            f"or all( (s2!={surr_obj_activate} , s3!={surr_obj_activate} , s4<{run_config.surrounding.atk_break_front_lower_threshold})))",
            # indicating front is empty
            return_type=bool,
            return_raw=False,
            function_name="std_atk_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_atk_breaker_with_edge_sensors(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect the timing to stop the atk action,
        impl by checking both the front obstacles and the edge of the stage

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.

        Notes:
            edge detection uses both the gray_io on the shovel and the edge sensors on the shovel arm
        """
        off_stage_activate = run_config.stage.gray_io_off_stage_case_value
        surr_obj_activate = run_config.surrounding.io_encounter_object_value

        fl_lower_threshold = run_config.edge.lower_threshold[0]
        fr_lower_threshold = run_config.edge.lower_threshold[-1]

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
                    required_data_indexes=[
                        app_config.sensor.front_adc_index,  # s4
                        app_config.sensor.edge_fl_index,  # s5
                        app_config.sensor.edge_fr_index,  # s6
                    ],
                ),
            ],
            judging_source=f"ret=bool(s0=={off_stage_activate} or s1=={off_stage_activate}  "  # use gray scaler, indicating the edge is encountered
            f"or all( (s2!={surr_obj_activate} , s3!={surr_obj_activate} , s4<{run_config.surrounding.atk_break_front_lower_threshold}))"  # indicating front is empty
            f"or s5<{fl_lower_threshold} or s6<{fr_lower_threshold})",  # long scan using edge sensors
            return_type=bool,
            return_raw=False,
            function_name="atk_breaker_with_edge_sensors",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_stage_align_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect the timing to stop the turning action,
        impl by checking obstacles in both front and rear

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
            An inlined function that assesses the braking state of the rear wheels based on sensor data.

        Notes:
            uses only the front and rear io sensors only
        """
        activate = run_config.fence.io_encounter_fence_value

        return menta.construct_inlined_function(
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
            ],
            judging_source=f"ret=(s0=={activate} and s1=={activate}) and (s2!={activate} and s3!={activate})",
            return_type=bool,
            return_raw=False,
            function_name="stage_align_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_stage_align_breaker_mpu(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect the timing to stop the turning action,
        impl by checking obstacles in the front and checking the mpu angle

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
            An inlined function that assesses the braking state of the rear wheels based on sensor data.

        Notes:
            uses both front sensors and the mpu built in the raspi
        """
        invalid_lower_bound, invalid_upper_bound = (
            run_config.fence.max_yaw_tolerance,
            90 - run_config.fence.max_yaw_tolerance,
        )
        activate = run_config.fence.io_encounter_fence_value
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.atti_all,
                    required_data_indexes=[
                        Attitude.yaw,  # s0
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        app_config.sensor.fl_io_index,  # s1
                        app_config.sensor.fr_io_index,  # s2
                    ],
                ),
            ],
            judging_source=f"ret=bool(not ({invalid_lower_bound}<abs(s0)//90<{invalid_upper_bound}) "
            f"and (s1=={activate} and s2=={activate}))",
            return_type=bool,
            return_raw=False,
            function_name="stage_align_breaker_mpu",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_fence_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Divide control flow to corresponding handle.
        Args:
            app_config:
            run_config:

        Returns:

        """
        conf = run_config.fence
        activate = conf.io_encounter_fence_value
        source = [
            f"ret={FenceWeights.Front}*(s0>{conf.front_adc_lower_threshold} or s4 == {activate} or s5 == {activate})"
            f"+{FenceWeights.Rear}*(s1>{conf.rear_adc_lower_threshold} or s6 == {activate} or s7 == {activate})"
            f"+{FenceWeights.Left}*(s2>{conf.left_adc_lower_threshold})"
            f"+{FenceWeights.Rear}*(s3>{conf.right_adc_lower_threshold})"
        ]

        ctx = {}
        if app_config.debug.log_level == "DEBUG":
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
    def make_lr_sides_blocked_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a function to judge if the left and right sides are blocked based on sensor data.

        Args:
            app_config: APPConfig object containing sensor configurations.
            run_config: RunConfig object containing fence threshold values.

        Returns:
            A callable function that evaluates if the left and right sides are blocked.
        """
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[app_config.sensor.left_adc_index, app_config.sensor.right_adc_index],
                )
            ],
            judging_source=f"ret=(s0>{run_config.fence.left_adc_lower_threshold} "
            f"and s1>{run_config.fence.right_adc_lower_threshold})",
            return_type=bool,
            return_raw=False,
            function_name="lr_sides_blocked_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_align_direction_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Generates a function that determines whether the alignment of a direction has breached the specified yaw tolerance.

        This function is designed to be used within a system that monitors and controls the directional alignment,
        typically in applications involving autonomous vehicles, drones, or any system requiring precise orientation control.
        It utilizes an LRU (Least Recently Used) cache decorator to optimize performance by storing previously computed results
        for reuse, which is particularly beneficial for repetitive checks with static or slowly changing configurations.

        Args:
            app_config (APPConfig): Configuration object containing global application settings.
            run_config (RunConfig): Configuration object detailing runtime parameters, including yaw tolerance.

        Returns:
        Callable[[Attitude], bool]: A function that accepts an `Attitude` object (which must include at least the yaw attribute)
        and returns a boolean indicating whether the current yaw deviation exceeds the tolerances defined in `run_config`.

        The generated function internally calculates the absolute difference between the yaw angle and the nearest multiple of 90 degrees,
        then compares this difference against the lower and upper bounds defined by `run_config.fence.max_yaw_tolerance`.
        If the difference falls outside these bounds, the function returns `True`, signifying a break in the desired alignment direction.


        """
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
    def make_std_scan_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Generates a function that acts as a breaker for standard scanning.

        Args:
            app_config (APPConfig): The application configuration.
            run_config (RunConfig): The run configuration.

        Returns:
            Callable[[], int]: A function that takes no arguments and returns an integer.

        This function uses the `lru_cache` decorator to cache the result of the function.
        It also registers a context getter for the ADC pack.
        The function constructs a source code string based on the provided configuration.
        If the debug log level is set to "DEBUG", an additional line of code is added to log the scan code.
        Finally, the function constructs and returns an inlined function using the `menta.construct_inlined_function` method.
        The inlined function has two usages: one for the ADC sampler and one for the IO sampler.
        The judging source is constructed based on the provided configuration.
        The function name is set to "std_scan_breaker".
        """
        adc_pack_getter: Callable[[], Tuple] = controller.register_context_getter(ContextVar.recorded_pack.name)
        conf = run_config.search.scan_move
        source = [  # activate once the deviation surpluses the tolerance
            "pack=adc_pack_getter()",
            f"front=pack[{app_config.sensor.front_adc_index}]",
            f"rear=pack[{app_config.sensor.rb_adc_index}]",
            f"left=pack[{app_config.sensor.left_adc_index}]",
            f"right=pack[{app_config.sensor.right_adc_index}]",
            f"ret={ScanWeights.Front}*(s0-front>{conf.front_max_tolerance} or s4 == {conf.io_encounter_object_value} or s5 == {conf.io_encounter_object_value})"
            f"+{ScanWeights.Rear}*(s1-rear>{conf.rear_max_tolerance} or s6 == {conf.io_encounter_object_value} or s7 == {conf.io_encounter_object_value})"
            f"+{ScanWeights.Left}*(s2-left>{conf.left_max_tolerance})"
            f"+{ScanWeights.Rear}*(s3-right>{conf.right_max_tolerance})",
        ]
        ctx = {"adc_pack_getter": adc_pack_getter}

        if app_config.debug.log_level == "DEBUG":
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
    def make_std_stage_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Creates a function that determines the stage break condition, dividing the control flow to reboot/on stage/off stage


        This function is designed to return a callable object that, when called, judges whether the current stage should transition
        based on the values of gray-scale ADC and reboot button, and returns the corresponding stage transition score.

        Args:
            app_config (APPCONfig): Application configuration object, containing configuration information such as sensors.
            run_config (RunConfig): Runtime configuration object, containing configuration information such as the current stage.

        Returns:
            Callable[[], int]: A callable object that takes no arguments and returns an integer value representing the stage transition score.
        """

        # Obtain the current stage configuration from the runtime configuration
        conf = run_config.stage
        # Construct an inline function that judges stage transition conditions using the menta library
        # The judgment logic includes the use of gray-scale ADC values and the state of the reboot button
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
            f"+{StageWeight.REBOOT}*(s1=={run_config.boot.button_io_activate_case_value})",
            return_type=int,
            return_raw=False,
            function_name="std_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_always_on_stage_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Creates a function that determines the stage break condition, always considering the stage to be on.

        Args:
            app_config (APPConfig): Configuration object for the application, holding sensor setup details.
            run_config (RunConfig): Configuration object for the current runtime context, including reboot settings.

        Returns:
            Callable[[], int]: A callable function that, when invoked, returns an integer indicating the stage outcome.

        This method utilizes the `menta.construct_inlined_function` to dynamically construct a function
        which evaluates the stage based on sensor inputs (ADC for gray data, and IO for reboot button status).
        The constructed function follows a predefined logic to decide between stage continuation or a reboot scenario.
        """
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
                f"+{StageWeight.REBOOT}*(s1=={run_config.boot.button_io_activate_case_value})",
                "ret=0",
            ],
            return_type=int,
            return_raw=False,
            function_name="always_on_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_always_off_stage_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Creates a function that determines the stage break condition, always considering the stage to be off.

        Args:
            app_config (APPConfig): Configuration object for the application, holding sensor setup details.
            run_config (RunConfig): Configuration object for the current runtime context, including reboot settings.

        Returns:
            Callable[[], int]: A callable function that, when invoked, returns an integer indicating the stage outcome.

        This method utilizes the `menta.construct_inlined_function` to dynamically construct a function
        which evaluates the stage based on sensor inputs (ADC for gray data, and IO for reboot button status).
        The constructed function follows a predefined logic to decide between stage continuation or a reboot scenario.
        """

        # Construct an inlined function with specific sampler usages and decision logic:
        # - Uses ADC sampler to read gray data (s0).
        # - Monitors IO sampler for reboot button state (s1).
        # The decision logic weighs stages based on sensor inputs, designed to consistently indicate an 'off' stage.
        return menta.construct_inlined_function(
            usages=[
                # ADC sampler setup to fetch gray ADC data.
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        app_config.sensor.gray_adc_index,  # s0
                    ],
                ),
                # IO sampler setup to monitor the reboot button.
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        app_config.sensor.reboot_button_index,  # s1
                    ],
                ),
            ],
            judging_source=[
                # Placeholder to mimic processing overhead (not operationally functional).
                "temp_data=s0",
                # Decision formula considering stage weight and reboot condition based on button state.
                f"ret={StageWeight.STAGE}*(True)"
                f"+{StageWeight.REBOOT}*(s1=={run_config.boot.button_io_activate_case_value})",
            ],
            return_type=int,  # Specifies the return type of the generated function as integer.
            return_raw=False,  # Indicates not to return raw data directly from samplers.
            function_name="always_off_stage_breaker",  # Names the generated function.
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_surr_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        创建一个用于处理周边环境感知的闭包函数。

        根据应用和运行配置，以及团队颜色，配置和构建用于判断周围环境状况的逻辑。
        当使用摄像头时，该函数会考虑视觉标签的信息；
        当不使用摄像头时，它将基于默认标签进行判断。

        参数:
        app_config: 应用配置对象，包含团队颜色和是否使用摄像头等设置。
        run_config: 运行配置对象，包含周边环境感知的配置信息。

        返回:
        一个闭包函数，用于根据传感器数据判断周围环境状况。
        """
        # 根据团队颜色创建标签组
        tag_group: TagGroup = TagGroup(team_color=app_config.vision.team_color)
        # 构建查询表格，用于快速查找标签信息
        query_table = make_query_table(tag_group)
        # 获取运行配置中的周边配置信息
        conf = run_config.surrounding
        # 从运行配置中获取IO相遇对象的值
        activate: int = conf.io_encounter_object_value

        if app_config.vision.use_camera:
            # 使用摄像头时，定义标签来源为检测到的标签ID
            get_id_source: str = "tag_d.tag_id"
            # 设置上下文，包含标签检测器和查询表格
            ctx = {"tag_d": tag_detector, "q_tb": query_table}
        else:
            # 不使用摄像头时，定义标签来源为默认标签
            get_id_source: str = f"{tag_group.default_tag}"
            # 设置上下文，只包含查询表格
            ctx = {"q_tb": query_table}

        # 构建判断周围环境状况的逻辑表达式
        source = [
            (
                f"ret=q_tb.get(({get_id_source}, bool(s0=={activate} or s1=={activate} or s4>{conf.front_adc_lower_threshold})))"
                f"+(s5>{conf.left_adc_lower_threshold})*{SurroundingWeights.LEFT_OBJECT}"
                f"+(s6>{conf.right_adc_lower_threshold})*{SurroundingWeights.RIGHT_OBJECT}"
                f"+(s2=={activate} or s3=={activate} or s7>{conf.back_adc_lower_threshold})*{SurroundingWeights.BEHIND_OBJECT}"
            )
        ]
        # 如果处于调试模式，添加日志记录逻辑
        if app_config.debug.log_level == "DEBUG":
            source.append('_logger.debug(f"Surrounding Code: {ret}")')
            ctx["_logger"] = _logger

        # 使用Menta工具构建闭包函数，用于判断周围环境状况
        # 函数将根据传感器数据（IO和ADC）返回一个综合评估值
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
    def make_reboot_button_pressed_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:
        """
        Generates a function that acts as a breaker for the reboot button pressed.

        Args:
            app_config (APPConfig): The application configuration.
            run_config (RunConfig): The run configuration.

        Returns:
            Callable[[], int]: A function that takes no arguments and returns an integer.

        This function uses the `lru_cache` decorator to cache the result of the function.
        It also registers a context getter for the ADC pack.
        The function constructs a source code string based on the provided configuration.
        If the debug log level is set to "DEBUG", an additional line of code is added to log the scan code.
        Finally, the function constructs and returns an inlined function using the `menta.construct_inlined_function` method.
        The inlined function has two usages: one for the ADC sampler and one for the IO sampler.
        The judging source is constructed based on the provided configuration.
        The function name is set to "reboot_button_pressed_breaker".
        """

        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_level_idx,
                    required_data_indexes=[
                        app_config.sensor.reboot_button_index,  # s0
                    ],
                ),
            ],
            judging_source=[
                f"ret=s0=={run_config.boot.button_io_activate_case_value}",
            ],
            return_type=int,
            return_raw=False,
            function_name="reboot_button_pressed_breaker",
        )
