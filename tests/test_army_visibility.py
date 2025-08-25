from tests.test_army_actions import setup_game


def test_army_movement_updates_visibility(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    from core.world import WorldMap

    wm = WorldMap(
        width=12,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    for x in range(12):
        wm.grid[0][x].obstacle = False
    game.world = wm
    game.hero.x = 11
    game.hero.y = 0
    game.path = []
    game.move_queue = []
    game.path_target = None

    # Ensure initial vision is calculated for hero and army
    game._update_player_visibility(game.hero)
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=5)
    game.world.player_armies.append(army)
    game._update_player_visibility(army)

    # Tile at x=5 is outside the initial combined vision
    assert game.world.visible[0][0][5] is False

    # Move the army one tile to the right
    game._on_select_hero(army)
    game.try_move_hero(1, 0)

    # Tile at x=5 should now be visible, but x=6 remains hidden
    assert game.world.visible[0][0][5] is True
    assert game.world.visible[0][0][6] is False

