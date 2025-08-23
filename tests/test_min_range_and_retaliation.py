import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from dataclasses import replace

import constants
from core.entities import Unit, ARCHER_STATS, SWORDSMAN_STATS
from core.combat import Combat


def _create_combat(hero_units, enemy_units):
    import pygame

    pygame.init()
    screen = pygame.Surface(
        (
            constants.COMBAT_GRID_WIDTH * constants.COMBAT_TILE_SIZE,
            constants.COMBAT_GRID_HEIGHT * constants.COMBAT_TILE_SIZE,
        )
    )
    assets = {}
    return Combat(screen, assets, hero_units, enemy_units)


def test_archer_min_range_excludes_adjacent():
    archer = Unit(ARCHER_STATS, 1, "hero")
    enemy = Unit(SWORDSMAN_STATS, 1, "enemy")
    combat = _create_combat([archer], [enemy])
    a = combat.hero_units[0]
    e = combat.enemy_units[0]
    combat.move_unit(a, 0, 0)
    combat.move_unit(e, 1, 0)
    squares = combat.attackable_squares(a, "ranged")
    assert (1, 0) not in squares
    combat.move_unit(e, 2, 0)
    squares = combat.attackable_squares(a, "ranged")
    assert (2, 0) in squares


def test_retaliation_limited_to_one():
    stats = replace(
        SWORDSMAN_STATS,
        attack_min=1,
        attack_max=1,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        luck=0,
        morale=0,
        min_range=1,
        retaliations_per_round=1,
    )
    attacker = Unit(stats, 1, "hero")
    defender = Unit(stats, 1, "enemy")
    combat = _create_combat([attacker], [defender])
    a = combat.hero_units[0]
    d = combat.enemy_units[0]
    combat.move_unit(a, 0, 0)
    combat.move_unit(d, 0, 1)
    combat.resolve_attack(a, d, "melee")
    hp_after_first = a.current_hp
    combat.resolve_attack(a, d, "melee")
    assert a.current_hp == hp_after_first

