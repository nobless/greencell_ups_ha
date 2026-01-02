from datetime import timedelta
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import DOMAIN, UPDATE_INTERVAL
from .api import GreencellApi

class GreencellCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry):
        self.api = GreencellApi(
            config_entry.data["host"],
            config_entry.data["password"],
        )

        super().__init__(
            hass,
            logger=None,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
        try:
            return await self.api.fetch_status()
        except Exception as err:
            raise UpdateFailed(err)
