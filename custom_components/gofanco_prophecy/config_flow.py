"""Config flow for the Gofanco Prophecy HDMI Matrix integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
import voluptuous as vol

from .const import DEFAULT_HOST_SUGGESTION, DEFAULT_PORT, DOMAIN
from .device import (
    GofancoProphecyClient,
    ProphecyConnectionError,
    ProphecyResponseError,
)

_LOGGER = logging.getLogger(__name__)

_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
    }
)


class GofancoProphecyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gofanco Prophecy."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            error = await self._async_try_connect(host, port)
            if error is None:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"HDMI Matrix ({host})",
                    data={CONF_HOST: host, CONF_PORT: port},
                )
            errors["base"] = error

        schema = self.add_suggested_values_to_schema(
            _STEP_USER_SCHEMA,
            {CONF_HOST: DEFAULT_HOST_SUGGESTION, CONF_PORT: DEFAULT_PORT},
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_mismatch(reason="wrong_device")

            error = await self._async_try_connect(host, port)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_HOST: host, CONF_PORT: port},
                )
            errors["base"] = error

        schema = self.add_suggested_values_to_schema(
            _STEP_USER_SCHEMA,
            {
                CONF_HOST: entry.data.get(CONF_HOST, ""),
                CONF_PORT: entry.data.get(CONF_PORT, DEFAULT_PORT),
            },
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    async def _async_try_connect(self, host: str, port: int) -> str | None:
        """Probe the device; return an error key or None on success."""
        client = GofancoProphecyClient(host, port)
        try:
            await client.async_get_state()
        except ProphecyConnectionError as err:
            _LOGGER.debug("Cannot connect to %s:%s - %s", host, port, err)
            return "cannot_connect"
        except ProphecyResponseError as err:
            _LOGGER.debug("Invalid response from %s:%s - %s", host, port, err)
            return "invalid_response"
        except Exception:
            # Anything not already surfaced as a Prophecy* error is unknown by
            # definition; log the traceback and show a generic message to the
            # user. This is the canonical HA config-flow pattern.
            _LOGGER.exception("Unexpected error probing %s:%s", host, port)
            return "unknown"
        return None
