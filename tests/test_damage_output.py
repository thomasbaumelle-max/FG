import core.entities as entities


def _make_unit(luck, count=10):
    stats = entities.UnitStats(
        name="Test",
        max_hp=10,
        attack_min=1,
        attack_max=3,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=5,
        attack_range=1,
        initiative=10,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
        luck=luck,
    )
    return entities.Unit(stats, count, "hero")


def test_damage_output_critical():
    unit = _make_unit(luck=1)

    class DummyRng:
        def __init__(self):
            self._rolls = iter([2, 5])

        def randint(self, a, b):
            return next(self._rolls)

        def random(self):
            return 0.0

    rng = DummyRng()
    assert unit.damage_output(rng) == 5 * unit.count


def test_damage_output_unlucky():
    unit = _make_unit(luck=-1)

    class DummyRng:
        def randint(self, a, b):
            return 3

        def random(self):
            return 0.0

    rng = DummyRng()
    assert unit.damage_output(rng) == unit.stats.attack_min * unit.count
