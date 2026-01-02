from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    Platform,
)

DOMAIN = "greencell_ups"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
MANUFACTURER = "Green Cell"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 5  # seconds
DEFAULT_VERIFY_SSL = False
