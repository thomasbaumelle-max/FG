import pygame
from core.game import Game
from core.world import WorldMap
from core.entities import Hero, Unit
from tests.unit_stats import get_unit_stats

SWORDSMAN_STATS = get_unit_stats("swordsman")
from core.buildings import Town
from state.game_state import GameState
from core import economy
from ui.main_screen import MainScreen


def _make_simple_world():
    world = WorldMap(width=5, height=1)
    for tile in world.grid[0]:
        tile.biome = "scarletia_echo_plain"
        tile.obstacle = False
    player_town = Town(); player_town.owner = 0
    world.grid[0][0].building = player_town
    world.hero_town = (0, 0)
    world.hero_start = (1, 0)
    enemy_town = Town(); enemy_town.owner = 1
    world.grid[0][4].building = enemy_town
    world.enemy_town = (4, 0)
    world.enemy_start = (3, 0)
    return world


def test_victory_overlay_after_city_capture():
    world = _make_simple_world()
    game = Game.__new__(Game)
    game.world = world
    game.screen = pygame.Surface((1, 1))
    hero = Hero(1, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    hero.resources = {}
    game.hero = hero
    game.state = GameState(world=world, heroes=[hero])
    game.turn = 0
    game.move_queue = []
    game.path = []
    game.path_costs = []
    game.path_target = None
    game._notify = lambda *a, **k: None
    game._sync_economy_from_hero = lambda: None
    game._sync_hero_from_economy = lambda: None
    game._publish_resources = lambda: None
    game.refresh_army_list = lambda: None
    game._update_player_visibility = lambda *a, **k: None
    game._run_ai_turn = lambda: None
    game.active_actor = hero
    game._victory_shown = False
    game._game_over_shown = False
    # Economy setup for capture
    econ_state = game.state.economy
    econ_state.players[0] = economy.PlayerEconomy()
    econ_state.players[1] = economy.PlayerEconomy()
    enemy_b = economy.Building(id="enemy_town", owner=1)
    econ_state.buildings = [enemy_b]
    game._econ_building_map = {world.grid[0][4].building: enemy_b}
    # Minimal main screen stub using actual method
    main_screen = MainScreen.__new__(MainScreen)
    main_screen.end_message = None
    main_screen.hero_list = type("HL", (), {"set_heroes": lambda self, heroes: None})()
    main_screen.show_end_overlay = MainScreen.show_end_overlay.__get__(main_screen, MainScreen)
    game.main_screen = main_screen
    # Simulate turns and capture
    for x in range(2, 5):
        hero.x = x
        game.end_turn()
        if x == 4:
            tile = world.grid[0][4]
            tile.building.garrison = []
            game._capture_tile(4, 0, tile, hero, 0, econ_state, enemy_b)
            game.end_turn()
    assert game.main_screen.end_message == "Victory!"
