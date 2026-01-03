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
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    def _safe_redact(value: Any) -> Any:
        try:
            return redact(value or {}, TO_REDACT)
        except Exception:
            return value

    def _safe_interval_seconds(coordinator_obj: Any) -> float | None:
        try:
            interval = getattr(coordinator_obj, "update_interval", None)
            return interval.total_seconds() if interval else None
        except Exception:
            return None

    def _safe_bool(attr: str) -> bool | None:
        try:
            return getattr(coordinator, attr)
        except Exception:
            return None

    coordinator_data = None
    specification = None
    try:
        coordinator_data = coordinator.data if coordinator else None
    except Exception:
        coordinator_data = None
    try:
        specification = getattr(coordinator, "specification", None) if coordinator else None
    except Exception:
        specification = None

    diagnostics_data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "domain": entry.domain,
            "entry_id": entry.entry_id,
            "data": _safe_redact(entry.data),
            "options": entry.options,
            "version": entry.version,
        },
        "coordinator": {
            "last_update_success": _safe_bool("last_update_success"),
            "update_interval": _safe_interval_seconds(coordinator),
        },
        "data": _safe_redact(coordinator_data),
        "specification": _safe_redact(specification),
    }

    return diagnostics_data
