from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.device_registry import format_mac

from .api import (
    GreencellApi,
    GreencellAuthError,
    GreencellRequestError,
    GreencellResponseError,
)
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


def _normalize_mac(mac: str | None) -> str | None:
    if not mac:
        return None
    try:
        return format_mac(mac)
    except Exception:
        return None


class GreencellConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            password = user_input[CONF_PASSWORD]
            name = user_input.get(CONF_NAME, "").strip() or None
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            api = GreencellApi(host, password)
            try:
                await api.login()
                entry_data = {
                    CONF_HOST: host,
                    CONF_PASSWORD: password,
                    CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                }
                if name:
                    entry_data[CONF_NAME] = name
                return self.async_create_entry(
                    title=name or host,
                    data=entry_data,
                )
            except GreencellAuthError:
                return self.async_abort(reason="invalid_auth")
            except (GreencellRequestError, GreencellResponseError):
                return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_NAME): str,
                    vol.Optional(
                        CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL
                    ): bool,
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return GreencellOptionsFlowHandler(config_entry)


class GreencellOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        # Avoid assigning to read-only properties; keep our own reference
        self._config_entry = config_entry

    @property
    def config_entry(self) -> config_entries.ConfigEntry:
        return self._config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            options: dict[str, Any] = {
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            mac = _normalize_mac(user_input.get(CONF_MAC))
            if mac:
                options[CONF_MAC] = mac
            return self.async_create_entry(title="", data=options)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_verify_ssl = self.config_entry.options.get(
            CONF_VERIFY_SSL,
            self.config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )
        current_mac = self.config_entry.options.get(
            CONF_MAC,
            self.config_entry.data.get(CONF_MAC, ""),
        )
        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL),
                    ),
                    vol.Required(
                        CONF_VERIFY_SSL, default=current_verify_ssl
                    ): bool,
                    vol.Optional(CONF_MAC, default=current_mac): str,
                }
            ),
        )
