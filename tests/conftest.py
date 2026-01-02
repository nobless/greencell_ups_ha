import sys
import types
from enum import Enum
from pathlib import Path

# Minimal Home Assistant stubs so imports work without HA installed
if "homeassistant.const" not in sys.modules:
    ha_const = types.ModuleType("homeassistant.const")

    class Platform(str, Enum):
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"

    ha_const.CONF_HOST = "host"
    ha_const.CONF_PASSWORD = "password"
    ha_const.Platform = Platform

    ha_module = types.ModuleType("homeassistant")
    ha_module.const = ha_const

    sys.modules["homeassistant"] = ha_module
    sys.modules["homeassistant.const"] = ha_const

# Ensure repository root is on sys.path so custom_components can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
