import audio
from tests.test_army_actions import setup_game
from state.event_bus import EVENT_BUS, ON_SEA_CHAIN_PROGRESS


def test_sea_chain_full_path(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    # make all tiles water
    for x in range(3):
        game.world.grid[0][x].biome = "ocean"
    # hero starts on first tile and is embarked
    game.hero.x = 0
    game.hero.y = 0
    game.hero.ap = 10
    game.hero.gold = 0
    game.hero.naval_unit = "barge"
    # load chain data
    game._load_sea_chain()
    progress = []
    EVENT_BUS.subscribe(ON_SEA_CHAIN_PROGRESS, lambda i, t: progress.append((i, t)))
    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)
    # move to first waypoint
    game.try_move_hero(1, 0)
    assert game.hero.gold == 10
    # move to second waypoint completing chain
    game.try_move_hero(1, 0)
    assert game.hero.gold == 30
    assert progress == [(1, 2), (2, 2)]
    assert game.sea_chain_index == len(game.sea_chain)
