from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSORS = {
    "inputVoltage": ("Input Voltage", "V"),
    "outputVoltage": ("Output Voltage", "V"),
    "batteryVoltage": ("Battery Voltage", "V"),
    "batteryLevel": ("Battery Level", "%"),
    "temperature": ("Temperature", "°C"),
    "load": ("Load", "%"),
    "inputFrequency": ("Input Frequency", "Hz"),
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GreencellSensor(coordinator, key, name, unit)
        for key, (name, unit) in SENSORS.items()
    ]
    async_add_entities(entities)

class GreencellSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Greencell {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"greencell_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)
