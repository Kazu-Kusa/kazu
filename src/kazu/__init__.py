from .logger import _logger, set_log_level
import bdmc
import mentabotix
import pyuptech

LOG_LEVEL = "INFO"
pyuptech.set_log_level(LOG_LEVEL)
mentabotix.set_log_level(LOG_LEVEL)
bdmc.set_log_level(LOG_LEVEL)
set_log_level(LOG_LEVEL)
