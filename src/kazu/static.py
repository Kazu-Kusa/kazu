from mentabotix import MovingState

from .config import ContextVar

continues_state = MovingState(
    speed_expressions=ContextVar.prev_salvo_speed.name,
    used_context_variables=[ContextVar.prev_salvo_speed.name],
)
