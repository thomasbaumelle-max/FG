import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import random
from dataclasses import replace

from core.entities import (
    ARCHER_STATS,
    CAVALRY_STATS,
    DRAGON_STATS,
    MAGE_STATS,
    PRIEST_STATS,
    SWORDSMAN_STATS,
    Unit,
    apply_defence,
)


def test_mage_action_panel_has_spell_not_ranged(simple_combat):
    hero = Unit(MAGE_STATS, 1, 'hero')
    combat = simple_combat([hero], hero_mana=10)
    mage = combat.hero_units[0]
    actions = combat.get_available_actions(mage)
    assert 'spell' in actions and 'ranged' not in actions


def test_archer_action_panel_has_spell_and_ranged(simple_combat):
    hero = Unit(ARCHER_STATS, 1, 'hero')
    combat = simple_combat([hero], hero_mana=10)
    archer = combat.hero_units[0]
    actions = combat.get_available_actions(archer)
    assert 'spell' in actions and 'ranged' in actions


def test_heal_spell_increases_hp_and_consumes_mana(simple_combat):
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    caster = combat.hero_units[0]
    target = caster
    target.current_hp = 5
    spell = combat.get_spell('Heal')
    combat.cast_spell(spell, caster, target)
    assert target.current_hp == min(target.stats.max_hp, 5 + 20)
    assert combat.hero_mana == 9


def test_buff_spell_increases_attack_bonus(simple_combat):
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    caster = combat.hero_units[0]
    target = caster
    spell = combat.get_spell('Buff')
    initial = target.attack_bonus
    combat.cast_spell(spell, caster, target)
    assert target.attack_bonus == initial + 2
    assert combat.hero_mana == 9


def test_fireball_spell_damages_enemies(simple_combat):
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    caster = combat.hero_units[0]
    enemy = combat.enemy_units[0]
    combat.move_unit(enemy, 3, 3)
    spell = combat.get_spell('Fireball')
    combat.cast_spell(spell, caster, (3, 3))
    assert enemy.current_hp < enemy.stats.max_hp
    assert combat.hero_mana == 9


def test_teleport_spell_moves_unit(simple_combat):
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    caster = combat.hero_units[0]
    spell = combat.get_spell('Teleport')
    combat.cast_spell(spell, caster, (caster, (5, 5)))
    assert caster.x == 5 and caster.y == 5
    assert combat.hero_mana == 9


def test_fireball_uses_magic_defence(simple_combat):
    enemy_stats = replace(
        SWORDSMAN_STATS, defence_melee=0, defence_ranged=0, defence_magic=20
    )
    enemy = Unit(enemy_stats, 1, 'enemy')
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    caster = combat.hero_units[0]
    combat.move_unit(enemy, 3, 3)
    spell = combat.get_spell('Fireball')
    combat.cast_spell(spell, caster, (3, 3))
    expected = apply_defence(30, enemy, 'magic')
    assert enemy.current_hp == enemy.stats.max_hp - expected


def test_chain_lightning_hits_multiple_targets(simple_combat):
    enemies = [Unit(SWORDSMAN_STATS, 1, 'enemy') for _ in range(3)]
    hero = Unit(MAGE_STATS, 1, 'hero')
    combat = simple_combat([hero], enemies, hero_mana=10)
    caster = combat.hero_units[0]
    positions = [(3, 3), (4, 3), (5, 3)]
    for unit, (x, y) in zip(combat.enemy_units, positions):
        combat.move_unit(unit, x, y)
    spell = combat.get_spell('Chain Lightning')
    combat.cast_spell(spell, caster, (4, 3))
    assert all(u.current_hp < u.stats.max_hp for u in combat.enemy_units)


def test_ice_wall_blocks_and_expires(simple_combat):
    hero = Unit(MAGE_STATS, 1, 'hero')
    combat = simple_combat([hero], hero_mana=10)
    caster = combat.hero_units[0]
    spell = combat.get_spell('Ice Wall')
    combat.cast_spell(spell, caster, (2, 2))
    assert (2, 2) in combat.ice_walls
    combat.advance_turn()
    combat.advance_turn()
    assert (2, 2) not in combat.ice_walls


def test_focus_doubles_next_ranged_attack(simple_combat):
    enemy_stats = replace(SWORDSMAN_STATS, defence_melee=0, defence_ranged=0)
    archer_stats = replace(ARCHER_STATS, attack_min=5, attack_max=5)
    hero = Unit(archer_stats, 1, 'hero')
    enemy = Unit(enemy_stats, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    caster = combat.hero_units[0]
    enemy = combat.enemy_units[0]
    spell = combat.get_spell('Focus')
    combat.cast_spell(spell, caster, caster)
    assert caster.mana == 0
    assert combat.hero_mana == 10
    random.seed(1)
    combat.resolve_attack(caster, enemy, 'ranged')
    assert enemy.current_hp == enemy.stats.max_hp - 10

def test_focus_only_applies_once(simple_combat):
    enemy_stats = replace(SWORDSMAN_STATS, defence_melee=0, defence_ranged=0)
    archer_stats = replace(ARCHER_STATS, attack_min=5, attack_max=5)
    hero = Unit(archer_stats, 1, 'hero')
    enemy = Unit(enemy_stats, 1, "enemy")
    combat = simple_combat([hero], [enemy], hero_mana=10)
    caster = combat.hero_units[0]
    enemy = combat.enemy_units[0]
    spell = combat.get_spell("Focus")
    combat.cast_spell(spell, caster, caster)
    assert caster.mana == 0
    assert combat.hero_mana == 10
    random.seed(1)
    combat.resolve_attack(caster, enemy, "ranged")
    hp_after = enemy.current_hp
    random.seed(1)
    combat.resolve_attack(caster, enemy, "ranged")
    assert enemy.current_hp == hp_after - 5




def test_shield_block_negates_melee_attack(simple_combat):
    enemy_stats = replace(SWORDSMAN_STATS, attack_min=5, attack_max=5)
    hero_stats = replace(SWORDSMAN_STATS, defence_melee=0)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(enemy_stats, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    hero = combat.hero_units[0]
    enemy = combat.enemy_units[0]
    spell = combat.get_spell('Shield Block')
    combat.cast_spell(spell, hero, hero)
    assert hero.mana == 0
    assert combat.hero_mana == 10
    combat.resolve_attack(enemy, hero, 'melee')
    assert hero.current_hp == hero.stats.max_hp


def test_priest_heal_restores_100_hp(simple_combat):
    hero = Unit(PRIEST_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    priest = combat.hero_units[0]
    priest.current_hp = 10
    spell = combat.get_spell('Heal')
    combat.cast_spell(spell, priest, priest)
    assert priest.current_hp == min(priest.stats.max_hp, 110)
    assert priest.mana == priest.stats.mana - 1
    assert combat.hero_mana == 10


def test_charge_status_consumed_after_attack(simple_combat):
    hero = Unit(CAVALRY_STATS, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    cav = combat.hero_units[0]
    enemy = combat.enemy_units[0]
    spell = combat.get_spell('Charge')
    combat.cast_spell(spell, cav, cav)
    combat.move_unit(cav, cav.x + 1, cav.y)
    assert cav.mana == 0
    assert combat.hero_mana == 10
    assert combat.get_status(cav, 'charge') == 1
    combat.resolve_attack(cav, enemy, 'melee')
    assert combat.get_status(cav, 'charge') == 0


def test_dragon_breath_burns_enemies(simple_combat):
    enemy_stats = replace(SWORDSMAN_STATS, max_hp=100, defence_magic=0)
    hero = Unit(DRAGON_STATS, 1, 'hero')
    enemy = Unit(enemy_stats, 1, 'enemy')
    combat = simple_combat([hero], [enemy], hero_mana=10)
    dragon = combat.hero_units[0]
    enemy = combat.enemy_units[0]
    combat.move_unit(enemy, 4, 3)
    spell = combat.get_spell('Dragon Breath')
    combat.cast_spell(spell, dragon, (4, 3))
    assert dragon.mana == dragon.stats.mana - 2
    assert combat.hero_mana == 10
    initial = apply_defence(40, enemy, 'magic')
    combat.apply_passive_abilities(enemy)
    combat.apply_passive_abilities(enemy)
    assert enemy.current_hp == enemy.stats.max_hp - initial - 10


def test_start_spell_sets_state(simple_combat):
    hero = Unit(MAGE_STATS, 1, 'hero')
    combat = simple_combat([hero], hero_mana=10)
    mage = combat.hero_units[0]
    assert combat.start_spell(mage, 'Fireball')
    assert combat.casting_spell and combat.selected_spell.name == 'Fireball'


def test_start_spell_requires_mana(simple_combat):
    hero = Unit(MAGE_STATS, 1, 'hero')
    combat = simple_combat([hero], hero_mana=10)
    mage = combat.hero_units[0]
    mage.mana = 0
    assert not combat.start_spell(mage, 'Fireball')
    assert not combat.casting_spell
