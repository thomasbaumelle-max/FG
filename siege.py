"""Placeholder module for siege mechanics.

This module defines basic data structures and hook registration points for
future siege combat features.

>>> from siege import SiegeEngine, register_hook, hooks
>>> engine = SiegeEngine(name="Catapult", damage=50)
>>> register_hook(lambda e: None)
>>> hooks[0](engine)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Protocol


@dataclass
class SiegeEngine:
    """Basic representation of a siege engine.

    Attributes:
        name: Display name of the engine.
        damage: Base damage dealt when attacking fortifications.
        range: Maximum attack range on the tactical grid.
    """

    name: str
    damage: int
    range: int = 1


@dataclass
class Fortification:
    """Structure protecting an army during a siege."""

    name: str
    durability: int

    def take_damage(self, amount: int) -> None:
        self.durability = max(0, self.durability - amount)

    @property
    def destroyed(self) -> bool:
        return self.durability <= 0


@dataclass
class SiegeAction:
    """Represents an action targeting a fortification during a siege."""

    engine: SiegeEngine
    fortification: Fortification

    def resolve(self) -> None:
        """Apply the engine's damage to the fortification."""

        self.fortification.take_damage(self.engine.damage)


class SiegeHook(Protocol):
    """Protocol for functions invoked during siege related events."""

    def __call__(self, engine: SiegeEngine, **kwargs: Any) -> None:
        """Handle a siege event."""


hooks: List[SiegeHook] = []
"""Registered callbacks for siege events."""


def register_hook(func: SiegeHook) -> None:
    """Register a callback to receive siege events."""

    hooks.append(func)
