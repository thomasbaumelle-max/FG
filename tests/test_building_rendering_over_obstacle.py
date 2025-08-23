import constants
from render.world_renderer import WorldRenderer
from core.world import WorldMap
from core.buildings import Building
import pygame


def test_building_sprite_overrides_obstacle(monkeypatch):
    # Create world with single tile
    world = WorldMap(
        width=1,
        height=1,
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
        num_resources=0,
        num_buildings=0,
        biome_weights={"scarletia_echo_plain": 1.0},
    )

    # Create a non-passable building and stamp it onto the tile
    building = Building()
    building.image = "custom_building"
    building.passable = False
    world._stamp_building(0, 0, building)

    # Fake assets manager that records requested images
    class FakeAssets(dict):
        def __init__(self):
            super().__init__()
            self.calls = []

        def get(self, name):
            self.calls.append(name)
            return super().get(name)

    assets = FakeAssets()
    tile_size = constants.TILE_SIZE
    assets[constants.IMG_OBSTACLE] = pygame.Surface((tile_size, tile_size))
    assets["custom_building"] = pygame.Surface((tile_size, tile_size))

    renderer = WorldRenderer(assets)
    renderer.world = world

    dest = pygame.Surface((tile_size, tile_size))
    renderer._draw_layers(dest, [], [], None)

    assert "custom_building" in assets.calls
    assert constants.IMG_OBSTACLE not in assets.calls
