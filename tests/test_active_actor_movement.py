from tests.test_army_actions import setup_game


def setup_extended(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    from core.world import WorldMap
    wm = WorldMap(
        width=4,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    for x in range(4):
        wm.grid[0][x].obstacle = False
    game.world = wm
    game.hero.x = 3
    game.path = []
    game.move_queue = []
    game.path_target = None
    return game, constants, Army, Unit, S_STATS


def test_selection_moves_correct_actor(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_extended(monkeypatch, pygame_stub)
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=5)
    game.world.player_armies.append(army)

    def fake_compute_path(start, goal, avoid_enemies=True):
        sx, sy = start
        gx, gy = goal
        path = []
        x, y = sx, sy
        while (x, y) != (gx, gy):
            if x < gx:
                x += 1
            elif x > gx:
                x -= 1
            elif y < gy:
                y += 1
            else:
                y -= 1
            path.append((x, y))
        return path

    game.compute_path = fake_compute_path

    # Move hero first
    game.handle_world_click((2 * constants.TILE_SIZE, 0))
    game.handle_world_click((2 * constants.TILE_SIZE, 0))
    game.update_movement()
    assert (game.hero.x, game.hero.y) == (2, 0)
    assert (army.x, army.y) == (0, 0)

    # Select army and move
    game._on_select_hero(army)
    game.handle_world_click((1 * constants.TILE_SIZE, 0))
    game.handle_world_click((1 * constants.TILE_SIZE, 0))
    game.update_movement()
    assert (army.x, army.y) == (1, 0)
    assert (game.hero.x, game.hero.y) == (2, 0)


def test_path_clears_on_selection_and_end_turn(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_extended(monkeypatch, pygame_stub)
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=5)
    game.world.player_armies.append(army)

    def fake_compute_path(start, goal, avoid_enemies=True):
        sx, sy = start
        gx, gy = goal
        path = []
        x, y = sx, sy
        while (x, y) != (gx, gy):
            if x < gx:
                x += 1
            elif x > gx:
                x -= 1
            elif y < gy:
                y += 1
            else:
                y -= 1
            path.append((x, y))
        return path

    game.compute_path = fake_compute_path

    # Queue movement for the army
    game._on_select_hero(army)
    game.handle_world_click((2 * constants.TILE_SIZE, 0))
    game.handle_world_click((2 * constants.TILE_SIZE, 0))
    assert game.move_queue

    # Selecting the hero should clear the queued path
    game._on_select_hero(game.hero)
    assert game.move_queue == []
    assert game.path == []
    assert game.path_target is None

    # Queue movement again and end the turn; the path should be cleared
    game._on_select_hero(army)
    game.handle_world_click((2 * constants.TILE_SIZE, 0))
    game.handle_world_click((2 * constants.TILE_SIZE, 0))
    assert game.move_queue

    import audio
    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)
    game.end_turn()
    assert game.move_queue == []
    assert game.path == []
    assert game.path_target is None
