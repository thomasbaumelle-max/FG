import os
import pygame

from ui.main_screen import MainScreen, EVENT_BUS as UI_BUS, ON_INFO_MESSAGE as UI_INFO


def test_save_game_missing_path(pygame_stub):
    pygame_stub()
    from core.game import Game
    screen = pygame.Surface((640, 480))
    game = Game(screen)
    game.default_save_path = None
    msg = game.save_game(None)
    assert msg and "No save path specified" in msg


def test_load_game_missing_file(pygame_stub, tmp_path):
    pygame_stub()
    from core.game import Game
    screen = pygame.Surface((640, 480))
    game = Game(screen)
    path = tmp_path / "missing.json"
    msg = game.load_game(str(path))
    assert msg and "not found" in msg


def test_main_screen_load_game_checks_file(pygame_stub, tmp_path):
    pygame_stub()
    from core.game import Game
    screen = pygame.Surface((640, 480))
    game = Game(screen)
    game.default_save_path = str(tmp_path / "missing.json")
    game.default_profile_path = str(tmp_path / "missing_profile.json")

    called = False

    def fake_load(path, profile):
        nonlocal called
        called = True

    game.load_game = fake_load
    messages = []
    UI_BUS.subscribe(UI_INFO, lambda msg: messages.append(msg))

    main = MainScreen(game)
    main.load_game()
    assert not called
    assert messages and "not found" in messages[0]


def test_toggle_pause(pygame_stub):
    pygame_stub()
    from core.game import Game
    screen = pygame.Surface((640, 480))
    game = Game(screen)
    assert not getattr(game, "paused", False)
    game.toggle_pause()
    assert game.paused
    game.toggle_pause()
    assert not game.paused


def test_end_day_advances_turn_and_resets_ap(pygame_stub):
    pygame_stub()
    from core.game import Game
    screen = pygame.Surface((640, 480))
    game = Game(screen)
    game.hero.ap = 0
    turn_before = game.turn
    game.end_day()
    assert game.hero.ap == game.hero.max_ap
    assert game.turn == turn_before + 1


def test_next_town_centers_camera(pygame_stub):
    pygame_stub()
    from core.game import Game
    screen = pygame.Surface((640, 480))
    game = Game(screen)
    tx, ty = game.world.hero_town
    called = []
    game.world_renderer.center_on = lambda pos: called.append(pos)
    game.next_town()
    assert called and called[0] == (tx, ty)


def test_nav_town_button_calls_game_next_town(monkeypatch, pygame_stub):
    import types

    pg = pygame_stub()
    from core.game import Game
    from ui.main_screen import MainScreen
    from ui.widgets.icon_button import MOUSEBUTTONDOWN, MOUSEBUTTONUP

    screen = pg.Surface((640, 480))
    game = Game(screen)
    called = []
    game.next_town = lambda: called.append(True)
    main = MainScreen(game)
    btn = next(b for b in main.menu_buttons if b.icon_id == "nav_town")
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    down = types.SimpleNamespace(type=MOUSEBUTTONDOWN, pos=(0, 0), button=1)
    up = types.SimpleNamespace(type=MOUSEBUTTONUP, pos=(0, 0), button=1)
    btn.handle(down)
    btn.handle(up)
    assert called == [True]


def test_next_town_no_town_notifies(pygame_stub):
    from core.game import Game
    from core.buildings import Town
    from state.event_bus import EVENT_BUS, ON_INFO_MESSAGE

    pg = pygame_stub()
    screen = pg.Surface((640, 480))
    game = Game(screen)
    for row in game.world.grid:
        for tile in row:
            if isinstance(tile.building, Town):
                tile.building.owner = 1
    messages = []
    EVENT_BUS.subscribe(ON_INFO_MESSAGE, lambda msg: messages.append(msg))
    game.next_town()
    assert messages and messages[-1] == "No town available"


def test_ctrl_click_next_town_opens_town(monkeypatch, pygame_stub):
    import types

    pg = pygame_stub(KMOD_CTRL=1)
    monkeypatch.setattr(
        pg, "key", types.SimpleNamespace(get_mods=lambda: pg.KMOD_CTRL), raising=False
    )

    from core.game import Game
    import importlib
    import ui.main_screen as ms

    importlib.reload(ms)

    screen = pg.Surface((640, 480))
    game = Game(screen)
    opened = {}

    def fake_open_town(town, army=None, town_pos=None):
        opened["town"] = town
        opened["pos"] = town_pos

    game.open_town = fake_open_town
    main = ms.MainScreen(game)
    main.next_town()
    tx, ty = game.world.hero_town
    expected = game.world.grid[ty][tx].building
    assert opened.get("town") is expected
    assert opened.get("pos") == (tx, ty)
