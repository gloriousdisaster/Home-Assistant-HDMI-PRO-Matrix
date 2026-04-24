"""Shared fixtures for the Gofanco Prophecy tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gofanco_prophecy.const import DOMAIN

HOST = "192.0.2.10"
PORT = 80

DEVICE_STATE: dict[str, Any] = {
    "out1": 1,
    "out2": 2,
    "out3": 3,
    "out4": 4,
    "namein1": "Roku",
    "namein2": "AppleTV",
    "namein3": "PC",
    "namein4": "NintSw",
    "nameout1": "LivTV",
    "nameout2": "Kitchn",
    "nameout3": "Office",
    "nameout4": "Bdrm",
    "powstatus": "1",
}

PRESET_NAMES: dict[str, str] = {f"namem{i}": f"Preset{i}" for i in range(1, 9)}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom integrations in every test."""
    return


class FakeDevice:
    """Stand-in for the HDMI matrix TCP endpoint.

    Records every request sent on the wire and dispatches a JSON reply based
    on the command body. Supports the current client's `/inform.cgi?<cmd>`
    format and the full set of commands: state query, `LOADMAP`, routing
    mutations, preset save/call/rename.
    """

    def __init__(self) -> None:
        self.requests: list[str] = []
        self._state: dict[str, Any] = dict(DEVICE_STATE)
        self._presets: dict[str, str] = dict(PRESET_NAMES)
        self._raw_override: str | None = None
        self._failure: type[BaseException] | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    def set_state(self, state: dict[str, Any]) -> None:
        """Update the canned state payload."""
        self._state = dict(state)

    def set_raw_response(self, raw: str) -> None:
        """Force the next response to be this raw bytes (HTTP preamble etc)."""
        self._raw_override = raw

    def set_failure(self, exc_type: type[BaseException]) -> None:
        """Make the next open_connection call raise."""
        self._failure = exc_type

    def _dispatch(self, body: str) -> str:
        """Pick the right response body for a command."""
        if self._raw_override is not None:
            raw, self._raw_override = self._raw_override, None
            return raw

        if body == "LOADMAP":
            return json.dumps(self._presets)
        if body == "LOADNAME":
            keys = (
                "namein1",
                "namein2",
                "namein3",
                "namein4",
                "nameout1",
                "nameout2",
                "nameout3",
                "nameout4",
            )
            return json.dumps({k: self._state.get(k, "") for k in keys})
        # State query or any mutation: return current state.
        return json.dumps(self._state)

    async def open_connection(
        self, host: str, port: int, **_kwargs: Any
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Return a reader/writer pair with a canned response for the next request."""
        if self._failure is not None:
            exc = self._failure
            self._failure = None
            raise exc("injected failure")

        # We don't know the request body until the client writes it, so build
        # a writer that dispatches on write and a reader fed from a Future.
        loop = asyncio.get_running_loop()
        response_future: asyncio.Future[bytes] = loop.create_future()
        reader = asyncio.StreamReader()

        async def _feed_reader() -> None:
            data = await response_future
            reader.feed_data(data)
            reader.feed_eof()

        self._tasks.add(loop.create_task(_feed_reader()))

        writer = MagicMock()
        writer.drain = AsyncMock()
        writer.wait_closed = AsyncMock()

        def _write(data: bytes) -> None:
            text = data.decode("utf-8", errors="replace")
            _, _, body = text.partition("\r\n\r\n")
            self.requests.append(body)
            if not response_future.done():
                response_future.set_result(self._dispatch(body).encode("utf-8"))

        writer.write = _write
        return reader, writer


@pytest.fixture
def mock_device() -> Generator[FakeDevice, None, None]:
    """Patch asyncio.open_connection to talk to a FakeDevice."""
    device = FakeDevice()
    with patch(
        "custom_components.gofanco_prophecy.device.asyncio.open_connection",
        device.open_connection,
    ):
        yield device


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry configured for the fake device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"HDMI Matrix ({HOST})",
        version=2,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_device: FakeDevice,
) -> AsyncGenerator[MockConfigEntry, None]:
    """Set up the integration with a fake device."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
