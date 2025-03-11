"""TFA.me station integration: config_flow.py."""

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import callback

from .const import CONF_INTERVAL, DOMAIN

# Scheme for IP/Domain and poll interval
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_INTERVAL, default=60): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=3600)
        ),  # Interval between 10 and 3600 secondsn
    }
)


_LOGGER = logging.getLogger(__name__)


# ---- TFA.me config flow ----
class TFAmeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for TFA.me stations."""

    VERSION = 1

    _LOGGER.debug("TFA.me config flow")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step: Configuration UI."""
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        # Get interval and IP or mDNS host name
        update_interval = user_input.get(CONF_INTERVAL)
        if not isinstance(update_interval, int):
            _LOGGER.debug("update_interval no Integer, set to default")
            update_interval = 60

        ip_host_str = user_input.get("ip_address")

        # Verify interval
        if update_interval <= 9:
            errors[CONF_INTERVAL] = "invalid_interval"
            # Error, interval validation failed
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        # if user_input is not None:
        if is_valid_ip_or_mdns(user_input):
            # host_str = user_input.get("ip_address")  # Get value as string
            title_str: str = "TFA.me Station"
            if isinstance(ip_host_str, str):
                title_str = "TFA.me Station '" + ip_host_str + "'"

            # Create a TFA.me device entry
            return self.async_create_entry(title=title_str, data=user_input)

        # error
        errors[CONF_IP_ADDRESS] = "invalid_ip_host"

        # Error, validation failed
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


# ---- Verify if user input is valid IP V4 or mDNS name ----
def is_valid_ip_or_mdns(to_verify: dict) -> bool:
    """Verify if input is an IP or a valid mDNS host name."""

    host = to_verify.get("ip_address")  # Get value as string
    if not isinstance(host, str):
        return False  # ip_address not available or not a string

    # IPv4 verify:
    # ipv4_pattern: str = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    ipv4_pattern = (
        r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}"
        r"(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"
    )
    if re.match(ipv4_pattern, host):
        return True

    # Special format for mDNS name verification: "tfa-me-XXX-XXX-XXX.local"
    mdns_pattern: str = r"^tfa-me-[0-9A-Fa-f]{3}-[0-9A-Fa-f]{3}-[0-9A-Fa-f]{3}\.local$"
    if re.match(mdns_pattern, host):
        return True

    # Letzter Test: Lässt sich der Hostname auflösen?
    # try:
    #    socket.gethostbyname(host)
    #    return True
    # except socket.gaierror:
    return False


# ---- Options handler: set poll interval ----
class OptionsFlowHandler(OptionsFlow):
    """Handle options flow."""

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Entry point for options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get actual values from entry
        interval = self.config_entry.data.get("interval")
        current_interval = self.config_entry.options.get(CONF_INTERVAL, interval)

        options_schema = vol.Schema(
            {
                vol.Required(CONF_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=3600)
                )
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            description_placeholders={
                "interval": str(self.config_entry.options.get("interval", 10))
            },
        )
