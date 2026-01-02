from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

BINARY_SENSORS = {
    "utilityFail": "Utility Fail",
    "batteryLow": "Battery Low",
    "offline": "Offline",
    "failed": "UPS Failed",
    "connected": "Connected",
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GreencellBinarySensor(coordinator, key, name)
        for key, name in BINARY_SENSORS.items()
    )

class GreencellBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Greencell {name}"
        self._attr_unique_id = f"greencell_{key}"

    @property
    def is_on(self):
        return bool(self.coordinator.data.get(self._key))
