from enum import Enum, auto
from pathlib import Path
from typing import Tuple, List, Self, Literal, TextIO, Any, Dict, Type, Optional

from click import secho
from colorama import Fore
from pydantic import BaseModel, Field, NonNegativeInt, PositiveFloat, PositiveInt, NonNegativeFloat
from pydantic.fields import FieldInfo
from toml import dump, load
from tomlkit import document, comment, dumps, TOMLDocument, table, nl
from upic import TagDetector

from kazu.logger import _logger

DEFAULT_APP_CONFIG_PATH = f"{Path.home().as_posix()}/.kazu/config.toml"


class CounterHashable(BaseModel):

    def __hash__(self) -> int:  #__hash__ 方法返回对象的内存地址的哈希值。这个方法通常用于在哈希表中存储对象，以便快速查找。
        return id(self)

    def __eq__(self, other) -> bool:    # __eq__ 方法用于比较两个对象是否相等。在这个方法中，我们比较的是对象的内存地址，而不是对象的值。
        return id(self) == id(other)

    def __int__(self) -> int:   # __int__ 方法用于将对象转换为整数。在这个方法中，我们返回对象的内存地址的哈希值。
        return id(self)


class TagGroup(BaseModel):  # TagGroup 类继承自 BaseModel 类，用于存储标签组的信息。
    team_color: Literal["yellow", "blue"] | str     # team_color 字段是一个字符串，表示队伍的颜色。它可以是 "yellow" 或 "blue"。
    enemy_tag: Literal[1, 2] = None     # enemy_tag 字段是一个整数，表示敌人的标签。它可以是 1 或 2。
    allay_tag: Literal[1, 2] = None     # allay_tag 字段是一个整数，表示盟友的标签。它可以是 1 或 2。
    neutral_tag: Literal[0] = 0     # neutral_tag 字段是一个整数，表示中立的标签。它只能是 0。
    default_tag: int = TagDetector.Config.default_tag_id    # default_tag 字段是一个整数，表示默认的标签。它默认是 TagDetector.Config.default_tag_id。

    def __init__(self, /, **data: Any):     # __init__ 方法是类的构造函数，用于初始化对象。在这个方法中，我们调用了父类的构造函数，并设置了 enemy_tag 和 allay_tag 字段。
        super().__init__(**data)    # 调用父类的构造函数，并传入 data 参数。

        match self.team_color:  # match 语句用于匹配 team_color 字段的值，并根据不同的值设置 enemy_tag 和 allay_tag 字段。
            case "yellow":
                self.enemy_tag = 1  # 如果 team_color 是 "yellow"，则设置 enemy_tag 为 1。
                self.allay_tag = 2  # 如果 team_color 是 "yellow"，则设置 allay_tag 为 2。
            case "blue":
                self.enemy_tag = 2  # 如果 team_color 是 "blue"，则设置 enemy_tag 为 2。
                self.allay_tag = 1  # 如果 team_color 是 "blue"，则设置 allay_tag 为 1。
            case _:
                raise ValueError(f"Invalid team_color, got {self.team_color}")  # 如果 team_color 不是 "yellow" 或 "blue"，则抛出一个 ValueError 异常。
        _logger.debug(f"{Fore.MAGENTA}Team color: {self.team_color}{Fore.RESET}")   # 打印 team_color 字段的值。


class EdgeConfig(BaseModel):
    lower_threshold: Tuple[float, float, float, float] = Field(     # lower_threshold 字段是一个元组，表示边缘检测的下限值。它默认是 (1740, 1819, 1819, 1740)。
        default=(1740, 1819, 1819, 1740),   # lower_threshold 字段的默认值是 (1740, 1819, 1819, 1740)。
        description="Lower threshold values for edge detection.",   # lower_threshold 字段的描述是 "Lower threshold values for edge detection."。
    )
    upper_threshold: Tuple[float, float, float, float] = Field(
        default=(2100, 2470, 2470, 2100), description="Upper threshold values for edge detection."  # upper_threshold 字段的默认值是 (2100, 2470, 2470, 2100)。
    )

    fallback_speed: PositiveInt = Field(default=2600, description="Speed when falling back.")   # fallback_speed 字段是一个整数，表示后退的速度。它默认是 2600。
    fallback_duration: PositiveFloat = Field(default=0.2, description="Duration of the fallback action.")   # fallback_duration 字段是一个浮点数，表示后退动作的持续时间。它默认是 0.2。

    advance_speed: PositiveInt = Field(default=2400, description="Speed when advancing.")   # advance_speed 字段是一个整数，表示前进的速度。它默认是 2400。
    advance_duration: PositiveFloat = Field(default=0.35, description="Duration of the advance action.")    # advance_duration 字段是一个浮点数，表示前进动作的持续时间。它默认是 0.35。

    turn_speed: PositiveInt = Field(default=2800, description="Speed when turning.")    # turn_speed 字段是一个整数，表示转弯的速度。它默认是 2800。
    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")     # full_turn_duration 字段是一个浮点数，表示全转动的持续时间。它默认是 0.45。
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")    # half_turn_duration 字段是一个浮点数，表示半转动的持续时间。它默认是 0.225。

    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob 字段是一个浮点数，表示左转的概率。它默认是 0.5。

    drift_speed: PositiveInt = Field(default=1500, description="Speed when drifting.")  # drift_speed 字段是一个整数，表示漂移的速度。它默认是 1500。
    drift_duration: PositiveFloat = Field(default=0.13, description="Duration of the drift action.")    # drift_duration 字段是一个浮点数，表示漂移动作的持续时间。它默认是 0.13。

    use_gray_io: bool = Field(default=True, description="Whether to use gray IO for detection.") # use_gray_io 字段是一个布尔值，表示是否使用灰度 IO 进行检测。它默认是 True。


class SurroundingConfig(BaseModel):
    io_encounter_object_value: int = Field(default=0, description="IO value when encountering an object.")  # io_encounter_object_value 字段是一个整数，表示遇到物体时的 IO 值。它默认是 0。

    left_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the left sensor.", gt=0, lt=4096     # left_adc_lower_threshold 字段是一个整数，表示左传感器的 ADC 下限值。它默认是 1000。
    )
    right_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the right sensor.", gt=0, lt=4096    # right_adc_lower_threshold 字段是一个整数，表示右传感器的 ADC 下限值。它默认是 1000。
    )

    front_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the front sensor.", gt=0, lt=4096    # front_adc_lower_threshold 字段是一个整数，表示前传感器的 ADC 下限值。它默认是 1000。
    )
    back_adc_lower_threshold: int = Field(
        default=1100, description="ADC lower threshold for the back sensor.", gt=0, lt=4096     # back_adc_lower_threshold 字段是一个整数，表示后传感器的 ADC 下限值。它默认是 1100。
    )

    atk_break_front_lower_threshold: int = Field(
        default=1500, description="Front ADC lower threshold for attack break.", gt=0, lt=4096  # atk_break_front_lower_threshold 字段是一个整数，表示攻击中断的前 ADC 下限值。它默认是 1500。
    )

    atk_break_use_edge_sensors: bool = Field(default=True, description="Whether to use edge sensors for attack break.")     # atk_break_use_edge_sensors 字段是一个布尔值，表示是否使用边缘传感器进行攻击中断。它默认是 True。

    atk_speed_enemy_car: PositiveInt = Field(default=2300, description="Attack speed for enemy car.")   # atk_speed_enemy_car 字段是一个整数，表示对敌方汽车的攻击速度。它默认是 2300。
    atk_speed_enemy_box: PositiveInt = Field(default=2500, description="Attack speed for enemy box.")   # atk_speed_enemy_box 字段是一个整数，表示对敌方箱子的攻击速度。它默认是 2500。
    atk_speed_neutral_box: PositiveInt = Field(default=2500, description="Attack speed for neutral box.")    # atk_speed_neutral_box 字段是一个整数，表示对中立箱子的攻击速度。它默认是 2500。
    fallback_speed_ally_box: PositiveInt = Field(default=2900, description="Fallback speed for ally box.")  # fallback_speed_ally_box 字段是一个整数，表示对友方箱子的后退速度。它默认是 2900。
    fallback_speed_edge: PositiveInt = Field(default=2400, description="Fallback speed for edge.")  # fallback_speed_edge 字段是一个整数，表示对边缘的后退速度。它默认是 2400。

    atk_enemy_car_duration: PositiveFloat = Field(default=4.2, description="Duration of attack on enemy car.")  # atk_enemy_car_duration 字段是一个浮点数，表示对敌方汽车的攻击持续时间。它默认是 4.2。
    atk_enemy_box_duration: PositiveFloat = Field(default=3.6, description="Duration of attack on enemy box.")  # atk_enemy_box_duration 字段是一个浮点数，表示对敌方箱子的攻击持续时间。它默认是 3.6。
    atk_neutral_box_duration: PositiveFloat = Field(default=3.6, description="Duration of attack on neutral box.")  # atk_neutral_box_duration 字段是一个浮点数，表示对中立箱子的攻击持续时间。它默认是 3.6。
    fallback_duration_ally_box: PositiveFloat = Field(default=0.3, description="Duration of fallback for ally box.")    # fallback_duration_ally_box 字段是一个浮点数，表示对友方箱子的后退持续时间。它默认是 0.3。
    fallback_duration_edge: PositiveFloat = Field(default=0.2, description="Duration of fallback for edge.")    # fallback_duration_edge 字段是一个浮点数，表示对边缘的后退持续时间。它默认是 0.2。

    turn_speed: NonNegativeInt = Field(default=2900, description="Speed when turning.")     # turn_speed 字段是一个非负整数，表示转弯的速度。它默认是 2900。
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob 字段是一个浮点数，表示左转的概率。它默认是 0.5。

    turn_to_front_use_front_sensor: bool = Field(
        default=False, description="Whether to use the front sensor for turning to front."  # turn_to_front_use_front_sensor 字段是一个布尔值，表示是否使用前传感器进行转向。它默认是 False。
    )

    rand_turn_speeds: List[NonNegativeInt] = Field(default=[1600, 2100, 3000], description="Random turn speeds.")   # rand_turn_speeds 字段是一个非负整数列表，表示随机转弯速度。它默认是 [1600, 2100, 3000]。
    rand_turn_speed_weights: List[float] = Field(default=[2, 3, 1], description="Weights for random turn speeds.")   # rand_turn_speed_weights 字段是一个浮点数列表，表示随机转弯速度的权重。它默认是 [2, 3, 1]。

    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")     # full_turn_duration 字段是一个浮点数，表示全转的持续时间。它默认是 0.45。
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")    # half_turn_duration 字段是一个浮点数，表示半转的持续时间。它默认是 0.225。


class GradientConfig(BaseModel):
    max_speed: PositiveInt = Field(default=2800, description="Maximum speed for gradient move.")    # max_speed 字段是一个正整数，表示梯度移动的最大速度。它默认是 2800。
    min_speed: NonNegativeInt = Field(default=500, description="Minimum speed for gradient move.")  # min_speed 字段是一个非负整数，表示梯度移动的最小速度。它默认是 500。
    lower_bound: int = Field(default=2900, description="Lower bound for gradient move.", gt=0, lt=4096)     # lower_bound 字段是一个整数，表示梯度移动的下限。它默认是 2900。
    upper_bound: int = Field(default=3700, description="Upper bound for gradient move.", gt=0, lt=4096)     # upper_bound 字段是一个整数，表示梯度移动的上限。它默认是 3700。


class ScanConfig(BaseModel):

    front_max_tolerance: int = Field(default=760, description="Maximum tolerance for the front sensor.", gt=0, lt=4096)     # front_max_tolerance 字段是一个整数，表示前传感器的最大容差。它默认是 760。
    rear_max_tolerance: int = Field(default=760, description="Maximum tolerance for the rear sensor.", gt=0, lt=4096)      # rear_max_tolerance 字段是一个整数，表示后传感器的最大容差。它默认是 760。
    left_max_tolerance: int = Field(default=760, description="Maximum tolerance for the left sensor.", gt=0, lt=4096)      # left_max_tolerance 字段是一个整数，表示左传感器的最大容差。它默认是 760。
    right_max_tolerance: int = Field(default=760, description="Maximum tolerance for the right sensor.", gt=0, lt=4096)     # right_max_tolerance 字段是一个整数，表示右传感器的最大容差。它默认是 760。

    io_encounter_object_value: int = Field(default=0, description="IO value when encountering an object.")  # io_encounter_object_value 字段是一个整数，表示遇到物体时的 IO 值。它默认是 0。

    scan_speed: PositiveInt = Field(default=300, description="Speed for scanning.")     # scan_speed 字段是一个正整数，表示扫描的速度。它默认是 300。
    scan_duration: PositiveFloat = Field(default=4.5, description="Duration of the scan action.")    # scan_duration 字段是一个浮点数，表示扫描动作的持续时间。它默认是 4.5。
    scan_turn_left_prob: float = Field(
        default=0.5, description="Probability of turning left during scan.", ge=0, le=1.0   # scan_turn_left_prob 字段是一个浮点数，表示扫描过程中左转的概率。它默认是 0.5。
    )

    fall_back_speed: PositiveInt = Field(default=3250, description="Speed for falling back.")      # fall_back_speed 字段是一个正整数，表示后退的速度。它默认是 3250。
    fall_back_duration: float = Field(default=0.2, description="Duration of the fall back action.")     # fall_back_duration 字段是一个浮点数，表示后退动作的持续时间。它默认是 0.2。

    turn_speed: PositiveInt = Field(default=2700, description="Speed when turning.")        # turn_speed 字段是一个正整数，表示转弯的速度。它默认是 2700。
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob 字段是一个浮点数，表示左转的概率。它默认是 0.5。

    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")     # full_turn_duration 字段是一个浮点数，表示全转的持续时间。它默认是 0.45。
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")    # half_turn_duration 字段是一个浮点数，表示半转的持续时间。它默认是 0.225。

    check_edge_before_scan: bool = Field(default=True, description="Whether to check edge before scanning.")    # check_edge_before_scan 字段是一个布尔值，表示是否在扫描之前检查边缘。它默认是 True。
    check_gray_adc_before_scan: bool = Field(default=True, description="Whether to check gray ADC before scanning.")    # check_gray_adc_before_scan 字段是一个布尔值，表示是否在扫描之前检查灰度 ADC。它默认是 True。
    gray_adc_lower_threshold: int = Field(
        default=3100, description="Gray ADC lower threshold for scanning.", gt=0, lt=4096   # gray_adc_lower_threshold 字段是一个整数，表示扫描的灰度 ADC 下限。它默认是 3100。
    )


class RandTurn(BaseModel):

    turn_speed: PositiveInt = Field(default=2300, description="Speed when turning.")        # turn_speed 字段是一个正整数，表示转弯的速度。它默认是 2300。
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)        # turn_left_prob 字段是一个浮点数，表示左转的概率。它默认是 0.5。
    full_turn_duration: PositiveFloat = Field(default=0.25, description="Duration of a full turn.")        # full_turn_duration 字段是一个浮点数，表示全转的持续时间。它默认是 0.25。
    half_turn_duration: PositiveFloat = Field(default=0.15, description="Duration of a half turn.")        # half_turn_duration 字段是一个浮点数，表示半转的持续时间。它默认是 0.15。

    use_turn_to_front: bool = Field(default=True, description="Whether to use turning to front.")        # use_turn_to_front 字段是一个布尔值，表示是否使用面向前方的转弯。它默认是 True。


class SearchConfig(BaseModel):

    use_gradient_move: bool = Field(default=True, description="Whether to use gradient move.")  # use_gradient_move 字段是一个布尔值，表示是否使用梯度移动。它默认是 True。
    gradient_move_weight: PositiveFloat = Field(default=100, description="Weight for gradient move.")    # gradient_move_weight 字段是一个正浮点数，表示梯度移动的权重。它默认是 100。
    use_scan_move: bool = Field(default=True, description="Whether to use scan move.")  # use_scan_move 字段是一个布尔值，表示是否使用扫描移动。它默认是 True。
    scan_move_weight: PositiveFloat = Field(default=1.96, description="Weight for scan move.")  # scan_move_weight 字段是一个正浮点数，表示扫描移动的权重。它默认是 1.96。
    use_rand_turn: bool = Field(default=True, description="Whether to use random turn.")    # use_rand_turn 字段是一个布尔值，表示是否使用随机转弯。它默认是 True。
    rand_turn_weight: PositiveFloat = Field(default=0.05, description="Weight for random turn.")    # rand_turn_weight 字段是一个正浮点数，表示随机转弯的权重。它默认是 0.05。

    gradient_move: GradientConfig = Field(default=GradientConfig(), description="Configuration for gradient move.")     # gradient_move 字段是一个 GradientConfig 对象，表示梯度移动的配置。它默认是一个空的 GradientConfig 对象。
    scan_move: ScanConfig = Field(default=ScanConfig(), description="Configuration for scan move.")     # scan_move 字段是一个 ScanConfig 对象，表示扫描移动的配置。它默认是一个空的 ScanConfig 对象。
    rand_turn: RandTurn = Field(default=RandTurn(), description="Configuration for random turn.")   # rand_turn 字段是一个 RandTurn 对象，表示随机转弯的配置。它默认是一个空的 RandTurn 对象。


class RandWalk(BaseModel):

    use_straight: bool = Field(default=True, description="Whether to use straight movement.")   # use_straight 字段是一个布尔值，表示是否使用直线移动。它默认是 True。
    straight_weight: PositiveFloat = Field(default=2, description="Weight for straight movement.")  # straight_weight 字段是一个正浮点数，表示直线移动的权重。它默认是 2。

    rand_straight_speeds: List[int] = Field(default=[-800, -500, 500, 800], description="Random straight speeds.")  # rand_straight_speeds 字段是一个整数列表，表示随机直线速度。它默认是 [-800, -500, 500, 800]
    rand_straight_speed_weights: List[float] = Field(
        default=[1, 3, 3, 1], description="Weights for random straight speeds."     # rand_straight_speed_weights 字段是一个浮点数列表，表示随机直线速度的权重。它默认是 [1, 3, 3, 1]
    )

    use_turn: bool = Field(default=True, description="Whether to use turning.")     # use_turn 字段是一个布尔值，表示是否使用转弯。它默认是 True。
    turn_weight: float = Field(default=1, description="Weight for turning.")    # turn_weight 字段是一个浮点数，表示转弯的权重。它默认是 1。
    rand_turn_speeds: List[int] = Field(default=[-1200, -800, 800, 1200], description="Random turn speeds.")    # rand_turn_speeds 字段是一个整数列表，表示随机转弯速度。它默认是 [-1200, -800, 800, 1200]
    rand_turn_speed_weights: List[float] = Field(default=[1, 3, 3, 1], description="Weights for random turn speeds.")   # rand_turn_speed_weights 字段是一个浮点数列表，表示随机转弯速度的权重。它默认是 [1, 3, 3, 1]

    walk_duration: PositiveFloat = Field(default=0.3, description="Duration of walking.")   # walk_duration 字段是一个正浮点数，表示行走的持续时间。它默认是 0.3。


class FenceConfig(BaseModel):
    front_adc_lower_threshold: int = Field(default=900, description="Front ADC lower threshold.")   # front_adc_lower_threshold 字段是一个整数，表示前方的 ADC 下限。它默认是 900。
    rear_adc_lower_threshold: int = Field(default=1100, description="Rear ADC lower threshold.")    # rear_adc_lower_threshold 字段是一个整数，表示后方的 ADC 下限。它默认是 1100。
    left_adc_lower_threshold: int = Field(default=900, description="Left ADC lower threshold.")     # left_adc_lower_threshold 字段是一个整数，表示左方的 ADC 下限。它默认是 900。
    right_adc_lower_threshold: int = Field(default=900, description="Right ADC lower threshold.")   # right_adc_lower_threshold 字段是一个整数，表示右方的 ADC 下限。它默认是 900。

    io_encounter_fence_value: int = Field(default=0, description="IO value when encountering a fence.")     # io_encounter_fence_value 字段是一个整数，表示遇到栅栏时的 IO 值。它默认是 0。
    max_yaw_tolerance: PositiveFloat = Field(default=20.0, description="Maximum yaw tolerance.")    # max_yaw_tolerance 字段是一个正浮点数，表示最大偏航容差。它默认是 20.0。

    use_mpu_align_stage: bool = Field(default=False, description="Whether to use MPU for aligning stage.")  # use_mpu_align_stage 字段是一个布尔值，表示是否使用 MPU 对齐舞台。它默认是 False。
    use_mpu_align_direction: bool = Field(default=False, description="Whether to use MPU for aligning direction.")  # use_mpu_align_direction 字段是一个布尔值，表示是否使用 MPU 对齐方向。它默认是 False。

    stage_align_speed: PositiveInt = Field(default=850, description="Speed for aligning stage.")    # stage_align_speed 字段是一个正整数，表示对齐舞台的速度。它默认是 850。
    max_stage_align_duration: PositiveFloat = Field(default=4.5, description="Maximum duration for aligning stage.")    # max_stage_align_duration 字段是一个正浮点数，表示对齐舞台的最大持续时间。它默认是 4.5。
    stage_align_direction: Literal["l", "r", "rand"] = Field(
        default="rand", description='Turn direction for aligning stage, allow ["l", "r", "rand"].'  # stage_align_direction 字段是一个字符串，表示对齐舞台的转向方向。它默认是 "rand"，表示随机方向。
    )

    direction_align_speed: PositiveInt = Field(default=850, description="Speed for aligning direction.")    # direction_align_speed 字段是一个正整数，表示对齐方向的速度。它默认是 850。
    max_direction_align_duration: PositiveFloat = Field(
        default=4.5, description="Maximum duration for aligning direction."     # max_direction_align_duration 字段是一个正浮点数，表示对齐方向的最大持续时间。它默认是 4.5。
    )
    direction_align_direction: Literal["l", "r", "rand"] = Field(   # direction_align_direction 字段是一个字符串，表示对齐方向的转向方向。它默认是 "rand"，表示随机方向。
        default="rand",
        description='Turn direction for aligning the parallel or vertical direction to the stage,  allow ["l", "r", "rand"].',  #这个参数或函数用于确定对齐舞台平行或垂直方向的转向方向，允许的值是 "l"（左）、"r"（右）或 "rand"（随机）。
    )

    exit_corner_speed: PositiveInt = Field(default=1200, description="Speed for exiting corner.")    # exit_corner_speed 字段是一个正整数，表示退出角落的速度。它默认是 1200。
    max_exit_corner_duration: PositiveFloat = Field(default=1.5, description="Maximum duration for exiting corner.")    # max_exit_corner_duration 字段是一个正浮点数，表示退出角落的最大持续时间。它默认是 1.5。

    rand_walk: RandWalk = Field(default=RandWalk(), description="Configuration for random walk.")    # rand_walk 字段是一个 RandWalk 对象，表示随机行走的配置。它默认是 RandWalk() 对象。


class StrategyConfig(BaseModel):
    use_edge_component: bool = Field(default=True, description="Whether to use edge component.")    # use_edge_component 字段是一个布尔值，表示是否使用边缘组件。它默认是 True。
    use_surrounding_component: bool = Field(default=True, description="Whether to use surrounding component.")  # use_surrounding_component 字段是一个布尔值，表示是否使用周围组件。它默认是 True。
    use_normal_component: bool = Field(default=True, description="Whether to use normal component.")    # use_normal_component 字段是一个布尔值，表示是否使用普通组件。它默认是 True。


class PerformanceConfig(BaseModel):
    checking_duration: NonNegativeFloat = Field(default=0.0, description="Duration for checking.")  # checking_duration 字段是一个非负浮点数，表示检查的持续时间。它默认是 0.0。


class BootConfig(BaseModel):
    button_io_activate_case_value: int = Field(default=0, description="Button IO value for activating case.")    # button_io_activate_case_value 字段是一个整数，表示激活情况的按钮 IO 值。它默认是 0。

    time_to_stabilize: PositiveFloat = Field(default=0.1, description="Time to stabilize after activation.")    # time_to_stabilize 字段是一个正浮点数，表示激活后的稳定时间。它默认是 0.1。

    max_holding_duration: PositiveFloat = Field(default=180.0, description="Maximum holding duration.")     # max_holding_duration 字段是一个正浮点数，表示最大保持持续时间。它默认是 180.0。

    left_threshold: int = Field(default=1100, description="Threshold for left sensor.")     # left_threshold 字段是一个整数，表示左方的阈值。它默认是 1100。
    right_threshold: int = Field(default=1100, description="Threshold for right sensor.")    # right_threshold 字段是一个整数，表示右方的阈值。它默认是 1100。

    dash_speed: PositiveInt = Field(default=7000, description="Speed for dashing.")     # dash_speed 字段是一个正整数，表示冲刺的速度。它默认是 7000。
    dash_duration: PositiveFloat = Field(default=0.55, description="Duration for dashing.")     # dash_duration 字段是一个正浮点数，表示冲刺的持续时间。它默认是 0.55。

    turn_speed: PositiveInt = Field(default=2150, description="Speed for turning.")     # turn_speed 字段是一个正整数，表示转向的速度。它默认是 2150。
    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration for a full turn.")    # full_turn_duration 字段是一个正浮点数，表示全转的持续时间。它默认是 0.45。
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob 字段是一个浮点数，表示左转的概率。它默认是 0.5，并且必须在 0 到 1.0 之间。


class BackStageConfig(BaseModel):
    time_to_stabilize: PositiveFloat = Field(default=0.1, description="Time to stabilize after activation.")    # time_to_stabilize 字段是一个正浮点数，表示激活后的稳定时间。它默认是 0.1。

    small_advance_speed: PositiveInt = Field(default=1500, description="Speed for small advance.")  # small_advance_speed 字段是一个正整数，表示小前行的速度。它默认是 1500。
    small_advance_duration: PositiveFloat = Field(default=0.6, description="Duration for small advance.")    # small_advance_duration 字段是一个正浮点数，表示小前行的持续时间。它默认是 0.6。

    dash_speed: PositiveInt = Field(default=7000, description="Speed for dashing.")     # dash_speed 字段是一个正整数，表示冲刺的速度。它默认是 7000。
    dash_duration: PositiveFloat = Field(default=0.55, description="Duration for dashing.")     # dash_duration 字段是一个正浮点数，表示冲刺的持续时间。它默认是 0.55。

    turn_speed: PositiveInt = Field(default=2600, description="Speed for turning.")     # turn_speed 字段是一个正整数，表示转向的速度。它默认是 2600。
    full_turn_duration: PositiveFloat = Field(default=0.35, description="Duration for a full turn.")    # full_turn_duration 字段是一个正浮点数，表示全转的持续时间。它默认是 0.35。
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob 字段是一个浮点数，表示左转的概率。它默认是 0.5，并且必须在 0 到 1.0 之间。

    use_is_on_stage_check: bool = Field(default=True, description="Whether to check if on stage.")  # use_is_on_stage_check 字段是一个布尔值，表示是否检查是否在舞台上。它默认是 True。
    use_side_away_check: bool = Field(
        default=True, description="Whether to check side away after the is_on_stage check."     # use_side_away_check 字段是一个布尔值，表示是否在 is_on_stage 检查后检查侧移。它默认是 True。
    )
    check_start_percent: PositiveFloat = Field(
        default=0.9,
        description="defining when does the is_on_stage check being brought on during the dashing. DO NOT set it too small!",   # check_start_percent 字段是一个正浮点数，表示在冲刺期间何时启动 is_on_stage 检查。不要设置得太小！
        lt=1.0,
    )

    side_away_degree_tolerance: PositiveFloat = Field(default=10.0, description="Degree tolerance for side away.")  # side_away_degree_tolerance 字段是一个正浮点数，表示侧移的度数容差。它默认是 10.0。
    exit_side_away_speed: PositiveInt = Field(default=1300, description="Speed for exiting side away.")        # exit_side_away_speed 字段是一个正整数，表示退出侧移的速度。它默认是 1300。
    exit_side_away_duration: PositiveFloat = Field(default=0.6, description="Duration for exiting side away.")    # exit_side_away_duration 字段是一个正浮点数，表示退出侧移的持续时间。它默认是 0.6。


class StageConfig(BaseModel): 
    gray_adc_off_stage_upper_threshold: int = Field(default=2630, description="Upper threshold for gray ADC off stage.")    # gray_adc_off_stage_upper_threshold 字段是一个整数，表示舞台外灰度 ADC 的上限阈值。它默认是 2630。
    gray_adc_on_stage_lower_threshold: int = Field(default=2830, description="Lower threshold for gray ADC on stage.")    # gray_adc_on_stage_lower_threshold 字段是一个整数，表示舞台上灰度 ADC 的下限阈值。它默认是 2830。
    unclear_zone_tolerance:int = Field(default=90, description="Tolerance for judging if the car is on stage in unclear zone state.")    # unclear_zone_tolerance 字段是一个整数，表示在模糊区域状态下判断汽车是否在舞台上的容差。它默认是 90。
    unclear_zone_turn_speed: PositiveInt = Field(default=1500, description="Speed for turning in unclear zone.")    # unclear_zone_turn_speed 字段是一个正整数，表示在模糊区域状态下的转向速度。它默认是 1500。
    unclear_zone_turn_duration: PositiveFloat = Field(default=0.6, description="Duration for turning in unclear zone.")     # unclear_zone_turn_duration 字段是一个正浮点数，表示在模糊区域状态下的转向持续时间。它默认是 0.6。
    unclear_zone_turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # unclear_zone_turn_left_prob 字段是一个浮点数，表示在模糊区域状态下左转的概率。它默认是 0.5，并且必须在 0 到 1.0 之间。
    gray_io_off_stage_case_value: int = Field(default=0, description="IO value for gray off stage.")    # gray_io_off_stage_case_value 字段是一个整数，表示灰度舞台外的 IO 值。它默认是 0。


class RunConfig(CounterHashable):
    strategy: StrategyConfig = StrategyConfig()     # strategy 字段是一个 StrategyConfig 类型的实例，表示策略配置。它默认是 StrategyConfig 类型的实例。
    boot: BootConfig = BootConfig()     # boot 字段是一个 BootConfig 类型的实例，表示启动配置。它默认是 BootConfig 类型的实例。
    backstage: BackStageConfig = BackStageConfig()   # backstage 字段是一个 BackStageConfig 类型的实例，表示后台配置。它默认是 BackStageConfig 类型的实例。
    stage: StageConfig = StageConfig()  # stage 字段是一个 StageConfig 类型的实例，表示舞台配置。它默认是 StageConfig 类型的实例。
    edge: EdgeConfig = EdgeConfig()     # edge 字段是一个 EdgeConfig 类型的实例，表示边缘配置。它默认是 EdgeConfig 类型的实例。
    surrounding: SurroundingConfig = SurroundingConfig()    # surrounding 字段是一个 SurroundingConfig 类型的实例，表示周围配置。它默认是 SurroundingConfig 类型的实例。
    search: SearchConfig = SearchConfig()    # search 字段是一个 SearchConfig 类型的实例，表示搜索配置。它默认是 SearchConfig 类型的实例。
    fence: FenceConfig = FenceConfig()      # fence 字段是一个 FenceConfig 类型的实例，表示栅栏配置。它默认是 FenceConfig 类型的实例。

    perf: PerformanceConfig = PerformanceConfig()    # perf 字段是一个 PerformanceConfig 类型的实例，表示性能配置。它默认是 PerformanceConfig 类型的实例。

    @classmethod
    def read_config(cls, fp: TextIO) -> Self:   # read_config 方法接受一个文件对象作为参数，并返回一个 RunConfig 类型的实例。
        """
        Reads a configuration from a file object and returns an instance of the class.  # 从文件对象中读取配置并返回类的实例。

        Args:
            fp (TextIOWrapper): A file object containing the configuration data.    # 一个包含配置数据的文件对象。

        Returns:
            Self: An instance of the class with the configuration data loaded from the file.    # 从文件中加载配置数据的类的实例。

        Raises:
            ValidationError: If the loaded configuration data fails validation.     # 如果加载的配置数据验证失败，则引发 ValidationError。
        """
        return cls.model_validate(load(fp))     # 使用 load 函数从文件对象中加载配置数据，并使用 model_validate 方法验证加载的数据。如果验证失败，则引发 ValidationError。

    @classmethod
    def dump_config(cls, fp: TextIO, config: Self, with_desc: bool = True) -> None:     # dump_config 方法接受一个文件对象、一个 RunConfig 类型的实例和一个布尔值作为参数，没有返回值。
        """
        Dump the configuration data to a file object.    # 将配置数据转储到文件对象中。

        Args:
            fp (TextIO): The file object to write the configuration data to.    # 要写入配置数据的文件对象。
            config (Config): The configuration data to be dumped.   # 要转储的配置数据。
            with_desc (bool): Whether to add descriptions to the dump file.     # 是否将描述添加到转储文件中。
        Returns:
            None    # 没有返回值。
        """
        if with_desc:
            # Extract description and raw data from the config  # 从配置中提取描述和原始数据
            desc_pack: Dict[str, Tuple[str | None, Dict | None]] = extract_description(config)  # desc_pack 字段是一个字典，它将配置中的每个字段映射到一个元组，该元组包含字段的描述和原始数据。
            raw_data = cls.model_dump(config)    # raw_data 字段是一个字典，它将配置中的每个字段映射到字段的原始数据。

            # Create a new TOML document    # 创建一个新的 TOML 文档
            data: TOMLDocument = document()     # data 字段是一个 TOMLDocument 类型的实例，它表示一个 TOML 文档。
            import kazu
            import datetime

            data.add(comment(f"Exported by Kazu-v{kazu.__version__} at {datetime.datetime.now()}"))     # 将注释添加到 TOML 文档中，注释中包含 Kazu 的版本号和导出时间。
            # Recursive function to inject descriptions into the TOML document  # 递归函数，将描述注入到 TOML 文档中

            # Inject the descriptions into the TOML document    # 将描述注入到 TOML 文档中
            inject_description_into_toml(desc_pack, data, raw_data)     # 使用 inject_description_into_toml 函数将描述注入到 TOML 文档中。

            fp.write(dumps(data))    # 将 TOML 文档写入文件对象中。

        else:
            # If no description is needed, just use the raw data    # 如果不需要描述，只需使用原始数据
            pure_data = cls.model_dump(config)  # pure_data 字段是一个字典，它将配置中的每个字段映射到字段的原始数据。
            dump(pure_data, fp)     # 将纯数据写入文件对象中。


class ContextVar(Enum):
    prev_salvo_speed: NonNegativeInt = auto()    # prev_salvo_speed 字段是一个非负整数，表示前一个弹丸的速度。它默认是 0。

    is_aligned: bool = auto()    # is_aligned 字段是一个布尔值，表示是否对齐。它默认是 False。

    recorded_pack: tuple = auto()    # recorded_pack 字段是一个元组，表示记录的包。它默认是一个空元组。

    gradient_speed: NonNegativeInt = auto()     # gradient_speed 字段是一个非负整数，表示梯度速度。它默认是 0。

    unclear_zone_gray:int=auto()    # unclear_zone_gray 字段是一个整数，表示不清楚区域的灰度。它默认是 0。
    @property
    def default(self) -> Any:
        """
        Get the default value for the context variable.     # 获取上下文变量的默认值。

        Returns:
            Any: The default value for the context variable.     # 上下文变量的默认值。
        """
        defaults = {"prev_salvo_speed": (0, 0, 0, 0), "is_aligned": False, "recorded_pack": (), "gradient_speed": 0,
                    "unclear_zone_gray":0}  # defaults 字典将上下文变量的名称映射到它们的默认值。
        assert self.name in defaults, "should always find a default value!"     # 断言上下文变量的名称在 defaults 字典中，如果不在，则抛出 AssertionError。
        return defaults.get(self.name)  # 返回上下文变量的默认值。

    @staticmethod
    def export_context() -> Dict[str, Any]:     # export_context 方法没有参数，返回一个字典。
        """
        Export the context variables and their default values as a dictionary.  # 将上下文变量及其默认值导出为字典。

        Returns:
            Dict[str, Any]: A dictionary containing the names of the context variables as keys and their default values as values.  # 一个字典，包含上下文变量的名称作为键，它们的默认值作为值。
        """
        return {a.name: a.default for a in ContextVar}  # 返回一个字典，其中包含上下文变量的名称作为键，它们的默认值作为值。


class MotionConfig(BaseModel):
    motor_fr: Tuple[int, int] = Field(default=(1, 1), description="Front-right motor configuration.")   #motor_fr：一个元组，表示前右轮的电机配置。默认值为 (1, 1)
    motor_fl: Tuple[int, int] = Field(default=(2, 1), description="Front-left motor configuration.")    # motor_fl：一个元组，表示前左轮的电机配置。默认值为 (2, 1)
    motor_rr: Tuple[int, int] = Field(default=(3, 1), description="Rear-right motor configuration.")    # motor_rr：一个元组，表示后右轮的电机配置。默认值为 (3, 1)
    motor_rl: Tuple[int, int] = Field(default=(4, 1), description="Rear-left motor configuration.")     # motor_rl：一个元组，表示后左轮的电机配置。默认值为 (4, 1)
    port: str = Field(default="/dev/ttyUSB0", description="Serial port for communication.")     # port：一个字符串，表示用于通信的串行端口。默认值为 "/dev/ttyUSB0"


class VisionConfig(BaseModel):
    team_color: Literal["yellow", "blue"] = Field(  # team_color：一个字符串，表示队伍的颜色。允许的值为 "yellow" 和 "blue"。默认值为 "blue"。
        default="blue", description='Team color for vision, allow ["yellow", "blue"]'
    )
    resolution_multiplier: float = Field(default=1.0, description="Resolution multiplier for camera.")# resolution_multiplier：一个浮点数，表示摄像头的分辨率乘数。默认值为 1.0。
    use_camera: bool = Field(default=True, description="Whether to use the camera.")    # use_camera：一个布尔值，表示是否使用摄像头。默认值为 True。
    camera_device_id: int = Field(default=0, description="Camera device ID.")    # camera_device_id：一个整数，表示摄像头的设备 ID。默认值为 0。


class DebugConfig(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(    # log_level：一个字符串，表示日志级别。允许的值为 "DEBUG"、"INFO"、"WARNING"、"ERROR" 和 "CRITICAL"。默认值为 "INFO
        default="INFO", description='Log level for debugging, allow ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].'
    )
    use_siglight: bool = Field(default=True, description="Whether to use signal light.")    # use_siglight：一个布尔值，表示是否使用信号灯。默认值为 True。


class SensorConfig(BaseModel):
    gyro_fsr: Literal[250, 500, 1000, 2000] = Field(
        default=1000, description="Gyroscope full scale range, allows [250, 500, 1000, 2000]."  # gyro_fsr：一个整数，表示陀螺仪的满量程范围。允许的值为 250、500、1000 和 2000。默认值为 1000。
    )
    accel_fsr: Literal[2, 4, 8, 16] = Field(
        default=8, description="Accelerometer full scale range, allows [2, 4, 8, 16]."  # accel_fsr：一个整数，表示加速度计的满量程范围。允许的值为 2、4、8 和 16。默认值为 8。
    )

    adc_min_sample_interval: int = Field(default=5, description="Minimum ADC sample interval.")     # adc_min_sample_interval：一个整数，表示 ADC 最小采样间隔。默认值为 5。

    edge_fl_index: int = Field(default=3, description="Index for front-left edge sensor.")      # edge_fl_index：一个整数，表示前左边缘传感器的索引。默认值为 3。
    edge_fr_index: int = Field(default=0, description="Index for front-right edge sensor.")     # edge_fr_index：一个整数，表示前右边缘传感器的索引。默认值为 0。
    edge_rl_index: int = Field(default=2, description="Index for rear-left edge sensor.")      # edge_rl_index：一个整数，表示后左边缘传感器的索引。默认值为 2。
    edge_rr_index: int = Field(default=1, description="Index for rear-right edge sensor.")      # edge_rr_index：一个整数，表示后右边缘传感器的索引。默认值为 1。

    left_adc_index: int = Field(default=6, description="Index for left ADC sensor.")        # left_adc_index：一个整数，表示左 ADC 传感器的索引。默认值为 6。
    right_adc_index: int = Field(default=4, description="Index for right ADC sensor.")      # right_adc_index：一个整数，表示右 ADC 传感器的索引。默认值为 4。
    
    front_adc_index: int = Field(default=5, description="Index for front ADC sensor.")      # front_adc_index：一个整数，表示前 ADC 传感器的索引。默认值为 5。
    rb_adc_index: int = Field(default=7, description="Index for rear-back ADC sensor.")     # rb_adc_index：一个整数，表示后背 ADC 传感器的索引。默认值为 7。

    gray_adc_index: int = Field(default=8, description="Index for gray ADC sensor.")        # gray_adc_index：一个整数，表示灰度 ADC 传感器的索引。默认值为 8。

    # ---------IO----------
    
    gray_io_left_index: int = Field(default=1, description="Index for left gray IO sensor.")    # gray_io_left_index：一个整数，表示左灰度 IO 传感器的索引。默认值为 1。
    gray_io_right_index: int = Field(default=0, description="Index for right gray IO sensor.")  # gray_io_right_index：一个整数，表示右灰度 IO 传感器的索引。默认值为 0。

    fl_io_index: int = Field(default=5, description="Index for front-left IO sensor.")      # fl_io_index：一个整数，表示前左 IO 传感器的索引。默认值为 5。
    fr_io_index: int = Field(default=2, description="Index for front-right IO sensor.")     # fr_io_index：一个整数，表示前右 IO 传感器的索引。默认值为 2。

    rl_io_index: int = Field(default=4, description="Index for rear-left IO sensor.")      # rl_io_index：一个整数，表示后左 IO 传感器的索引。默认值为 4。
    rr_io_index: int = Field(default=3, description="Index for rear-right IO sensor.")      # rr_io_index：一个整数，表示后右 IO 传感器的索引。默认值为 3。

    reboot_button_index: int = Field(default=6, description="Index for reboot button.")        # reboot_button_index：一个整数，表示重启按钮的索引。默认值为 6。


class APPConfig(CounterHashable):   #APPConfig：一个继承自 CounterHashable 的类，用于存储应用程序的配置信息。
    motion: MotionConfig = MotionConfig()   # motion：一个 MotionConfig 类型的实例，用于存储运动相关的配置信息。
    vision: VisionConfig = VisionConfig()   # vision：一个 VisionConfig 类型的实例，用于存储视觉相关的配置信息。
    debug: DebugConfig = DebugConfig()      # debug：一个 DebugConfig 类型的实例，用于存储调试相关的配置信息。
    sensor: SensorConfig = SensorConfig()     # sensor：一个 SensorConfig 类型的实例，用于存储传感器相关的配置信息。

    @classmethod
    def read_config(cls, fp: TextIO) -> Self:    #read_config：一个类方法，用于从文件对象中读取配置信息。
        """
        Reads a configuration from a file object and returns an instance of the class.  #从文件对象中读取配置信息并返回类的实例。

        Args:
            fp (TextIOWrapper): A file object containing the configuration data.    # fp：一个包含配置数据的文件对象。

        Returns:
            Self: An instance of the class with the configuration data loaded from the file.    #一个带有从文件中加载的配置数据的类的实例。

        Raises:
            ValidationError: If the loaded configuration data fails validation.     #如果加载的配置数据验证失败，则引发 ValidationError 异常。
        """

        import toml     #导入 toml 模块，用于处理 TOML 格式的配置文件。

        return cls.model_validate(toml.load(fp))    #使用 toml 模块从文件对象中加载配置数据，并使用 model_validate 方法验证数据。如果验证成功，则返回一个带有

    @classmethod
    def dump_config(cls, fp: TextIO, config: Self, with_desc: bool = True) -> None:     #dump_config：一个类方法，用于将配置数据写入文件对象。
        """
        Dump the configuration data to a file object.   #将配置数据写入文件对象。

        Args:
            fp (TextIO): The file object to write the configuration data to.    # fp：要写入配置数据的文件对象。
            config (Config): The configuration data to be dumped.           # config：要转储的配置数据。
            with_desc (bool): Whether to add descriptions to the dump file.     # with_desc：是否将描述添加到转储文件中。默认值为 True。
        Returns:
            None
        """
        if with_desc:
            # Extract description and raw data from the config  # 从配置中提取描述和原始数据
            desc_pack: Dict[str, Tuple[str | None, Dict | None]] = extract_description(config)  # desc_pack：一个字典，其中键是字段名称，值是包含字段描述和子模型字段的元组（如果有的话）。
            raw_data = cls.model_dump(config)   # raw_data：一个字典，包含从配置中提取的原始数据。

            # Create a new TOML document    # 创建一个新的 TOML 文档
            data: TOMLDocument = document()     # data：一个 TOMLDocument 类型的实例，表示新的 TOML 文档。
            import kazu     # 导入 kazu 模块，用于获取 Kazu 的版本信息。
            import datetime     # 导入 datetime 模块，用于获取当前时间戳。

            data.add(comment(f"Exported by Kazu-v{kazu.__version__} at {datetime.datetime.now().timestamp()}"))     # 将 Kazu 的版本信息和当前时间戳作为注释添加到 TOML 文档中。

            # Recursive function to inject descriptions into the TOML document  # 递归函数，用于将描述注入 TOML 文档中

            # Inject the descriptions into the TOML document    # 将描述注入 TOML 文档中
            inject_description_into_toml(desc_pack, data, raw_data)
            
            fp.write(dumps(data))    # 将 TOML 文档写入文件对象中。

        else:
            # If no description is needed, just use the raw data    # 如果不需要描述，只需使用原始数据
            pure_data = cls.model_dump(config)  # pure_data：一个字典，包含从配置中提取的原始数据。
            dump(pure_data, fp)     # 将原始数据写入文件对象中。


def inject_description_into_toml(   # inject_description_into_toml：一个函数，用于将描述注入 TOML 文档中。
    desc_pack: Dict[str, Tuple[str | None, Dict | None]],    # desc_pack：一个字典，其中键是字段名称，值是包含字段描述和子模型字段的元组（如果有的话）。
    toml_doc: TOMLDocument,     # toml_doc：一个 TOMLDocument 类型的实例，表示 TOML 文档。
    raw_data: Dict[str, Any],    # raw_data：一个字典，包含从配置中提取的原始数据。
    path: List[str] = None,      # path：一个列表，表示当前处理的字段的路径。默认值为 None，用于递归调用以构建完整的路径。
):
    """
    Injects descriptions into a TOML document.  # 将描述注入 TOML 文档中。

    This function recursively iterates through a dictionary containing description information and sub-model fields.    # 此函数递归地遍历包含描述信息和子模型字段的字典。
    It adds these descriptions as comments to the TOML document. If the current item is a sub-model (i.e., contains     # 它将这些描述作为注释添加到 TOML 文档中。如果当前项是子模型（即，包含子模型字段），则创建一个新的表来处理子模型字段。
    sub-fields), it recursively calls itself to handle the sub-model fields. For non-sub-model items, it adds the   # 对于非子模型项，它将原始数据中相应的值添加到 TOML 文档中。
    description as a comment and retrieves the corresponding value from the raw data to add to the TOML document.

    Parameters:
    - desc_pack: A dictionary where keys are field names and values are tuples containing the description of the field  # desc_pack：一个字典，其中键是字段名称，值是包含字段描述的元组。
      and sub-model fields (if any).
    - toml_doc: A TOMLDocument object representing the TOML document to be modified.    # toml_doc：一个 TOMLDocument 对象，表示要修改的 TOML 文档。
    - raw_data: A dictionary containing the source data from which to retrieve values.  # raw_data：一个字典，包含要从中检索值的源数据。
    - path: A list representing the current path of the field being processed. Defaults to an empty list, used for  # path：一个列表，表示当前正在处理的字段的路径。默认值为空列表，用于递归调用以构建完整的路径。
      recursive calls to build the complete path.

    Returns:
    No return value; the function modifies the provided `toml_doc` parameter directly.  # 无返回值；该函数直接修改提供的 `toml_doc` 参数。
    """

    def _nested_get(k_list: List[str], _dict: dict) -> Any:     # _nested_get：一个内部函数，用于从嵌套字典中检索值。
        cur = _dict.get(k_list.pop(0))  # cur：从嵌套字典中检索的当前值。
        for k in k_list:    # k：嵌套字典中的键。
            cur = cur.get(k)    # cur：从嵌套字典中检索的当前值。

        return cur  # 返回从嵌套字典中检索的当前值。

    # Initialize the path if not provided    # 如果未提供路径，则初始化路径
    if path is None:    # path：一个列表，表示当前正在处理的字段的路径。
        path = []    # 初始化路径为空列表。

    # Iterate through the dictionary of description information and sub-model fields    # 遍历描述信息和子模型字段的字典
    for key, (desc, sub_model_fields) in desc_pack.items():     # key：字段名称。
        # Build the complete path for the current item  # 构建当前项的完整路径
        cur_path = path + [key]     # cur_path：当前项的完整路径。

        # If the current item is a sub-model, add the description (if any) to the TOML document and create a new table  # 如果当前项是子模型，则将描述（如果有）添加到 TOML 文档中，并创建一个新的表
        # to handle the sub-model fields    # 处理子模型字段
        if sub_model_fields:    # sub_model_fields：子模型字段。
            toml_doc.add(comment("#" * 76 + " #"))  # 将描述添加到 TOML 文档中
            if desc:    # desc：字段描述。
                toml_doc.add(comment(desc))        # 将描述添加到 TOML 文档中
                toml_doc.add(nl())  
            toml_doc[key] = (sub_table := table())
            # Recursively call itself to handle the sub-model fields    # 递归调用自身以处理子模型字段
            inject_description_into_toml(sub_model_fields, sub_table, raw_data, cur_path)
            toml_doc.add(nl())      # 添加换行符

        else:
            # If the current item is not a sub-model, add the description    # 如果当前项不是子模型，则添加描述
            toml_doc.add(comment(desc))
            # Retrieve the corresponding value from the raw data and add it to the TOML document    # 从原始数据中检索相应的值并将其添加到 TOML 文档中
            toml_doc[key] = _nested_get(cur_path, raw_data)


class _InternalConfig(BaseModel):
    app_config: APPConfig = APPConfig()     # app_config：应用程序配置。
    app_config_file_path: Path = Path(DEFAULT_APP_CONFIG_PATH)  # app_config_file_path：应用程序配置文件的路径。


def load_run_config(run_config_path: Path | None) -> RunConfig:
    """
    A function that loads the run configuration based on the provided run_config_path.  # 一个根据提供的 run_config_path 加载运行配置的函数。

    Parameters:
        run_config_path (Path | None): The path to the run configuration file.  # run_config_path：运行配置文件的路径。

    Returns:
        RunConfig: The loaded run configuration.    # 运行配置。
    """
    if run_config_path and (r_conf := Path(run_config_path)).exists():  # r_conf：运行配置文件的路径。
        secho(f'Loading run config from "{r_conf.absolute().as_posix()}"', fg="green", bold=True)    # 加载运行配置文件
        with open(r_conf) as fp:
            run_config_path: RunConfig = RunConfig.read_config(fp)  # run_config_path：运行配置文件的路径。
    else:
        secho(f"Loading DEFAULT run config", fg="yellow", bold=True)    # 加载默认运行配置文件
        run_config_path = RunConfig()    # run_config_path：运行配置文件的路径。
    return run_config_path  # 返回运行配置文件


def load_app_config(app_config_path: Path | None) -> APPConfig:     # 一个根据提供的 app_config_path 加载应用程序配置的函数。
    """
    A function that loads the application configuration based on the provided app_config_path.  # 一个根据提供的 app_config_path 加载应用程序配置的函数。

    Parameters: 
        app_config_path (Path | None): The path to the application configuration file.  # app_config_path：应用程序配置文件的路径。

    Returns:
        APPConfig: The loaded application configuration.    # 应用程序配置。
    """
    if app_config_path and app_config_path.exists():     # app_config_path：应用程序配置文件的路径。
        secho(f"Load app config from {app_config_path.absolute().as_posix()}", fg="yellow")     # 加载应用程序配置文件
        with open(app_config_path, encoding="utf-8") as fp:     # fp：应用程序配置文件的路径。
            app_config = APPConfig.read_config(fp)  # app_config：应用程序配置文件。
    else:
        secho(f"Create and load default app config at {app_config_path.absolute().as_posix()}", fg="yellow")    # 创建并加载默认应用程序配置文件
        app_config_path.parent.mkdir(parents=True, exist_ok=True)    # app_config_path：应用程序配置文件的路径。
        app_config = APPConfig()    # app_config：应用程序配置文件。
        with open(app_config_path, "w", encoding="utf-8") as fp:     # fp：应用程序配置文件的路径。
            APPConfig.dump_config(fp, app_config)    # 将应用程序配置文件写入文件中。
    return app_config    # 返回应用程序配置文件。


def extract_description(model: Type[BaseModel]) -> Dict[str, Any]:   # 一个根据提供的模型提取描述信息的函数。
    """
    Recursively extracts description information from a given model.    # 递归地从给定的模型中提取描述信息。

    This function first extracts the information of all fields in the model (including field names and related info).   #这个函数首先提取模型中所有字段的信息（包括字段名称和相关信息）。然后，它遍历每个字段，处理其信息。
    It then iterates through each field, processing its information. For each field, if the associated model is None,   #对于每个字段，如果关联的模型为 None，它将字段的描述和 None 值打包到结果字典中。否则，它将字段的描述和递归提取的子模型描述信息打包到结果字典中。
    it packs the field's description and None value into the result dictionary. Otherwise, it packs the field's     #函数返回一个字典，其中键是字段名称，值是包含字段描述和其关联模型描述（或 None）的元组
    description and the recursively extracted sub-model description information into the result dictionary.
    The function returns a dictionary where keys are field names and values are tuples containing the field's
    description and its associated model description (or None).

    Parameters:
        model: Type[BaseModel] - A class that inherits from BaseModel, representing some data structure or schema.  # model：Type[BaseModel] - 一个继承自 BaseModel 的类，表示某种数据结构或模式。

    Returns:
        Dict[str, Any] - A dictionary containing field names and their descriptions along with the associated model     # 返回一个字典，其中包含字段名称及其描述以及关联的模型描述（或 None）。
                       description (or None).
    """

    def _extract(model_field: FieldInfo) -> Tuple[str, Optional[Type[BaseModel]]]:   # 一个根据提供的模型字段提取描述信息的函数。

        ano = model_field.annotation    # ano：模型字段的注释。

        is_model = False    # is_model：模型字段是否为模型。

        try:
            is_model = issubclass(ano, BaseModel)    # is_model：模型字段是否为模型。
        except:
            pass

        return model_field.description, ano if is_model else None    # 返回模型字段的描述和其关联的模型描述（或 None）。

    # Extract all fields and their related information from the model   # 从模型中提取所有字段及其相关信息。
    temp = {f_name: _extract(info) for f_name, info in model.model_fields.items()}
    # Initialize the final container dictionary to store processed field descriptions and related info  # 初始化最终容器字典，以存储处理过的字段描述和相关信息。
    fi_container = {}
    # Iterate through preprocessed field information    # 遍历预处理过的字段信息。
    for f_name, pack in temp.items():
        # Unpack the field information, including description and possible sub-model    # 解包字段信息，包括描述和可能的子模型。
        desc, model = pack
        # If the field does not have an associated sub-model, store the description and None value  # 如果字段没有关联的子模型，将字段的描述和 None 值打包到结果字典中。
        if model is None:
            fi_container[f_name] = pack     # fi_container：最终容器字典，以存储处理过的字段描述和相关信息。
        else:
            # If the field has an associated sub-model, store the description and recursively extracted sub-model info  # 如果字段有关联的子模型，将字段的描述和递归提取的子模型信息打包到结果字典中。
            fi_container[f_name] = desc, extract_description(model)     # fi_container：最终容器字典，以存储处理过的字段描述和相关信息。

    return fi_container     # 返回最终容器字典，以存储处理过的字段描述和相关信息。
