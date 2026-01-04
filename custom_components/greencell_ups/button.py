from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_HOST, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GreencellApiError
from .coordinator import GreencellCoordinator
from .const import (
    DOMAIN,
    MANUFACTURER,
    SERVICE_CANCEL_TEST,
    SERVICE_LONG_TEST,
    SERVICE_SHORT_TEST,
)

BUTTONS = [
    {
        "key": "refresh_data",
        "name": "Refresh Now",
        "icon": "mdi:refresh",
        "method": None,
        "category": EntityCategory.DIAGNOSTIC,
        "special": "refresh",
    },
    {
        "key": SERVICE_CANCEL_TEST,
        "name": "Cancel Test",
        "icon": "mdi:cancel",
        "method": "cancel_test",
        "category": EntityCategory.DIAGNOSTIC,
    },
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: GreencellCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GreencellButton(
            coordinator,
            entry.entry_id,
            entry.data[CONF_HOST],
            button,
        )
        for button in BUTTONS
    ]
    async_add_entities(entities)


class GreencellButton(CoordinatorEntity[GreencellCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, host, button_conf):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._host = host
        self._conf = button_conf
        self._attr_name = button_conf["name"]
        self._attr_icon = button_conf.get("icon")
        self._attr_entity_category = button_conf.get("category")
        self._attr_unique_id = f"greencell_{entry_id}_btn_{button_conf['key']}"

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

    async def async_press(self) -> None:
        special = self._conf.get("special")
        if special == "refresh":
            await self.coordinator.async_request_refresh()
            return

        method = getattr(self.coordinator.api, self._conf.get("method", ""), None)
        if method is None:
            raise HomeAssistantError(f"Command {self._conf['key']} not available")
        try:
            await method()
            await self.coordinator.async_request_refresh()
        except GreencellApiError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err
