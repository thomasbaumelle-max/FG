from core.combat import Combat


def test_final_facing_from_path(simple_combat):
    combat: Combat = simple_combat()
    path = [(1, 0), (1, 1), (2, 1)]
    facing = combat._facing_from_last_step(path, (0, 0))
    assert facing == (1, 0)

