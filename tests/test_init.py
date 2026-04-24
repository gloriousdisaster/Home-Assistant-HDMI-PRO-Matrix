"""Tests for integration setup, unload, and migration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gofanco_prophecy.const import DOMAIN

from .conftest import HOST, PORT, FakeDevice


async def test_setup_and_unload(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Setup succeeds and unload cleans up platforms."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_on_connection_error(
    hass: HomeAssistant,
    mock_device: FakeDevice,
) -> None:
    """Setup raises ConfigEntryNotReady when the device is unreachable."""
    mock_device.set_failure(OSError)

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_migration_from_v1(
    hass: HomeAssistant,
    mock_device: FakeDevice,
) -> None:
    """Old v1 entries using ip_address are migrated to v2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={"ip_address": HOST, "port": PORT},
        unique_id=f"{HOST}:{PORT}",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_HOST] == HOST
    assert entry.data[CONF_PORT] == PORT


async def test_save_preset_service_with_no_entries(
    hass: HomeAssistant,
) -> None:
    """The save_preset service errors cleanly when no matrix is loaded."""
    # Call async_setup directly so the service is registered without an entry.
    from custom_components.gofanco_prophecy import async_setup

    await async_setup(hass, {})

    with pytest.raises(HomeAssistantError, match="No HDMI Matrix entries are loaded"):
        await hass.services.async_call(
            DOMAIN, "save_preset", {"index": 1}, blocking=True
        )


async def test_save_preset_service_with_unknown_entry_id(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Passing an unknown entry_id to save_preset errors clearly."""
    with pytest.raises(HomeAssistantError, match="No loaded HDMI Matrix entry with id"):
        await hass.services.async_call(
            DOMAIN,
            "save_preset",
            {"entry_id": "does-not-exist", "index": 1},
            blocking=True,
        )


async def test_save_preset_service_with_multiple_entries_requires_entry_id(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """With more than one loaded matrix, save_preset requires an entry_id."""
    # Load a second matrix on a different host.
    second = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_HOST: "192.0.2.11", CONF_PORT: PORT},
        unique_id="192.0.2.11:80",
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError, match="Multiple HDMI Matrix entries"):
        await hass.services.async_call(
            DOMAIN, "save_preset", {"index": 1}, blocking=True
        )

    # And with an explicit entry_id it works against that specific matrix.
    await hass.services.async_call(
        DOMAIN,
        "save_preset",
        {"entry_id": second.entry_id, "index": 2},
        blocking=True,
    )
    assert any("save=2" in req for req in mock_device.requests)
