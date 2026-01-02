from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_HOST
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import GreencellCoordinator

SENSORS = {
    "inputVoltage": ("Input Voltage", "V"),
    "inputVoltageFault": ("Input Voltage Fault", "V"),
    "outputVoltage": ("Output Voltage", "V"),
    "batteryVoltage": ("Battery Voltage", "V"),
    "batteryVoltageNominal": ("Battery Voltage Nominal", "V"),
    "batteryVoltageHighNominal": ("Battery Voltage High Nominal", "V"),
    "batteryVoltageLowNominal": ("Battery Voltage Low Nominal", "V"),
    "batteryLevel": ("Battery Level", "%"),
    "temperature": ("Temperature", "°C"),
    "load": ("Load", "%"),
    "inputFrequency": ("Input Frequency", "Hz"),
    "inputFrequencyNominal": ("Input Frequency Nominal", "Hz"),
    "inputVoltageNominal": ("Input Voltage Nominal", "V"),
    "inputCurrentNominal": ("Input Current Nominal", "A"),
    "batteryNumberNominal": ("Battery Number Nominal", None),
    "status": ("Status", None),
    "errno": ("Error Code", None),
    "reg": ("Register", None),
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GreencellSensor(
            coordinator,
            entry.entry_id,
            entry.data[CONF_HOST],
            key,
            name,
            unit,
        )
        for key, (name, unit) in SENSORS.items()
    ]
    async_add_entities(entities)

class GreencellSensor(CoordinatorEntity["GreencellCoordinator"], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, host, key, name, unit):
        super().__init__(coordinator)
        self._key = key
        self._entry_id = entry_id
        self._host = host
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
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
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=f"Greencell UPS ({self._host})",
            manufacturer=MANUFACTURER,
            model=model,
        )
