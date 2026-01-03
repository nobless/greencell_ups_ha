from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_CANCEL_TEST,
    SERVICE_LONG_TEST,
    SERVICE_SHORT_TEST,
    SERVICE_SHUTDOWN,
    SERVICE_TOGGLE_BEEPER,
    SERVICE_WAKE_UP,
)

if TYPE_CHECKING:  # Only import Home Assistant types when available
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.core import ServiceCall


async def async_setup_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    # Import lazily so tests can run without Home Assistant installed
    from .coordinator import GreencellCoordinator

    coordinator = GreencellCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = coordinator
    if not domain_data.get("_services_registered"):
        _register_services(hass)
        domain_data["_services_registered"] = True
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        entry.add_update_listener(
            lambda hass, e: hass.config_entries.async_reload(e.entry_id)
        )
    )
    return True


async def async_unload_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def _register_services(hass: "HomeAssistant") -> None:
    from .coordinator import GreencellCoordinator
    from .api import GreencellApiError

    service_map = {
        SERVICE_TOGGLE_BEEPER: "toggle_beeper",
        SERVICE_SHUTDOWN: "shutdown",
        SERVICE_WAKE_UP: "wake_up",
        SERVICE_SHORT_TEST: "short_test",
        SERVICE_LONG_TEST: "long_test",
        SERVICE_CANCEL_TEST: "cancel_test",
    }

    schema = vol.Schema({vol.Optional("entry_id"): str})

    async def _get_coordinator(entry_id: str | None) -> GreencellCoordinator:
        domain_data = hass.data.get(DOMAIN) or {}
        if not domain_data:
            raise HomeAssistantError("Greencell UPS is not set up.")

        if entry_id:
            coordinator = domain_data.get(entry_id)
            if coordinator:
                return coordinator
            raise HomeAssistantError(f"No Greencell UPS entry with id {entry_id}")

        # Attempt auto-pick if only one coordinator is present
        coordinators = [
            value for key, value in domain_data.items() if not key.startswith("_")
        ]
        if len(coordinators) == 1:
            return coordinators[0]
        raise HomeAssistantError("Multiple entries present; provide entry_id.")

    async def _handle_service(call: "ServiceCall") -> None:
        coordinator = await _get_coordinator(call.data.get("entry_id"))
        method_name = service_map[call.service]
        method = getattr(coordinator.api, method_name, None)
        if method is None:
            raise HomeAssistantError(f"Command {call.service} not available")
        try:
            await method()
        except GreencellApiError as err:
            raise HomeAssistantError(f"Command failed: {err}") from err

    for service in service_map:
        hass.services.async_register(DOMAIN, service, _handle_service, schema=schema)
