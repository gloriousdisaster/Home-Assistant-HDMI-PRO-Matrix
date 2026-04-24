"""Platform smoke tests."""

from __future__ import annotations

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.text import DOMAIN as TEXT_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import FakeDevice

SWITCH_ENTITY = "switch.hdmi_matrix_power"
SELECT_OUTPUT_1 = "select.hdmi_matrix_output_1"
SELECT_OUTPUT_ALL = "select.hdmi_matrix_all_outputs"
BUTTON_MUTE_ALL = "button.hdmi_matrix_mute_all_outputs"
TEXT_INPUT_1 = "text.hdmi_matrix_input_1_label"


async def test_power_switch_state(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Power switch reports on when powstatus == '1'."""
    state = hass.states.get(SWITCH_ENTITY)
    assert state is not None
    assert state.state == STATE_ON


async def test_power_switch_turn_on(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Turning the switch on issues a poweron POST."""
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: SWITCH_ENTITY},
        blocking=True,
    )
    assert any("poweron" in req for req in mock_device.requests)


async def test_output_select_current_option(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Output selects reflect the currently routed input."""
    state = hass.states.get(SELECT_OUTPUT_1)
    assert state is not None
    assert state.state == "Roku"


async def test_output_select_change(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Changing a select sends the correct command."""
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: SELECT_OUTPUT_1, "option": "AppleTV"},
        blocking=True,
    )
    assert any("out1=2" in req for req in mock_device.requests)


async def test_output_all_select_differing_outputs(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """With outputs on different inputs, output_all reads unknown."""
    state = hass.states.get(SELECT_OUTPUT_ALL)
    assert state is not None
    assert state.state in ("unknown", "None", "")


async def test_mute_all_button_press(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Pressing the mute-all button issues the command."""
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: BUTTON_MUTE_ALL},
        blocking=True,
    )
    assert any("outa=0" in req for req in mock_device.requests)


async def test_text_entity_state(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Text entities expose the current device labels."""
    state = hass.states.get(TEXT_INPUT_1)
    assert state is not None
    assert state.state == "Roku"


async def test_text_entity_set_value(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Setting a text value writes a namein command."""
    await hass.services.async_call(
        TEXT_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: TEXT_INPUT_1, "value": "Xbox"},
        blocking=True,
    )
    assert any("namein1?Xbox?" in req for req in mock_device.requests)


async def test_command_failure_raises(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Client errors during commands surface as HomeAssistantError."""
    mock_device.set_failure(OSError)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            "turn_on",
            {ATTR_ENTITY_ID: SWITCH_ENTITY},
            blocking=True,
        )
