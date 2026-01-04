from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import GreencellCoordinator

BINARY_SENSORS = {
    "utilityFail": {
        "name": "Utility Fail",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:transmission-tower-off",
    },
    "batteryLow": {
        "name": "Battery Low",
        "device_class": BinarySensorDeviceClass.BATTERY,
        "icon": "mdi:battery-alert-variant-outline",
    },
    "offline": {
        "name": "Offline",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:server-network-off",
    },
    "failed": {
        "name": "UPS Failed",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:alert-octagon",
    },
    "connected": {
        "name": "Connected",
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
        "icon": "mdi:lan-connect",
    },
    "bypassBoost": {
        "name": "Bypass/Boost Active",
        "icon": "mdi:flash-triangle",
    },
    "testInProgress": {
        "name": "Test In Progress",
        "device_class": BinarySensorDeviceClass.RUNNING,
        "icon": "mdi:progress-clock",
    },
    "shutdownActive": {
        "name": "Shutdown Active",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:power-plug-off",
    },
    "beeperOn": {
        "name": "Beeper On",
        "icon": "mdi:volume-high",
    },
    "active": {
        "name": "Active",
        "device_class": BinarySensorDeviceClass.RUNNING,
        "icon": "mdi:play-circle-outline",
    },
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GreencellBinarySensor(
            coordinator,
            entry.entry_id,
            entry.data[CONF_HOST],
            key,
            sensor,
        )
        for key, sensor in BINARY_SENSORS.items()
    )

class GreencellBinarySensor(CoordinatorEntity["GreencellCoordinator"], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, host, key, sensor_config):
        super().__init__(coordinator)
        self._key = key
        self._entry_id = entry_id
        self._host = host
        self._attr_name = sensor_config["name"]
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_icon = sensor_config.get("icon")
        self._attr_unique_id = f"greencell_{entry_id}_{key}"

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        return bool(data.get(self._key))

    @property
    def device_info(self) -> DeviceInfo:
        spec = getattr(self.coordinator, "specification", None) or {}
        model = spec.get("name") or (
            ", ".join(spec["codes"]) if spec.get("codes") else None
        )
        connections = set()
        if getattr(self.coordinator, "mac_address", None):
            connections.add((dr.CONNECTION_NETWORK_MAC, self.coordinator.mac_address))
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self.coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=model,
            connections=connections,
            configuration_url=self.coordinator.configuration_url,
        )
