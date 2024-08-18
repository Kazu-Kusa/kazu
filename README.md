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

In addition, you can change the appconfig values in the config file by directly editing it. The path of the App-config file is at `<USERHOME>/.kazu/config.toml`



## TODO

- [ ] divide stage cases into 3 categories: on stage, off stage, and fuzzy
- [ ] add back stage success checker

