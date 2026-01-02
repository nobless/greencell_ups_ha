import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, UPDATE_INTERVAL
from .api import GreencellApi, GreencellApiError

_LOGGER = logging.getLogger(__name__)

class GreencellCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.api = GreencellApi(
            config_entry.data[CONF_HOST],
            config_entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
        )
        self.specification = None

        super().__init__(
            hass,
            _LOGGER, 
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.fetch_status()
            if self.specification is None:
                try:
                    self.specification = await self.api.fetch_specification()
                except Exception as err:
                    _LOGGER.debug("Failed to fetch specification: %s", err)
            return data
        except GreencellApiError as err:
            raise UpdateFailed(err)
