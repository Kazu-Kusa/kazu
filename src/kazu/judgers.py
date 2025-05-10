from functools import lru_cache
from math import cos, radians
from typing import Callable, Tuple

from mentabotix import SamplerUsage

from kazu.config import APPConfig, RunConfig, ContextVar, TagGroup
from kazu.constant import EdgeWeights, Attitude, ScanWeights, StageWeight, SurroundingWeights, FenceWeights, Axis
from kazu.hardwares import controller, menta, SamplerIndexes, tag_detector
from kazu.logger import _logger
from kazu.static import make_query_table


class Breakers:

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_rear_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:
        """
        Constructs a standard function to detect edge at the rear direction,    #构造一个标准函数，用于检测后方方向的边缘

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.    #应用程序配置对象，包含传感器索引和其他设置
        - run_config: Configuration object for the runtime, including threshold values.     #运行时配置对象，包括阈值值

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.    #一个内联函数，根据传感器数据评估后轮的制动状态
        """
        # Retrieve lower and upper threshold sequences  # 获取下限和上限阈值序列
        lt_seq = run_config.edge.lower_threshold    #获取下限阈值序列
        ut_seq = run_config.edge.upper_threshold    #获取上限阈值序列

        # Constructs and returns an inlined function to judge the rear brake status     #构造并返回一个内联函数来判断后制动状态
        # The function leverages the ADC for all channels and focuses on specific sensor indices    # 该函数利用所有通道的ADC，并关注特定传感器索引  
        # The judgment logic is based on whether sensor data exceeds set thresholds     # 判断逻辑基于传感器数据是否超过设定阈值
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
            judging_source=f"ret= ({lt_seq[1]}>s0 or s0 > {ut_seq[1]}) or ({lt_seq[2]}>s1 or s1 > {ut_seq[2]})",    # 判断逻辑
            return_type=bool,   #返回类型
            return_raw=False,   #返回原始值
            function_name="std_edge_rear_breaker",  #函数名称
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_front_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:    #构造一个标准函数，用于检测前方方向的边缘
        """
        Constructs a standard function to detect edge at the front direction,   #构造一个标准函数，用于检测前方方向的边缘

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.    #应用程序配置对象，包含传感器索引和其他设置
        - run_config: Configuration object for the runtime, including threshold values.     #运行时配置对象，包括阈值值

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.    #一个内联函数，根据传感器数据评估后轮的制动状态
        """
        lt_seq = run_config.edge.lower_threshold    #获取下限阈值序列
        ut_seq = run_config.edge.upper_threshold    #获取上限阈值序列
        activate = run_config.stage.gray_io_off_stage_case_value    #获取灰度IO关闭时的阶段值
        return menta.construct_inlined_function(    #构造一个内联函数
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
            judging_source=f"ret=s0=={activate} "   #判断逻辑
            f"or s1=={activate} "
            f"or ({lt_seq[0]}>s2 or s2 > {ut_seq[0]}) "
            f"or ({lt_seq[-1]}>s3 or s3 > {ut_seq[-1]})",
            return_type=bool,
            return_raw=False,
            function_name="std_edge_front_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_edge_full_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:  #构造一个标准函数，用于检测前后方向的边缘
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
    def make_std_turn_to_front_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:     #构造一个标准函数，用于检测前后方向的边缘
        """
        Constructs a standard function to detect the timing to stop the turning action, impl by checking the front obstacles

        Parameters:
        - app_config: Configuration object for the application, holding sensor indices among other settings.
        - run_config: Configuration object for the runtime, including threshold values.

        Returns:
        An inlined function that assesses the braking state of the rear wheels based on sensor data.
        """
        activate = run_config.surrounding.io_encounter_object_value
        if run_config.surrounding.turn_to_front_use_front_sensor:
            _logger.info("Using front sensor for turn to front detection")
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
        else:
            return menta.construct_inlined_function(
                usages=[
                    SamplerUsage(
                        used_sampler_index=SamplerIndexes.io_all,
                        required_data_indexes=[
                            app_config.sensor.gray_io_left_index,  # s0
                            app_config.sensor.gray_io_right_index,  # s1
                        ],
                    ),
                ],
                judging_source=f"ret=s0=={activate} or s1=={activate}",
                return_type=bool,
                return_raw=False,
                function_name="std_turn_to_front_breaker",
            )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_atk_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:   #构造一个标准函数，用于检测前后方向的边缘
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
    def make_atk_breaker_with_edge_sensors(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:     #构造一个标准函数，用于检测前后方向的边缘
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
    def make_std_stage_align_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:   #构造一个标准函数，用于检测前后方向的边缘
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
    def make_stage_align_breaker_mpu(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:   #构造一个标准函数，用于检测前后方向的边缘
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
    def make_std_fence_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:  #构造一个标准函数，用于检测前后方向的边缘
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
    def make_align_direction_breaker_mpu(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:   #构造一个MPU方向判断函数
        """
        Generates a function that determines whether the alignment of a direction has breached the specified yaw tolerance.     #生成一个函数，用于判断方向的对齐是否超过了指定的偏航角容差。

        This function is designed to be used within a system that monitors and controls the directional alignment,  #这个函数被设计用于监控系统，以监控和控制方向的对齐。
        typically in applications involving autonomous vehicles, drones, or any system requiring precise orientation control.   #通常在自动驾驶汽车、无人机或任何需要精确控制方向的系统中使用。
        It utilizes an LRU (Least Recently Used) cache decorator to optimize performance by storing previously computed results     #它使用LRU（最近最少使用）缓存装饰器来通过存储先前计算的结果来优化性能。
        for reuse, which is particularly beneficial for repetitive checks with static or slowly changing configurations.    #这对于重复检查具有静态或缓慢变化的配置特别有益。

        Args:
            app_config (APPConfig): Configuration object containing global application settings.    #包含全局应用程序设置的配置对象。
            run_config (RunConfig): Configuration object detailing runtime parameters, including yaw tolerance.     #详细说明运行时参数的配置对象，包括偏航容差。

        Returns:
        Callable[[Attitude], bool]: A function that accepts an `Attitude` object (which must include at least the yaw attribute)    #接受包含至少yaw属性的Attitude对象的函数
        and returns a boolean indicating whether the current yaw deviation exceeds the tolerances defined in `run_config`.  #返回一个布尔值，指示当前的偏航偏差是否超过了在`run_config`中定义的容差。

        The generated function internally calculates the absolute difference between the yaw angle and the nearest multiple of 90 degrees,  #生成的函数内部计算偏航角与90度的最近倍数的绝对差值，
        then compares this difference against the lower and upper bounds defined by `run_config.fence.max_yaw_tolerance`.   #然后将其与`run_config.fence.max_yaw_tolerance`定义的下限和上限进行比较。
        If the difference falls outside these bounds, the function returns `True`, signifying a break in the desired alignment direction.   #如果差值超出这些范围，函数返回`True`，表示对所需对齐方向的破坏。


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
    def make_std_align_direction_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:   #构造一个标准方向判断函数
        """
        Creates a function that checks if the alignment direction is correct based on the sensor and run configurations.    #创建一个基于传感器和运行配置检查对齐方向是否正确的函数。

        Parameters:
        - app_config (APPConfig): The application configuration object, containing sensor indices and other settings.    #应用程序配置对象，包含传感器索引和其他设置。
        - run_config (RunConfig): The runtime configuration object, including threshold values.     #运行时配置对象，包括阈值值。

        Returns:
        - Callable[[], bool]: A function that takes no arguments and returns a boolean indicating if the alignment direction is correct.    #一个不接受参数并返回一个布尔值，指示对齐方向是否正确的函数。

        Notes:
        - The function uses the `construct_inlined_function` method from the `menta` module to create an inlined function.   #函数使用`menta`模块中的`construct_inlined_function`方法创建内联函数。
        - The function uses the `usages` parameter to specify the required sampler usage.    #函数使用`usages`参数指定所需的采样器使用情况。
        - The function uses the `judging_source` parameter to specify the logic for checking the alignment direction.        #函数使用`judging_source`参数指定检查对齐方向的逻辑。
        - The function uses the `return_type` parameter to specify the return type of the function. #函数使用`return_type`参数指定函数的返回类型。
        - The function uses the `function_name` parameter to specify the name of the function.      #函数使用`function_name`参数指定函数的名称。
        """
        conf = app_config.sensor
        fconf = run_config.fence
        activate = fconf.io_encounter_fence_value
        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[
                        conf.front_adc_index,  # s0
                        conf.rb_adc_index,  # s1
                        conf.left_adc_index,  # s2
                        conf.right_adc_index,  # s3
                    ],
                ),
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.io_all,
                    required_data_indexes=[
                        conf.fl_io_index,  # s4
                        conf.fr_io_index,  # s5
                        conf.rl_io_index,  # s6
                        conf.rr_io_index,  # s7
                    ],
                ),
            ],
            judging_source=(
                (
                    [
                        f"code=(s0>{fconf.front_adc_lower_threshold} or (s4==s5=={activate})) "
                        f"+ (s1>{fconf.rear_adc_lower_threshold} or (s6==s7=={activate})) "
                        f"+ (s2>{fconf.left_adc_lower_threshold})"
                        f"+ (s3>{fconf.right_adc_lower_threshold})",
                        "_logger.debug(f'AlignD: {code}')",
                        "ret=code==2",
                    ]
                )
                if app_config.debug.log_level == "DEBUG"
                else (
                    f"ret=((s0>{fconf.front_adc_lower_threshold} or (s4==s5=={activate})) "
                    f"+ (s1>{fconf.rear_adc_lower_threshold} or (s6==s7=={activate})) "
                    f"+ (s2>{fconf.left_adc_lower_threshold})"
                    f"+ (s3>{fconf.right_adc_lower_threshold})==2)"
                )
            ),
            return_type=bool,
            extra_context={"_logger": _logger},
            function_name="std_align_direction_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_std_scan_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:    #构造一个标准扫描判断函数
        """
        Generates a function that acts as a breaker for standard scanning.  #生成一个作为标准扫描断路器的函数。

        Args:
            app_config (APPConfig): The application configuration.  #应用程序配置。
            run_config (RunConfig): The run configuration.  #运行配置。

        Returns: 
            Callable[[], int]: A function that takes no arguments and returns an integer.   #一个不接受参数并返回整数的函数。

        This function uses the `lru_cache` decorator to cache the result of the function.   #该函数使用`lru_cache`装饰器来缓存函数的结果。
        It also registers a context getter for the ADC pack.    #它还注册了一个ADC包的上下文获取器。
        The function constructs a source code string based on the provided configuration.    #函数根据提供的配置构建一个源代码字符串。
        If the debug log level is set to "DEBUG", an additional line of code is added to log the scan code.     #如果调试日志级别设置为"DEBUG"，则添加一行代码以记录扫描代码。
        Finally, the function constructs and returns an inlined function using the `menta.construct_inlined_function` method.    #最后，函数使用`menta.construct_inlined_function`方法构造并返回一个内联函数。
        The inlined function has two usages: one for the ADC sampler and one for the IO sampler.    #内联函数有两个用法：一个用于ADC采样器，一个用于IO采样器。
        The judging source is constructed based on the provided configuration.  #判断源根据提供的配置构建。
        The function name is set to "std_scan_breaker".     #函数名称设置为"std_scan_breaker"。
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
    def make_std_stage_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:  #构造一个标准阶段判断函数
        """
        Creates a function that determines the stage break condition, dividing the control flow to reboot/on stage/off stage    #创建一个函数，确定阶段断开条件，将控制流分为重启/开启阶段/关闭阶段。


        This function is designed to return a callable object that, when called, judges whether the current stage should transition     #该函数旨在返回一个可调用对象，当调用时，判断当前阶段是否应该过渡
        based on the values of gray-scale ADC and reboot button, and returns the corresponding stage transition score.  #根据灰度ADC和重启按钮的值判断当前阶段是否应该过渡，并返回相应的阶段过渡分数。

        Args:
            app_config (APPCONfig): Application configuration object, containing configuration information such as sensors.     #应用程序配置对象，包含诸如传感器之类的配置信息。
            run_config (RunConfig): Runtime configuration object, containing configuration information such as the current stage.   #运行时配置对象，包含当前阶段之类的配置信息。

        Returns:
            Callable[[], int]: A callable object that takes no arguments and returns an integer value representing the stage transition score.  #一个可调用对象，不接受任何参数，并返回一个整数值，表示阶段过渡分数。
        """

        # Obtain the current stage configuration from the runtime configuration     #从运行时配置中获取当前阶段配置
        conf = run_config.stage
        # Construct an inline function that judges stage transition conditions using the menta library  #使用menta库构建一个内联函数，用于判断阶段过渡条件
        # The judgment logic includes the use of gray-scale ADC values and the state of the reboot button   # 判断逻辑包括使用灰度ADC值和重启按钮的状态
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
            judging_source=
            f"ret={StageWeight.STAGE}*(s0<={conf.gray_adc_off_stage_upper_threshold})"
            f"+{StageWeight.UNCLEAR}*({conf.gray_adc_off_stage_upper_threshold}<s0<{conf.gray_adc_on_stage_lower_threshold})"
            f"+{StageWeight.REBOOT}*(s1=={run_config.boot.button_io_activate_case_value})",
            return_type=int,
            return_raw=False,
            function_name="std_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_always_on_stage_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:    #构造一个始终开启阶段判断函数
        """
        Creates a function that determines the stage break condition, always considering the stage to be on.    #创建一个函数，始终认为阶段是开启的，确定阶段断开条件。

        Args:
            app_config (APPConfig): Configuration object for the application, holding sensor setup details.     #应用程序配置对象，包含传感器设置详细信息。
            run_config (RunConfig): Configuration object for the current runtime context, including reboot settings.    #当前运行时上下文的配置对象，包括重启设置。

        Returns:
            Callable[[], int]: A callable function that, when invoked, returns an integer indicating the stage outcome.     #一个可调用函数，当被调用时，返回一个整数，指示阶段结果。

        This method utilizes the `menta.construct_inlined_function` to dynamically construct a function     #该方法利用`menta.construct_inlined_function`动态构造一个函数
        which evaluates the stage based on sensor inputs (ADC for gray data, and IO for reboot button status).  #该函数根据传感器输入（灰度数据的ADC和重启按钮状态的IO）评估阶段。
        The constructed function follows a predefined logic to decide between stage continuation or a reboot scenario.  #构造的函数遵循预定义的逻辑，以决定阶段是否继续或重启场景。
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
                f"true_ret={StageWeight.STAGE}*(s0<{conf.gray_adc_off_stage_upper_threshold})"
                f"+{StageWeight.REBOOT}*(s1=={run_config.boot.button_io_activate_case_value})",
                "ret=0",
            ],
            return_type=int,
            return_raw=False,
            function_name="always_on_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_always_off_stage_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:    #构造一个始终关闭阶段判断函数
        """
        Creates a function that determines the stage break condition, always considering the stage to be off.    #创建一个函数，始终认为阶段是关闭的，确定阶段断开条件。

        Args:
            app_config (APPConfig): Configuration object for the application, holding sensor setup details.     #应用程序配置对象，包含传感器设置详细信息。
            run_config (RunConfig): Configuration object for the current runtime context, including reboot settings.    #当前运行时上下文的配置对象，包括重启设置。

        Returns:
            Callable[[], int]: A callable function that, when invoked, returns an integer indicating the stage outcome.     #一个可调用函数，当被调用时，返回一个整数，指示阶段结果。

        This method utilizes the `menta.construct_inlined_function` to dynamically construct a function     #该方法利用`menta.construct_inlined_function`动态构造一个函数
        which evaluates the stage based on sensor inputs (ADC for gray data, and IO for reboot button status).  #该函数根据传感器输入（灰度数据的ADC和重启按钮状态的IO）评估阶段。
        The constructed function follows a predefined logic to decide between stage continuation or a reboot scenario.  #构造的函数遵循预定义的逻辑，以决定阶段是否继续或重启场景。
        """

        # Construct an inlined function with specific sampler usages and decision logic:    # 构造一个内联函数，具有特定的采样器用法和决策逻辑：
        # - Uses ADC sampler to read gray data (s0).
        # - Monitors IO sampler for reboot button state (s1).
        # The decision logic weighs stages based on sensor inputs, designed to consistently indicate an 'off' stage.    # 决策逻辑根据传感器输入对阶段进行加权，旨在始终指示“关闭”阶段。
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
    def make_surr_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], int]:    #创建一个用于处理周边环境感知的闭包函数
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
    def make_reboot_button_pressed_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:     #创建一个用于处理重启按钮按下的闭包函数
        """
        Generates a function that acts as a breaker for the reboot button pressed.  #生成一个作为重启按钮按下断点的函数。

        Args:
            app_config (APPConfig): The application configuration.  #应用程序配置。
            run_config (RunConfig): The run configuration.  #运行配置。

        Returns:
            Callable[[], int]: A function that takes no arguments and returns an integer.   #一个不接受参数并返回整数的函数。

        This function uses the `lru_cache` decorator to cache the result of the function.   #该函数使用lru_cache装饰器来缓存函数的结果。
        It also registers a context getter for the ADC pack.    #它还为ADC包注册了一个上下文获取器。
        The function constructs a source code string based on the provided configuration.    #根据提供的配置构建源代码字符串。
        If the debug log level is set to "DEBUG", an additional line of code is added to log the scan code.     #如果调试日志级别设置为“DEBUG”，则添加一行代码以记录扫描代码。
        Finally, the function constructs and returns an inlined function using the `menta.construct_inlined_function` method.   #最后，该函数使用“menta.construct_inlined_function”方法构建并返回一个内联函数。
        The inlined function has two usages: one for the ADC sampler and one for the IO sampler.    #内联函数有两个用法：一个用于ADC采样器，一个用于IO采样器。
        The judging source is constructed based on the provided configuration.  #判断源根据提供的配置构建。
        The function name is set to "reboot_button_pressed_breaker".    #函数名称设置为“reboot_button_pressed_breaker”。
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
            return_type=bool,
            return_raw=False,
            function_name="reboot_button_pressed_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_check_gray_adc_for_scan_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:   #创建一个用于处理灰度ADC扫描断点的闭包函数
        """
        Generates a function that acts as a breaker for the gray ADC data.  #生成一个作为灰度ADC数据的断点的函数。

        Args:
            app_config (APPConfig): The application configuration.  #应用程序配置。
            run_config (RunConfig): The run configuration.  #运行配置。

        Returns:
            Callable[[], int]: A function that takes no arguments and returns an integer.   #一个不接受参数并返回整数的函数。

        This function uses the `lru_cache` decorator to cache the result of the function.    #该函数使用lru_cache装饰器来缓存函数的结果。
        It also registers a context getter for the ADC pack.    #它还为ADC包注册了一个上下文获取器。
        The function constructs a source code string based on the provided configuration.    #根据提供的配置构建源代码字符串。
        If the debug log level is set to "DEBUG", an additional line of code is added to log the scan code.     #如果调试日志级别设置为“DEBUG”，则添加一行代码以记录扫描代码。
        Finally, the function constructs and returns an inlined function using the `menta.construct_inlined_function` method.    #最后，该函数使用“menta.construct_inlined_function”方法构建并返回一个内联函数。
        The inlined function has two usages: one for the ADC sampler and one for the IO sampler.    #内联函数有两个用法：一个用于ADC采样器，一个用于IO采样器。
        The judging source is constructed based on the provided configuration.  #判断源根据提供的配置构建。
        The function name is set to "check_gray_adc_for_scan_breaker".  #函数名称设置为“check_gray_adc_for_scan_breaker”。
        """

        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all,
                    required_data_indexes=[app_config.sensor.gray_adc_index],  # s0
                ),
            ],
            judging_source=[
                f"ret=s0<{run_config.search.scan_move.gray_adc_lower_threshold}",
            ],
            return_type=bool,
            return_raw=False,
            function_name="check_gray_adc_for_scan_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_is_on_stage_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:    #创建一个用于处理舞台断点的闭包函数
        """
        Generates a function that acts as a breaker for the stage.   #生成一个作为舞台断点的函数。

        Args:
            app_config (APPConfig): The application configuration.  #应用程序配置。
            run_config (RunConfig): The run configuration.  #运行配置。

        Returns:
            Callable[[], int]: A function that takes no arguments and returns an integer.    #一个不接受参数并返回整数的函数。

        This function uses the `lru_cache` decorator to cache the result of the function.    #该函数使用lru_cache装饰器来缓存函数的结果。
        It also registers a context getter for the ADC pack.    #它还为ADC包注册了一个上下文获取器。
        The function constructs a source code string based on the provided configuration.    #根据提供的配置构建源代码字符串。
        If the debug log level is set to "DEBUG", an additional line of code is added to log the scan code.     #如果调试日志级别设置为“DEBUG”，则添加一行代码以记录扫描代码。
        Finally, the function constructs and returns an inlined function using the `menta.construct_inlined_function` method.    #最后，该函数使用“menta.construct_inlined_function”方法构建并返回一个内联函数。
        The inlined function has two usages: one for the ADC sampler and one for the IO sampler.    #内联函数有两个用法：一个用于ADC采样器，一个用于IO采样器。
        The judging source is constructed based on the provided configuration.  #判断源根据提供的配置构建。
        The function name is set to "is_on_stage_breaker".   #函数名称设置为“is_on_stage_breaker”。
        """

        return menta.construct_inlined_function(
            usages=[
                SamplerUsage(
                    used_sampler_index=SamplerIndexes.adc_all, required_data_indexes=[app_config.sensor.gray_adc_index]
                ),
            ],
            judging_source=[
                f"ret=s0<{run_config.stage.gray_adc_off_stage_upper_threshold}",
            ],
            return_type=bool,
            return_raw=False,
            function_name="is_on_stage_breaker",
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def make_back_stage_side_away_breaker(app_config: APPConfig, run_config: RunConfig) -> Callable[[], bool]:  #创建一个用于处理舞台断点的闭包函数
        """
        Generates a function that acts as a breaker for the stage.  #生成一个作为舞台断点的函数。

        Args:
            app_config (APPConfig): The application configuration.  #应用程序配置。
            run_config (RunConfig): The run configuration.  #运行配置。

        Returns:
            Callable[[], int]: A function that takes no arguments and returns an integer.   #一个不接受参数并返回整数的函数。

        This function uses the `lru_cache` decorator to cache the result of the function.    #该函数使用lru_cache装饰器来缓存函数的结果。
        It also registers a context getter for the ADC pack.    #它还为ADC包注册了一个上下文获取器。
        The function constructs a source code string based on the provided configuration.    #根据提供的配置构建源代码字符串。
        If the debug log level is set to "DEBUG", an additional line of code is added to log the scan code.     #如果调试日志级别设置为“DEBUG”，则添加一行代码以记录扫描代码。
        Finally, the function constructs and returns an inlined function using the `menta.construct_inlined_function` method.   #最后，该函数使用“menta.construct_inlined_function”方法构建并返回一个内联函数。
        The inlined function has two usages: one for the ADC sampler and one for the IO sampler.    #内联函数有两个用法：一个用于ADC采样器，一个用于IO采样器。
        The judging source is constructed based on the provided configuration.  #判断源根据提供的配置构建。
        The function name is set to "back_stage_side_away_breaker". #函数名称设置为“back_stage_side_away_breaker”。
        """

        return menta.construct_inlined_function(
            usages=[SamplerUsage(used_sampler_index=SamplerIndexes.acc_all, required_data_indexes=[Axis.z])],
            judging_source=[f"ret=s0<{cos(radians(run_config.backstage.side_away_degree_tolerance))}"],
            return_type=bool,
            return_raw=False,
            function_name="back_stage_side_away_breaker",
        )
