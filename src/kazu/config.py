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

    def __hash__(self) -> int:  #__hash__ �������ض�����ڴ��ַ�Ĺ�ϣֵ���������ͨ�������ڹ�ϣ���д洢�����Ա���ٲ��ҡ�
        return id(self)

    def __eq__(self, other) -> bool:    # __eq__ �������ڱȽ����������Ƿ���ȡ�����������У����ǱȽϵ��Ƕ�����ڴ��ַ�������Ƕ����ֵ��
        return id(self) == id(other)

    def __int__(self) -> int:   # __int__ �������ڽ�����ת��Ϊ����������������У����Ƿ��ض�����ڴ��ַ�Ĺ�ϣֵ��
        return id(self)


class TagGroup(BaseModel):  # TagGroup ��̳��� BaseModel �࣬���ڴ洢��ǩ�����Ϣ��
    team_color: Literal["yellow", "blue"] | str     # team_color �ֶ���һ���ַ�������ʾ�������ɫ���������� "yellow" �� "blue"��
    enemy_tag: Literal[1, 2] = None     # enemy_tag �ֶ���һ����������ʾ���˵ı�ǩ���������� 1 �� 2��
    allay_tag: Literal[1, 2] = None     # allay_tag �ֶ���һ����������ʾ���ѵı�ǩ���������� 1 �� 2��
    neutral_tag: Literal[0] = 0     # neutral_tag �ֶ���һ����������ʾ�����ı�ǩ����ֻ���� 0��
    default_tag: int = TagDetector.Config.default_tag_id    # default_tag �ֶ���һ����������ʾĬ�ϵı�ǩ����Ĭ���� TagDetector.Config.default_tag_id��

    def __init__(self, /, **data: Any):     # __init__ ��������Ĺ��캯�������ڳ�ʼ����������������У����ǵ����˸���Ĺ��캯������������ enemy_tag �� allay_tag �ֶΡ�
        super().__init__(**data)    # ���ø���Ĺ��캯���������� data ������

        match self.team_color:  # match �������ƥ�� team_color �ֶε�ֵ�������ݲ�ͬ��ֵ���� enemy_tag �� allay_tag �ֶΡ�
            case "yellow":
                self.enemy_tag = 1  # ��� team_color �� "yellow"�������� enemy_tag Ϊ 1��
                self.allay_tag = 2  # ��� team_color �� "yellow"�������� allay_tag Ϊ 2��
            case "blue":
                self.enemy_tag = 2  # ��� team_color �� "blue"�������� enemy_tag Ϊ 2��
                self.allay_tag = 1  # ��� team_color �� "blue"�������� allay_tag Ϊ 1��
            case _:
                raise ValueError(f"Invalid team_color, got {self.team_color}")  # ��� team_color ���� "yellow" �� "blue"�����׳�һ�� ValueError �쳣��
        _logger.debug(f"{Fore.MAGENTA}Team color: {self.team_color}{Fore.RESET}")   # ��ӡ team_color �ֶε�ֵ��


class EdgeConfig(BaseModel):
    lower_threshold: Tuple[float, float, float, float] = Field(     # lower_threshold �ֶ���һ��Ԫ�飬��ʾ��Ե��������ֵ����Ĭ���� (1740, 1819, 1819, 1740)��
        default=(1740, 1819, 1819, 1740),   # lower_threshold �ֶε�Ĭ��ֵ�� (1740, 1819, 1819, 1740)��
        description="Lower threshold values for edge detection.",   # lower_threshold �ֶε������� "Lower threshold values for edge detection."��
    )
    upper_threshold: Tuple[float, float, float, float] = Field(
        default=(2100, 2470, 2470, 2100), description="Upper threshold values for edge detection."  # upper_threshold �ֶε�Ĭ��ֵ�� (2100, 2470, 2470, 2100)��
    )

    fallback_speed: PositiveInt = Field(default=2600, description="Speed when falling back.")   # fallback_speed �ֶ���һ����������ʾ���˵��ٶȡ���Ĭ���� 2600��
    fallback_duration: PositiveFloat = Field(default=0.2, description="Duration of the fallback action.")   # fallback_duration �ֶ���һ������������ʾ���˶����ĳ���ʱ�䡣��Ĭ���� 0.2��

    advance_speed: PositiveInt = Field(default=2400, description="Speed when advancing.")   # advance_speed �ֶ���һ����������ʾǰ�����ٶȡ���Ĭ���� 2400��
    advance_duration: PositiveFloat = Field(default=0.35, description="Duration of the advance action.")    # advance_duration �ֶ���һ������������ʾǰ�������ĳ���ʱ�䡣��Ĭ���� 0.35��

    turn_speed: PositiveInt = Field(default=2800, description="Speed when turning.")    # turn_speed �ֶ���һ����������ʾת����ٶȡ���Ĭ���� 2800��
    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")     # full_turn_duration �ֶ���һ������������ʾȫת���ĳ���ʱ�䡣��Ĭ���� 0.45��
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")    # half_turn_duration �ֶ���һ������������ʾ��ת���ĳ���ʱ�䡣��Ĭ���� 0.225��

    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob �ֶ���һ������������ʾ��ת�ĸ��ʡ���Ĭ���� 0.5��

    drift_speed: PositiveInt = Field(default=1500, description="Speed when drifting.")  # drift_speed �ֶ���һ����������ʾƯ�Ƶ��ٶȡ���Ĭ���� 1500��
    drift_duration: PositiveFloat = Field(default=0.13, description="Duration of the drift action.")    # drift_duration �ֶ���һ������������ʾƯ�ƶ����ĳ���ʱ�䡣��Ĭ���� 0.13��

    use_gray_io: bool = Field(default=True, description="Whether to use gray IO for detection.") # use_gray_io �ֶ���һ������ֵ����ʾ�Ƿ�ʹ�ûҶ� IO ���м�⡣��Ĭ���� True��


class SurroundingConfig(BaseModel):
    io_encounter_object_value: int = Field(default=0, description="IO value when encountering an object.")  # io_encounter_object_value �ֶ���һ����������ʾ��������ʱ�� IO ֵ����Ĭ���� 0��

    left_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the left sensor.", gt=0, lt=4096     # left_adc_lower_threshold �ֶ���һ����������ʾ�󴫸����� ADC ����ֵ����Ĭ���� 1000��
    )
    right_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the right sensor.", gt=0, lt=4096    # right_adc_lower_threshold �ֶ���һ����������ʾ�Ҵ������� ADC ����ֵ����Ĭ���� 1000��
    )

    front_adc_lower_threshold: int = Field(
        default=1000, description="ADC lower threshold for the front sensor.", gt=0, lt=4096    # front_adc_lower_threshold �ֶ���һ����������ʾǰ�������� ADC ����ֵ����Ĭ���� 1000��
    )
    back_adc_lower_threshold: int = Field(
        default=1100, description="ADC lower threshold for the back sensor.", gt=0, lt=4096     # back_adc_lower_threshold �ֶ���һ����������ʾ�󴫸����� ADC ����ֵ����Ĭ���� 1100��
    )

    atk_break_front_lower_threshold: int = Field(
        default=1500, description="Front ADC lower threshold for attack break.", gt=0, lt=4096  # atk_break_front_lower_threshold �ֶ���һ����������ʾ�����жϵ�ǰ ADC ����ֵ����Ĭ���� 1500��
    )

    atk_break_use_edge_sensors: bool = Field(default=True, description="Whether to use edge sensors for attack break.")     # atk_break_use_edge_sensors �ֶ���һ������ֵ����ʾ�Ƿ�ʹ�ñ�Ե���������й����жϡ���Ĭ���� True��

    atk_speed_enemy_car: PositiveInt = Field(default=2300, description="Attack speed for enemy car.")   # atk_speed_enemy_car �ֶ���һ����������ʾ�Եз������Ĺ����ٶȡ���Ĭ���� 2300��
    atk_speed_enemy_box: PositiveInt = Field(default=2500, description="Attack speed for enemy box.")   # atk_speed_enemy_box �ֶ���һ����������ʾ�Եз����ӵĹ����ٶȡ���Ĭ���� 2500��
    atk_speed_neutral_box: PositiveInt = Field(default=2500, description="Attack speed for neutral box.")    # atk_speed_neutral_box �ֶ���һ����������ʾ���������ӵĹ����ٶȡ���Ĭ���� 2500��
    fallback_speed_ally_box: PositiveInt = Field(default=2900, description="Fallback speed for ally box.")  # fallback_speed_ally_box �ֶ���һ����������ʾ���ѷ����ӵĺ����ٶȡ���Ĭ���� 2900��
    fallback_speed_edge: PositiveInt = Field(default=2400, description="Fallback speed for edge.")  # fallback_speed_edge �ֶ���һ����������ʾ�Ա�Ե�ĺ����ٶȡ���Ĭ���� 2400��

    atk_enemy_car_duration: PositiveFloat = Field(default=4.2, description="Duration of attack on enemy car.")  # atk_enemy_car_duration �ֶ���һ������������ʾ�Եз������Ĺ�������ʱ�䡣��Ĭ���� 4.2��
    atk_enemy_box_duration: PositiveFloat = Field(default=3.6, description="Duration of attack on enemy box.")  # atk_enemy_box_duration �ֶ���һ������������ʾ�Եз����ӵĹ�������ʱ�䡣��Ĭ���� 3.6��
    atk_neutral_box_duration: PositiveFloat = Field(default=3.6, description="Duration of attack on neutral box.")  # atk_neutral_box_duration �ֶ���һ������������ʾ���������ӵĹ�������ʱ�䡣��Ĭ���� 3.6��
    fallback_duration_ally_box: PositiveFloat = Field(default=0.3, description="Duration of fallback for ally box.")    # fallback_duration_ally_box �ֶ���һ������������ʾ���ѷ����ӵĺ��˳���ʱ�䡣��Ĭ���� 0.3��
    fallback_duration_edge: PositiveFloat = Field(default=0.2, description="Duration of fallback for edge.")    # fallback_duration_edge �ֶ���һ������������ʾ�Ա�Ե�ĺ��˳���ʱ�䡣��Ĭ���� 0.2��

    turn_speed: NonNegativeInt = Field(default=2900, description="Speed when turning.")     # turn_speed �ֶ���һ���Ǹ���������ʾת����ٶȡ���Ĭ���� 2900��
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob �ֶ���һ������������ʾ��ת�ĸ��ʡ���Ĭ���� 0.5��

    turn_to_front_use_front_sensor: bool = Field(
        default=False, description="Whether to use the front sensor for turning to front."  # turn_to_front_use_front_sensor �ֶ���һ������ֵ����ʾ�Ƿ�ʹ��ǰ����������ת����Ĭ���� False��
    )

    rand_turn_speeds: List[NonNegativeInt] = Field(default=[1600, 2100, 3000], description="Random turn speeds.")   # rand_turn_speeds �ֶ���һ���Ǹ������б���ʾ���ת���ٶȡ���Ĭ���� [1600, 2100, 3000]��
    rand_turn_speed_weights: List[float] = Field(default=[2, 3, 1], description="Weights for random turn speeds.")   # rand_turn_speed_weights �ֶ���һ���������б���ʾ���ת���ٶȵ�Ȩ�ء���Ĭ���� [2, 3, 1]��

    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")     # full_turn_duration �ֶ���һ������������ʾȫת�ĳ���ʱ�䡣��Ĭ���� 0.45��
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")    # half_turn_duration �ֶ���һ������������ʾ��ת�ĳ���ʱ�䡣��Ĭ���� 0.225��


class GradientConfig(BaseModel):
    max_speed: PositiveInt = Field(default=2800, description="Maximum speed for gradient move.")    # max_speed �ֶ���һ������������ʾ�ݶ��ƶ�������ٶȡ���Ĭ���� 2800��
    min_speed: NonNegativeInt = Field(default=500, description="Minimum speed for gradient move.")  # min_speed �ֶ���һ���Ǹ���������ʾ�ݶ��ƶ�����С�ٶȡ���Ĭ���� 500��
    lower_bound: int = Field(default=2900, description="Lower bound for gradient move.", gt=0, lt=4096)     # lower_bound �ֶ���һ����������ʾ�ݶ��ƶ������ޡ���Ĭ���� 2900��
    upper_bound: int = Field(default=3700, description="Upper bound for gradient move.", gt=0, lt=4096)     # upper_bound �ֶ���һ����������ʾ�ݶ��ƶ������ޡ���Ĭ���� 3700��


class ScanConfig(BaseModel):

    front_max_tolerance: int = Field(default=760, description="Maximum tolerance for the front sensor.", gt=0, lt=4096)     # front_max_tolerance �ֶ���һ����������ʾǰ������������ݲ��Ĭ���� 760��
    rear_max_tolerance: int = Field(default=760, description="Maximum tolerance for the rear sensor.", gt=0, lt=4096)      # rear_max_tolerance �ֶ���һ����������ʾ�󴫸���������ݲ��Ĭ���� 760��
    left_max_tolerance: int = Field(default=760, description="Maximum tolerance for the left sensor.", gt=0, lt=4096)      # left_max_tolerance �ֶ���һ����������ʾ�󴫸���������ݲ��Ĭ���� 760��
    right_max_tolerance: int = Field(default=760, description="Maximum tolerance for the right sensor.", gt=0, lt=4096)     # right_max_tolerance �ֶ���һ����������ʾ�Ҵ�����������ݲ��Ĭ���� 760��

    io_encounter_object_value: int = Field(default=0, description="IO value when encountering an object.")  # io_encounter_object_value �ֶ���һ����������ʾ��������ʱ�� IO ֵ����Ĭ���� 0��

    scan_speed: PositiveInt = Field(default=300, description="Speed for scanning.")     # scan_speed �ֶ���һ������������ʾɨ����ٶȡ���Ĭ���� 300��
    scan_duration: PositiveFloat = Field(default=4.5, description="Duration of the scan action.")    # scan_duration �ֶ���һ������������ʾɨ�趯���ĳ���ʱ�䡣��Ĭ���� 4.5��
    scan_turn_left_prob: float = Field(
        default=0.5, description="Probability of turning left during scan.", ge=0, le=1.0   # scan_turn_left_prob �ֶ���һ������������ʾɨ���������ת�ĸ��ʡ���Ĭ���� 0.5��
    )

    fall_back_speed: PositiveInt = Field(default=3250, description="Speed for falling back.")      # fall_back_speed �ֶ���һ������������ʾ���˵��ٶȡ���Ĭ���� 3250��
    fall_back_duration: float = Field(default=0.2, description="Duration of the fall back action.")     # fall_back_duration �ֶ���һ������������ʾ���˶����ĳ���ʱ�䡣��Ĭ���� 0.2��

    turn_speed: PositiveInt = Field(default=2700, description="Speed when turning.")        # turn_speed �ֶ���һ������������ʾת����ٶȡ���Ĭ���� 2700��
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob �ֶ���һ������������ʾ��ת�ĸ��ʡ���Ĭ���� 0.5��

    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration of a full turn.")     # full_turn_duration �ֶ���һ������������ʾȫת�ĳ���ʱ�䡣��Ĭ���� 0.45��
    half_turn_duration: PositiveFloat = Field(default=0.225, description="Duration of a half turn.")    # half_turn_duration �ֶ���һ������������ʾ��ת�ĳ���ʱ�䡣��Ĭ���� 0.225��

    check_edge_before_scan: bool = Field(default=True, description="Whether to check edge before scanning.")    # check_edge_before_scan �ֶ���һ������ֵ����ʾ�Ƿ���ɨ��֮ǰ����Ե����Ĭ���� True��
    check_gray_adc_before_scan: bool = Field(default=True, description="Whether to check gray ADC before scanning.")    # check_gray_adc_before_scan �ֶ���һ������ֵ����ʾ�Ƿ���ɨ��֮ǰ���Ҷ� ADC����Ĭ���� True��
    gray_adc_lower_threshold: int = Field(
        default=3100, description="Gray ADC lower threshold for scanning.", gt=0, lt=4096   # gray_adc_lower_threshold �ֶ���һ����������ʾɨ��ĻҶ� ADC ���ޡ���Ĭ���� 3100��
    )


class RandTurn(BaseModel):

    turn_speed: PositiveInt = Field(default=2300, description="Speed when turning.")        # turn_speed �ֶ���һ������������ʾת����ٶȡ���Ĭ���� 2300��
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)        # turn_left_prob �ֶ���һ������������ʾ��ת�ĸ��ʡ���Ĭ���� 0.5��
    full_turn_duration: PositiveFloat = Field(default=0.25, description="Duration of a full turn.")        # full_turn_duration �ֶ���һ������������ʾȫת�ĳ���ʱ�䡣��Ĭ���� 0.25��
    half_turn_duration: PositiveFloat = Field(default=0.15, description="Duration of a half turn.")        # half_turn_duration �ֶ���һ������������ʾ��ת�ĳ���ʱ�䡣��Ĭ���� 0.15��

    use_turn_to_front: bool = Field(default=True, description="Whether to use turning to front.")        # use_turn_to_front �ֶ���һ������ֵ����ʾ�Ƿ�ʹ������ǰ����ת�䡣��Ĭ���� True��


class SearchConfig(BaseModel):

    use_gradient_move: bool = Field(default=True, description="Whether to use gradient move.")  # use_gradient_move �ֶ���һ������ֵ����ʾ�Ƿ�ʹ���ݶ��ƶ�����Ĭ���� True��
    gradient_move_weight: PositiveFloat = Field(default=100, description="Weight for gradient move.")    # gradient_move_weight �ֶ���һ��������������ʾ�ݶ��ƶ���Ȩ�ء���Ĭ���� 100��
    use_scan_move: bool = Field(default=True, description="Whether to use scan move.")  # use_scan_move �ֶ���һ������ֵ����ʾ�Ƿ�ʹ��ɨ���ƶ�����Ĭ���� True��
    scan_move_weight: PositiveFloat = Field(default=1.96, description="Weight for scan move.")  # scan_move_weight �ֶ���һ��������������ʾɨ���ƶ���Ȩ�ء���Ĭ���� 1.96��
    use_rand_turn: bool = Field(default=True, description="Whether to use random turn.")    # use_rand_turn �ֶ���һ������ֵ����ʾ�Ƿ�ʹ�����ת�䡣��Ĭ���� True��
    rand_turn_weight: PositiveFloat = Field(default=0.05, description="Weight for random turn.")    # rand_turn_weight �ֶ���һ��������������ʾ���ת���Ȩ�ء���Ĭ���� 0.05��

    gradient_move: GradientConfig = Field(default=GradientConfig(), description="Configuration for gradient move.")     # gradient_move �ֶ���һ�� GradientConfig ���󣬱�ʾ�ݶ��ƶ������á���Ĭ����һ���յ� GradientConfig ����
    scan_move: ScanConfig = Field(default=ScanConfig(), description="Configuration for scan move.")     # scan_move �ֶ���һ�� ScanConfig ���󣬱�ʾɨ���ƶ������á���Ĭ����һ���յ� ScanConfig ����
    rand_turn: RandTurn = Field(default=RandTurn(), description="Configuration for random turn.")   # rand_turn �ֶ���һ�� RandTurn ���󣬱�ʾ���ת������á���Ĭ����һ���յ� RandTurn ����


class RandWalk(BaseModel):

    use_straight: bool = Field(default=True, description="Whether to use straight movement.")   # use_straight �ֶ���һ������ֵ����ʾ�Ƿ�ʹ��ֱ���ƶ�����Ĭ���� True��
    straight_weight: PositiveFloat = Field(default=2, description="Weight for straight movement.")  # straight_weight �ֶ���һ��������������ʾֱ���ƶ���Ȩ�ء���Ĭ���� 2��

    rand_straight_speeds: List[int] = Field(default=[-800, -500, 500, 800], description="Random straight speeds.")  # rand_straight_speeds �ֶ���һ�������б���ʾ���ֱ���ٶȡ���Ĭ���� [-800, -500, 500, 800]
    rand_straight_speed_weights: List[float] = Field(
        default=[1, 3, 3, 1], description="Weights for random straight speeds."     # rand_straight_speed_weights �ֶ���һ���������б���ʾ���ֱ���ٶȵ�Ȩ�ء���Ĭ���� [1, 3, 3, 1]
    )

    use_turn: bool = Field(default=True, description="Whether to use turning.")     # use_turn �ֶ���һ������ֵ����ʾ�Ƿ�ʹ��ת�䡣��Ĭ���� True��
    turn_weight: float = Field(default=1, description="Weight for turning.")    # turn_weight �ֶ���һ������������ʾת���Ȩ�ء���Ĭ���� 1��
    rand_turn_speeds: List[int] = Field(default=[-1200, -800, 800, 1200], description="Random turn speeds.")    # rand_turn_speeds �ֶ���һ�������б���ʾ���ת���ٶȡ���Ĭ���� [-1200, -800, 800, 1200]
    rand_turn_speed_weights: List[float] = Field(default=[1, 3, 3, 1], description="Weights for random turn speeds.")   # rand_turn_speed_weights �ֶ���һ���������б���ʾ���ת���ٶȵ�Ȩ�ء���Ĭ���� [1, 3, 3, 1]

    walk_duration: PositiveFloat = Field(default=0.3, description="Duration of walking.")   # walk_duration �ֶ���һ��������������ʾ���ߵĳ���ʱ�䡣��Ĭ���� 0.3��


class FenceConfig(BaseModel):
    front_adc_lower_threshold: int = Field(default=900, description="Front ADC lower threshold.")   # front_adc_lower_threshold �ֶ���һ����������ʾǰ���� ADC ���ޡ���Ĭ���� 900��
    rear_adc_lower_threshold: int = Field(default=1100, description="Rear ADC lower threshold.")    # rear_adc_lower_threshold �ֶ���һ����������ʾ�󷽵� ADC ���ޡ���Ĭ���� 1100��
    left_adc_lower_threshold: int = Field(default=900, description="Left ADC lower threshold.")     # left_adc_lower_threshold �ֶ���һ����������ʾ�󷽵� ADC ���ޡ���Ĭ���� 900��
    right_adc_lower_threshold: int = Field(default=900, description="Right ADC lower threshold.")   # right_adc_lower_threshold �ֶ���һ����������ʾ�ҷ��� ADC ���ޡ���Ĭ���� 900��

    io_encounter_fence_value: int = Field(default=0, description="IO value when encountering a fence.")     # io_encounter_fence_value �ֶ���һ����������ʾ����դ��ʱ�� IO ֵ����Ĭ���� 0��
    max_yaw_tolerance: PositiveFloat = Field(default=20.0, description="Maximum yaw tolerance.")    # max_yaw_tolerance �ֶ���һ��������������ʾ���ƫ���ݲ��Ĭ���� 20.0��

    use_mpu_align_stage: bool = Field(default=False, description="Whether to use MPU for aligning stage.")  # use_mpu_align_stage �ֶ���һ������ֵ����ʾ�Ƿ�ʹ�� MPU ������̨����Ĭ���� False��
    use_mpu_align_direction: bool = Field(default=False, description="Whether to use MPU for aligning direction.")  # use_mpu_align_direction �ֶ���һ������ֵ����ʾ�Ƿ�ʹ�� MPU ���뷽����Ĭ���� False��

    stage_align_speed: PositiveInt = Field(default=850, description="Speed for aligning stage.")    # stage_align_speed �ֶ���һ������������ʾ������̨���ٶȡ���Ĭ���� 850��
    max_stage_align_duration: PositiveFloat = Field(default=4.5, description="Maximum duration for aligning stage.")    # max_stage_align_duration �ֶ���һ��������������ʾ������̨��������ʱ�䡣��Ĭ���� 4.5��
    stage_align_direction: Literal["l", "r", "rand"] = Field(
        default="rand", description='Turn direction for aligning stage, allow ["l", "r", "rand"].'  # stage_align_direction �ֶ���һ���ַ�������ʾ������̨��ת������Ĭ���� "rand"����ʾ�������
    )

    direction_align_speed: PositiveInt = Field(default=850, description="Speed for aligning direction.")    # direction_align_speed �ֶ���һ������������ʾ���뷽����ٶȡ���Ĭ���� 850��
    max_direction_align_duration: PositiveFloat = Field(
        default=4.5, description="Maximum duration for aligning direction."     # max_direction_align_duration �ֶ���һ��������������ʾ���뷽���������ʱ�䡣��Ĭ���� 4.5��
    )
    direction_align_direction: Literal["l", "r", "rand"] = Field(   # direction_align_direction �ֶ���һ���ַ�������ʾ���뷽���ת������Ĭ���� "rand"����ʾ�������
        default="rand",
        description='Turn direction for aligning the parallel or vertical direction to the stage,  allow ["l", "r", "rand"].',  #���������������ȷ��������̨ƽ�л�ֱ�����ת���������ֵ�� "l"���󣩡�"r"���ң��� "rand"���������
    )

    exit_corner_speed: PositiveInt = Field(default=1200, description="Speed for exiting corner.")    # exit_corner_speed �ֶ���һ������������ʾ�˳�������ٶȡ���Ĭ���� 1200��
    max_exit_corner_duration: PositiveFloat = Field(default=1.5, description="Maximum duration for exiting corner.")    # max_exit_corner_duration �ֶ���һ��������������ʾ�˳������������ʱ�䡣��Ĭ���� 1.5��

    rand_walk: RandWalk = Field(default=RandWalk(), description="Configuration for random walk.")    # rand_walk �ֶ���һ�� RandWalk ���󣬱�ʾ������ߵ����á���Ĭ���� RandWalk() ����


class StrategyConfig(BaseModel):
    use_edge_component: bool = Field(default=True, description="Whether to use edge component.")    # use_edge_component �ֶ���һ������ֵ����ʾ�Ƿ�ʹ�ñ�Ե�������Ĭ���� True��
    use_surrounding_component: bool = Field(default=True, description="Whether to use surrounding component.")  # use_surrounding_component �ֶ���һ������ֵ����ʾ�Ƿ�ʹ����Χ�������Ĭ���� True��
    use_normal_component: bool = Field(default=True, description="Whether to use normal component.")    # use_normal_component �ֶ���һ������ֵ����ʾ�Ƿ�ʹ����ͨ�������Ĭ���� True��


class PerformanceConfig(BaseModel):
    checking_duration: NonNegativeFloat = Field(default=0.0, description="Duration for checking.")  # checking_duration �ֶ���һ���Ǹ�����������ʾ���ĳ���ʱ�䡣��Ĭ���� 0.0��


class BootConfig(BaseModel):
    button_io_activate_case_value: int = Field(default=0, description="Button IO value for activating case.")    # button_io_activate_case_value �ֶ���һ����������ʾ��������İ�ť IO ֵ����Ĭ���� 0��

    time_to_stabilize: PositiveFloat = Field(default=0.1, description="Time to stabilize after activation.")    # time_to_stabilize �ֶ���һ��������������ʾ�������ȶ�ʱ�䡣��Ĭ���� 0.1��

    max_holding_duration: PositiveFloat = Field(default=180.0, description="Maximum holding duration.")     # max_holding_duration �ֶ���һ��������������ʾ��󱣳ֳ���ʱ�䡣��Ĭ���� 180.0��

    left_threshold: int = Field(default=1100, description="Threshold for left sensor.")     # left_threshold �ֶ���һ����������ʾ�󷽵���ֵ����Ĭ���� 1100��
    right_threshold: int = Field(default=1100, description="Threshold for right sensor.")    # right_threshold �ֶ���һ����������ʾ�ҷ�����ֵ����Ĭ���� 1100��

    dash_speed: PositiveInt = Field(default=7000, description="Speed for dashing.")     # dash_speed �ֶ���һ������������ʾ��̵��ٶȡ���Ĭ���� 7000��
    dash_duration: PositiveFloat = Field(default=0.55, description="Duration for dashing.")     # dash_duration �ֶ���һ��������������ʾ��̵ĳ���ʱ�䡣��Ĭ���� 0.55��

    turn_speed: PositiveInt = Field(default=2150, description="Speed for turning.")     # turn_speed �ֶ���һ������������ʾת����ٶȡ���Ĭ���� 2150��
    full_turn_duration: PositiveFloat = Field(default=0.45, description="Duration for a full turn.")    # full_turn_duration �ֶ���һ��������������ʾȫת�ĳ���ʱ�䡣��Ĭ���� 0.45��
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob �ֶ���һ������������ʾ��ת�ĸ��ʡ���Ĭ���� 0.5�����ұ����� 0 �� 1.0 ֮�䡣


class BackStageConfig(BaseModel):
    time_to_stabilize: PositiveFloat = Field(default=0.1, description="Time to stabilize after activation.")    # time_to_stabilize �ֶ���һ��������������ʾ�������ȶ�ʱ�䡣��Ĭ���� 0.1��

    small_advance_speed: PositiveInt = Field(default=1500, description="Speed for small advance.")  # small_advance_speed �ֶ���һ������������ʾСǰ�е��ٶȡ���Ĭ���� 1500��
    small_advance_duration: PositiveFloat = Field(default=0.6, description="Duration for small advance.")    # small_advance_duration �ֶ���һ��������������ʾСǰ�еĳ���ʱ�䡣��Ĭ���� 0.6��

    dash_speed: PositiveInt = Field(default=7000, description="Speed for dashing.")     # dash_speed �ֶ���һ������������ʾ��̵��ٶȡ���Ĭ���� 7000��
    dash_duration: PositiveFloat = Field(default=0.55, description="Duration for dashing.")     # dash_duration �ֶ���һ��������������ʾ��̵ĳ���ʱ�䡣��Ĭ���� 0.55��

    turn_speed: PositiveInt = Field(default=2600, description="Speed for turning.")     # turn_speed �ֶ���һ������������ʾת����ٶȡ���Ĭ���� 2600��
    full_turn_duration: PositiveFloat = Field(default=0.35, description="Duration for a full turn.")    # full_turn_duration �ֶ���һ��������������ʾȫת�ĳ���ʱ�䡣��Ĭ���� 0.35��
    turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # turn_left_prob �ֶ���һ������������ʾ��ת�ĸ��ʡ���Ĭ���� 0.5�����ұ����� 0 �� 1.0 ֮�䡣

    use_is_on_stage_check: bool = Field(default=True, description="Whether to check if on stage.")  # use_is_on_stage_check �ֶ���һ������ֵ����ʾ�Ƿ����Ƿ�����̨�ϡ���Ĭ���� True��
    use_side_away_check: bool = Field(
        default=True, description="Whether to check side away after the is_on_stage check."     # use_side_away_check �ֶ���һ������ֵ����ʾ�Ƿ��� is_on_stage ��������ơ���Ĭ���� True��
    )
    check_start_percent: PositiveFloat = Field(
        default=0.9,
        description="defining when does the is_on_stage check being brought on during the dashing. DO NOT set it too small!",   # check_start_percent �ֶ���һ��������������ʾ�ڳ���ڼ��ʱ���� is_on_stage ��顣��Ҫ���õ�̫С��
        lt=1.0,
    )

    side_away_degree_tolerance: PositiveFloat = Field(default=10.0, description="Degree tolerance for side away.")  # side_away_degree_tolerance �ֶ���һ��������������ʾ���ƵĶ����ݲ��Ĭ���� 10.0��
    exit_side_away_speed: PositiveInt = Field(default=1300, description="Speed for exiting side away.")        # exit_side_away_speed �ֶ���һ������������ʾ�˳����Ƶ��ٶȡ���Ĭ���� 1300��
    exit_side_away_duration: PositiveFloat = Field(default=0.6, description="Duration for exiting side away.")    # exit_side_away_duration �ֶ���һ��������������ʾ�˳����Ƶĳ���ʱ�䡣��Ĭ���� 0.6��


class StageConfig(BaseModel): 
    gray_adc_off_stage_upper_threshold: int = Field(default=2630, description="Upper threshold for gray ADC off stage.")    # gray_adc_off_stage_upper_threshold �ֶ���һ����������ʾ��̨��Ҷ� ADC ��������ֵ����Ĭ���� 2630��
    gray_adc_on_stage_lower_threshold: int = Field(default=2830, description="Lower threshold for gray ADC on stage.")    # gray_adc_on_stage_lower_threshold �ֶ���һ����������ʾ��̨�ϻҶ� ADC ��������ֵ����Ĭ���� 2830��
    unclear_zone_tolerance:int = Field(default=90, description="Tolerance for judging if the car is on stage in unclear zone state.")    # unclear_zone_tolerance �ֶ���һ����������ʾ��ģ������״̬���ж������Ƿ�����̨�ϵ��ݲ��Ĭ���� 90��
    unclear_zone_turn_speed: PositiveInt = Field(default=1500, description="Speed for turning in unclear zone.")    # unclear_zone_turn_speed �ֶ���һ������������ʾ��ģ������״̬�µ�ת���ٶȡ���Ĭ���� 1500��
    unclear_zone_turn_duration: PositiveFloat = Field(default=0.6, description="Duration for turning in unclear zone.")     # unclear_zone_turn_duration �ֶ���һ��������������ʾ��ģ������״̬�µ�ת�����ʱ�䡣��Ĭ���� 0.6��
    unclear_zone_turn_left_prob: float = Field(default=0.5, description="Probability of turning left.", ge=0, le=1.0)    # unclear_zone_turn_left_prob �ֶ���һ������������ʾ��ģ������״̬����ת�ĸ��ʡ���Ĭ���� 0.5�����ұ����� 0 �� 1.0 ֮�䡣
    gray_io_off_stage_case_value: int = Field(default=0, description="IO value for gray off stage.")    # gray_io_off_stage_case_value �ֶ���һ����������ʾ�Ҷ���̨��� IO ֵ����Ĭ���� 0��


class RunConfig(CounterHashable):
    strategy: StrategyConfig = StrategyConfig()     # strategy �ֶ���һ�� StrategyConfig ���͵�ʵ������ʾ�������á���Ĭ���� StrategyConfig ���͵�ʵ����
    boot: BootConfig = BootConfig()     # boot �ֶ���һ�� BootConfig ���͵�ʵ������ʾ�������á���Ĭ���� BootConfig ���͵�ʵ����
    backstage: BackStageConfig = BackStageConfig()   # backstage �ֶ���һ�� BackStageConfig ���͵�ʵ������ʾ��̨���á���Ĭ���� BackStageConfig ���͵�ʵ����
    stage: StageConfig = StageConfig()  # stage �ֶ���һ�� StageConfig ���͵�ʵ������ʾ��̨���á���Ĭ���� StageConfig ���͵�ʵ����
    edge: EdgeConfig = EdgeConfig()     # edge �ֶ���һ�� EdgeConfig ���͵�ʵ������ʾ��Ե���á���Ĭ���� EdgeConfig ���͵�ʵ����
    surrounding: SurroundingConfig = SurroundingConfig()    # surrounding �ֶ���һ�� SurroundingConfig ���͵�ʵ������ʾ��Χ���á���Ĭ���� SurroundingConfig ���͵�ʵ����
    search: SearchConfig = SearchConfig()    # search �ֶ���һ�� SearchConfig ���͵�ʵ������ʾ�������á���Ĭ���� SearchConfig ���͵�ʵ����
    fence: FenceConfig = FenceConfig()      # fence �ֶ���һ�� FenceConfig ���͵�ʵ������ʾդ�����á���Ĭ���� FenceConfig ���͵�ʵ����

    perf: PerformanceConfig = PerformanceConfig()    # perf �ֶ���һ�� PerformanceConfig ���͵�ʵ������ʾ�������á���Ĭ���� PerformanceConfig ���͵�ʵ����

    @classmethod
    def read_config(cls, fp: TextIO) -> Self:   # read_config ��������һ���ļ�������Ϊ������������һ�� RunConfig ���͵�ʵ����
        """
        Reads a configuration from a file object and returns an instance of the class.  # ���ļ������ж�ȡ���ò��������ʵ����

        Args:
            fp (TextIOWrapper): A file object containing the configuration data.    # һ�������������ݵ��ļ�����

        Returns:
            Self: An instance of the class with the configuration data loaded from the file.    # ���ļ��м����������ݵ����ʵ����

        Raises:
            ValidationError: If the loaded configuration data fails validation.     # ������ص�����������֤ʧ�ܣ������� ValidationError��
        """
        return cls.model_validate(load(fp))     # ʹ�� load �������ļ������м����������ݣ���ʹ�� model_validate ������֤���ص����ݡ������֤ʧ�ܣ������� ValidationError��

    @classmethod
    def dump_config(cls, fp: TextIO, config: Self, with_desc: bool = True) -> None:     # dump_config ��������һ���ļ�����һ�� RunConfig ���͵�ʵ����һ������ֵ��Ϊ������û�з���ֵ��
        """
        Dump the configuration data to a file object.    # ����������ת�����ļ������С�

        Args:
            fp (TextIO): The file object to write the configuration data to.    # Ҫд���������ݵ��ļ�����
            config (Config): The configuration data to be dumped.   # Ҫת�����������ݡ�
            with_desc (bool): Whether to add descriptions to the dump file.     # �Ƿ�������ӵ�ת���ļ��С�
        Returns:
            None    # û�з���ֵ��
        """
        if with_desc:
            # Extract description and raw data from the config  # ����������ȡ������ԭʼ����
            desc_pack: Dict[str, Tuple[str | None, Dict | None]] = extract_description(config)  # desc_pack �ֶ���һ���ֵ䣬���������е�ÿ���ֶ�ӳ�䵽һ��Ԫ�飬��Ԫ������ֶε�������ԭʼ���ݡ�
            raw_data = cls.model_dump(config)    # raw_data �ֶ���һ���ֵ䣬���������е�ÿ���ֶ�ӳ�䵽�ֶε�ԭʼ���ݡ�

            # Create a new TOML document    # ����һ���µ� TOML �ĵ�
            data: TOMLDocument = document()     # data �ֶ���һ�� TOMLDocument ���͵�ʵ��������ʾһ�� TOML �ĵ���
            import kazu
            import datetime

            data.add(comment(f"Exported by Kazu-v{kazu.__version__} at {datetime.datetime.now()}"))     # ��ע����ӵ� TOML �ĵ��У�ע���а��� Kazu �İ汾�ź͵���ʱ�䡣
            # Recursive function to inject descriptions into the TOML document  # �ݹ麯����������ע�뵽 TOML �ĵ���

            # Inject the descriptions into the TOML document    # ������ע�뵽 TOML �ĵ���
            inject_description_into_toml(desc_pack, data, raw_data)     # ʹ�� inject_description_into_toml ����������ע�뵽 TOML �ĵ��С�

            fp.write(dumps(data))    # �� TOML �ĵ�д���ļ������С�

        else:
            # If no description is needed, just use the raw data    # �������Ҫ������ֻ��ʹ��ԭʼ����
            pure_data = cls.model_dump(config)  # pure_data �ֶ���һ���ֵ䣬���������е�ÿ���ֶ�ӳ�䵽�ֶε�ԭʼ���ݡ�
            dump(pure_data, fp)     # ��������д���ļ������С�


class ContextVar(Enum):
    prev_salvo_speed: NonNegativeInt = auto()    # prev_salvo_speed �ֶ���һ���Ǹ���������ʾǰһ��������ٶȡ���Ĭ���� 0��

    is_aligned: bool = auto()    # is_aligned �ֶ���һ������ֵ����ʾ�Ƿ���롣��Ĭ���� False��

    recorded_pack: tuple = auto()    # recorded_pack �ֶ���һ��Ԫ�飬��ʾ��¼�İ�����Ĭ����һ����Ԫ�顣

    gradient_speed: NonNegativeInt = auto()     # gradient_speed �ֶ���һ���Ǹ���������ʾ�ݶ��ٶȡ���Ĭ���� 0��

    unclear_zone_gray:int=auto()    # unclear_zone_gray �ֶ���һ����������ʾ���������ĻҶȡ���Ĭ���� 0��
    @property
    def default(self) -> Any:
        """
        Get the default value for the context variable.     # ��ȡ�����ı�����Ĭ��ֵ��

        Returns:
            Any: The default value for the context variable.     # �����ı�����Ĭ��ֵ��
        """
        defaults = {"prev_salvo_speed": (0, 0, 0, 0), "is_aligned": False, "recorded_pack": (), "gradient_speed": 0,
                    "unclear_zone_gray":0}  # defaults �ֵ佫�����ı���������ӳ�䵽���ǵ�Ĭ��ֵ��
        assert self.name in defaults, "should always find a default value!"     # ���������ı����������� defaults �ֵ��У�������ڣ����׳� AssertionError��
        return defaults.get(self.name)  # ���������ı�����Ĭ��ֵ��

    @staticmethod
    def export_context() -> Dict[str, Any]:     # export_context ����û�в���������һ���ֵ䡣
        """
        Export the context variables and their default values as a dictionary.  # �������ı�������Ĭ��ֵ����Ϊ�ֵ䡣

        Returns:
            Dict[str, Any]: A dictionary containing the names of the context variables as keys and their default values as values.  # һ���ֵ䣬���������ı�����������Ϊ�������ǵ�Ĭ��ֵ��Ϊֵ��
        """
        return {a.name: a.default for a in ContextVar}  # ����һ���ֵ䣬���а��������ı�����������Ϊ�������ǵ�Ĭ��ֵ��Ϊֵ��


class MotionConfig(BaseModel):
    motor_fr: Tuple[int, int] = Field(default=(1, 1), description="Front-right motor configuration.")   #motor_fr��һ��Ԫ�飬��ʾǰ���ֵĵ�����á�Ĭ��ֵΪ (1, 1)
    motor_fl: Tuple[int, int] = Field(default=(2, 1), description="Front-left motor configuration.")    # motor_fl��һ��Ԫ�飬��ʾǰ���ֵĵ�����á�Ĭ��ֵΪ (2, 1)
    motor_rr: Tuple[int, int] = Field(default=(3, 1), description="Rear-right motor configuration.")    # motor_rr��һ��Ԫ�飬��ʾ�����ֵĵ�����á�Ĭ��ֵΪ (3, 1)
    motor_rl: Tuple[int, int] = Field(default=(4, 1), description="Rear-left motor configuration.")     # motor_rl��һ��Ԫ�飬��ʾ�����ֵĵ�����á�Ĭ��ֵΪ (4, 1)
    port: str = Field(default="/dev/ttyUSB0", description="Serial port for communication.")     # port��һ���ַ�������ʾ����ͨ�ŵĴ��ж˿ڡ�Ĭ��ֵΪ "/dev/ttyUSB0"


class VisionConfig(BaseModel):
    team_color: Literal["yellow", "blue"] = Field(  # team_color��һ���ַ�������ʾ�������ɫ�������ֵΪ "yellow" �� "blue"��Ĭ��ֵΪ "blue"��
        default="blue", description='Team color for vision, allow ["yellow", "blue"]'
    )
    resolution_multiplier: float = Field(default=1.0, description="Resolution multiplier for camera.")# resolution_multiplier��һ������������ʾ����ͷ�ķֱ��ʳ�����Ĭ��ֵΪ 1.0��
    use_camera: bool = Field(default=True, description="Whether to use the camera.")    # use_camera��һ������ֵ����ʾ�Ƿ�ʹ������ͷ��Ĭ��ֵΪ True��
    camera_device_id: int = Field(default=0, description="Camera device ID.")    # camera_device_id��һ����������ʾ����ͷ���豸 ID��Ĭ��ֵΪ 0��


class DebugConfig(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(    # log_level��һ���ַ�������ʾ��־���������ֵΪ "DEBUG"��"INFO"��"WARNING"��"ERROR" �� "CRITICAL"��Ĭ��ֵΪ "INFO
        default="INFO", description='Log level for debugging, allow ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].'
    )
    use_siglight: bool = Field(default=True, description="Whether to use signal light.")    # use_siglight��һ������ֵ����ʾ�Ƿ�ʹ���źŵơ�Ĭ��ֵΪ True��


class SensorConfig(BaseModel):
    gyro_fsr: Literal[250, 500, 1000, 2000] = Field(
        default=1000, description="Gyroscope full scale range, allows [250, 500, 1000, 2000]."  # gyro_fsr��һ����������ʾ�����ǵ������̷�Χ�������ֵΪ 250��500��1000 �� 2000��Ĭ��ֵΪ 1000��
    )
    accel_fsr: Literal[2, 4, 8, 16] = Field(
        default=8, description="Accelerometer full scale range, allows [2, 4, 8, 16]."  # accel_fsr��һ����������ʾ���ٶȼƵ������̷�Χ�������ֵΪ 2��4��8 �� 16��Ĭ��ֵΪ 8��
    )

    adc_min_sample_interval: int = Field(default=5, description="Minimum ADC sample interval.")     # adc_min_sample_interval��һ����������ʾ ADC ��С���������Ĭ��ֵΪ 5��

    edge_fl_index: int = Field(default=3, description="Index for front-left edge sensor.")      # edge_fl_index��һ����������ʾǰ���Ե��������������Ĭ��ֵΪ 3��
    edge_fr_index: int = Field(default=0, description="Index for front-right edge sensor.")     # edge_fr_index��һ����������ʾǰ�ұ�Ե��������������Ĭ��ֵΪ 0��
    edge_rl_index: int = Field(default=2, description="Index for rear-left edge sensor.")      # edge_rl_index��һ����������ʾ�����Ե��������������Ĭ��ֵΪ 2��
    edge_rr_index: int = Field(default=1, description="Index for rear-right edge sensor.")      # edge_rr_index��һ����������ʾ���ұ�Ե��������������Ĭ��ֵΪ 1��

    left_adc_index: int = Field(default=6, description="Index for left ADC sensor.")        # left_adc_index��һ����������ʾ�� ADC ��������������Ĭ��ֵΪ 6��
    right_adc_index: int = Field(default=4, description="Index for right ADC sensor.")      # right_adc_index��һ����������ʾ�� ADC ��������������Ĭ��ֵΪ 4��
    
    front_adc_index: int = Field(default=5, description="Index for front ADC sensor.")      # front_adc_index��һ����������ʾǰ ADC ��������������Ĭ��ֵΪ 5��
    rb_adc_index: int = Field(default=7, description="Index for rear-back ADC sensor.")     # rb_adc_index��һ����������ʾ�� ADC ��������������Ĭ��ֵΪ 7��

    gray_adc_index: int = Field(default=8, description="Index for gray ADC sensor.")        # gray_adc_index��һ����������ʾ�Ҷ� ADC ��������������Ĭ��ֵΪ 8��

    # ---------IO----------
    
    gray_io_left_index: int = Field(default=1, description="Index for left gray IO sensor.")    # gray_io_left_index��һ����������ʾ��Ҷ� IO ��������������Ĭ��ֵΪ 1��
    gray_io_right_index: int = Field(default=0, description="Index for right gray IO sensor.")  # gray_io_right_index��һ����������ʾ�һҶ� IO ��������������Ĭ��ֵΪ 0��

    fl_io_index: int = Field(default=5, description="Index for front-left IO sensor.")      # fl_io_index��һ����������ʾǰ�� IO ��������������Ĭ��ֵΪ 5��
    fr_io_index: int = Field(default=2, description="Index for front-right IO sensor.")     # fr_io_index��һ����������ʾǰ�� IO ��������������Ĭ��ֵΪ 2��

    rl_io_index: int = Field(default=4, description="Index for rear-left IO sensor.")      # rl_io_index��һ����������ʾ���� IO ��������������Ĭ��ֵΪ 4��
    rr_io_index: int = Field(default=3, description="Index for rear-right IO sensor.")      # rr_io_index��һ����������ʾ���� IO ��������������Ĭ��ֵΪ 3��

    reboot_button_index: int = Field(default=6, description="Index for reboot button.")        # reboot_button_index��һ����������ʾ������ť��������Ĭ��ֵΪ 6��


class APPConfig(CounterHashable):   #APPConfig��һ���̳��� CounterHashable ���࣬���ڴ洢Ӧ�ó����������Ϣ��
    motion: MotionConfig = MotionConfig()   # motion��һ�� MotionConfig ���͵�ʵ�������ڴ洢�˶���ص�������Ϣ��
    vision: VisionConfig = VisionConfig()   # vision��һ�� VisionConfig ���͵�ʵ�������ڴ洢�Ӿ���ص�������Ϣ��
    debug: DebugConfig = DebugConfig()      # debug��һ�� DebugConfig ���͵�ʵ�������ڴ洢������ص�������Ϣ��
    sensor: SensorConfig = SensorConfig()     # sensor��һ�� SensorConfig ���͵�ʵ�������ڴ洢��������ص�������Ϣ��

    @classmethod
    def read_config(cls, fp: TextIO) -> Self:    #read_config��һ���෽�������ڴ��ļ������ж�ȡ������Ϣ��
        """
        Reads a configuration from a file object and returns an instance of the class.  #���ļ������ж�ȡ������Ϣ���������ʵ����

        Args:
            fp (TextIOWrapper): A file object containing the configuration data.    # fp��һ�������������ݵ��ļ�����

        Returns:
            Self: An instance of the class with the configuration data loaded from the file.    #һ�����д��ļ��м��ص��������ݵ����ʵ����

        Raises:
            ValidationError: If the loaded configuration data fails validation.     #������ص�����������֤ʧ�ܣ������� ValidationError �쳣��
        """

        import toml     #���� toml ģ�飬���ڴ��� TOML ��ʽ�������ļ���

        return cls.model_validate(toml.load(fp))    #ʹ�� toml ģ����ļ������м����������ݣ���ʹ�� model_validate ������֤���ݡ������֤�ɹ����򷵻�һ������

    @classmethod
    def dump_config(cls, fp: TextIO, config: Self, with_desc: bool = True) -> None:     #dump_config��һ���෽�������ڽ���������д���ļ�����
        """
        Dump the configuration data to a file object.   #����������д���ļ�����

        Args:
            fp (TextIO): The file object to write the configuration data to.    # fp��Ҫд���������ݵ��ļ�����
            config (Config): The configuration data to be dumped.           # config��Ҫת�����������ݡ�
            with_desc (bool): Whether to add descriptions to the dump file.     # with_desc���Ƿ�������ӵ�ת���ļ��С�Ĭ��ֵΪ True��
        Returns:
            None
        """
        if with_desc:
            # Extract description and raw data from the config  # ����������ȡ������ԭʼ����
            desc_pack: Dict[str, Tuple[str | None, Dict | None]] = extract_description(config)  # desc_pack��һ���ֵ䣬���м����ֶ����ƣ�ֵ�ǰ����ֶ���������ģ���ֶε�Ԫ�飨����еĻ�����
            raw_data = cls.model_dump(config)   # raw_data��һ���ֵ䣬��������������ȡ��ԭʼ���ݡ�

            # Create a new TOML document    # ����һ���µ� TOML �ĵ�
            data: TOMLDocument = document()     # data��һ�� TOMLDocument ���͵�ʵ������ʾ�µ� TOML �ĵ���
            import kazu     # ���� kazu ģ�飬���ڻ�ȡ Kazu �İ汾��Ϣ��
            import datetime     # ���� datetime ģ�飬���ڻ�ȡ��ǰʱ�����

            data.add(comment(f"Exported by Kazu-v{kazu.__version__} at {datetime.datetime.now().timestamp()}"))     # �� Kazu �İ汾��Ϣ�͵�ǰʱ�����Ϊע����ӵ� TOML �ĵ��С�

            # Recursive function to inject descriptions into the TOML document  # �ݹ麯�������ڽ�����ע�� TOML �ĵ���

            # Inject the descriptions into the TOML document    # ������ע�� TOML �ĵ���
            inject_description_into_toml(desc_pack, data, raw_data)
            
            fp.write(dumps(data))    # �� TOML �ĵ�д���ļ������С�

        else:
            # If no description is needed, just use the raw data    # �������Ҫ������ֻ��ʹ��ԭʼ����
            pure_data = cls.model_dump(config)  # pure_data��һ���ֵ䣬��������������ȡ��ԭʼ���ݡ�
            dump(pure_data, fp)     # ��ԭʼ����д���ļ������С�


def inject_description_into_toml(   # inject_description_into_toml��һ�����������ڽ�����ע�� TOML �ĵ��С�
    desc_pack: Dict[str, Tuple[str | None, Dict | None]],    # desc_pack��һ���ֵ䣬���м����ֶ����ƣ�ֵ�ǰ����ֶ���������ģ���ֶε�Ԫ�飨����еĻ�����
    toml_doc: TOMLDocument,     # toml_doc��һ�� TOMLDocument ���͵�ʵ������ʾ TOML �ĵ���
    raw_data: Dict[str, Any],    # raw_data��һ���ֵ䣬��������������ȡ��ԭʼ���ݡ�
    path: List[str] = None,      # path��һ���б���ʾ��ǰ������ֶε�·����Ĭ��ֵΪ None�����ڵݹ�����Թ���������·����
):
    """
    Injects descriptions into a TOML document.  # ������ע�� TOML �ĵ��С�

    This function recursively iterates through a dictionary containing description information and sub-model fields.    # �˺����ݹ�ر�������������Ϣ����ģ���ֶε��ֵ䡣
    It adds these descriptions as comments to the TOML document. If the current item is a sub-model (i.e., contains     # ������Щ������Ϊע����ӵ� TOML �ĵ��С������ǰ������ģ�ͣ�����������ģ���ֶΣ����򴴽�һ���µı���������ģ���ֶΡ�
    sub-fields), it recursively calls itself to handle the sub-model fields. For non-sub-model items, it adds the   # ���ڷ���ģ�������ԭʼ��������Ӧ��ֵ��ӵ� TOML �ĵ��С�
    description as a comment and retrieves the corresponding value from the raw data to add to the TOML document.

    Parameters:
    - desc_pack: A dictionary where keys are field names and values are tuples containing the description of the field  # desc_pack��һ���ֵ䣬���м����ֶ����ƣ�ֵ�ǰ����ֶ�������Ԫ�顣
      and sub-model fields (if any).
    - toml_doc: A TOMLDocument object representing the TOML document to be modified.    # toml_doc��һ�� TOMLDocument ���󣬱�ʾҪ�޸ĵ� TOML �ĵ���
    - raw_data: A dictionary containing the source data from which to retrieve values.  # raw_data��һ���ֵ䣬����Ҫ���м���ֵ��Դ���ݡ�
    - path: A list representing the current path of the field being processed. Defaults to an empty list, used for  # path��һ���б���ʾ��ǰ���ڴ�����ֶε�·����Ĭ��ֵΪ���б����ڵݹ�����Թ���������·����
      recursive calls to build the complete path.

    Returns:
    No return value; the function modifies the provided `toml_doc` parameter directly.  # �޷���ֵ���ú���ֱ���޸��ṩ�� `toml_doc` ������
    """

    def _nested_get(k_list: List[str], _dict: dict) -> Any:     # _nested_get��һ���ڲ����������ڴ�Ƕ���ֵ��м���ֵ��
        cur = _dict.get(k_list.pop(0))  # cur����Ƕ���ֵ��м����ĵ�ǰֵ��
        for k in k_list:    # k��Ƕ���ֵ��еļ���
            cur = cur.get(k)    # cur����Ƕ���ֵ��м����ĵ�ǰֵ��

        return cur  # ���ش�Ƕ���ֵ��м����ĵ�ǰֵ��

    # Initialize the path if not provided    # ���δ�ṩ·�������ʼ��·��
    if path is None:    # path��һ���б���ʾ��ǰ���ڴ�����ֶε�·����
        path = []    # ��ʼ��·��Ϊ���б�

    # Iterate through the dictionary of description information and sub-model fields    # ����������Ϣ����ģ���ֶε��ֵ�
    for key, (desc, sub_model_fields) in desc_pack.items():     # key���ֶ����ơ�
        # Build the complete path for the current item  # ������ǰ�������·��
        cur_path = path + [key]     # cur_path����ǰ�������·����

        # If the current item is a sub-model, add the description (if any) to the TOML document and create a new table  # �����ǰ������ģ�ͣ�������������У���ӵ� TOML �ĵ��У�������һ���µı�
        # to handle the sub-model fields    # ������ģ���ֶ�
        if sub_model_fields:    # sub_model_fields����ģ���ֶΡ�
            toml_doc.add(comment("#" * 76 + " #"))  # ��������ӵ� TOML �ĵ���
            if desc:    # desc���ֶ�������
                toml_doc.add(comment(desc))        # ��������ӵ� TOML �ĵ���
                toml_doc.add(nl())  
            toml_doc[key] = (sub_table := table())
            # Recursively call itself to handle the sub-model fields    # �ݹ���������Դ�����ģ���ֶ�
            inject_description_into_toml(sub_model_fields, sub_table, raw_data, cur_path)
            toml_doc.add(nl())      # ��ӻ��з�

        else:
            # If the current item is not a sub-model, add the description    # �����ǰ�����ģ�ͣ����������
            toml_doc.add(comment(desc))
            # Retrieve the corresponding value from the raw data and add it to the TOML document    # ��ԭʼ�����м�����Ӧ��ֵ��������ӵ� TOML �ĵ���
            toml_doc[key] = _nested_get(cur_path, raw_data)


class _InternalConfig(BaseModel):
    app_config: APPConfig = APPConfig()     # app_config��Ӧ�ó������á�
    app_config_file_path: Path = Path(DEFAULT_APP_CONFIG_PATH)  # app_config_file_path��Ӧ�ó��������ļ���·����


def load_run_config(run_config_path: Path | None) -> RunConfig:
    """
    A function that loads the run configuration based on the provided run_config_path.  # һ�������ṩ�� run_config_path �����������õĺ�����

    Parameters:
        run_config_path (Path | None): The path to the run configuration file.  # run_config_path�����������ļ���·����

    Returns:
        RunConfig: The loaded run configuration.    # �������á�
    """
    if run_config_path and (r_conf := Path(run_config_path)).exists():  # r_conf�����������ļ���·����
        secho(f'Loading run config from "{r_conf.absolute().as_posix()}"', fg="green", bold=True)    # �������������ļ�
        with open(r_conf) as fp:
            run_config_path: RunConfig = RunConfig.read_config(fp)  # run_config_path�����������ļ���·����
    else:
        secho(f"Loading DEFAULT run config", fg="yellow", bold=True)    # ����Ĭ�����������ļ�
        run_config_path = RunConfig()    # run_config_path�����������ļ���·����
    return run_config_path  # �������������ļ�


def load_app_config(app_config_path: Path | None) -> APPConfig:     # һ�������ṩ�� app_config_path ����Ӧ�ó������õĺ�����
    """
    A function that loads the application configuration based on the provided app_config_path.  # һ�������ṩ�� app_config_path ����Ӧ�ó������õĺ�����

    Parameters: 
        app_config_path (Path | None): The path to the application configuration file.  # app_config_path��Ӧ�ó��������ļ���·����

    Returns:
        APPConfig: The loaded application configuration.    # Ӧ�ó������á�
    """
    if app_config_path and app_config_path.exists():     # app_config_path��Ӧ�ó��������ļ���·����
        secho(f"Load app config from {app_config_path.absolute().as_posix()}", fg="yellow")     # ����Ӧ�ó��������ļ�
        with open(app_config_path, encoding="utf-8") as fp:     # fp��Ӧ�ó��������ļ���·����
            app_config = APPConfig.read_config(fp)  # app_config��Ӧ�ó��������ļ���
    else:
        secho(f"Create and load default app config at {app_config_path.absolute().as_posix()}", fg="yellow")    # ����������Ĭ��Ӧ�ó��������ļ�
        app_config_path.parent.mkdir(parents=True, exist_ok=True)    # app_config_path��Ӧ�ó��������ļ���·����
        app_config = APPConfig()    # app_config��Ӧ�ó��������ļ���
        with open(app_config_path, "w", encoding="utf-8") as fp:     # fp��Ӧ�ó��������ļ���·����
            APPConfig.dump_config(fp, app_config)    # ��Ӧ�ó��������ļ�д���ļ��С�
    return app_config    # ����Ӧ�ó��������ļ���


def extract_description(model: Type[BaseModel]) -> Dict[str, Any]:   # һ�������ṩ��ģ����ȡ������Ϣ�ĺ�����
    """
    Recursively extracts description information from a given model.    # �ݹ�شӸ�����ģ������ȡ������Ϣ��

    This function first extracts the information of all fields in the model (including field names and related info).   #�������������ȡģ���������ֶε���Ϣ�������ֶ����ƺ������Ϣ����Ȼ��������ÿ���ֶΣ���������Ϣ��
    It then iterates through each field, processing its information. For each field, if the associated model is None,   #����ÿ���ֶΣ����������ģ��Ϊ None�������ֶε������� None ֵ���������ֵ��С����������ֶε������͵ݹ���ȡ����ģ��������Ϣ���������ֵ��С�
    it packs the field's description and None value into the result dictionary. Otherwise, it packs the field's     #��������һ���ֵ䣬���м����ֶ����ƣ�ֵ�ǰ����ֶ������������ģ���������� None����Ԫ��
    description and the recursively extracted sub-model description information into the result dictionary.
    The function returns a dictionary where keys are field names and values are tuples containing the field's
    description and its associated model description (or None).

    Parameters:
        model: Type[BaseModel] - A class that inherits from BaseModel, representing some data structure or schema.  # model��Type[BaseModel] - һ���̳��� BaseModel ���࣬��ʾĳ�����ݽṹ��ģʽ��

    Returns:
        Dict[str, Any] - A dictionary containing field names and their descriptions along with the associated model     # ����һ���ֵ䣬���а����ֶ����Ƽ��������Լ�������ģ���������� None����
                       description (or None).
    """

    def _extract(model_field: FieldInfo) -> Tuple[str, Optional[Type[BaseModel]]]:   # һ�������ṩ��ģ���ֶ���ȡ������Ϣ�ĺ�����

        ano = model_field.annotation    # ano��ģ���ֶε�ע�͡�

        is_model = False    # is_model��ģ���ֶ��Ƿ�Ϊģ�͡�

        try:
            is_model = issubclass(ano, BaseModel)    # is_model��ģ���ֶ��Ƿ�Ϊģ�͡�
        except:
            pass

        return model_field.description, ano if is_model else None    # ����ģ���ֶε��������������ģ���������� None����

    # Extract all fields and their related information from the model   # ��ģ������ȡ�����ֶμ��������Ϣ��
    temp = {f_name: _extract(info) for f_name, info in model.model_fields.items()}
    # Initialize the final container dictionary to store processed field descriptions and related info  # ��ʼ�����������ֵ䣬�Դ洢��������ֶ������������Ϣ��
    fi_container = {}
    # Iterate through preprocessed field information    # ����Ԥ��������ֶ���Ϣ��
    for f_name, pack in temp.items():
        # Unpack the field information, including description and possible sub-model    # ����ֶ���Ϣ�����������Ϳ��ܵ���ģ�͡�
        desc, model = pack
        # If the field does not have an associated sub-model, store the description and None value  # ����ֶ�û�й�������ģ�ͣ����ֶε������� None ֵ���������ֵ��С�
        if model is None:
            fi_container[f_name] = pack     # fi_container�����������ֵ䣬�Դ洢��������ֶ������������Ϣ��
        else:
            # If the field has an associated sub-model, store the description and recursively extracted sub-model info  # ����ֶ��й�������ģ�ͣ����ֶε������͵ݹ���ȡ����ģ����Ϣ���������ֵ��С�
            fi_container[f_name] = desc, extract_description(model)     # fi_container�����������ֵ䣬�Դ洢��������ֶ������������Ϣ��

    return fi_container     # �������������ֵ䣬�Դ洢��������ֶ������������Ϣ��
