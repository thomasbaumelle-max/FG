import pygame
from ui.widgets.hero_list import HeroList
from ui.widgets.hero_army_panel import HeroArmyPanel
from render.world_renderer import WorldRenderer
from core.world import WorldMap
import constants


class DummyHero:
    def __init__(self, portrait):
        self.name = "H"
        self.x = 0
        self.y = 0
        self.ap = 0
        self.army = []
        # ``WorldRenderer`` expects a ``units`` attribute for actors on the map
        # mirroring the hero's army.
        self.units = self.army
        self.portrait = portrait


class DummyAssets(dict):
    def get(self, key, default=None):
        if key in self:
            return self[key]
        return pygame.Surface((1, 1), pygame.SRCALPHA)


class DummyStats:
    def __init__(self, name):
        self.name = name
        self.attack_min = 1
        self.attack_max = 1


class DummyUnit:
    def __init__(self, name):
        self.stats = DummyStats(name)
        self.count = 1


def test_widgets_render_given_portrait():
    colour = (1, 2, 3)
    portrait = pygame.Surface((HeroList.CARD_SIZE, HeroList.CARD_SIZE))
    portrait.fill(colour)
    hero = DummyHero(portrait)

    hl = HeroList()
    hl.set_heroes([hero])
    assert hl._heroes[0].portrait is portrait

    panel = HeroArmyPanel(hero)
    assert panel.portrait is portrait


def test_world_renderer_uses_icon_and_anchor():
    world = WorldMap(map_data=["."])
    icon = pygame.Surface((2, 1))
    assets = DummyAssets(
        default_hero={"icon": {"surface": icon, "anchor": (1, 0)}},
        enemy_army=None,
    )
    renderer = WorldRenderer(assets)
    dest = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    hero = DummyHero(None)
    calls = []
    orig_blit = pygame.Surface.blit

    def spy_blit(self, source, pos):
        calls.append((self, source, pos))
        orig_blit(self, source, pos)

    pygame.Surface.blit = spy_blit  # type: ignore
    try:
        renderer.draw(dest, world, heroes=[hero], armies=[], selected=None)
    finally:
        pygame.Surface.blit = orig_blit  # type: ignore
    assert any(src is icon and pos == (-1, 0) for _self, src, pos in calls)


def test_world_renderer_keeps_hero_portrait_over_units():
    world = WorldMap(map_data=["."])
    portrait = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    unit_img = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    assets = DummyAssets(swordsman=unit_img, enemy_army=None)
    renderer = WorldRenderer(assets)
    dest = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    hero = DummyHero(portrait)
    hero.army = [DummyUnit("swordsman")]
    hero.units = hero.army
    calls = []
    orig_blit = pygame.Surface.blit

    def spy_blit(self, source, pos):
        calls.append((self, source, pos))
        return orig_blit(self, source, pos)

    pygame.Surface.blit = spy_blit  # type: ignore
    try:
        renderer.draw(dest, world, heroes=[hero], armies=[], selected=None)
    finally:
        pygame.Surface.blit = orig_blit  # type: ignore
    assert any(src is portrait for _self, src, _pos in calls)
    assert all(src is not unit_img for _self, src, _pos in calls)


def test_world_renderer_uses_generic_enemy_when_no_images():
    world = WorldMap(map_data=["."])
    generic = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    assets = {"enemy_army": generic}
    renderer = WorldRenderer(assets)
    dest = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))

    class DummyArmy:
        def __init__(self):
            self.x = 0
            self.y = 0
            self.portrait = None
            self.units = [DummyUnit("unknown")]

    army = DummyArmy()
    calls = []
    orig_blit = pygame.Surface.blit

    def spy_blit(self, source, pos):
        calls.append((self, source, pos))
        return orig_blit(self, source, pos)

    pygame.Surface.blit = spy_blit  # type: ignore
    try:
        renderer.draw(dest, world, heroes=[], armies=[army], selected=None)
    finally:
        pygame.Surface.blit = orig_blit  # type: ignore
    assert any(src is generic for _self, src, _pos in calls)
