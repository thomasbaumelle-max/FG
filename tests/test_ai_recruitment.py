import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame

from core.buildings import Town
from core.entities import Hero
from core.world import WorldMap
from state.game_state import GameState
from core import economy


def test_ai_weekly_recruitment_consumes_resources():
    pygame.init()
    world = WorldMap(map_data=["G"])
    town = Town(faction_id="red_knights")
    town.owner = 1
    world.grid[0][0].building = town

    hero = Hero(0, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 100
    assert town.build_structure('barracks', hero)

    state = GameState(world=world)
    state.economy.players[1] = economy.PlayerEconomy()
    state.economy.players[1].resources['gold'] = 1000

    state.next_week()

    assert any(u.stats.name == 'Swordsman' and u.count == 10 for u in town.garrison)
    assert state.economy.players[1].resources['gold'] == 500
