import os
import math
import pygame

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from core.entities import Unit, SWORDSMAN_STATS, DRAGON_STATS, MAGE_STATS
from core.combat import Combat
from core.combat_ai import ai_take_turn, allied_ai_turn, select_spell, _a_star
import constants

pygame.init()


def _create_combat(hero_units, enemy_units):
    hex_w = constants.COMBAT_HEX_SIZE
    hex_h = int(constants.COMBAT_HEX_SIZE * math.sqrt(3) / 2)
    screen = pygame.Surface(
        (
            int(hex_w + (constants.COMBAT_GRID_WIDTH - 1) * hex_w * 3 / 4),
            int(hex_h * constants.COMBAT_GRID_HEIGHT + hex_h / 2),
        )
    )
    assets = {}
    return Combat(screen, assets, hero_units, enemy_units)


def test_ai_attacks_nearest_enemy():
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.move_unit(hero_unit, 0, 0)
    combat.move_unit(enemy_unit, 3, 0)
    allied_ai_turn(combat, hero_unit)
    assert enemy_unit.current_hp < enemy_unit.stats.max_hp


def test_target_priority_by_threat():
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy1 = Unit(SWORDSMAN_STATS, 1, 'enemy')
    enemy2 = Unit(DRAGON_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy1, enemy2])
    hero_unit = combat.hero_units[0]
    e1 = combat.enemy_units[0]
    e2 = combat.enemy_units[1]
    combat.move_unit(hero_unit, 2, 2)
    combat.move_unit(e1, 2, 1)
    combat.move_unit(e2, 2, 3)
    allied_ai_turn(combat, hero_unit)
    assert e2.current_hp < e2.stats.max_hp
    assert e1.current_hp == e1.stats.max_hp


def test_ai_mage_casts_fireball_when_out_of_range():
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    mage = Unit(MAGE_STATS, 1, 'enemy')
    combat = _create_combat([hero], [mage])
    hero_unit = combat.hero_units[0]
    mage_unit = combat.enemy_units[0]
    combat.move_unit(hero_unit, 5, 0)
    combat.move_unit(mage_unit, 0, 0)
    ai_take_turn(combat, mage_unit, [hero_unit])
    assert hero_unit.current_hp < hero_unit.stats.max_hp


def test_select_spell_prefers_fireball_for_cluster():
    mage = Unit(MAGE_STATS, 1, 'hero')
    enemy1 = Unit(SWORDSMAN_STATS, 1, 'enemy')
    enemy2 = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([mage], [enemy1, enemy2])
    mage_unit = combat.hero_units[0]
    e1 = combat.enemy_units[0]
    e2 = combat.enemy_units[1]
    combat.move_unit(mage_unit, 0, 0)
    combat.move_unit(e1, 2, 0)
    combat.move_unit(e2, 2, 1)
    spell = select_spell(mage_unit, [e1, e2], combat)
    assert spell and spell[0] == 'fireball'
    ai_take_turn(combat, mage_unit, [e1, e2])
    assert e1.current_hp < e1.stats.max_hp
    assert e2.current_hp < e2.stats.max_hp


def test_hex_neighbors_within_bounds():
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    center_neighbors = combat.hex_neighbors(5, 5)
    assert len(center_neighbors) == 6
    edge_neighbors = combat.hex_neighbors(0, 0)
    assert len(edge_neighbors) < 6
    for nx, ny in edge_neighbors:
        assert 0 <= nx < constants.COMBAT_GRID_WIDTH
        assert 0 <= ny < constants.COMBAT_GRID_HEIGHT


def test_hex_distance_and_diagonal_attack():
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.move_unit(hero_unit, 2, 2)
    combat.move_unit(enemy_unit, 3, 1)
    assert combat.hex_distance((2, 2), (3, 1)) == 1
    allied_ai_turn(combat, hero_unit)
    assert enemy_unit.current_hp < enemy_unit.stats.max_hp


def test_ai_hex_pathfinding():
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    path = _a_star((0, 0), (3, 3), set())
    assert path[-1] == (3, 3)
    prev = (0, 0)
    for step in path:
        assert combat.hex_distance(prev, step) == 1
        prev = step
