from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN
from .api import GreencellApi

class GreencellConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            api = GreencellApi(
                user_input["host"],
                user_input["password"],
            )
            try:
                await api.login()
                return self.async_create_entry(
                    title=user_input["host"],
                    data=user_input,
                )
            except Exception:
                return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): str,
                    vol.Required("password"): str,
                }
            ),
        )
