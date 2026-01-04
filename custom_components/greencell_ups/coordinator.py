import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
import socket
from urllib.parse import urlparse

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .api import GreencellApi, GreencellApiError

_LOGGER = logging.getLogger(__name__)

class GreencellCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.hass = hass
        self.config_entry = config_entry
        self.host = config_entry.data[CONF_HOST]
        user_name = config_entry.data.get(CONF_NAME)
        self._user_named = bool(user_name)
        self.device_name = user_name or f"Greencell UPS ({self.host})"
        scan_interval = max(
            config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            MIN_SCAN_INTERVAL,
        )
        mac = self._normalize_mac(
            config_entry.options.get(CONF_MAC) or config_entry.data.get(CONF_MAC)
        )
        self.mac_address = mac

        password = config_entry.options.get(
            CONF_PASSWORD, config_entry.data.get(CONF_PASSWORD)
        )
        verify_ssl = config_entry.options.get(
            CONF_VERIFY_SSL,
            config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )
        self.api = GreencellApi(
            self.host,
            password,
            session=async_get_clientsession(hass),
            verify_ssl=verify_ssl,
        )
        self.specification = None

        super().__init__(
            hass,
            _LOGGER, 
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    @property
    def _debug_enabled(self) -> bool:
        """Return True when HA logging is set to debug for this logger."""
        return _LOGGER.isEnabledFor(logging.DEBUG)

    @property
    def configuration_url(self) -> str:
        """Return a URL to the UPS web UI based on the configured host."""
        parsed = urlparse(self.host)
        if parsed.scheme:
            return self.host
        return f"http://{self.host}"

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.fetch_status()
            if self.mac_address is None:
                self.mac_address = self._normalize_mac(self._extract_mac(data))
            if self.mac_address is None:
                resolved_mac = await self._async_resolve_mac()
                if resolved_mac:
                    self.mac_address = resolved_mac
            if self.specification is None:
                try:
                    self.specification = await self.api.fetch_specification()
                    if self.mac_address is None:
                        self.mac_address = self._normalize_mac(
                            self._extract_mac(self.specification)
                        )
                    if not self._user_named:
                        self.device_name = self._build_name_from_spec(self.specification)
                    if self.mac_address is None:
                        resolved_mac = await self._async_resolve_mac()
                        if resolved_mac:
                            self.mac_address = resolved_mac
                except Exception as err:
                    if self._debug_enabled:
                        _LOGGER.debug("Failed to fetch specification: %s", err)
            elif not self._user_named:
                # Keep name in sync if spec was already available
                self.device_name = self._build_name_from_spec(self.specification)
            return data
        except GreencellApiError as err:
            raise UpdateFailed(err)

    @staticmethod
    def _normalize_mac(mac: Any) -> str | None:
        if not mac:
            return None
        try:
            return format_mac(str(mac))
        except Exception:
            return None

    @staticmethod
    def _extract_mac(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        for key in ("mac", "macAddress", "mac_address", "macaddr", "mac_addr"):
            mac = payload.get(key)
            if mac:
                return str(mac)
        return None

    async def _async_resolve_mac(self) -> str | None:
        """Try to resolve MAC address using host/IP via getmac without blocking."""
        try:
            from getmac import get_mac_address
        except ImportError:
            return None

        if self.mac_address:
            return self.mac_address

        def _lookup(target):
            return get_mac_address(ip=target)

        for candidate in self._host_candidates_for_mac():
            mac = await self.hass.async_add_executor_job(_lookup, candidate)
            normalized = self._normalize_mac(mac)
            if normalized:
                if self._debug_enabled:
                    _LOGGER.debug("MAC lookup success for host %s (target=%s, mac=%s)", self.host, candidate, normalized)
                return normalized
            if self._debug_enabled:
                _LOGGER.debug("MAC lookup failed for host %s (target=%s, raw=%s)", self.host, candidate, mac)
        return None

    def _host_for_mac_lookup(self) -> str:
        """Normalize host for MAC lookup (strip scheme/port, resolve to IP if possible)."""
        parsed = urlparse(self.host)
        host = parsed.hostname if parsed.scheme else self.host
        if not host:
            return self.host
        try:
            info = socket.getaddrinfo(host, None)
            for family, _, _, _, sockaddr in info:
                if family in (socket.AF_INET, socket.AF_INET6):
                    return sockaddr[0]
        except Exception:
            pass
        return host

    def _host_candidates_for_mac(self) -> list[str]:
        """Return possible targets to try when resolving a MAC."""
        candidates: list[str] = []
        primary = self._host_for_mac_lookup()
        if primary:
            candidates.append(primary)
        parsed = urlparse(self.host)
        raw = parsed.hostname if parsed.scheme else self.host
        if raw and raw not in candidates:
            candidates.append(raw)
        return candidates

    def _build_name_from_spec(self, spec: Any) -> str:
        if not isinstance(spec, dict):
            return self.device_name
        name = spec.get("name")
        capacity = spec.get("capacity")
        if name and capacity:
            return f"{name} {capacity}VA"
        if name:
            return str(name)
        return self.device_name

    async def async_refresh_current_parameters(self) -> None:
        """Fetch current parameters immediately and update coordinator data."""
        try:
            data = await self.api.fetch_status()
            self.async_set_updated_data(data)
        except GreencellApiError as err:
            if self._debug_enabled:
                _LOGGER.debug("Manual refresh of current parameters failed: %s", err)
