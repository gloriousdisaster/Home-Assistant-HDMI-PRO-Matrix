# init.property
"""
HDMI Switcher Integration for Home Assistant.

This module initializes the HDMI Switcher custom component,
handling setup and integration with Home Assistant.
"""

import logging

# import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .device import HDMISwitcherDataHandler

_LOGGER = logging.getLogger(__name__)

# Define CONFIG_SCHEMA to indicate the integration is set up via config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the HDMI Switcher integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up HDMI Switcher from a config entry."""
    _LOGGER.debug("Setting up HDMI Switcher component")
    host = entry.data.get("ip_address")
    # Leaving port as an optional parameter
    # despite my device being hardcoded to port 80
    port = entry.data.get("port", 80)  # Use default port if not specified
    data_handler = HDMISwitcherDataHandler(host=host, port=port)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "data_handler": data_handler,
    }

    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading HDMI Switcher component")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
