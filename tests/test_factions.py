import os

import pygame

from loaders.core import Context
from loaders.faction_loader import load_factions
from core.entities import Unit, SWORDSMAN_STATS


def _ctx():
    repo = os.path.join(os.path.dirname(__file__), "..")
    repo = os.path.abspath(repo)
    search = [os.path.join(repo, "assets")]
    return Context(repo_root=repo, search_paths=search, asset_loader=None)


def test_doctrine_bonus(simple_combat):
    factions = load_factions(_ctx())
    rk = factions["red_knights"]
    unit = Unit(SWORDSMAN_STATS, 5, "hero")
    combat = simple_combat([unit], [], screen=pygame.Surface((1, 1)), hero_faction=rk)
    assert combat.hero_units[0].stats.morale == 1


def test_army_synergy(simple_combat):
    factions = load_factions(_ctx())
    rk = factions["red_knights"]
    units = [Unit(SWORDSMAN_STATS, 5, "hero") for _ in range(3)]
    combat = simple_combat(units, [], screen=pygame.Surface((1, 1)), hero_faction=rk)
    assert all(u.stats.morale == 2 for u in combat.hero_units)

    undead = Unit(SWORDSMAN_STATS, 5, "hero")
    undead.tags.append("undead")
    combat = simple_combat(units + [undead], [], screen=pygame.Surface((1, 1)), hero_faction=rk)
    assert all(u.stats.morale == 1 for u in combat.hero_units)

