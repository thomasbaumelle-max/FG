"""Data structures for temporary status effects used in combat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class StatusEffect:
    """Represents a temporary status modifier applied to a combat unit.

    Parameters
    ----------
    name:
        Identifier of the effect (e.g. ``"burn"`` or ``"focus"``).
    duration:
        Number of turns the effect should remain active.
    modifiers:
        Mapping of stat name to the integer delta applied while the effect is
        active.  The modifiers are reapplied at the start of each turn.
    icon:
        Identifier of the icon used by the HUD to display the effect.
    """

    name: str
    duration: int
    modifiers: Dict[str, int] = field(default_factory=dict)
    icon: str = ""

