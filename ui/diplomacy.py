"""Minimal diplomacy user interface.

Provides a simple object for modifying diplomatic relations and
triggering diplomacy hooks from gameplay code or tests.
"""

from __future__ import annotations

from diplomacy import (
    DiplomaticAction,
    DiplomaticRelation,
    RelationState,
    hooks,
    trigger_action,
)


class DiplomacyInterface:
    """Simple helper to manage relations through code or hypothetical UI widgets."""

    def __init__(self, relation: DiplomaticRelation) -> None:
        self.relation = relation

    def set_state(self, state: RelationState) -> None:
        """Change relation state and notify listeners."""

        self.relation.state = state
        for hook in hooks:
            hook(self.relation)

    def perform_action(self, action: DiplomaticAction) -> None:
        """Trigger a diplomacy action."""

        trigger_action(self.relation, action)
