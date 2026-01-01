"""Greencell integration"""
from homeassistant.const import CONF_PASSWORD, CONF_HOST
from homeassistant.helpers import discovery

async def async_setup(hass, config):
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    hass.data[DOMAIN] = conf

    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    return True
