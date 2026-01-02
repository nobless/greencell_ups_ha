from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import redact

from .const import DOMAIN

TO_REDACT = {
    "password",
    "access_token",
    "refresh_token",
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    diagnostics_data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "domain": entry.domain,
            "entry_id": entry.entry_id,
            "data": redact(entry.data, TO_REDACT),
            "options": entry.options,
            "version": entry.version,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "data": redact(coordinator.data or {}, TO_REDACT),
    }

    return diagnostics_data
