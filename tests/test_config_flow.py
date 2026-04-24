"""Tests for the Gofanco Prophecy config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gofanco_prophecy.const import DOMAIN
from custom_components.gofanco_prophecy.device import (
    ProphecyConnectionError,
    ProphecyResponseError,
)

from .conftest import HOST, PORT, FakeDevice


async def _start_user_flow(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_happy_path(
    hass: HomeAssistant, mock_device: FakeDevice
) -> None:
    """User completes the flow with a valid device."""
    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.gofanco_prophecy.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"HDMI Matrix ({HOST})"
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: PORT}
    assert result["result"].unique_id == f"{HOST}:{PORT}"


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_device: FakeDevice,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Duplicate entries are rejected."""
    mock_config_entry.add_to_hass(hass)
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("exception", "expected_error"),
    [
        (ProphecyConnectionError("boom"), "cannot_connect"),
        (ProphecyResponseError("bad json"), "invalid_response"),
        (RuntimeError("weird"), "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    exception: Exception,
    expected_error: str,
) -> None:
    """Errors are mapped to translation keys and the form is redisplayed."""
    result = await _start_user_flow(hass)
    with patch(
        "custom_components.gofanco_prophecy.config_flow.GofancoProphecyClient.async_get_state",
        AsyncMock(side_effect=exception),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}


async def test_reconfigure_happy_path(
    hass: HomeAssistant,
    mock_device: FakeDevice,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfiguring updates host/port and reloads."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: PORT}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_HOST] == HOST


async def test_reconfigure_wrong_device(
    hass: HomeAssistant,
    mock_device: FakeDevice,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Changing to a host that yields a different unique_id is rejected."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.99", CONF_PORT: PORT}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"


async def test_user_flow_rejects_out_of_range_port(
    hass: HomeAssistant, mock_device: FakeDevice
) -> None:
    """Ports outside 1-65535 fail schema validation before any I/O."""
    from homeassistant.data_entry_flow import InvalidData

    result = await _start_user_flow(hass)
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 99999}
        )
