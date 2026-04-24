"""Switch platform for the Gofanco Prophecy HDMI Matrix."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ProphecyConfigEntry, ProphecyDataUpdateCoordinator
from .device import ProphecyError
from .entity import ProphecyEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProphecyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the power switch entity."""
    async_add_entities([ProphecyPowerSwitch(entry.runtime_data)])


class ProphecyPowerSwitch(ProphecyEntity, SwitchEntity):
    """Power switch for the HDMI matrix."""

    _attr_translation_key = "power"

    def __init__(self, coordinator: ProphecyDataUpdateCoordinator) -> None:
        """Initialize the power switch."""
        super().__init__(coordinator, "power")

    @property
    def is_on(self) -> bool:
        """Return whether the device is powered on."""
        return self.coordinator.data.power

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Power the device on."""
        await self._async_set_power(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Power the device off."""
        await self._async_set_power(False)

    async def _async_set_power(self, on: bool) -> None:
        """Send a power command and refresh."""
        try:
            await self.coordinator.client.async_power(on)
        except ProphecyError as err:
            raise HomeAssistantError(
                f"Failed to {'power on' if on else 'power off'} HDMI matrix: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
