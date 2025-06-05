# kazu
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Kazu-Kusa/kazu)
[![Python 3.11](https://img.shields.io/badge/python-3.11-green.svg)](https://www.python.org/downloads/release/python-311/)
[![Release Package](https://github.com/Kazu-Kusa/kazu/actions/workflows/auto-make-prerelease.yml/badge.svg)](https://github.com/Kazu-Kusa/kazu/actions/workflows/auto-make-prerelease.yml)

[![Build Status](https://github.com/Kazu-Kusa/kazu/actions/workflows/build_on_push.yml/badge.svg)](
https://github.com/Kazu-Kusa/kazu/actions/workflows/build_on_push.yml
)

---


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

To get the template config file, you do as below, after which you should get a toml file like [this](./examples/run_config.toml), or  [zh_CN ver](./examples/run_config_zh_CN.toml).

```shell
# export run config to ./run_config.toml 
kazu config -r ./run_config.toml
```


Use your favourite text editor to open `./run_config.toml`, you should see the default run config. 

You can make some tweak by reading the comment over each config item. After that you can feed the run config to the `kazu` as below.

```shell
#run with ./run_config.toml
kazu run -r ./run_config.toml

#generate puml using ./run_config.toml
kazu viz -r ./run_config.toml 
```

## TODO

- [x] divide stage cases into 3 categories: on stage, off stage, and unclear
- [x] add back stage success checker

