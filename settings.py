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


def _get_int(env_var: str, key: str, default: int) -> int:
    """Return an integer setting from environment or JSON."""
    value = os.environ.get(env_var)
    if value is not None:
        try:
            return int(value)
        except ValueError:
            return default
    try:
        return int(_FILE_SETTINGS.get(key, default))
    except Exception:
        return default


def _get_float(env_var: str, key: str, default: float) -> float:
    """Return a float setting from environment or JSON."""
    value = os.environ.get(env_var)
    if value is not None:
        try:
            return float(value)
        except ValueError:
            return default
    try:
        return float(_FILE_SETTINGS.get(key, default))
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Public settings
# ---------------------------------------------------------------------------
# Draw helper markers for buildings in the world renderer
DEBUG_BUILDINGS: bool = _get_bool("FG_DEBUG_BUILDINGS", "debug_buildings", False)

# Language used for UI text
LANGUAGE: str = _get_str("FG_LANGUAGE", "language", "fr")

# Master audio volume (0.0 - 1.0)
VOLUME: float = _get_float("FG_VOLUME", "volume", 1.0)

# Map scroll speed in pixels per key press
SCROLL_SPEED: int = _get_int("FG_SCROLL_SPEED", "scroll_speed", 20)

# Animation speed multiplier for game visuals
ANIMATION_SPEED: float = _get_float(
    "FG_ANIMATION_SPEED", "animation_speed", 1.0
)

# Enable a reading-friendly mode for tooltips
TOOLTIP_READ_MODE: bool = _get_bool(
    "FG_TOOLTIP_READ_MODE", "tooltip_read_mode", False
)

# Enable super user mode for debugging and cheats
SUPER_USER_MODE: bool = _get_bool("FG_SUPER_USER", "super_user_mode", False)

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

def save_settings(**kwargs: Any) -> None:
    """Persist ``kwargs`` to :data:`SETTINGS_FILE`."""
    data: Dict[str, Any] = {}
    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data.update(kwargs)
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)


def remap_key(action: str, keys: List[str]) -> None:
    """Assign new ``keys`` to ``action`` and persist the mapping."""

    KEYMAP[action] = keys
    save_settings(keymap=KEYMAP)


__all__ = [
    "DEBUG_BUILDINGS",
    "LANGUAGE",
    "VOLUME",
    "SCROLL_SPEED",
    "ANIMATION_SPEED",
    "TOOLTIP_READ_MODE",
    "SUPER_USER_MODE",
    "KEYMAP",
    "save_settings",
    "remap_key",
]
