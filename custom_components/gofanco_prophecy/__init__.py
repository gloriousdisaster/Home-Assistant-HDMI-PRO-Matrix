"""The Gofanco Prophecy HDMI Matrix integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import DEFAULT_PORT, DOMAIN, NUM_PRESETS, PLATFORMS
from .coordinator import ProphecyConfigEntry, ProphecyDataUpdateCoordinator
from .device import GofancoProphecyClient, ProphecyError

_LOGGER = logging.getLogger(__name__)

SERVICE_SAVE_PRESET = "save_preset"
ATTR_ENTRY_ID = "entry_id"
ATTR_INDEX = "index"

_SAVE_PRESET_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Required(ATTR_INDEX): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=NUM_PRESETS)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration-wide save_preset service."""
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ProphecyConfigEntry) -> bool:
    """Set up Gofanco Prophecy from a config entry."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)

    client = GofancoProphecyClient(host, port)
    coordinator = ProphecyDataUpdateCoordinator(hass, entry, client, _LOGGER)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ProphecyError as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProphecyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ProphecyConfigEntry) -> bool:
    """Migrate old config entries to the current schema."""
    if entry.version >= 2:
        return True

    data = {**entry.data}
    if CONF_HOST not in data and "ip_address" in data:
        data[CONF_HOST] = data.pop("ip_address")
    data.setdefault(CONF_PORT, DEFAULT_PORT)

    hass.config_entries.async_update_entry(entry, data=data, version=2)
    _LOGGER.debug("Migrated config entry %s to version 2", entry.entry_id)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ProphecyConfigEntry
) -> None:
    """Reload integration when options or data change."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _register_services(hass: HomeAssistant) -> None:
    """Register global services once per HA startup."""
    if hass.services.has_service(DOMAIN, SERVICE_SAVE_PRESET):
        return

    async def _handle_save_preset(call: ServiceCall) -> None:
        coordinator = _pick_coordinator(hass, call.data.get(ATTR_ENTRY_ID))
        index: int = call.data[ATTR_INDEX]
        try:
            await coordinator.client.async_save_preset(index)
        except ProphecyError as err:
            raise HomeAssistantError(f"Failed to save preset {index}: {err}") from err
        await coordinator.async_reload_presets()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_PRESET,
        _handle_save_preset,
        schema=_SAVE_PRESET_SCHEMA,
    )


def _pick_coordinator(
    hass: HomeAssistant, entry_id: str | None
) -> ProphecyDataUpdateCoordinator:
    """Resolve which matrix's coordinator to act on."""
    loaded: list[ProphecyConfigEntry] = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if entry_id is not None:
        for entry in loaded:
            if entry.entry_id == entry_id:
                return entry.runtime_data
        raise HomeAssistantError(f"No loaded HDMI Matrix entry with id {entry_id}")
    if not loaded:
        raise HomeAssistantError("No HDMI Matrix entries are loaded")
    if len(loaded) > 1:
        raise HomeAssistantError(
            "Multiple HDMI Matrix entries are loaded; pass entry_id to choose one"
        )
    return loaded[0].runtime_data
