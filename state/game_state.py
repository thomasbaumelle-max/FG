"""Data structures representing the game state.

This module defines :class:`PlayerResources` used by the UI to display the
player's current stock of resources.  The structure is deliberately minimal so
it can be easily serialised or expanded in the future.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core import economy


@dataclass
class PlayerResources:
    """Container for a player's resources.

    The attributes mirror the different resource types found in the game.  All
    values default to ``0`` so new instances start empty.
    """

    gold: int = 0
    wood: int = 0
    stone: int = 0
    crystal: int = 0

    def as_dict(self) -> Dict[str, int]:
        """Return the resources as a regular dictionary.

        This is handy when iterating over resources generically, for example
        when updating UI elements.
        """

        return {
            "gold": self.gold,
            "wood": self.wood,
            "stone": self.stone,
            "crystal": self.crystal,
        }


@dataclass
class GameCalendar:
    """Utility class converting a turn index into calendar values.

    The game counts time in turns.  Each turn represents a day and months are
    divided into four weeks.  The calendar starts at month ``1``, week ``1`` and
    day ``1`` for ``turn_index`` ``0``.
    """

    turn_index: int = 0

    @property
    def day(self) -> int:
        """Current day within the week (1-7)."""

        return self.turn_index % 7 + 1

    @property
    def week(self) -> int:
        """Current week within the month (1-4)."""

        return (self.turn_index // 7) % 4 + 1

    @property
    def month(self) -> int:
        """Current month (starting at 1)."""

        return self.turn_index // 28 + 1

    def label(self) -> str:
        """Return a formatted ``"Month/Wk/Day"`` string."""

        return f"Month {self.month} Week {self.week} Day {self.day}"


@dataclass
class GameEconomyState:
    """Lightweight snapshot of the economy state.

    It mirrors :mod:`core.economy` structures so the UI can drive daily and
    weekly updates without depending on the full game implementation.
    """

    calendar: economy.GameCalendar = field(default_factory=economy.GameCalendar)
    players: Dict[int, economy.PlayerEconomy] = field(default_factory=dict)
    buildings: List[economy.Building] = field(default_factory=list)


@dataclass
class GameState:
    """High level container holding dynamic game information.

    This lightweight structure is used by the UI layer to obtain
    information about the current game without directly coupling to the
    :class:`game.Game` implementation.  Only a subset of data is tracked
    here which is sufficient for the sample widgets and tests.
    """

    world: Optional["WorldMap"] = None
    players: List[str] = field(default_factory=list)
    heroes: List["Hero"] = field(default_factory=list)
    resources: Dict[str, PlayerResources] = field(default_factory=dict)
    turn: GameCalendar = field(default_factory=GameCalendar)
    economy: GameEconomyState = field(default_factory=GameEconomyState)

    def _advance_towns_week(self) -> None:
        """Trigger weekly updates for all towns on the world map."""
        if not self.world:
            return
        for town in getattr(self.world, "towns", []):
            town.next_week()
            owner = getattr(town, "owner", None)
            if owner and owner in self.economy.players and owner != 0:
                econ_player = self.economy.players[owner]
                if hasattr(town, "recruit"):
                    town.recruit(econ_player)

    def next_day(self) -> None:
        """Advance the game by one day applying economic effects."""

        economy.advance_day(self.economy)
        if self.world is not None:
            if hasattr(self.world, "advance_day"):
                self.world.advance_day()
            else:
                for town in self.world.towns:
                    if hasattr(town, "advance_day"):
                        town.advance_day()
        self.turn.turn_index += 1
        if self.economy.calendar.day == 1:
            self._advance_towns_week()

    def next_week(self) -> None:
        """Apply weekly economic effects."""

        economy.advance_week(self.economy)
        self._advance_towns_week()


# Type checking imports -------------------------------------------------
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for static analysis
    from core.world import WorldMap
    from core.entities import Hero
