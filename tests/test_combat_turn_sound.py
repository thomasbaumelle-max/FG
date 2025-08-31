import audio
from core.entities import UnitStats, Unit


def _unit(side: str) -> Unit:
    stats = UnitStats(
        name="Test",
        max_hp=10,
        attack_min=0,
        attack_max=0,
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


def test_turn_sound_once_per_unit_turn(simple_combat, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(audio, "play_sound", lambda key: calls.append(key))
    combat = simple_combat(hero_units=[_unit("hero")], enemy_units=[_unit("enemy")])

    assert calls == ["turn_start"]

    for expected in range(2, 5):
        combat.advance_turn()
        assert calls == ["turn_start"] * expected
