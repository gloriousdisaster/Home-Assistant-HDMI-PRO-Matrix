"""Text platform exposing input and output labels on the HDMI Matrix."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import NAME_MAX_LEN, NUM_INPUTS, NUM_OUTPUTS, NUM_PRESETS
from .coordinator import ProphecyConfigEntry, ProphecyDataUpdateCoordinator
from .device import ProphecyError
from .entity import ProphecyEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProphecyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up text entities for naming inputs and outputs."""
    coordinator = entry.runtime_data
    entities: list[TextEntity] = [
        ProphecyInputNameText(coordinator, i) for i in range(1, NUM_INPUTS + 1)
    ]
    entities.extend(
        ProphecyOutputNameText(coordinator, i) for i in range(1, NUM_OUTPUTS + 1)
    )
    entities.extend(
        ProphecyPresetNameText(coordinator, i) for i in range(1, NUM_PRESETS + 1)
    )
    async_add_entities(entities)


class _ProphecyNameText(ProphecyEntity, TextEntity):
    """Base class for name-editing text entities."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_max = NAME_MAX_LEN
    _attr_native_min = 0

    def __init__(
        self,
        coordinator: ProphecyDataUpdateCoordinator,
        index: int,
        unique_suffix: str,
        translation_key: str,
        object_id: str,
    ) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, unique_suffix)
        self._index = index
        self._attr_translation_key = translation_key
        self._attr_translation_placeholders = {"number": str(index)}
        self._attr_suggested_object_id = object_id


class ProphecyInputNameText(_ProphecyNameText):
    """Editable label for an input."""

    def __init__(self, coordinator: ProphecyDataUpdateCoordinator, index: int) -> None:
        """Initialize the input-name text entity."""
        super().__init__(
            coordinator,
            index,
            unique_suffix=f"input_name_{index}",
            translation_key="input_name",
            object_id=f"input_{index}_name",
        )

    @property
    def native_value(self) -> str | None:
        """Return the current label for this input."""
        return self.coordinator.data.input_names.get(self._index)

    async def async_set_value(self, value: str) -> None:
        """Persist a new label for this input."""
        inputs = dict(self.coordinator.data.input_names)
        inputs[self._index] = value
        try:
            await self.coordinator.client.async_set_names(
                inputs, self.coordinator.data.output_names
            )
        except ProphecyError as err:
            raise HomeAssistantError(
                f"Failed to rename input {self._index}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()


class ProphecyOutputNameText(_ProphecyNameText):
    """Editable label for an output."""

    def __init__(self, coordinator: ProphecyDataUpdateCoordinator, index: int) -> None:
        """Initialize the output-name text entity."""
        super().__init__(
            coordinator,
            index,
            unique_suffix=f"output_name_{index}",
            translation_key="output_name",
            object_id=f"output_{index}_name",
        )

    @property
    def native_value(self) -> str | None:
        """Return the current label for this output."""
        return self.coordinator.data.output_names.get(self._index)

    async def async_set_value(self, value: str) -> None:
        """Persist a new label for this output."""
        outputs = dict(self.coordinator.data.output_names)
        outputs[self._index] = value
        try:
            await self.coordinator.client.async_set_names(
                self.coordinator.data.input_names, outputs
            )
        except ProphecyError as err:
            raise HomeAssistantError(
                f"Failed to rename output {self._index}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()


class ProphecyPresetNameText(_ProphecyNameText):
    """Editable label for a preset slot."""

    def __init__(self, coordinator: ProphecyDataUpdateCoordinator, index: int) -> None:
        """Initialize the preset-name text entity."""
        super().__init__(
            coordinator,
            index,
            unique_suffix=f"preset_name_{index}",
            translation_key="preset_name",
            object_id=f"preset_{index}_name",
        )

    @property
    def native_value(self) -> str | None:
        """Return the current name of this preset slot."""
        return self.coordinator.data.preset_names.get(self._index)

    async def async_set_value(self, value: str) -> None:
        """Persist a new name for this preset slot."""
        try:
            await self.coordinator.client.async_set_preset_name(self._index, value)
        except ProphecyError as err:
            raise HomeAssistantError(
                f"Failed to rename preset {self._index}: {err}"
            ) from err
        await self.coordinator.async_reload_presets()
