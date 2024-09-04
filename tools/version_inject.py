from tomlkit import load


with open("pyproject.toml", "r") as fp:
    pyproject_toml = load(fp)


package_version = pyproject_toml.get("project").get("version")

with open("src/kazu/__init__.py", "r") as fp:
    __init__ = fp.read()

tokens = __init__.split("=")
tokens.pop()
tokens.append(f' "{package_version}"\n')

with open("src/kazu/__init__.py", "w") as fp:
    fp.write("=".join(tokens))
