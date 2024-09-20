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
# Exported by Kazu-v0.3.4 at 2024-09-20 11:41:37.017816
# ############################################################################ #

[strategy]
# Whether to use edge component.
use_edge_component = true
# Whether to use surrounding component.
use_surrounding_component = true
# Whether to use normal component.
use_normal_component = true

# ############################################################################ #

[boot]
# Button IO value for activating case.
button_io_activate_case_value = 0
# Time to stabilize after activation.
time_to_stabilize = 0.1
# Maximum holding duration.
max_holding_duration = 180.0
# Threshold for left sensor.
left_threshold = 1100
# Threshold for right sensor.
right_threshold = 1100
# Speed for dashing.
dash_speed = 7000
# Duration for dashing.
dash_duration = 0.55
# Speed for turning.
turn_speed = 2150
# Duration for a full turn.
full_turn_duration = 0.45
# Probability of turning left.
turn_left_prob = 0.5

# ############################################################################ #

[backstage]
# Time to stabilize after activation.
time_to_stabilize = 0.1
# Speed for small advance.
small_advance_speed = 1500
# Duration for small advance.
small_advance_duration = 0.6
# Speed for dashing.
dash_speed = 7000
# Duration for dashing.
dash_duration = 0.55
# Speed for turning.
turn_speed = 2600
# Duration for a full turn.
full_turn_duration = 0.35
# Probability of turning left.
turn_left_prob = 0.5
# Whether to check if on stage.
use_is_on_stage_check = true
# Whether to check side away after the is_on_stage check.
use_side_away_check = true
# defining when does the is_on_stage check being brought on during the dashing. DO NOT set it too small!
check_start_percent = 0.9
# Degree tolerance for side away.
side_away_degree_tolerance = 10.0
# Speed for exiting side away.
exit_side_away_speed = 1300
# Duration for exiting side away.
exit_side_away_duration = 0.6

# ############################################################################ #

[stage]
# Upper threshold for gray ADC off stage.
gray_adc_off_stage_upper_threshold = 2730
# IO value for gray off stage.
gray_io_off_stage_case_value = 0

# ############################################################################ #

[edge]
# Lower threshold values for edge detection.
lower_threshold = [1740, 1819, 1819, 1740]
# Upper threshold values for edge detection.
upper_threshold = [2100, 2470, 2470, 2100]
# Speed when falling back.
fallback_speed = 2600
# Duration of the fallback action.
fallback_duration = 0.2
# Speed when advancing.
advance_speed = 2400
# Duration of the advance action.
advance_duration = 0.35
# Speed when turning.
turn_speed = 2800
# Duration of a full turn.
full_turn_duration = 0.45
# Duration of a half turn.
half_turn_duration = 0.225
# Probability of turning left.
turn_left_prob = 0.5
# Speed when drifting.
drift_speed = 1500
# Duration of the drift action.
drift_duration = 0.13
# Whether to use gray IO for detection.
use_gray_io = true

# ############################################################################ #

[surrounding]
# IO value when encountering an object.
io_encounter_object_value = 0
# ADC lower threshold for the left sensor.
left_adc_lower_threshold = 1000
# ADC lower threshold for the right sensor.
right_adc_lower_threshold = 1000
# ADC lower threshold for the front sensor.
front_adc_lower_threshold = 1000
# ADC lower threshold for the back sensor.
back_adc_lower_threshold = 1100
# Front ADC lower threshold for attack break.
atk_break_front_lower_threshold = 1500
# Whether to use edge sensors for attack break.
atk_break_use_edge_sensors = true
# Attack speed for enemy car.
atk_speed_enemy_car = 2300
# Attack speed for enemy box.
atk_speed_enemy_box = 2500
# Attack speed for neutral box.
atk_speed_neutral_box = 2500
# Fallback speed for ally box.
fallback_speed_ally_box = 2900
# Fallback speed for edge.
fallback_speed_edge = 2400
# Duration of attack on enemy car.
atk_enemy_car_duration = 4.2
# Duration of attack on enemy box.
atk_enemy_box_duration = 3.6
# Duration of attack on neutral box.
atk_neutral_box_duration = 3.6
# Duration of fallback for ally box.
fallback_duration_ally_box = 0.3
# Duration of fallback for edge.
fallback_duration_edge = 0.2
# Speed when turning.
turn_speed = 2900
# Probability of turning left.
turn_left_prob = 0.5
# Whether to use the front sensor for turning to front.
turn_to_front_use_front_sensor = false
# Random turn speeds.
rand_turn_speeds = [1600, 2100, 3000]
# Weights for random turn speeds.
rand_turn_speed_weights = [2, 3, 1]
# Duration of a full turn.
full_turn_duration = 0.45
# Duration of a half turn.
half_turn_duration = 0.225

# ############################################################################ #

[search]
# Whether to use gradient move.
use_gradient_move = true
# Weight for gradient move.
gradient_move_weight = 100
# Whether to use scan move.
use_scan_move = true
# Weight for scan move.
scan_move_weight = 1.96
# Whether to use random turn.
use_rand_turn = true
# Weight for random turn.
rand_turn_weight = 0.05
# ############################################################################ #
# Configuration for gradient move.

[search.gradient_move]
# Maximum speed for gradient move.
max_speed = 2800
# Minimum speed for gradient move.
min_speed = 500
# Lower bound for gradient move.
lower_bound = 2900
# Upper bound for gradient move.
upper_bound = 3700

# ############################################################################ #
# Configuration for scan move.

[search.scan_move]
# Maximum tolerance for the front sensor.
front_max_tolerance = 760
# Maximum tolerance for the rear sensor.
rear_max_tolerance = 760
# Maximum tolerance for the left sensor.
left_max_tolerance = 760
# Maximum tolerance for the right sensor.
right_max_tolerance = 760
# IO value when encountering an object.
io_encounter_object_value = 0
# Speed for scanning.
scan_speed = 300
# Duration of the scan action.
scan_duration = 4.5
# Probability of turning left during scan.
scan_turn_left_prob = 0.5
# Speed for falling back.
fall_back_speed = 3250
# Duration of the fall back action.
fall_back_duration = 0.2
# Speed when turning.
turn_speed = 2700
# Probability of turning left.
turn_left_prob = 0.5
# Duration of a full turn.
full_turn_duration = 0.45
# Duration of a half turn.
half_turn_duration = 0.225
# Whether to check edge before scanning.
check_edge_before_scan = true
# Whether to check gray ADC before scanning.
check_gray_adc_before_scan = true
# Gray ADC lower threshold for scanning.
gray_adc_lower_threshold = 3100

# ############################################################################ #
# Configuration for random turn.

[search.rand_turn]
# Speed when turning.
turn_speed = 2300
# Probability of turning left.
turn_left_prob = 0.5
# Duration of a full turn.
full_turn_duration = 0.25
# Duration of a half turn.
half_turn_duration = 0.15
# Whether to use turning to front.
use_turn_to_front = true


# ############################################################################ #

[fence]
# Front ADC lower threshold.
front_adc_lower_threshold = 900
# Rear ADC lower threshold.
rear_adc_lower_threshold = 1100
# Left ADC lower threshold.
left_adc_lower_threshold = 900
# Right ADC lower threshold.
right_adc_lower_threshold = 900
# IO value when encountering a fence.
io_encounter_fence_value = 0
# Maximum yaw tolerance.
max_yaw_tolerance = 20.0
# Whether to use MPU for aligning stage.
use_mpu_align_stage = false
# Whether to use MPU for aligning direction.
use_mpu_align_direction = false
# Speed for aligning stage.
stage_align_speed = 850
# Maximum duration for aligning stage.
max_stage_align_duration = 4.5
# Turn direction for aligning stage, allow ["l", "r", "rand"].
stage_align_direction = "rand"
# Speed for aligning direction.
direction_align_speed = 850
# Maximum duration for aligning direction.
max_direction_align_duration = 4.5
# Turn direction for aligning the parallel or vertical direction to the stage,  allow ["l", "r", "rand"].
direction_align_direction = "rand"
# Speed for exiting corner.
exit_corner_speed = 1200
# Maximum duration for exiting corner.
max_exit_corner_duration = 1.5
# ############################################################################ #
# Configuration for random walk.

[fence.rand_walk]
# Whether to use straight movement.
use_straight = true
# Weight for straight movement.
straight_weight = 2
# Random straight speeds.
rand_straight_speeds = [-800, -500, 500, 800]
# Weights for random straight speeds.
rand_straight_speed_weights = [1, 3, 3, 1]
# Whether to use turning.
use_turn = true
# Weight for turning.
turn_weight = 1
# Random turn speeds.
rand_turn_speeds = [-1200, -800, 800, 1200]
# Weights for random turn speeds.
rand_turn_speed_weights = [1, 3, 3, 1]
# Duration of walking.
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

- [ ] divide stage cases into 3 categories: on stage, off stage, and fuzzy
- [x] add back stage success checker

