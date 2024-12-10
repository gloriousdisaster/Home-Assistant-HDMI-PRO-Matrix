# button.py
"""
HDMI Switcher Button Entities.

This module defines the button entities for the HDMI Switcher integration.
"""

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.core import callback, HomeAssistant
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
    """Set up HDMI Switcher button entities from a config entry."""
    data_handler = hass.data[DOMAIN][entry.entry_id]["data_handler"]

    # Create the 'Mute All' button entity
    mute_all_button = HDMISwitcherMuteAllButton(hass, data_handler, entry)
    # # Create the 'Set Name' button entity
    # set_name_button = HDMISwitcherSetNameButton(hass, data_handler, entry)

    # Add the entities to Home Assistant
    # async_add_entities([mute_all_button, set_name_button], True)
    async_add_entities([mute_all_button], True)


class HDMISwitcherSetNameButton(ButtonEntity):
    """Button entity to set a new name for an input/output."""

    def __init__(
        self, hass: HomeAssistant, data_handler, entry: ConfigEntry
    ) -> None:
        """Initialize the button."""
        self.hass = hass
        self.data_handler = data_handler
        self.entry_id = entry.entry_id
        self._attr_name = "Set Name"
        self._attr_unique_id = (
            f"{DOMAIN}_{data_handler.host}"
            f"_{data_handler.port}_set_name_button"
        )

    async def async_press(self):
        """Handle the button press to set a new name."""
        rename_select = self.hass.data[DOMAIN][self.entry_id][
            "rename_select_entity"
        ]
        new_name_text = self.hass.data[DOMAIN][self.entry_id][
            "new_name_text_entity"
        ]

        item = rename_select.current_option
        new_name = (
            new_name_text.native_value
        )  # Use public property instead of protected member

        if not item or not new_name:
            _LOGGER.error("Item or new name not specified")
            return

        # Determine if item is an input or output
        if item.startswith("Input"):
            is_input = True
            num = int(item.split(" ")[1])
        elif item.startswith("Output"):
            is_input = False
            num = int(item.split(" ")[1])
        else:
            _LOGGER.error("Invalid item specified: %s", item)
            return

        # Update the name in the data handler
        if is_input:
            self.data_handler.input_names[str(num)] = new_name
        else:
            self.data_handler.output_names[str(num)] = new_name

        # Send the new names to the device
        success = await self.hass.async_add_executor_job(
            self.data_handler.set_names,
            self.data_handler.input_names,
            self.data_handler.output_names,
        )

        if success:
            _LOGGER.debug(
                "Successfully set name for %s to '%s'", item, new_name
            )
            # Update entities
            await self._update_entities()
            # Clear the new name text entity
            new_name_text.native_value = (
                ""  # Use public property instead of protected member
            )
            new_name_text.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set name for %s", item)

    def press(self):
        """Handle synchronous button press."""
        # Call the asynchronous press method in the event loop
        run_callback_threadsafe(self.hass.loop, self.async_press).result()

    @callback
    async def _update_entities(self):
        """Update entities after setting names."""
        # Update text entities
        text_entities = self.hass.data[DOMAIN][self.entry_id].get(
            "text_entities", []
        )
        for entity in text_entities:
            await entity.async_update()
            entity.async_write_ha_state()

        # Update select entities
        select_entities = self.hass.data[DOMAIN][self.entry_id].get(
            "select_entities", []
        )
        for entity in select_entities:
            await entity.async_update()
            entity.async_write_ha_state()

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


class HDMISwitcherMuteAllButton(ButtonEntity):
    """Representation of the HDMI Switcher's 'Mute All' button."""

    def __init__(self, hass, data_handler, entry):
        """Initialize the button."""
        self.hass = hass
        self.data_handler = data_handler
        self.entry_id = entry.entry_id
        self._attr_name = "Mute All"
        self._attr_unique_id = (
            f"{DOMAIN}_{data_handler.host}_{data_handler.port}"
            f"_mute_all_button"
        )

    async def async_press(self):
        """Handle the button press to mute all outputs."""
        success = await self.hass.async_add_executor_job(
            self.data_handler.mute_all_outputs
        )
        if success:
            _LOGGER.debug("Muted all outputs successfully")
            # Update individual output select entities

            output_select_entities = self.hass.data[DOMAIN][
                self.entry_id
            ].get("output_select_entities", [])

            for entity in output_select_entities:
                await entity.async_update()
                entity.async_write_ha_state()
        else:
            _LOGGER.error("Failed to mute all outputs")

    def press(self):
        """Handle synchronous button press."""
        # Call the asynchronous press method in the event loop
        run_callback_threadsafe(self.hass.loop, self.async_press).result()

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
