"""Greencell integration"""


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_PASSWORD, CONF_HOST
from homeassistant.helpers import discovery



from .const import PLATFORMS
from .coordinator import SnmpCoordinator

async def async_setup(hass, config):
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    hass.data[DOMAIN] = conf

    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    return True
