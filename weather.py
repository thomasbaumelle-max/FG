"""Placeholder module for world weather systems.

Provides simple data structures and a hook registry for future weather
simulation.

>>> from weather import WeatherState, register_hook, hooks
>>> state = WeatherState()
>>> state.condition
'clear'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Protocol


@dataclass
class WeatherState:
    """Basic description of world weather."""

    condition: str = "clear"
    temperature: float = 20.0


class WeatherHook(Protocol):
    """Protocol for functions triggered on weather updates."""

    def __call__(self, state: WeatherState, **kwargs: Any) -> None:
        """Handle a weather event."""


hooks: List[WeatherHook] = []
"""Registered callbacks for weather events."""


def register_hook(func: WeatherHook) -> None:
    """Register a callback to receive weather events."""

    hooks.append(func)
