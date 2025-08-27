import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from core.buildings import Town
from core.world import WorldMap
from core.entities import Hero
from state.game_state import GameState


def test_weekly_growth_via_next_day():
    pygame.init()
    world = WorldMap(map_data=["G"])
    town = Town(faction_id="red_knights")
    world.grid[0][0].building = town
    hero = Hero(0, 0, [])
    state = GameState(world=world, heroes=[hero])

    hero.resources["wood"] = 5
    hero.resources["stone"] = 5
    hero.gold = 100
    assert town.build_structure("barracks", hero)
    assert town.available_units("barracks").get("Swordsman") == 5

    for _ in range(7):
        state.next_day()

    assert town.available_units("barracks").get("Swordsman") == 10

