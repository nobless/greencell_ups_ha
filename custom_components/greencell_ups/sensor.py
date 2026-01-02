from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import GreencellCoordinator

SENSORS = {
    "inputVoltage": {
        "name": "Input Voltage",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:transmission-tower",
    },
    "inputVoltageFault": {
        "name": "Input Voltage Fault",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:flash-alert",
    },
    "outputVoltage": {
        "name": "Output Voltage",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:power-plug",
    },
    "batteryVoltage": {
        "name": "Battery Voltage",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:car-battery",
    },
    "batteryVoltageNominal": {
        "name": "Battery Voltage Nominal",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:car-battery",
    },
    "batteryVoltageHighNominal": {
        "name": "Battery Voltage High Nominal",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:battery-positive",
    },
    "batteryVoltageLowNominal": {
        "name": "Battery Voltage Low Nominal",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:battery-negative",
    },
    "batteryLevel": {
        "name": "Battery Level",
        "unit": "%",
        "device_class": SensorDeviceClass.BATTERY,
        "icon": "mdi:battery",
    },
    "temperature": {
        "name": "Temperature",
        "unit": "°C",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "icon": "mdi:thermometer",
    },
    "load": {
        "name": "Load",
        "unit": "%",
        "icon": "mdi:gauge",
    },
    "inputFrequency": {
        "name": "Input Frequency",
        "unit": "Hz",
        "device_class": SensorDeviceClass.FREQUENCY,
        "icon": "mdi:sine-wave",
    },
    "inputFrequencyNominal": {
        "name": "Input Frequency Nominal",
        "unit": "Hz",
        "device_class": SensorDeviceClass.FREQUENCY,
        "icon": "mdi:sine-wave",
    },
    "inputVoltageNominal": {
        "name": "Input Voltage Nominal",
        "unit": "V",
        "device_class": SensorDeviceClass.VOLTAGE,
        "icon": "mdi:flash-outline",
    },
    "inputCurrentNominal": {
        "name": "Input Current Nominal",
        "unit": "A",
        "device_class": SensorDeviceClass.CURRENT,
        "icon": "mdi:current-ac",
    },
    "batteryNumberNominal": {
        "name": "Battery Number Nominal",
        "unit": None,
        "icon": "mdi:battery-plus",
    },
    "status": {
        "name": "Status",
        "unit": None,
        "icon": "mdi:information",
    },
    "errno": {
        "name": "Error Code",
        "unit": None,
        "icon": "mdi:alert-circle-outline",
    },
    "reg": {
        "name": "Register",
        "unit": None,
        "icon": "mdi:code-brackets",
    },
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GreencellSensor(
            coordinator,
            entry.entry_id,
            entry.data[CONF_HOST],
            key,
            sensor,
        )
        for key, sensor in SENSORS.items()
    ]
    async_add_entities(entities)

class GreencellSensor(CoordinatorEntity["GreencellCoordinator"], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, host, key, sensor_config):
        super().__init__(coordinator)
        self._key = key
        self._entry_id = entry_id
        self._host = host
        self._attr_name = sensor_config["name"]
        self._attr_native_unit_of_measurement = sensor_config["unit"]
        self._attr_icon = sensor_config.get("icon")
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_unique_id = f"greencell_{entry_id}_{key}"

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        return data.get(self._key)

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
            name=f"Greencell UPS ({self._host})",
            manufacturer=MANUFACTURER,
            model=model,
            connections=connections,
        )
