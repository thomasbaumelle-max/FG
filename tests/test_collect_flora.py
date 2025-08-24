import sys
import types
import random

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.game import Game
from core.entities import Hero
from core.world import WorldMap
from loaders.flora_loader import PropInstance


def test_collect_flora_adds_item_and_removes_prop(monkeypatch):
    import audio

    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)

    random.seed(0)

    game = Game.__new__(Game)
    game.world = WorldMap(width=2, height=1, num_obstacles=0, num_treasures=0, num_enemies=0)
    hero = Hero(0, 0, [])
    hero.ap = 10
    hero.inventory = []
    game.hero = hero
    game.enemy_heroes = []
    game._update_player_visibility = lambda h: None
    game.state = types.SimpleNamespace()

    asset = types.SimpleNamespace(
        type="collectible",
        collectible={"item": "scarlet_leaf", "qty": [1, 3]},
        footprint=(1, 1),
        anchor_px=(0, 0),
        passable=True,
        occludes=False,
    )
    loader = types.SimpleNamespace(assets={"scarlet_herb_a": asset})
    game.world.flora_loader = loader

    prop = PropInstance(
        "scarlet_herb_a",
        "scarletia",
        (1, 0),
        0,
        (1, 1),
        (0, 0),
        True,
        False,
        types.SimpleNamespace(),
    )
    game.world.flora_props = [prop]
    game.world.collectibles = {(1, 0): prop}
    game.world.invalidate_prop_chunk(prop)

    game._try_move_hero(1, 0)

    assert len(game.hero.inventory) == 1
    item = game.hero.inventory[0]
    assert item.id == "scarlet_herb_a"
    assert 1 <= item.qty <= 3
    assert prop not in game.world.flora_props
    assert (1, 0) not in game.world.collectibles
