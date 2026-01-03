import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
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
from urllib.parse import urlparse

from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_VERIFY_SSL, DOMAIN, MIN_SCAN_INTERVAL
from .api import GreencellApi, GreencellApiError

_LOGGER = logging.getLogger(__name__)

class GreencellCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.hass = hass
        self.host = config_entry.data[CONF_HOST]
        scan_interval = max(
            config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            MIN_SCAN_INTERVAL,
        )
        mac = self._normalize_mac(
            config_entry.options.get(CONF_MAC) or config_entry.data.get(CONF_MAC)
        )
        self.mac_address = mac

        verify_ssl = config_entry.options.get(
            CONF_VERIFY_SSL,
            config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )
        self.api = GreencellApi(
            self.host,
            config_entry.data[CONF_PASSWORD],
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
                    if self.mac_address is None:
                        resolved_mac = await self._async_resolve_mac()
                        if resolved_mac:
                            self.mac_address = resolved_mac
                except Exception as err:
                    _LOGGER.debug("Failed to fetch specification: %s", err)
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

        def _lookup():
            return get_mac_address(ip=self._host_for_mac_lookup())

        mac = await self.hass.async_add_executor_job(_lookup)
        return self._normalize_mac(mac)

    def _host_for_mac_lookup(self) -> str:
        """Normalize host for MAC lookup (strip scheme/port)."""
        parsed = urlparse(self.host)
        if parsed.scheme:
            return parsed.hostname or self.host
        return self.host
