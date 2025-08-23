import constants
from core.world import WorldMap
from render.world_renderer import WorldRenderer
from render import autotile
import pygame


def test_adjacent_biomes_blend(monkeypatch):
    tile_size = constants.TILE_SIZE

    class FakeAssets(dict):
        def get(self, name):
            return dict.get(self, name)

    assets = FakeAssets()
    # Base biome tiles
    assets['plain'] = pygame.Surface((tile_size, tile_size))
    assets['forest'] = pygame.Surface((tile_size, tile_size))
    # Transition masks
    for name in ('n', 'e', 's', 'w', 'ne', 'nw', 'se', 'sw'):
        assets[f'mask_{name}'] = pygame.Surface((tile_size, tile_size))
    mask_e = assets['mask_e']

    calls = []

    def fake_apply(surface, base_img, overlay_img, mask):
        calls.append((base_img, overlay_img, mask))
        return surface

    monkeypatch.setattr(autotile, 'apply_overlay', fake_apply)
    monkeypatch.setattr(pygame.Surface, 'get_size', lambda self: (self.get_width(), self.get_height()), raising=False)

    world = WorldMap(
        width=2,
        height=1,
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
        num_resources=0,
        num_buildings=0,
        biome_weights={'scarletia_echo_plain': 1.0},
    )

    world.grid[0][0].biome = 'scarletia_echo_plain'
    world.grid[0][1].biome = 'scarletia_crimson_forest'
    world.biome_grid = [[tile.biome for tile in row] for row in world.grid]
    world.water_map = [[False, False]]

    world.init_renderer(
        assets,
        {'scarletia_echo_plain': ['plain'], 'scarletia_crimson_forest': ['forest']},
        {},
        {},
    )

    renderer = WorldRenderer(assets)
    renderer.world = world
    renderer._render_biome_chunk(0, 0)

    assert any(overlay is assets['forest'] and mask is mask_e for _, overlay, mask in calls)
