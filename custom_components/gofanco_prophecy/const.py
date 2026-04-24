"""Constants for the Gofanco Prophecy HDMI Matrix integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "gofanco_prophecy"

MANUFACTURER: Final = "Gofanco Prophecy"
MODEL: Final = "PRO-Matrix44-SC"

DEFAULT_HOST_SUGGESTION: Final = "192.168.1.92"
DEFAULT_PORT: Final = 80
DEFAULT_TIMEOUT: Final = 10.0
SCAN_INTERVAL: Final = timedelta(seconds=15)
REFRESH_DEBOUNCE_COOLDOWN: Final = 0.5

NUM_INPUTS: Final = 4
NUM_OUTPUTS: Final = 4
NUM_PRESETS: Final = 8
NAME_MAX_LEN: Final = 7
MUTE_INPUT: Final = 0

PLATFORMS: Final = [
    "button",
    "media_player",
    "select",
    "switch",
    "text",
]
