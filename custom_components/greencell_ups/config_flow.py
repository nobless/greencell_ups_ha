from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD

from .api import (
    GreencellApi,
    GreencellAuthError,
    GreencellRequestError,
    GreencellResponseError,
)
from .const import DOMAIN


class GreencellConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            password = user_input[CONF_PASSWORD]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            api = GreencellApi(host, password)
            try:
                await api.login()
                return self.async_create_entry(
                    title=host,
                    data={
                        CONF_HOST: host,
                        CONF_PASSWORD: password,
                    },
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
                }
            ),
        )
