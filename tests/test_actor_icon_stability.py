import pygame
import constants
from render.world_renderer import WorldRenderer
from core.world import WorldMap
from core.entities import Army, Unit, SWORDSMAN_STATS
class DummyCarrier:
    def __init__(self, x, y, colour):
        self.x = x
        self.y = y
        self.ap = 0
        self.units = []
        self.name = "A"
        surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
        surf.fill(colour)
        self.portrait = surf


def _ensure_surface_get_size() -> None:
    if not hasattr(pygame.Surface, "get_size"):
        pygame.Surface.get_size = lambda self: (self.get_width(), self.get_height())  # type: ignore


def test_actor_icons_remain_when_switching_selection():
    _ensure_surface_get_size()
    world = WorldMap(map_data=["..."])
    hero1 = DummyCarrier(0, 0, (255, 0, 0))
    hero2 = DummyCarrier(1, 0, (0, 255, 0))
    army = DummyCarrier(2, 0, (0, 0, 255))
    assets = {}
    renderer = WorldRenderer(assets)
    dest = pygame.Surface((world.width * constants.TILE_SIZE, constants.TILE_SIZE))

    def draw(selected):
        calls = {}
        orig_blit = pygame.Surface.blit

        def spy_blit(self, source, pos):
            calls[source] = pos
            return orig_blit(self, source, pos)

        pygame.Surface.blit = spy_blit  # type: ignore
        try:
            renderer.draw(dest, world, heroes=[hero1, hero2], armies=[army], selected=selected)
        finally:
            pygame.Surface.blit = orig_blit  # type: ignore
        return {hero1.portrait: calls[hero1.portrait],
                hero2.portrait: calls[hero2.portrait],
                army.portrait: calls[army.portrait]}

    pos1 = draw(hero1)
    pos2 = draw(hero2)
    assert pos1 == pos2


def test_hero_and_army_icons_remain_separate():
    _ensure_surface_get_size()
    world = WorldMap(map_data=[".."])
    hero = DummyCarrier(0, 0, (255, 0, 0))
    army = DummyCarrier(1, 0, (0, 255, 0))
    assets = {}
    renderer = WorldRenderer(assets)
    dest = pygame.Surface((world.width * constants.TILE_SIZE, constants.TILE_SIZE))

    def draw(selected):
        calls = {}
        orig_blit = pygame.Surface.blit

        def spy(self, source, pos):
            calls[source] = pos
            return orig_blit(self, source, pos)

        pygame.Surface.blit = spy  # type: ignore
        try:
            renderer.draw(dest, world, heroes=[hero], armies=[army], selected=selected)
        finally:
            pygame.Surface.blit = orig_blit  # type: ignore
        return {hero.portrait: calls[hero.portrait], army.portrait: calls[army.portrait]}

    hero_sel = draw(hero)
    army_sel = draw(army)
    assert hero_sel == army_sel
    assert hero_sel[hero.portrait] != hero_sel[army.portrait]


def test_army_uses_unit_image_not_portrait():
    _ensure_surface_get_size()
    world = WorldMap(map_data=[".."]) 
    unit_img = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    assets = {"swordsman": unit_img}
    renderer = WorldRenderer(assets)
    stats = SWORDSMAN_STATS
    army = Army(1, 0, [Unit(stats, 1, "hero")])
    # Give the army a portrait that should not be used
    portrait = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    portrait.fill((255, 0, 0))
    army.portrait = portrait
    dest = pygame.Surface((world.width * constants.TILE_SIZE, constants.TILE_SIZE))

    calls = {}
    orig_blit = pygame.Surface.blit

    def spy(self, source, pos):
        calls[source] = pos
        return orig_blit(self, source, pos)

    pygame.Surface.blit = spy  # type: ignore
    try:
        renderer.draw(dest, world, heroes=[], armies=[army])
    finally:
        pygame.Surface.blit = orig_blit  # type: ignore

    # Renderer should draw the unit image rather than the portrait
    assert unit_img in calls
    assert portrait not in calls
