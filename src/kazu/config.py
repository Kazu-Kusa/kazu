from typing import Tuple

from pydantic import BaseModel


class Config(BaseModel):

    motor_fr: Tuple[int, int]
    motor_fl: Tuple[int, int]
    motor_rr: Tuple[int, int]
    motor_rl: Tuple[int, int]

    port: str

    log_level: str
    ...
