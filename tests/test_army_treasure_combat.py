import types
import sys
import pygame

from tests.test_army_actions import setup_game
from ui.widgets.hero_list import HeroList


def test_army_without_hero_treasure_and_combat(monkeypatch):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch)

    # Replace Army.update_portrait to avoid file loading
    def fake_update_portrait(self):
        self.portrait = pygame.Surface((HeroList.CARD_SIZE, HeroList.CARD_SIZE))
    monkeypatch.setattr(Army, "update_portrait", fake_update_portrait)

    army = Army(0, 0, [Unit(S_STATS, 3, "hero")], ap=5)
    army.update_portrait()
    game.world.player_armies.append(army)

    # Place the main hero far away to avoid exchange triggers
    game.hero.x = 99
    game.hero.y = 99

    # hero list should include army with a non-null portrait
    game.main_screen.hero_list.set_heroes([game.hero, army])
    assert isinstance(game.main_screen.hero_list.heroes[-1].portrait, pygame.Surface)

    # Place treasure and collect it
    tile = game.world.grid[0][1]
    tile.treasure = {"gold": (10, 10)}
    monkeypatch.setattr(game, "prompt_treasure_choice", lambda t: "gold")
    start_gold = game.hero.gold
    game._on_select_hero(army)
    game.try_move_hero(1, 0)
    assert game.hero.gold == start_gold + 10
    assert tile.treasure is None
    assert (army.x, army.y) == (1, 0)

    # Place enemy units and resolve combat
    tile2 = game.world.grid[0][2]
    tile2.enemy_units = [Unit(S_STATS, 1, "enemy")]
    import core.auto_resolve as auto_resolve

    def fake_resolve(hero_units, enemy_units):
        return True, 0, [Unit(S_STATS, 2, "hero")], [Unit(S_STATS, 0, "enemy")]

    monkeypatch.setattr(auto_resolve, "resolve", fake_resolve)
    game.try_move_hero(1, 0)
    assert tile2.enemy_units is None
    assert army.units[0].count == 2
