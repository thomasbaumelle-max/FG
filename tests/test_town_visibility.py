from tests.test_army_actions import setup_game


def test_town_reveals_tiles(monkeypatch):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch)
    from core.world import WorldMap
    from core.buildings import Town

    wm = WorldMap(
        width=10,
        height=10,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    for row in wm.grid:
        for tile in row:
            tile.obstacle = False
    game.world = wm
    game.hero.x = 0
    game.hero.y = 0

    game._update_player_visibility(game.hero)
    assert game.world.visible[0][5][5] is False

    town = Town()
    wm._stamp_building(5, 5, town)
    town.owner = 0

    game._update_player_visibility()
    assert game.world.visible[0][5][5] is True
    assert game.world.visible[0][5][7] is True
    assert game.world.visible[0][5][8] is False
    assert game.world.explored[0][5][7] is True
