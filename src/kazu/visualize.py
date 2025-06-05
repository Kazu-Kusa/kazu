from click import secho


def print_colored_toml(toml_content) -> None:
    # 假设 toml_content 是一个字符串形式的 TOML 数据
    lines = toml_content.split("\n")
    for line in lines:
        if line.startswith("["):  # 高亮 section
            secho(line, fg="blue", bold=True)
        elif "=" in line and not line.startswith("#"):  # 高亮 key-value 对
            key, value = line.split("=", 1)
            secho(key, fg="green", bold=True, nl=False)
            secho(" = ", fg="white", nl=False)
            secho(value.strip(), fg="yellow")
        else:  # 其他文本
            secho(line)
