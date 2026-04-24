"""Unit tests for the async client itself."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.gofanco_prophecy.const import NAME_MAX_LEN
from custom_components.gofanco_prophecy.device import (
    GofancoProphecyClient,
    ProphecyConnectionError,
    ProphecyError,
    ProphecyResponseError,
    _looks_like_state,
    _strip_http_preamble,
    _truncate,
)


def test_strip_http_preamble_bare_body() -> None:
    """Bare JSON bodies pass through unchanged."""
    assert _strip_http_preamble('{"out1":"1"}') == '{"out1":"1"}'


def test_strip_http_preamble_http10_ok() -> None:
    """Status line + headers are stripped on 200."""
    raw = 'HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n{"out1":"1"}'
    assert _strip_http_preamble(raw) == '{"out1":"1"}'


def test_strip_http_preamble_http10_non_2xx_raises() -> None:
    """Non-2xx status codes surface as ProphecyResponseError."""
    raw = "HTTP/1.0 500 Internal\r\n\r\noops"
    with pytest.raises(ProphecyResponseError):
        _strip_http_preamble(raw)


def test_strip_http_preamble_empty() -> None:
    """Empty response is returned as-is (caller decides)."""
    assert _strip_http_preamble("") == ""


def test_looks_like_state_positive() -> None:
    """Real state responses pass the heuristic."""
    assert _looks_like_state({"out1": "1", "powstatus": "1"})


def test_looks_like_state_negative() -> None:
    """Preset-name responses are *not* state responses."""
    assert not _looks_like_state({"namem1": "Preset1"})


def test_name_truncation_at_max_len() -> None:
    """The client silently truncates labels to the device's 7-char limit."""
    assert len(_truncate("TelevisionLabel")) == NAME_MAX_LEN
    assert _truncate("TelevisionLabel") == "Televis"
    # Exact-length strings pass through unchanged.
    assert _truncate("1234567") == "1234567"
    # Shorter strings are preserved.
    assert _truncate("TV") == "TV"
    assert _truncate("") == ""


async def test_invalid_preset_index_rejected() -> None:
    """Out-of-range preset index raises ProphecyError before hitting the wire."""
    client = GofancoProphecyClient("127.0.0.1", 80)
    with pytest.raises(ProphecyError):
        await client.async_recall_preset(9)
    with pytest.raises(ProphecyError):
        await client.async_save_preset(0)


async def test_connection_refused_raises_connection_error() -> None:
    """Low-level OSErrors become ProphecyConnectionError."""

    async def fake_open(*_args, **_kwargs):
        raise OSError("nope")

    with patch(
        "custom_components.gofanco_prophecy.device.asyncio.open_connection",
        fake_open,
    ):
        client = GofancoProphecyClient("127.0.0.1", 80)
        with pytest.raises(ProphecyConnectionError):
            await client.async_get_state()


async def test_concurrent_commands_serialize() -> None:
    """Overlapping commands are serialized by the internal asyncio.Lock."""
    order: list[str] = []

    async def fake_open(*_args, **_kwargs):
        order.append("enter")
        # Yield so a sibling task gets a chance to also try entering.
        await asyncio.sleep(0)
        order.append("exit")
        reader = asyncio.StreamReader()
        reader.feed_data(b'{"out1":"1","powstatus":"1"}')
        reader.feed_eof()
        writer = MagicMock()
        writer.drain = AsyncMock()
        writer.wait_closed = AsyncMock()
        writer.write = lambda _data: None
        return reader, writer

    with patch(
        "custom_components.gofanco_prophecy.device.asyncio.open_connection",
        fake_open,
    ):
        client = GofancoProphecyClient("127.0.0.1", 80)
        await asyncio.gather(
            client.async_set_output(1, 2),
            client.async_set_output(2, 3),
            client.async_set_output(3, 1),
        )

    # Each "enter" is followed by its own "exit" before the next "enter".
    # If the lock were missing we'd see interleaved enter/enter/exit/exit.
    assert order == ["enter", "exit"] * 3
