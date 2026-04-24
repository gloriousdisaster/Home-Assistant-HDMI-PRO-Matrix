"""Tests for the data update coordinator."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import FakeDevice


async def test_coordinator_initial_refresh(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The coordinator populates state on first refresh."""
    coordinator = setup_integration.runtime_data
    assert coordinator.data.power is True
    assert coordinator.data.outputs == {1: 1, 2: 2, 3: 3, 4: 4}
    assert coordinator.data.input_names[1] == "Roku"


async def test_coordinator_update_failure(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Transient failures produce UpdateFailed."""
    coordinator = setup_integration.runtime_data

    mock_device.set_failure(OSError)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_invalid_response(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Malformed responses surface as UpdateFailed."""
    coordinator = setup_integration.runtime_data

    mock_device.set_raw_response("HTTP/1.1 200 OK\r\n\r\n<html>nope</html>")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
