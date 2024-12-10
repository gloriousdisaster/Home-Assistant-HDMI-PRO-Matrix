# select.py
"""
HDMI Switcher Select Entities.

This module defines the select entities for the HDMI Switcher integration,
allowing users to select inputs for outputs and rename items.
"""

# pylint: disable=duplicate-code

import logging
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers import entity_registry as er
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.async_ import run_callback_threadsafe
from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HDMI Switcher select entities from a config entry."""
    data_handler = hass.data[DOMAIN][entry.entry_id]["data_handler"]

    # Create select entities
    selects = []

    # Existing output select entities
    output_selects = []
    for output_num in range(1, 5):
        output_select = HDMISwitcherSelect(
            hass, data_handler, output_num, entry.entry_id
        )
        selects.append(output_select)
        output_selects.append(output_select)

    # 'Output All' select entity
    output_all_select = HDMISwitcherOutputAllSelect(
        hass, data_handler, entry.entry_id
    )
    selects.append(output_all_select)

    # # Rename select entity
    # rename_select = HDMISwitcherRenameSelect(hass, entry, data_handler)
    # selects.append(rename_select)

    # # Store the select entities for later reference
    # hass.data[DOMAIN][entry.entry_id]["select_entities"] = selects
    # hass.data[DOMAIN][entry.entry_id][
    #     "output_select_entities"
    # ] = output_selects
    # hass.data[DOMAIN][entry.entry_id]["rename_select_entity"] = rename_select

    # # Add entities to Home Assistant
    async_add_entities(selects, True)


# pylint: disable=too-many-instance-attributes
class HDMISwitcherSelect(SelectEntity):
    """Representation of an HDMI Switcher
    select entity for an individual output.
    """

    def __init__(self, hass, data_handler, output_num, entry_id):
        """Initialize the select entity."""
        self.hass = hass
        self.data_handler = data_handler
        self.output_num = output_num
        self.entry_id = entry_id
        self._state = None
        self._default_name = f"Output {output_num}"
        self._attr_unique_id = (
            f"{DOMAIN}_{data_handler.host}_{data_handler.port}_output_"
            f"{output_num}_select"
        )
        self._attr_name = (
            self._default_name
        )  # Static name for entity ID generation
        self._attr_suggested_object_id = f"output{output_num}"
        self._attr_options = list(self.data_handler.input_names.values())

    @property
    def options(self):
        """Return the list of available options."""
        return list(self.data_handler.input_names.values())

    @property
    def current_option(self):
        """Return the currently selected option."""
        return self._state

    async def async_select_option(self, option):
        """Change the selected input for this output."""
        # Find the input number corresponding to the selected option
        input_num = next(
            (
                int(num)
                for num, name in self.data_handler.input_names.items()
                if name == option
            ),
            None,
        )

        if input_num is None:
            _LOGGER.error("Invalid input name selected: %s", option)
            return

        # Send command to change the input
        success = await self.hass.async_add_executor_job(
            self.data_handler.set_output_input, self.output_num, input_num
        )

        if success:
            # Update the state and notify Home Assistant
            self._state = option
            self.async_write_ha_state()
        else:
            _LOGGER.error(
                "Failed to set output %s to input %s",
                self.output_num,
                option,
            )

    def select_option(self, option: str) -> None:
        """Select an option synchronously."""
        run_callback_threadsafe(
            self.hass.loop, self.async_select_option, option
        ).result()

    async def async_update(self):
        """Fetch new state data for the select entity."""
        # Update data from the device
        await self.hass.async_add_executor_job(self.data_handler.update)
        out_key = f"out{self.output_num}"
        input_num = self.data_handler.data.get(out_key)
        self._state = self._get_input_name(input_num)
        self._attr_options = list(self.data_handler.input_names.values())

        # Update friendly name in the entity registry
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.entity_id)
        if entry:
            friendly_name = self.data_handler.output_names.get(
                str(self.output_num), self._default_name
            )
            if entry.name != friendly_name:
                registry.async_update_entity(
                    self.entity_id, name=friendly_name
                )

    def _get_input_name(self, input_num):
        """Get the input name for a given input number."""
        if input_num is None:
            return None
        return self.data_handler.input_names.get(
            str(input_num), f"Input {input_num}"
        )

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


# pylint: disable=too-many-instance-attributes
class HDMISwitcherOutputAllSelect(SelectEntity):
    """Representation of the HDMI Switcher's 'Output All' select entity."""

    def __init__(self, hass, data_handler, entry_id):
        """Initialize the 'Output All' select entity."""
        self.hass = hass
        self.data_handler = data_handler
        self.entry_id = entry_id
        self._state = None
        self._attr_name = "Output All"
        self._attr_unique_id = (
            f"{DOMAIN}_{data_handler.host}_{data_handler.port}"
            f"_output_all_select"
        )
        self._attr_suggested_object_id = "output_all"
        self._attr_options = list(self.data_handler.input_names.values())

    @property
    def options(self):
        """Return the list of available options."""
        return list(self.data_handler.input_names.values())

    @property
    def current_option(self):
        """Return None to reset the dropdown after selection."""
        return self._state

    async def async_select_option(self, option):
        """Change all outputs to the selected input."""
        # Find the input number corresponding to the selected option
        input_num = next(
            (
                int(num)
                for num, name in self.data_handler.input_names.items()
                if name == option
            ),
            None,
        )

        if input_num is None:
            _LOGGER.error(
                "Invalid input name selected for Output All: %s", option
            )
            return

        # Send command to change all outputs
        success = await self.hass.async_add_executor_job(
            self.data_handler.set_all_outputs_input, input_num
        )

        if success:
            # Reset state to None to clear the selection in the UI
            self._state = None
            self.async_write_ha_state()

            # Update individual output select entities
            output_select_entities = self.hass.data[DOMAIN][
                self.entry_id
            ].get("output_select_entities", [])
            for entity in output_select_entities:
                await entity.async_update()
                entity.async_write_ha_state()
        else:
            _LOGGER.error(
                "Failed to set all outputs to input %s",
                option,
            )

    def select_option(self, option: str) -> None:
        """Select an option synchronously."""
        run_callback_threadsafe(
            self.hass.loop, self.async_select_option, option
        ).result()

    async def async_update(self):
        """Fetch new state data for the select entity."""
        # Update options based on the latest input names
        await self.hass.async_add_executor_job(self.data_handler.update)
        self._attr_options = list(self.data_handler.input_names.values())
        # Reset state to None to keep the dropdown empty
        self._state = None

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


# pylint: disable=too-many-instance-attributes
# class HDMISwitcherRenameSelect(SelectEntity):
#     """Select entity for choosing input/output to rename."""

#     def __init__(self, hass: HomeAssistant, entry, data_handler) -> None:
#         """Initialize the rename select entity."""
#         self.hass = hass
#         self.entry = entry
#         self.data_handler = data_handler
#         self._attr_name = "Select Item to Rename"
#         self._attr_unique_id = (
#             f"{DOMAIN}_{data_handler.host}_{data_handler.port}_rename_select"
#         )
#         self._attr_suggested_object_id = "hdmi_switcher_rename_select"
#         self._attr_options = [f"Input {i}" for i in range(1, 5)] + [
#             f"Output {i}" for i in range(1, 5)
#         ]
#         self._attr_current_option = self._attr_options[0]
#         self._attr_entity_category = EntityCategory.CONFIG

#     async def async_select_option(self, option: str) -> None:
#         """Handle option selection."""
#         self._attr_current_option = option
#         self.async_write_ha_state()

#         # Update the new_name_text_entity with
#         # the current name of the selected item
#         new_name_text_entity = self.hass.data[DOMAIN][self.entry.entry_id][
#             "new_name_text_entity"
#         ]

#         # Determine if item is an input or output
#         if option.startswith("Input"):
#             num = int(option.split(" ")[1])
#             current_name = self.data_handler.input_names.get(
#                 str(num), f"Input {num}"
#             )
#         elif option.startswith("Output"):
#             num = int(option.split(" ")[1])
#             current_name = self.data_handler.output_names.get(
#                 str(num), f"Output {num}"
#             )
#         else:
#             _LOGGER.error("Invalid item selected: %s", option)
#             current_name = ""

#         # Truncate the current name to 7 characters if necessary
#         current_name = current_name[:7]

#         # Update the new_name_text_entity
#         new_name_text_entity.native_value = (
#             current_name  # Use public property instead of protected member
#         )
#         new_name_text_entity.async_write_ha_state()

#     def select_option(self, option: str) -> None:
#         """Select an option synchronously."""
#         run_callback_threadsafe(
#             self.hass.loop, self.async_select_option, option
#         ).result()

#     async def async_update(self):
#         """Update the select entity."""
#         # No dynamic updates needed; method intentionally left empty

#     @property
#     def device_info(self):
#         """Return device information about this HDMI Switcher."""
#         return DeviceInfo(
#             identifiers={
#                 (DOMAIN, f"{self.data_handler.host}:{self.data_handler.port}")
#             },
#             name=f"HDMI Switcher ({self.data_handler.host})",
#             manufacturer=MANUFACTURER,
#             model=MODEL,
#         )
