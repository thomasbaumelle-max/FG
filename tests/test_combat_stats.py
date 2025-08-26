import random
import pytest

from core.entities import UnitStats, Unit, apply_defence


pytestmark = pytest.mark.combat


def _create_unit(**kwargs) -> Unit:
    data = dict(
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
    data.update(kwargs)
    stats = UnitStats(**data)
    return Unit(stats, 1, "hero")


@pytest.mark.parametrize("attack_type, field", [
    ("melee", "defence_melee"),
    ("ranged", "defence_ranged"),
    ("magic", "defence_magic"),
])
def test_apply_defence_uses_correct_stat(attack_type, field):
    unit = _create_unit(**{field: 2})
    assert apply_defence(10, unit, attack_type) == 8


def test_apply_defence_has_minimum_one():
    unit = _create_unit(defence_magic=10)
    assert apply_defence(5, unit, "magic") == 1


def test_damage_output_positive_luck(rng):
    unit = _create_unit(luck=1)
    assert unit.damage_output(rng) == 10


def test_damage_output_negative_luck(rng):
    unit = _create_unit(luck=-1)
    assert unit.damage_output(rng) == 2


def test_damage_output_positive_morale(rng):
    unit = _create_unit(morale=1)
    assert unit.damage_output(rng) == 10


def test_damage_output_negative_morale(rng):
    unit = _create_unit(morale=-1)
    assert unit.damage_output(rng) == 0
