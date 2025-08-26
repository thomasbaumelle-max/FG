import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from core.buildings import Town
from core.entities import Hero
from core import economy


def test_one_structure_per_day():
    pygame.init()
    town = Town()
    hero = Hero(0, 0, [])
    hero.resources["wood"] = 10
    hero.resources["stone"] = 10
    hero.gold = 1000

    assert town.build_structure("barracks", hero)
    assert not town.build_structure("market", hero)

    town.advance_day()
    assert town.build_structure("market", hero)


def test_economy_build_lock():
    st = economy.GameEconomyState(
        calendar=economy.GameCalendar(),
        players={0: economy.PlayerEconomy()},
        buildings=[],
    )
    b = economy.Building("test")
    st.buildings.append(b)

    assert economy.build_structure(b, "barracks")
    assert not economy.build_structure(b, "market")
    economy.advance_day(st)
    assert economy.build_structure(b, "market")

