"""DataUpdateCoordinator for the Gofanco Prophecy HDMI Matrix."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, REFRESH_DEBOUNCE_COOLDOWN, SCAN_INTERVAL
from .device import GofancoProphecyClient, ProphecyError, ProphecyState

type ProphecyConfigEntry = ConfigEntry[ProphecyDataUpdateCoordinator]


class ProphecyDataUpdateCoordinator(DataUpdateCoordinator[ProphecyState]):
    """Coordinate polling of the HDMI matrix."""

    config_entry: ProphecyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ProphecyConfigEntry,
        client: GofancoProphecyClient,
        logger: logging.Logger,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            always_update=False,
            request_refresh_debouncer=Debouncer(
                hass,
                logger,
                cooldown=REFRESH_DEBOUNCE_COOLDOWN,
                immediate=False,
            ),
        )
        self.client = client
        self._preset_names: dict[int, str] = {}

    async def _async_update_data(self) -> ProphecyState:
        """Fetch the latest state from the device, preserving cached presets."""
        try:
            state = await self.client.async_get_state()
        except ProphecyError as err:
            raise UpdateFailed(str(err)) from err

        if not self._preset_names:
            try:
                self._preset_names = await self.client.async_load_presets()
            except ProphecyError as err:
                self.logger.debug("Could not load preset names: %s", err)

        state.preset_names = dict(self._preset_names)
        return state

    async def async_reload_presets(self) -> None:
        """Force a re-fetch of preset names on the next poll."""
        self._preset_names = {}
        await self.async_request_refresh()
