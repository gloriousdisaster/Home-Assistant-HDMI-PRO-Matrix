"""Select platform for the Gofanco Prophecy HDMI Matrix."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MUTE_INPUT, NUM_OUTPUTS, NUM_PRESETS
from .coordinator import ProphecyConfigEntry, ProphecyDataUpdateCoordinator
from .device import ProphecyError
from .entity import ProphecyEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProphecyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = [
        ProphecyOutputSelect(coordinator, output)
        for output in range(1, NUM_OUTPUTS + 1)
    ]
    entities.append(ProphecyOutputAllSelect(coordinator))
    entities.append(ProphecyPresetRecallSelect(coordinator))
    async_add_entities(entities)


class _OutputBase(ProphecyEntity, SelectEntity):
    """Shared behaviour for output-routing selects."""

    @property
    def options(self) -> list[str]:
        """Return the input names, including the mute option."""
        return list(self.coordinator.data.input_choices().values())

    def _input_num_for(self, option: str) -> int | None:
        """Resolve a user-visible option back to its input number."""
        for num, name in self.coordinator.data.input_choices().items():
            if name == option:
                return num
        return None


class ProphecyOutputSelect(_OutputBase):
    """A select exposing which input is routed to a specific output."""

    _attr_translation_key = "output"

    def __init__(
        self,
        coordinator: ProphecyDataUpdateCoordinator,
        output: int,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, f"output_{output}")
        self._output = output
        self._attr_translation_placeholders = {"number": str(output)}
        self._attr_suggested_object_id = f"output_{output}"

    @property
    def current_option(self) -> str | None:
        """Return the currently routed input name."""
        source = self.coordinator.data.outputs.get(self._output)
        if source is None:
            return None
        return self.coordinator.data.input_choices().get(source)

    async def async_select_option(self, option: str) -> None:
        """Route a new input to this output."""
        source = self._input_num_for(option)
        if source is None:
            raise HomeAssistantError(f"Unknown input selection: {option}")
        try:
            await self.coordinator.client.async_set_output(self._output, source)
        except ProphecyError as err:
            raise HomeAssistantError(
                f"Failed to set output {self._output}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()


class ProphecyOutputAllSelect(_OutputBase):
    """A select that routes a single input to every output at once."""

    _attr_translation_key = "output_all"

    def __init__(self, coordinator: ProphecyDataUpdateCoordinator) -> None:
        """Initialize the all-outputs select."""
        super().__init__(coordinator, "output_all")
        self._attr_suggested_object_id = "output_all"

    @property
    def current_option(self) -> str | None:
        """Return the common input if all outputs are on the same input."""
        outputs = self.coordinator.data.outputs
        sources = set(outputs.values())
        if len(sources) != 1:
            return None
        (common,) = sources
        if common == MUTE_INPUT:
            return self.coordinator.data.input_choices().get(MUTE_INPUT)
        return self.coordinator.data.input_choices().get(common)

    async def async_select_option(self, option: str) -> None:
        """Route all outputs to the chosen input."""
        source = self._input_num_for(option)
        if source is None:
            raise HomeAssistantError(f"Unknown input selection: {option}")
        try:
            await self.coordinator.client.async_set_all_outputs(source)
        except ProphecyError as err:
            raise HomeAssistantError(f"Failed to set all outputs: {err}") from err
        await self.coordinator.async_request_refresh()


class ProphecyPresetRecallSelect(ProphecyEntity, SelectEntity):
    """A dropdown that recalls one of the 8 stored presets when selected."""

    _attr_translation_key = "preset_recall"

    def __init__(self, coordinator: ProphecyDataUpdateCoordinator) -> None:
        """Initialize the preset-recall select."""
        super().__init__(coordinator, "preset_recall")
        self._attr_suggested_object_id = "recall_preset"

    @property
    def options(self) -> list[str]:
        """Return the list of preset names."""
        return [self._preset_label(i) for i in range(1, NUM_PRESETS + 1)]

    @property
    def current_option(self) -> str | None:
        """There's no "current preset" reported — always None."""
        return None

    def _preset_label(self, index: int) -> str:
        """Format a user-facing preset label."""
        name = self.coordinator.data.preset_names.get(index, f"Preset {index}")
        return f"{index}: {name}"

    async def async_select_option(self, option: str) -> None:
        """Recall the preset matching the option."""
        index: int | None = None
        for i in range(1, NUM_PRESETS + 1):
            if self._preset_label(i) == option:
                index = i
                break
        if index is None:
            raise HomeAssistantError(f"Unknown preset: {option}")
        try:
            await self.coordinator.client.async_recall_preset(index)
        except ProphecyError as err:
            raise HomeAssistantError(f"Failed to recall preset {index}: {err}") from err
        await self.coordinator.async_request_refresh()
