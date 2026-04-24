"""Async client for the Gofanco Prophecy HDMI Matrix.

The device is a small embedded HTTP/1.0 server that responds with bare JSON
bodies, sometimes preceded by a status line, sometimes not. aiohttp can't
parse that reliably, so we speak the wire directly over `asyncio.open_connection`.

The wire format mirrors the device's own web UI: every request is a POST to
``/inform.cgi?<cmd>`` where ``<cmd>`` is also the request body. Both the
querystring and body are consulted by the firmware; we keep them in sync.

The 13-key state response (`out1..4`, `namein1..4`, `nameout1..4`, `powstatus`)
is all we consistently see on this firmware. Preset names are fetched on demand
via the ``LOADMAP`` command (returning `namem1..namem8`). Standby/lock and EDID
state are not readable — intentionally not modelled here.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
import json
import logging

from .const import (
    DEFAULT_TIMEOUT,
    MUTE_INPUT,
    NAME_MAX_LEN,
    NUM_INPUTS,
    NUM_OUTPUTS,
    NUM_PRESETS,
)

_LOGGER = logging.getLogger(__name__)

_ENDPOINT = "/inform.cgi"
_STATE_CMD = '{"param1":"1"}'
_LOAD_PRESETS_CMD = "LOADMAP"


class ProphecyError(Exception):
    """Base error for Prophecy client failures."""


class ProphecyConnectionError(ProphecyError):
    """Raised when the device cannot be reached."""


class ProphecyResponseError(ProphecyError):
    """Raised when the device responds with unparsable data."""


@dataclass(slots=True)
class ProphecyState:
    """Parsed state of the HDMI matrix."""

    power: bool
    outputs: dict[int, int]
    input_names: dict[int, str]
    output_names: dict[int, str]
    preset_names: dict[int, str] = field(default_factory=dict)
    raw: dict[str, object] = field(default_factory=dict)

    def input_choices(self) -> dict[int, str]:
        """Return input number → display name, including mute."""
        return {MUTE_INPUT: "Mute", **self.input_names}


class GofancoProphecyClient:
    """Async client for the Gofanco Prophecy HDMI matrix."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the client."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the device host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the device port."""
        return self._port

    async def _post(self, body: str) -> str:
        """Send a POST and return the response body (preamble stripped)."""
        request = (
            f"POST {_ENDPOINT}?{body} HTTP/1.1\r\n"
            f"Host: {self._host}\r\n"
            f"Content-Type: application/json\r\n"
            f"Origin: http://{self._host}\r\n"
            f"Referer: http://{self._host}/\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        ).encode()

        async with self._lock:
            try:
                raw = await asyncio.wait_for(
                    self._exchange(request), timeout=self._timeout
                )
            except TimeoutError as err:
                raise ProphecyConnectionError(
                    f"Timeout communicating with {self._host}"
                ) from err
            except OSError as err:
                raise ProphecyConnectionError(
                    f"Error communicating with {self._host}: {err}"
                ) from err

        return _strip_http_preamble(raw)

    async def _exchange(self, request: bytes) -> str:
        """Write the request and read the full response, closing the socket.

        The device is HTTP/1.0 and always closes the connection at end-of-response,
        so connection reuse / keep-alive is not available — a new TCP socket per
        command is the supported behaviour.
        """
        reader, writer = await asyncio.open_connection(self._host, self._port)
        try:
            writer.write(request)
            await writer.drain()
            chunks: list[bytes] = []
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks).decode("utf-8", errors="replace")
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    async def async_get_state(self) -> ProphecyState:
        """Fetch current device state. Merges preset names from a recent cache."""
        raw = await self._post(_STATE_CMD)
        data = _parse_json_response(raw)
        if not _looks_like_state(data):
            raise ProphecyResponseError(
                "Device response is missing expected state keys"
            )
        return _parse_state(data)

    async def async_load_presets(self) -> dict[int, str]:
        """Fetch the 8 preset names (`namem1..namem8`)."""
        raw = await self._post(_LOAD_PRESETS_CMD)
        data = _parse_json_response(raw)
        return {
            i: _truncate(str(data.get(f"namem{i}", f"Preset {i}")))
            for i in range(1, NUM_PRESETS + 1)
        }

    async def async_set_output(self, output: int, source: int) -> None:
        """Route a single output to a specific input (0 = mute)."""
        await self._post(f"out{output}={source}")

    async def async_set_all_outputs(self, source: int) -> None:
        """Route all outputs to a single input."""
        await self._post(f"outa={source}")

    async def async_mute_all(self) -> None:
        """Mute all outputs."""
        await self.async_set_all_outputs(MUTE_INPUT)

    async def async_power(self, on: bool) -> None:
        """Turn the device power on or off."""
        await self._post("poweron" if on else "poweroff")

    async def async_set_names(
        self,
        input_names: dict[int, str],
        output_names: dict[int, str],
    ) -> None:
        """Write input and output name labels to the device."""
        parts: list[str] = []
        for i in range(1, NUM_INPUTS + 1):
            name = _truncate(input_names.get(i, f"Input {i}"))
            parts.append(f"namein{i}?{name}?")
        for i in range(1, NUM_OUTPUTS + 1):
            name = _truncate(output_names.get(i, f"Output {i}"))
            parts.append(f"nameout{i}?{name}?")
        await self._post("".join(parts))

    async def async_recall_preset(self, index: int) -> None:
        """Recall a saved preset (1-indexed)."""
        _validate_preset_index(index)
        await self._post(f"call={index}")

    async def async_save_preset(self, index: int) -> None:
        """Save the current routing into a preset slot (1-indexed)."""
        _validate_preset_index(index)
        await self._post(f"save={index}")

    async def async_set_preset_name(self, index: int, name: str) -> None:
        """Rename a preset slot."""
        _validate_preset_index(index)
        await self._post(f"mname{index}?{_truncate(name)}?")


def _validate_preset_index(index: int) -> None:
    """Raise if an index is outside the presets range."""
    if not 1 <= index <= NUM_PRESETS:
        raise ProphecyError(
            f"Preset index must be between 1 and {NUM_PRESETS}, got {index}"
        )


def _truncate(value: str) -> str:
    """Truncate a label to the device's max name length."""
    return value[:NAME_MAX_LEN]


def _strip_http_preamble(raw: str) -> str:
    r"""Return just the body, rejecting non-2xx responses.

    The device replies with either ``HTTP/1.0 <code> <msg>\r\n\r\n<body>`` or
    (rarely) a bare JSON body. When a status line is present we honour it;
    a non-2xx is surfaced as a ``ProphecyResponseError``.
    """
    if not raw:
        return raw
    if raw.startswith("HTTP/"):
        try:
            status_line, rest = raw.split("\r\n", 1)
        except ValueError:
            return raw
        parts = status_line.split(" ", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            code = int(parts[1])
            if not 200 <= code < 300:
                raise ProphecyResponseError(f"HTTP {code} from device")
        header_end = rest.find("\r\n\r\n")
        if header_end != -1:
            return rest[header_end + 4 :]
        return rest
    return raw


def _parse_json_response(raw: str) -> dict[str, object]:
    """Parse a JSON object response, with diagnostic logging on failure."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        _LOGGER.debug("Unparsable response: %r", raw)
        raise ProphecyResponseError(f"Invalid response from device: {err}") from err
    if not isinstance(data, dict):
        raise ProphecyResponseError("Device response was not a JSON object")
    return data


def _looks_like_state(data: dict[str, object]) -> bool:
    """Heuristic: the reply is a state dump if it has any of the known keys."""
    return any(k in data for k in ("out1", "powstatus", "poweron"))


def _parse_state(data: dict[str, object]) -> ProphecyState:
    """Parse a raw state response into a ProphecyState."""
    outputs: dict[int, int] = {}
    for i in range(1, NUM_OUTPUTS + 1):
        value = data.get(f"out{i}")
        if value is None:
            outputs[i] = MUTE_INPUT
            continue
        try:
            outputs[i] = int(str(value))
        except (TypeError, ValueError):
            outputs[i] = MUTE_INPUT

    input_names: dict[int, str] = {}
    for i in range(1, NUM_INPUTS + 1):
        raw_name = data.get(f"namein{i}")
        input_names[i] = _truncate(str(raw_name) if raw_name else f"Input {i}")

    output_names: dict[int, str] = {}
    for i in range(1, NUM_OUTPUTS + 1):
        raw_name = data.get(f"nameout{i}")
        output_names[i] = _truncate(str(raw_name) if raw_name else f"Output {i}")

    power = str(data.get("powstatus", "0")) == "1"

    return ProphecyState(
        power=power,
        outputs=outputs,
        input_names=input_names,
        output_names=output_names,
        raw=data,
    )


__all__ = [
    "GofancoProphecyClient",
    "ProphecyConnectionError",
    "ProphecyError",
    "ProphecyResponseError",
    "ProphecyState",
]
