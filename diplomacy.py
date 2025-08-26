"""Placeholder module for diplomacy systems.

Defines basic data classes and hook registration points for future diplomacy
mechanics.

>>> from diplomacy import DiplomaticRelation, register_hook, hooks
>>> relation = DiplomaticRelation("Elves", "Orcs")
>>> relation.state is RelationState.NEUTRAL
True
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Protocol


class RelationState(str, Enum):
    """Possible relationship states between two factions."""

    ALLY = "ally"
    NEUTRAL = "neutral"
    ENEMY = "enemy"


class DiplomaticAction(str, Enum):
    """High level diplomatic actions two factions may take."""

    PACT = "pact"
    ULTIMATUM = "ultimatum"


@dataclass
class DiplomaticRelation:
    """Relationship state between two factions."""

    faction_a: str
    faction_b: str
    state: RelationState = RelationState.NEUTRAL


class DiplomacyHook(Protocol):
    """Protocol for functions triggered on diplomacy events."""

    def __call__(
        self, relation: DiplomaticRelation, action: DiplomaticAction | None = None, **kwargs: Any
    ) -> None:
        """Handle a diplomacy event."""


hooks: List[DiplomacyHook] = []
"""Registered callbacks for diplomacy events."""


def register_hook(func: DiplomacyHook) -> None:
    """Register a callback to receive diplomacy events."""

    hooks.append(func)


def trigger_action(relation: DiplomaticRelation, action: DiplomaticAction) -> None:
    """Trigger a diplomacy action and notify hooks."""

    for hook in hooks:
        hook(relation, action=action)
