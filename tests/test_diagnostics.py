"""Diagnostics tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gofanco_prophecy.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redact_host(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Host is redacted from diagnostics output."""
    data = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert data["entry"]["data"]["host"] == "**REDACTED**"
    assert data["state"]["power"] is True
    assert data["state"]["outputs"] == {1: 1, 2: 2, 3: 3, 4: 4}
