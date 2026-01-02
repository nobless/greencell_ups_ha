from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, UPDATE_INTERVAL
from .api import GreencellApi, GreencellApiError

_LOGGER = logging.getLogger(__name__)

class GreencellCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry):
        self.api = GreencellApi(
            config_entry.data["host"],
            config_entry.data["password"],
        )
        self.specification = None

        super().__init__(
            hass,
            _LOGGER, 
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
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
