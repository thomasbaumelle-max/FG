import types
import constants
from render.world_renderer import WorldRenderer
from core.world import WorldMap
from loaders.flora_loader import PropInstance

class DummyRect:
    left = 0
    top = 0
    right = constants.TILE_SIZE
    bottom = constants.TILE_SIZE

    def colliderect(self, other):
        return True

def test_collectible_rendering_does_not_error():
    world = WorldMap(width=1, height=1, num_obstacles=0, num_treasures=0, num_enemies=0)
    asset = types.SimpleNamespace(type="collectible", collectible={}, footprint=(1,1), anchor_px=(0,0), passable=True, occludes=False)
    loader = types.SimpleNamespace(
        assets={"scarlet_herb_a": asset},
        draw_props=lambda layers, props, grid_to_screen: None,
        get_surface=lambda asset_id, variant: (None, (0,0)),
    )
    world.flora_loader = loader
    prop = PropInstance("scarlet_herb_a", "scarletia", (0,0), 0, (1,1), (0,0), True, False, DummyRect())
    world.flora_props = [prop]
    world.collectibles = {(0,0): prop}
    world.invalidate_prop_chunk(prop)
    renderer = WorldRenderer({})
    renderer.world = world
    dest = types.SimpleNamespace(get_width=lambda: constants.TILE_SIZE, get_height=lambda: constants.TILE_SIZE, blit=lambda *a,**k: None)
    renderer._draw_layers(dest, [], [], None)
