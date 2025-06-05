# kazu

<!-- TOC -->
* [kazu](#kazu)
* [Installation](#installation)
* [Configure KAZU](#configure-kazu)
    * [AppConfig](#appconfig)

<!-- TOC -->


# Installation

This project uses `pdm` to manage dependencies, so you can use `pdm` to install it.
```shell
# upgrade pip using tuna mirror
python -m pip --upgrade install pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# config pip mirror, change it to tuna mirror
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# install pdm
python -m pip install pdm

# config pdm mirror, change it to tuna mirror either
pdm config pypi.url https://pypi.tuna.tsinghua.edu.cn/simple

# clone the project repo to local
git clone https://github.com/Kazu-Kusa/kazu --depth=1

# change directory to the cloned repo in the local
cd ./kazu

# run pdm to install the project
pdm install
```


# Configure KAZU

## AppConfig

Configure the app config file using the `kazu config` command.

for example:
```shell
kazu config debug.log_level DEBUG
```

If the Key-value pair is not specified, kazu config will display the current value in the config file.

```shell
kazu config
```

You should see the details of config in console
```shell

[motion]
motor_fr  = [ 1, 1,]
motor_fl  = [ 2, 1,]
motor_rr  = [ 3, 1,]
motor_rl  = [ 4, 1,]
port  = "/dev/ttyUSB0"

[vision]
team_color  = "blue"
resolution_multiplier  = 1.0
use_camera  = true
camera_device_id  = 0

[debug]
log_level  = "INFO"
use_siglight  = true

[sensor]
gyro_fsr  = 1000
accel_fsr  = 8
adc_min_sample_interval  = 5
edge_fl_index  = 0
edge_fr_index  = 1
edge_rl_index  = 2
edge_rr_index  = 3
left_adc_index  = 4
right_adc_index  = 5
front_adc_index  = 6
rb_adc_index  = 7
gray_adc_index  = 8
gray_io_left_index  = 0
gray_io_right_index  = 1
fl_io_index  = 2
fr_io_index  = 3
rl_io_index  = 4
rr_io_index  = 5
reboot_button_index  = 7

```

In addition, you can change the appconfig values in the config file by directly editing it. The path of the App-config file is at `<USERHOME>/.kazu/config.toml`, also, if you are can change the directory in which app config file is stored by changing environment variable `KAZU_APP_CONFIG_PATH`

## RunConfig

For runtime configuration, currently only supports direct editing the config file, `RunConfig` will not read any config file and will use built-in default run config  while the user neither specify `--run-config-path`  under related subcommands(e.g. `run`, `viz`, `trac`) nor set the environment variable `KAZU_RUN_CONFIG_PATH`.

To get the template config file, you do as below

```shell
# export run config to ./run_config.toml 
kazu config -r ./run_config.toml
```

Use your favourite text editor to open `./run_config.toml`, you should see the default run config. 

```toml
# Exported by Kazu-v0.3.8 at 2025-06-02 15:37:38.987861
# ############################################################################ #

[strategy]
# Whether to use edge component.是否使用边缘组件
use_edge_component = true
# Whether to use surrounding component.是否使用周围组件
use_surrounding_component = true
# Whether to use normal component.是否使用普通组件
use_normal_component = true

# ############################################################################ #

[boot]
# Button IO value for activating case.激活情况下的按钮输入输出值
button_io_activate_case_value = 0
# Time to stabilize after activation.激活后稳定所需要的时间
time_to_stabilize = 0.1
# Maximum holding duration.最大保持时长
max_holding_duration = 180.0
# Threshold for left sensor.左侧传感器的阈值
left_threshold = 1100
# Threshold for right sensor.右侧传感器阈值
right_threshold = 1100
# Speed for dashing.冲刺速度
dash_speed = 7000
# Duration for dashing.冲刺时间
dash_duration = 0.55
# Speed for turning.转向速度
turn_speed = 2150
# Duration for a full turn.完全转向时间
full_turn_duration = 0.45
# Probability of turning left.左转概率
turn_left_prob = 0.5

# ############################################################################ #

[backstage]
# Time to stabilize after activation.激活后稳定所需要的时间
time_to_stabilize = 0.1
# Speed for small advance.小步前进速度
small_advance_speed = 1500
# Duration for small advance.小步前进时间
small_advance_duration = 0.6
# Speed for dashing.冲刺速度
dash_speed = 7000
# Duration for dashing.冲刺时间
dash_duration = 0.55
# Speed for turning.转向速度
turn_speed = 2600
# Duration for a full turn.完全转向时间
full_turn_duration = 0.35
# Probability of turning left.左转概率
turn_left_prob = 0.5
# Whether to check if on stage.在舞台上是否检查
use_is_on_stage_check = true
# Whether to check side away after the is_on_stage check.在执行 is_on_stage 检查之后是否检查侧面离开
use_side_away_check = true
# defining when does the is_on_stage check being brought on during the dashing. DO NOT set it too small!定义在冲刺过程中何时进行 is_on_stage 检查。不要设置得太小！
check_start_percent = 0.9
# Degree tolerance for side away.边缘离开的角度容差
side_away_degree_tolerance = 10.0
# Speed for exiting side away.离开边缘的速递
exit_side_away_speed = 1300
# Duration for exiting side away.离开边缘的持续时间
exit_side_away_duration = 0.6

# ############################################################################ #

[stage]
# Upper threshold for gray ADC off stage.灰色ADC离台的上限阈值
gray_adc_off_stage_upper_threshold = 2630
# Lower threshold for gray ADC on stage.灰色ADC离台下限阈值
gray_adc_on_stage_lower_threshold = 2830
# Tolerance for judging if the car is on stage in unclear zone state.判断车辆在模糊区域状态下是否处于舞台上的容差
unclear_zone_tolerance = 90
# Speed for turning in unclear zone.模糊区域转向速度
unclear_zone_turn_speed = 1500
# Duration for turning in unclear zone.模糊区域转向时间
unclear_zone_turn_duration = 0.6
# Probability of turning left.左转概率
unclear_zone_turn_left_prob = 0.5
# IO value for gray off stage.离场灰度io值
gray_io_off_stage_case_value = 0

# ############################################################################ #

[edge]
# Lower threshold values for edge detection.边缘检测的下阈值
lower_threshold = [1740, 1819, 1819, 1740]
# Upper threshold values for edge detection.边缘检测的上阈值
upper_threshold = [2100, 2470, 2470, 2100]
# Speed when falling back.撤退速度
fallback_speed = 2600
# Duration of the fallback action.撤退时间
fallback_duration = 0.2
# Speed when advancing.前进速度
advance_speed = 2400
# Duration of the advance action.前进时间
advance_duration = 0.35
# Speed when turning.转向速度
turn_speed = 2800
# Duration of a full turn.完全转向时间
full_turn_duration = 0.45
# Duration of a half turn.半转向时间
half_turn_duration = 0.225
# Probability of turning left.左转概率
turn_left_prob = 0.5
# Speed when drifting.漂移速度
drift_speed = 1500
# Duration of the drift action.漂移时间
drift_duration = 0.13
# Whether to use gray IO for detection.是否使用灰度传感器
use_gray_io = true

# ############################################################################ #

[surrounding]
# IO value when encountering an object.遇到物体io值
io_encounter_object_value = 0
# ADC lower threshold for the left sensor.左传感器adc下阈值
left_adc_lower_threshold = 1000
# ADC lower threshold for the right sensor.右传感器adc器下阈值
right_adc_lower_threshold = 1000
# ADC lower threshold for the front sensor.前传感器adc下阈值
front_adc_lower_threshold = 1000
# ADC lower threshold for the back sensor.后传感器adc下阈值
back_adc_lower_threshold = 1100
# Front ADC lower threshold for attack break.攻击中断时前adc下阈值
atk_break_front_lower_threshold = 1500
# Whether to use edge sensors for attack break.是否在攻击中断时使用边缘传感器
atk_break_use_edge_sensors = true
# Attack speed for enemy car.攻击敌方车辆速度
atk_speed_enemy_car = 2300
# Attack speed for enemy box.攻击敌方方块速度
atk_speed_enemy_box = 2500
# Attack speed for neutral box.攻击中立方块速度
atk_speed_neutral_box = 2500
# Fallback speed for ally box.后撤友方方块速度
fallback_speed_ally_box = 2900
# Fallback speed for edge.边缘后退速度
fallback_speed_edge = 2400
# Duration of attack on enemy car.攻击敌方车辆时间
atk_enemy_car_duration = 4.2
# Duration of attack on enemy box.攻击敌方方块时间
atk_enemy_box_duration = 3.6
# Duration of attack on neutral box.攻击中立方块时间
atk_neutral_box_duration = 3.6
# Duration of fallback for ally box.后撤友方方块时间
fallback_duration_ally_box = 0.3
# Duration of fallback for edge.后撤边缘时间
fallback_duration_edge = 0.2
# Speed when turning.转向速度
turn_speed = 2900
# Probability of turning left.左转概率
turn_left_prob = 0.5
# Whether to use the front sensor for turning to front.是否在“转向正前方”动作中使用前向传感器
turn_to_front_use_front_sensor = false
# Random turn speeds.随机转向速度列表
rand_turn_speeds = [1600, 2100, 3000]
# Weights for random turn speeds.随机转向速度对应的权重
rand_turn_speed_weights = [2, 3, 1]
# Duration of a full turn.完全转向时间
full_turn_duration = 0.45
# Duration of a half turn.半转向时间
half_turn_duration = 0.225

# ############################################################################ #

[search]
# Whether to use gradient move.是否使用梯度移动
use_gradient_move = true
# Weight for gradient move.梯度移动权重
gradient_move_weight = 100
# Whether to use scan move.是否使用扫描移动
use_scan_move = true
# Weight for scan move.扫描移动权重
scan_move_weight = 1.96
# Whether to use random turn.是否使用随机转动
use_rand_turn = false
# Weight for random turn.随机转动权重
rand_turn_weight = 0.05
# ############################################################################ #
# Configuration for gradient move.

[search.gradient_move]
# Maximum speed for gradient move.梯度移动速度最大值
max_speed = 2800
# Minimum speed for gradient move.梯度移动速度最小值
min_speed = 500
# Lower bound for gradient move.梯度移动下限值
lower_bound = 2900
# Upper bound for gradient move.梯度移动上限值
upper_bound = 3700

# ############################################################################ #
# Configuration for scan move.

[search.scan_move]
# Maximum tolerance for the front sensor.前传感器最大容差
front_max_tolerance = 760
# Maximum tolerance for the rear sensor.后传感器最大容差
rear_max_tolerance = 760
# Maximum tolerance for the left sensor.左传感器最大容差
left_max_tolerance = 760
# Maximum tolerance for the right sensor.右传感器最大容差
right_max_tolerance = 760
# IO value when encountering an object.遇到物体的io值
io_encounter_object_value = 0
# Speed for scanning.扫描速度
scan_speed = 300
# Duration of the scan action.扫描时间
scan_duration = 4.5
# Probability of turning left during scan.扫描过程中左转概率
scan_turn_left_prob = 0.5
# Speed for falling back.撤退速度
fall_back_speed = 3250
# Duration of the fall back action.撤退时间
fall_back_duration = 0.2
# Speed when turning.转向速度
turn_speed = 2700
# Probability of turning left.左转概率
turn_left_prob = 0.5
# Duration of a full turn.完全转向时间
full_turn_duration = 0.45
# Duration of a half turn.半转向时间
half_turn_duration = 0.225
# Whether to check edge before scanning.扫描之前是否检查边缘
check_edge_before_scan = true
# Whether to check gray ADC before scanning.扫描之前是否检查灰度adc
check_gray_adc_before_scan = true
# Gray ADC lower threshold for scanning.扫描时灰度adc下阈值
gray_adc_lower_threshold = 3100

# ############################################################################ #
# Configuration for random turn.

[search.rand_turn]
# Speed when turning.转向速度
turn_speed = 2300
# Probability of turning left.左转概率
turn_left_prob = 0.5
# Duration of a full turn.完全转向时间
full_turn_duration = 0.25
# Duration of a half turn.半转向时间
half_turn_duration = 0.15
# Whether to use turning to front.是否启用转向正前方
use_turn_to_front = true


# ############################################################################ #

[fence]
# Front ADC lower threshold.前adc下阈值
front_adc_lower_threshold = 900
# Rear ADC lower threshold.后adc下阈值
rear_adc_lower_threshold = 1100
# Left ADC lower threshold.左adc下阈值
left_adc_lower_threshold = 900
# Right ADC lower threshold.右adc下阈值
right_adc_lower_threshold = 900
# IO value when encountering a fence.遇到围栏的io值
io_encounter_fence_value = 0
# Maximum yaw tolerance.最大偏航角容差
max_yaw_tolerance = 20.0
# Whether to use MPU for aligning stage.是否使用MPU进行舞台对齐
use_mpu_align_stage = false
# Whether to use MPU for aligning direction.是否使用MPU进行方向对齐
use_mpu_align_direction = false
# Speed for aligning stage.舞台对齐时的速度
stage_align_speed = 850
# Maximum duration for aligning stage.舞台对齐的最大持续时间
max_stage_align_duration = 4.5
# Turn direction for aligning stage, allow ["l", "r", "rand"].舞台对齐时的转向方向，可选 ["l", "r", "rand"]
stage_align_direction = "rand"
# Speed for aligning direction.方向对齐速度
direction_align_speed = 850
# Maximum duration for aligning direction.方向对齐最大时间
max_direction_align_duration = 4.5
# Turn direction for aligning the parallel or vertical direction to the stage,  allow ["l", "r", "rand"]. 平行或垂直方向对齐时的转向方向，可选 ["l", "r", "rand"]
direction_align_direction = "rand"
# Speed for exiting corner.退出角落速度
exit_corner_speed = 1200
# Maximum duration for exiting corner.退出角落最大时间
max_exit_corner_duration = 1.5
# ############################################################################ #
# Configuration for random walk.

[fence.rand_walk]
# Whether to use straight movement.是否使用直线移动
use_straight = true
# Weight for straight movement.直线移动权重
straight_weight = 2
# Random straight speeds.随机速度
rand_straight_speeds = [-800, -500, 500, 800]
# Weights for random straight speeds.随机速度权重
rand_straight_speed_weights = [1, 3, 3, 1]
# Whether to use turning.是否使用转向
use_turn = true
# Weight for turning.转向权重
turn_weight = 1
# Random turn speeds.随机转向速度
rand_turn_speeds = [-1200, -800, 800, 1200]
# Weights for random turn speeds.随机转向速度权重
rand_turn_speed_weights = [1, 3, 3, 1]
# Duration of walking.行走时间
walk_duration = 0.3


# ############################################################################ #

[perf]
# Duration for checking.
checking_duration = 0.0
```

You can make some tweak by reading the comment over each config item. After that you can feed the run config to the `kazu` as below.

```shell
#run with ./run_config.toml
kazu run -r ./run_config.toml

#generate puml using ./run_config.toml
kazu viz -r ./run_config.toml 

...
```

## TODO

- [x] divide stage cases into 3 categories: on stage, off stage, and unclear
- [x] add back stage success checker

