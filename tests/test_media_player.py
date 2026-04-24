"""Media player platform tests."""

from __future__ import annotations

from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MP_DOMAIN,
    SERVICE_SELECT_SOURCE,
    SERVICE_VOLUME_MUTE,
    MediaPlayerState,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import FakeDevice

ENTITY_OUT1 = "media_player.hdmi_matrix_output_1"


async def test_media_player_initial_state(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Media player reports current source and on state for output 1."""
    state = hass.states.get(ENTITY_OUT1)
    assert state is not None
    assert state.state == MediaPlayerState.ON
    assert state.attributes.get(ATTR_INPUT_SOURCE) == "Roku"
    assert "AppleTV" in state.attributes.get("source_list", [])


async def test_media_player_select_source(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Selecting a source issues out1=<N>."""
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_OUT1, ATTR_INPUT_SOURCE: "AppleTV"},
        blocking=True,
    )
    assert any("out1=2" in req for req in mock_device.requests)


async def test_media_player_turn_on_off(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Turn_on / turn_off drive the matrix power."""
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_OUT1}, blocking=True
    )
    assert any("poweron" in req for req in mock_device.requests)

    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_OUT1}, blocking=True
    )
    assert any("poweroff" in req for req in mock_device.requests)


async def test_media_player_mute_routes_to_zero(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_device: FakeDevice,
) -> None:
    """Muting a media_player routes that output to input 0."""
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: ENTITY_OUT1, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )
    assert any("out1=0" in req for req in mock_device.requests)


async def test_media_player_unmute_with_no_inputs_raises(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Unmuting with no known inputs and no prior source raises a clear error."""
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.gofanco_prophecy.media_player import (
        ProphecyOutputMediaPlayer,
    )

    coordinator = setup_integration.runtime_data
    entity = ProphecyOutputMediaPlayer(coordinator, 1)
    # Force the theoretical edge case: no remembered source and no known inputs.
    entity._last_source = None
    coordinator.data.input_names = {}

    with pytest.raises(HomeAssistantError, match="No input available"):
        await entity.async_mute_volume(False)
