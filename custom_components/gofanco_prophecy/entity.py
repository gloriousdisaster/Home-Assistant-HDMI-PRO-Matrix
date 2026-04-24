"""Shared base entity for the Gofanco Prophecy HDMI Matrix integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ProphecyDataUpdateCoordinator


class ProphecyEntity(CoordinatorEntity[ProphecyDataUpdateCoordinator]):
    """Base class for Gofanco Prophecy entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProphecyDataUpdateCoordinator,
        unique_suffix: str,
    ) -> None:
        """Initialize a Prophecy entity."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="HDMI Matrix",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=f"http://{coordinator.client.host}",
        )
