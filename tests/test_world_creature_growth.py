import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from core.world import WorldMap
from core.entities import Unit, RECRUITABLE_UNITS
from core.ai.creature_ai import RoamingAI
from state.game_state import GameState


def test_neutral_creatures_grow_each_week():
    pygame.init()
    world = WorldMap(map_data=["G"])
    stats = RECRUITABLE_UNITS["Swordsman"]
    creature = RoamingAI(0, 0, [Unit(stats, 10, "enemy")])
    world.creatures.append(creature)
    world.grid[0][0].enemy_units = creature.units
    state = GameState(world=world)

    for _ in range(7):
        state.next_day()

    assert creature.units[0].count == 11
