from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GreencellApiError
from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import GreencellCoordinator


SWITCHES = [
    {
        "key": "beeper",
        "name": "Beeper",
        "icon": "mdi:volume-high",
        "category": EntityCategory.CONFIG,
        "state_key": "beeperOn",
        "toggle_method": "toggle_beeper",
    },
    {
        "key": "ups_output",
        "name": "UPS Output",
        "icon": "mdi:power-plug",
        "category": EntityCategory.CONFIG,
        "state_key": "shutdownActive",
        "toggle_method": {"on": "wake_up", "off": "shutdown"},
    },
    {
        "key": "short_test",
        "name": "Short Test (≈10s)",
        "icon": "mdi:timer-outline",
        "category": EntityCategory.DIAGNOSTIC,
        "state_key": "testInProgress",
        "toggle_method": {"on": "short_test", "off": "cancel_test"},
    },
    {
        "key": "long_test",
        "name": "Long Test (Battery Discharge)",
        "icon": "mdi:timer-cog-outline",
        "category": EntityCategory.DIAGNOSTIC,
        "state_key": "testInProgress",
        "toggle_method": {"on": "long_test", "off": "cancel_test"},
    },
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: GreencellCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GreencellSwitch(
            coordinator,
            entry.entry_id,
            entry.data[CONF_HOST],
            switch_conf,
        )
        for switch_conf in SWITCHES
    ]
    async_add_entities(entities)


class GreencellSwitch(CoordinatorEntity["GreencellCoordinator"], SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, host, switch_conf):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._host = host
        self._conf = switch_conf
        self._attr_name = switch_conf["name"]
        self._attr_icon = switch_conf.get("icon")
        self._attr_entity_category = switch_conf.get("category")
        self._attr_unique_id = f"greencell_{entry_id}_switch_{switch_conf['key']}"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        state_key = self._conf.get("state_key")
        if state_key == "shutdownActive":
            # Consider ON when not shutdown
            return not bool(data.get("shutdownActive"))
        if state_key == "testInProgress":
            return bool(data.get("testInProgress"))
        return bool(data.get(state_key))

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

    async def async_turn_on(self, **kwargs) -> None:
        await self._apply_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._apply_state(False)

    async def _apply_state(self, turn_on: bool) -> None:
        method_conf = self._conf.get("toggle_method")
        try:
            if isinstance(method_conf, dict):
                method_name = method_conf["on"] if turn_on else method_conf["off"]
                method = getattr(self.coordinator.api, method_name, None)
                if method is None:
                    raise HomeAssistantError(f"Command {method_name} not available")
                await method()
            else:
                method = getattr(self.coordinator.api, method_conf, None)
                if method is None:
                    raise HomeAssistantError(f"Command {method_conf} not available")
                await method()
            await self.coordinator.async_request_refresh()
        except GreencellApiError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err
