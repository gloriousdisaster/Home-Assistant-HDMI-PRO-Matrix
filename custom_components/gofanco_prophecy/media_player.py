"""Media player platform for the Gofanco Prophecy HDMI Matrix.

One `media_player` entity per physical output. Each one exposes:

- `source` / `source_list` — the routed input (user-named).
- Mute volume — routes the output to input 0 (the device's mute input).
- `turn_on` / `turn_off` — toggles the matrix's global power.

Power is globally toggled on this device (not per-output), so turning any
output "on" powers up the matrix and turning any output "off" powers it
down. The per-output `state` still honours mute, so you can see at a glance
which outputs are routed vs. silenced.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MUTE_INPUT, NUM_OUTPUTS
from .coordinator import ProphecyConfigEntry, ProphecyDataUpdateCoordinator
from .device import ProphecyError
from .entity import ProphecyEntity

PARALLEL_UPDATES = 0

_SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_MUTE
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProphecyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up media_player entities — one per output."""
    coordinator = entry.runtime_data
    async_add_entities(
        ProphecyOutputMediaPlayer(coordinator, output)
        for output in range(1, NUM_OUTPUTS + 1)
    )


class ProphecyOutputMediaPlayer(ProphecyEntity, MediaPlayerEntity):
    """A media player representing one physical output of the matrix."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = _SUPPORTED_FEATURES
    _attr_translation_key = "output_player"

    def __init__(
        self,
        coordinator: ProphecyDataUpdateCoordinator,
        output: int,
    ) -> None:
        """Initialize the media player."""
        super().__init__(coordinator, f"output_{output}_player")
        self._output = output
        self._attr_translation_placeholders = {"number": str(output)}
        self._attr_suggested_object_id = f"output_{output}"
        self._last_source: int | None = None

    @property
    def state(self) -> MediaPlayerState:
        """Reflect power + mute state."""
        data = self.coordinator.data
        if not data.power:
            return MediaPlayerState.OFF
        if data.outputs.get(self._output) == MUTE_INPUT:
            return MediaPlayerState.IDLE
        return MediaPlayerState.ON

    @property
    def source_list(self) -> list[str]:
        """Return the list of selectable inputs (excluding mute)."""
        return list(self.coordinator.data.input_names.values())

    @property
    def source(self) -> str | None:
        """Return the currently routed input's name, or None when muted."""
        source_num = self.coordinator.data.outputs.get(self._output)
        if source_num is None or source_num == MUTE_INPUT:
            return None
        return self.coordinator.data.input_names.get(source_num)

    @property
    def is_volume_muted(self) -> bool:
        """Report mute state based on routing to the mute input."""
        return self.coordinator.data.outputs.get(self._output) == MUTE_INPUT

    async def async_select_source(self, source: str) -> None:
        """Route a new input to this output."""
        input_num = _resolve_source(self.coordinator, source)
        await self._run(
            "select source",
            self.coordinator.client.async_set_output,
            self._output,
            input_num,
        )
        self._last_source = input_num

    async def async_mute_volume(self, mute: bool) -> None:
        """Route to the mute input, or unmute by restoring the previous source."""
        if mute:
            current = self.coordinator.data.outputs.get(self._output)
            if current and current != MUTE_INPUT:
                self._last_source = current
            await self._run(
                "mute output",
                self.coordinator.client.async_set_output,
                self._output,
                MUTE_INPUT,
            )
            return

        restore = self._last_source or next(
            iter(self.coordinator.data.input_names), None
        )
        if restore is None:
            raise HomeAssistantError("No input available to unmute onto")
        await self._run(
            "unmute output",
            self.coordinator.client.async_set_output,
            self._output,
            restore,
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Power the matrix on (global)."""
        await self._run("power on", self.coordinator.client.async_power, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Power the matrix off (global)."""
        await self._run("power off", self.coordinator.client.async_power, False)

    async def _run(self, label: str, func: Any, *args: Any) -> None:
        """Wrap a client mutation so failures surface as HomeAssistantError."""
        try:
            await func(*args)
        except ProphecyError as err:
            raise HomeAssistantError(
                f"Failed to {label} on output {self._output}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()


def _resolve_source(coordinator: ProphecyDataUpdateCoordinator, source: str) -> int:
    """Map a user-selected source name back to its input number."""
    for num, name in coordinator.data.input_names.items():
        if name == source:
            return num
    raise HomeAssistantError(f"Unknown source: {source}")
