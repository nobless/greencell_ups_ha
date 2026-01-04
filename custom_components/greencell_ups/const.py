from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    Platform,
)

DOMAIN = "greencell_ups"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SWITCH]
MANUFACTURER = "Green Cell"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 5  # seconds
DEFAULT_VERIFY_SSL = False

# Services
SERVICE_TOGGLE_BEEPER = "toggle_beeper"
SERVICE_SHUTDOWN = "shutdown"
SERVICE_WAKE_UP = "wake_up"
SERVICE_SHORT_TEST = "short_test"
SERVICE_LONG_TEST = "long_test"
SERVICE_CANCEL_TEST = "cancel_test"
