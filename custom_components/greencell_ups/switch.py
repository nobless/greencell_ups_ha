from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
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
        "check_response": True,
    },
    {
        "key": "ups_output",
        "name": "UPS Output",
        "icon": "mdi:power-plug",
        "category": EntityCategory.CONFIG,
        "state_key": "shutdownActive",
        "toggle_method": {"on": "wake_up", "off": "shutdown"},
        "check_response": True,
    },
    {
        "key": "short_test",
        "name": "Test: Short (≈10s)",
        "icon": "mdi:timer-outline",
        "category": EntityCategory.DIAGNOSTIC,
        "state_key": "testInProgress",
        "toggle_method": {"on": "short_test", "off": "cancel_test"},
        "check_response": True,
    },
    {
        "key": "long_test",
        "name": "Test: Long (Battery Discharge)",
        "icon": "mdi:timer-cog-outline",
        "category": EntityCategory.DIAGNOSTIC,
        "state_key": "testInProgress",
        "toggle_method": {"on": "long_test", "off": "cancel_test"},
        "check_response": True,
    },
    {
        "key": "cancel_test",
        "name": "Test: Status",
        "icon": "mdi:cancel",
        "category": EntityCategory.DIAGNOSTIC,
        "state_key": "testInProgress",
        "toggle_method": {"on": None, "off": "cancel_test"},
        "check_response": True,
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
            name=self.coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=model,
            connections=connections,
            configuration_url=self.coordinator.configuration_url,
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
                if method_name is None:
                    raise HomeAssistantError("Command not available for this action")
                method = getattr(self.coordinator.api, method_name, None)
                if method is None:
                    raise HomeAssistantError(f"Command {method_name} not available")
                resp = await method()
            else:
                method = getattr(self.coordinator.api, method_conf, None)
                if method is None:
                    raise HomeAssistantError(f"Command {method_conf} not available")
                resp = await method()
            if self._conf.get("check_response", False) and not self._is_success(resp):
                message = f"Command did not succeed (response={resp})"
                self._log_activity(message)
                raise HomeAssistantError(message)
            self._log_success(turn_on)
            await self.coordinator.async_refresh_current_parameters_with_delay(0.75)
        except GreencellApiError as err:
            self._log_activity(f"Command failed: {err}")
            raise HomeAssistantError(f"Command failed: {err}") from err

    @staticmethod
    def _is_success(resp: object) -> bool:
        if isinstance(resp, int) and resp == 1:
            return True
        return False

    @callback
    def _log_activity(self, message: str) -> None:
        try:
            self.hass.bus.async_fire(
                "logbook_entry",
                {
                    "name": self.name or "Greencell UPS",
                    "message": message,
                    "domain": DOMAIN,
                    "entity_id": self.entity_id,
                },
            )
        except Exception:
            pass

    @callback
    def _log_success(self, turn_on: bool) -> None:
        """Log successful test commands to the device activity log."""
        key = self._conf.get("key")
        if key not in {"short_test", "long_test", "cancel_test"}:
            return
        if key == "short_test":
            action = "Short test started" if turn_on else "Test cancelled"
        elif key == "long_test":
            action = "Long test started" if turn_on else "Test cancelled"
        else:
            action = "Test cancelled"
        try:
            self.hass.bus.async_fire(
                "logbook_entry",
                {
                    "name": self.name or "Greencell UPS",
                    "message": action,
                    "domain": DOMAIN,
                    "entity_id": self.entity_id,
                },
            )
        except Exception:
            pass
