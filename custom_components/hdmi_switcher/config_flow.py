# config_flow.py
"""
HDMI Switcher Configuration Flow.

This module handles the configuration flow for the HDMI Switcher integration,
allowing users to set up the integration via the Home Assistant UI.
"""

# pylint: disable=duplicate-code

import logging
import socket
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .device import HDMISwitcherDataHandler

_LOGGER = logging.getLogger(__name__)


class HDMISwitcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HDMI Switcher."""

    VERSION = 1

    @staticmethod
    def is_matching(entry: ConfigEntry, host: str, port: int) -> bool:
        """Check if config entry matches the host and port."""
        return (
            entry.data.get("host") == host and entry.data.get("port") == port
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            ip_address = user_input.get("ip_address")
            port = user_input.get("port", 80)

            # Validate the IP address and port
            if not await self._test_connection(ip_address, port):
                errors["base"] = "cannot_connect"
            else:
                # Check for existing entries with the same IP and port
                await self.async_set_unique_id(f"{ip_address}:{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"HDMI Switcher ({ip_address})", data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Required("ip_address"): str,
                vol.Optional("port", default=80): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_connection(self, ip_address, port):
        """Test the connection to the HDMI Switcher."""
        try:
            data_handler = HDMISwitcherDataHandler(ip_address, port)
            await self.hass.async_add_executor_job(data_handler.update)
            return True
        except (socket.error, json.JSONDecodeError, ValueError) as e:
            _LOGGER.error("Connection test failed: %s", e)
            return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Handle creation of the options flow handler."""
        return HDMISwitcherOptionsFlowHandler(config_entry)


class HDMISwitcherOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle HDMI Switcher options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> dict:
        """Manage the HDMI Switcher options.

        Args:
            user_input: Configuration data from the frontend

        Returns:
            Configuration form
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init")
