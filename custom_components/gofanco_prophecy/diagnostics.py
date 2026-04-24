"""Diagnostics support for the Gofanco Prophecy HDMI Matrix integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import ProphecyConfigEntry

_REDACT_KEYS = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ProphecyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    state = coordinator.data
    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), _REDACT_KEYS),
        },
        "state": {
            "power": state.power if state else None,
            "outputs": state.outputs if state else None,
            "input_names": state.input_names if state else None,
            "output_names": state.output_names if state else None,
            "preset_names": state.preset_names if state else None,
        },
    }
