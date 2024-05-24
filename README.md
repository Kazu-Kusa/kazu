# kazu

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
