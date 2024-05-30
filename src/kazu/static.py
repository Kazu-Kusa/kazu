from mentabotix import MovingState

from kazu.config import ContextVar

name = ContextVar.prev_salvo_speed.name
continues_state = MovingState(
    speed_expressions=(f"{name}[0]", f"{name}[1]", f"{name}[2]", f"{name}[3]"),
    used_context_variables=[ContextVar.prev_salvo_speed.name],
)
