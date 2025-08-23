import random
import pytest

from core.entities import Hero, Unit, UnitStats


def create_unit(side: str = 'hero') -> Unit:
    stats = UnitStats(
        name="Test",
        max_hp=10,
        attack_min=5,
        attack_max=5,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=0,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
        morale=0,
        luck=0,
        abilities=[],
    )
    return Unit(stats, 1, side)


def test_gain_exp_and_level_up():
    hero = Hero(0, 0, [create_unit()])
    hero.gain_exp(120)
    assert hero.level == 2
    assert hero.exp == 20
    assert hero.skill_points == 1


def test_strength_and_wisdom_skills():
    hero = Hero(0, 0, [create_unit()])
    hero.gain_exp(300)  # level up twice -> 2 skill points
    hero.choose_skill('strength')
    unit = hero.army[0]
    # damage_output should include +1 bonus
    assert unit.attack_bonus == 1
    assert unit.damage_output(random.Random(0)) == 6
    hero.choose_skill('wisdom')
    assert hero.max_mana == 4
    assert hero.mana == 4


def test_tactics_skill_increases_initiative():
    hero = Hero(0, 0, [create_unit()])
    hero.gain_exp(200)
    hero.choose_skill('tactics')
    unit = hero.army[0]
    assert unit.initiative == 2


def test_logistics_skill_increases_ap():
    hero = Hero(0, 0, [create_unit()])
    hero.gain_exp(200)
    hero.choose_skill('logistics')
    assert hero.max_ap == 5
    assert hero.ap == 5
