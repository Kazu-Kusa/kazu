import mentabotix


def greet(name="World"):
    return f"Hello, {name}!"

if __name__ == "__main__":
    import fire
    fire.Fire(greet)