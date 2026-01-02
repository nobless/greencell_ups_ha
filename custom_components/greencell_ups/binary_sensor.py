from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER

BINARY_SENSORS = {
    "utilityFail": "Utility Fail",
    "batteryLow": "Battery Low",
    "offline": "Offline",
    "failed": "UPS Failed",
    "connected": "Connected",
    "bypassBoost": "Bypass/Boost Active",
    "testInProgress": "Test In Progress",
    "shutdownActive": "Shutdown Active",
    "beeperOn": "Beeper On",
    "active": "Active",
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GreencellBinarySensor(
            coordinator,
            entry.entry_id,
            entry.data["host"],
            key,
            name,
        )
        for key, name in BINARY_SENSORS.items()
    )

class GreencellBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry_id, host, key, name):
        super().__init__(coordinator)
        self._key = key
        self._entry_id = entry_id
        self._host = host
        self._attr_name = f"Greencell {name}"
        self._attr_unique_id = f"greencell_{entry_id}_{key}"

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        return bool(data.get(self._key))

    @property
    def device_info(self):
        info = {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Greencell UPS ({self._host})",
            "manufacturer": MANUFACTURER,
        }
        spec = getattr(self.coordinator, "specification", None) or {}
        model = spec.get("name") or (
            ", ".join(spec["codes"]) if spec.get("codes") else None
        )
        if model:
            info["model"] = model
        return info
