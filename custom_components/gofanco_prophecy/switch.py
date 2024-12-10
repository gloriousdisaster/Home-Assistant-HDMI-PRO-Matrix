# switch.py
"""
HDMI Switcher Switch Entities.

This module defines the switch entities for the HDMI Switcher integration,
including power control of the HDMI Switcher device.
"""

import logging
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util.async_ import run_callback_threadsafe
from .const import DOMAIN, MANUFACTURER, MODEL


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant | None,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HDMI Switcher switch entities from a config entry."""
    data_handler = hass.data[DOMAIN][entry.entry_id]["data_handler"]

    # Create the power switch entity
    power_switch = HDMISwitcherPowerSwitch(hass, data_handler, entry)

    # Add the entity to Home Assistant
    async_add_entities([power_switch], True)


class HDMISwitcherPowerSwitch(SwitchEntity):
    """Representation of the HDMI Switcher's power switch."""

    def __init__(
        self,
        hass: HomeAssistant | None,
        data_handler: Any,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        self.hass = hass
        self.data_handler = data_handler
        self.entry_id = entry.entry_id
        self._attr_name = "Power"
        self._attr_unique_id = (
            f"{DOMAIN}_{data_handler.host}_{data_handler.port}_power_switch"
        )
        self._is_on = False

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        success = await self.hass.async_add_executor_job(
            self.data_handler.power_on
        )
        if success:
            self._is_on = True
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to power on the HDMI Switcher")

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        success = await self.hass.async_add_executor_job(
            self.data_handler.power_off
        )
        if success:
            self._is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to power off the HDMI Switcher")

    def turn_on(self, **kwargs):
        """Turn the switch on synchronously."""
        run_callback_threadsafe(
            self.hass.loop, self.async_turn_on, **kwargs
        ).result()

    def turn_off(self, **kwargs):
        """Turn the switch off synchronously."""
        run_callback_threadsafe(
            self.hass.loop, self.async_turn_off, **kwargs
        ).result()

    async def async_update(self):
        """Fetch new state data for the switch."""
        await self.hass.async_add_executor_job(self.data_handler.update)
        # Update self._is_on based on data_handler's data
        # Assuming 'powstatus' in data represents power status
        powstatus = self.data_handler.data.get("powstatus")
        self._is_on = powstatus == "1"

    @property
    def device_info(self):
        """Return device information about this HDMI Switcher."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self.data_handler.host}:{self.data_handler.port}")
            },
            name=f"HDMI Switcher ({self.data_handler.host})",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
