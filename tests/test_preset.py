"""Tests for preset recall, rename, and save service."""

from __future__ import annotations

from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.text import DOMAIN as TEXT_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gofanco_prophecy.const import DOMAIN

from .conftest import FakeDevice

RECALL_ENTITY = "select.hdmi_matrix_recall_preset"
PRESET_3_NAME_ENTITY = "text.hdmi_matrix_preset_3_name"


async def test_preset_names_exposed(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Preset text entities expose the device's LOADMAP response."""
    state = hass.states.get(PRESET_3_NAME_ENTITY)
    assert state is not None
    assert state.state == "Preset3"


async def test_preset_recall_fires_call_command(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Selecting a preset option issues call=<N>."""
    recall_state = hass.states.get(RECALL_ENTITY)
    assert recall_state is not None
    option = recall_state.attributes["options"][2]  # "3: Preset3"
    assert option.startswith("3:")

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: RECALL_ENTITY, "option": option},
        blocking=True,
    )
    assert any("call=3" in req for req in mock_device.requests)


async def test_preset_rename_fires_mname_command(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Setting a preset-name text writes mname<N>?<name>?."""
    await hass.services.async_call(
        TEXT_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: PRESET_3_NAME_ENTITY, "value": "Movie"},
        blocking=True,
    )
    assert any("mname3?Movie?" in req for req in mock_device.requests)


async def test_save_preset_service(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """The save_preset service issues save=<N>."""
    await hass.services.async_call(
        DOMAIN,
        "save_preset",
        {"index": 4},
        blocking=True,
    )
    assert any("save=4" in req for req in mock_device.requests)


async def test_save_preset_service_invalid_index_rejected(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The save_preset service validates the range in its schema."""
    with pytest.raises((HomeAssistantError, Exception)):
        await hass.services.async_call(
            DOMAIN,
            "save_preset",
            {"index": 99},
            blocking=True,
        )
