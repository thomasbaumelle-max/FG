from __future__ import annotations

"""Game configuration loaded from environment variables and ``settings.json``.

The module provides a central location for runtime options.  Environment
variables take precedence over values stored in the JSON file found next to
this module.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

# Path to the JSON configuration file bundled with the game
SETTINGS_FILE = Path(__file__).with_name("settings.json")

try:
    with SETTINGS_FILE.open("r", encoding="utf-8") as f:
        _FILE_SETTINGS: Dict[str, Any] = json.load(f)
except Exception:
    # If the settings file is missing or invalid, fall back to defaults
    _FILE_SETTINGS = {}


def _get_bool(env_var: str, key: str, default: bool = False) -> bool:
    """Return a boolean setting from ``env_var`` or ``key`` in the JSON file."""
    value = os.environ.get(env_var)
    if value is not None:
        return value.lower() not in ("0", "false", "")
    return bool(_FILE_SETTINGS.get(key, default))


def _get_str(env_var: str, key: str, default: str) -> str:
    """Return a string setting from ``env_var`` or ``key`` in the JSON file."""
    value = os.environ.get(env_var)
    if value is not None:
        return value
    return str(_FILE_SETTINGS.get(key, default))


# ---------------------------------------------------------------------------
# Public settings
# ---------------------------------------------------------------------------
# Draw helper markers for buildings in the world renderer
DEBUG_BUILDINGS: bool = _get_bool("FG_DEBUG_BUILDINGS", "debug_buildings", False)

# Language used for UI text
LANGUAGE: str = _get_str("FG_LANGUAGE", "language", "en")

_DEFAULT_KEYMAP: Dict[str, List[str]] = {
    "pan_left": ["K_LEFT", "K_a"],
    "pan_right": ["K_RIGHT", "K_d"],
    "pan_up": ["K_UP", "K_w"],
    "pan_down": ["K_DOWN", "K_s"],
    "zoom_in": ["K_EQUALS", "K_PLUS"],
    "zoom_out": ["K_MINUS", "K_UNDERSCORE"],
}

_FILE_KEYMAP = _FILE_SETTINGS.get("keymap", {}) if isinstance(_FILE_SETTINGS, dict) else {}
KEYMAP: Dict[str, List[str]] = {**_DEFAULT_KEYMAP, **_FILE_KEYMAP}

__all__ = ["DEBUG_BUILDINGS", "LANGUAGE", "KEYMAP"]
