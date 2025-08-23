from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Ressources par défaut (tu peux en ajouter)
DEFAULT_RESOURCES = ("gold", "wood", "stone", "crystal")

@dataclass
class PlayerEconomy:
    resources: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in DEFAULT_RESOURCES})

@dataclass
class Building:
    id: str
    owner: Optional[int] = None        # index joueur (0..n-1) ou None
    provides: Dict[str, int] = field(default_factory=dict)  # {"wood": 2} par jour
    growth_per_week: Dict[str, int] = field(default_factory=dict)  # dwellings: {"unit_id": 8}
    stock: Dict[str, int] = field(default_factory=dict)     # stock interne (ex: unités disponibles)
    garrison: Dict[str, int] = field(default_factory=dict)  # garnison permanente
    level: int = 1
    upgrade_cost: Dict[str, int] = field(default_factory=dict)
    production_per_level: Dict[str, int] = field(default_factory=dict)

@dataclass
class GameCalendar:
    day: int = 1   # 1..7
    week: int = 1  # 1..∞

@dataclass
class GameEconomyState:
    calendar: GameCalendar
    players: Dict[int, PlayerEconomy]
    buildings: List[Building]

# --------- API ---------
def advance_day(state: GameEconomyState) -> None:
    """Tick quotidien: revenus passifs, régénérations légères, etc."""
    # Revenus de bâtiments
    for b in state.buildings:
        if b.owner is None: 
            continue
        if not b.provides:
            continue
        pe = state.players[b.owner]
        for res, amt in b.provides.items():
            pe.resources[res] = pe.resources.get(res, 0) + int(amt)

    # Avance calendrier
    state.calendar.day += 1
    if state.calendar.day > 7:
        state.calendar.day = 1
        state.calendar.week += 1
        advance_week(state)

def advance_week(state: GameEconomyState) -> None:
    """Tick hebdomadaire: croissance de troupes dans les dwellings/villes."""
    for b in state.buildings:
        if not b.growth_per_week:
            continue
        for unit_id, add in b.growth_per_week.items():
            b.stock[unit_id] = int(b.stock.get(unit_id, 0)) + int(add)
        for unit_id, amount in list(b.stock.items()):
            if amount > 0:
                b.garrison[unit_id] = b.garrison.get(unit_id, 0) + amount
                b.stock[unit_id] = 0

# --------- Helpers utilitaires ---------
def capture_building(
    state: GameEconomyState,
    building: Building,
    new_owner: Optional[int],
    level: Optional[int] = None,
) -> None:
    """Transfert de propriété (ex: le héros entre dans la mine)."""
    building.owner = new_owner
    if level is not None:
        building.level = level
        if building.production_per_level:
            building.provides = {
                res: amt * building.level for res, amt in building.production_per_level.items()
            }

def can_afford(player: PlayerEconomy, cost: Dict[str, int]) -> bool:
    return all(player.resources.get(k, 0) >= v for k, v in cost.items())

def pay(player: PlayerEconomy, cost: Dict[str, int]) -> None:
    for k, v in cost.items():
        player.resources[k] = player.resources.get(k, 0) - int(v)
