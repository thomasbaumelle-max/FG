from __future__ import annotations

"""Utilities for handling elemental resistances.

This module defines a lightweight :class:`Resistances` container used by units
and heroes.  Resistances are stored as percentage values mapped by school name
(e.g. ``{"fire": 25}`` for 25%% fire resistance).  The data structure is
intentionally simple so UI code can easily query and display the values.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Resistances:
    """Container storing resistance percentages for each damage school."""

    values: Dict[str, int] = field(default_factory=dict)

    def get(self, school: str) -> int:
        """Return resistance for ``school`` (default 0)."""
        return self.values.get(school, 0)

    def set(self, school: str, value: int) -> None:
        """Assign a resistance ``value`` for ``school``."""
        self.values[school] = value

    def as_dict(self) -> Dict[str, int]:
        """Return a copy of the underlying dictionary."""
        return dict(self.values)
