"""Button platform for the Gofanco Prophecy HDMI Matrix."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up button entities."""
    async_add_entities([ProphecyMuteAllButton(entry.runtime_data)])


class ProphecyMuteAllButton(ProphecyEntity, ButtonEntity):
    """Button that mutes every output at once."""

    _attr_translation_key = "mute_all"

    def __init__(self, coordinator: ProphecyDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "mute_all")
        self._attr_suggested_object_id = "mute_all"

    async def async_press(self) -> None:
        """Mute all outputs."""
        try:
            await self.coordinator.client.async_mute_all()
        except ProphecyError as err:
            raise HomeAssistantError(f"Failed to mute all outputs: {err}") from err
        await self.coordinator.async_request_refresh()
