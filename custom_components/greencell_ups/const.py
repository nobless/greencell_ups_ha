from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform

DOMAIN = "greencell_ups"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
MANUFACTURER = "Green Cell"

UPDATE_INTERVAL = 30  # seconds
