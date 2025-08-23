import pygame
import constants
from render.world_renderer import WorldRenderer
from core.world import WorldMap
from core.entities import EnemyHero


def _ensure_surface_get_size() -> None:
    if not hasattr(pygame.Surface, "get_size"):
        pygame.Surface.get_size = lambda self: (self.get_width(), self.get_height())  # type: ignore


def test_enemy_hero_hidden_when_not_visible():
    _ensure_surface_get_size()
    world = WorldMap(map_data=["."])
    world.visible[0] = [[False]]
    world.explored[0] = [[True]]
    hero = EnemyHero(0, 0)
    renderer = WorldRenderer({})
    dest = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))

    calls = {}
    orig_blit = pygame.Surface.blit

    def spy(self, source, pos):
        calls[source] = pos
        return orig_blit(self, source, pos)

    pygame.Surface.blit = spy  # type: ignore
    try:
        renderer.draw(dest, world, heroes=[hero], armies=[])
    finally:
        pygame.Surface.blit = orig_blit  # type: ignore

    assert hero.portrait not in calls

    world.visible[0][0][0] = True
    calls.clear()
    pygame.Surface.blit = spy  # type: ignore
    try:
        renderer.draw(dest, world, heroes=[hero], armies=[])
    finally:
        pygame.Surface.blit = orig_blit  # type: ignore

    assert hero.portrait in calls
