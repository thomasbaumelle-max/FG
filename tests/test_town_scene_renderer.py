from loaders.town_scene_loader import TownScene, TownLayer, TownBuilding
from render.town_scene_renderer import TownSceneRenderer

from loaders.town_scene_loader import TownScene, TownLayer, TownBuilding
from render.town_scene_renderer import TownSceneRenderer


class DummyAssets:
    def __init__(self, mapping):
        self.mapping = mapping

    def get(self, key):
        return self.mapping[key]


class DummySurface:
    def __init__(self):
        self.calls = []

    def blit(self, img, pos):
        self.calls.append((img, pos))


def test_draws_layers_and_buildings_in_order():
    bg1 = object()
    bg2 = object()
    built = object()
    unbuilt = object()
    assets = DummyAssets({
        "l1.png": bg1,
        "l2.png": bg2,
        "b_built.png": built,
        "b_unbuilt.png": unbuilt,
    })

    scene = TownScene(
        size=(10, 10),
        layers=[TownLayer("l1", "l1.png"), TownLayer("l2", "l2.png")],
        buildings=[
            TownBuilding(
                id="b",
                layer="l2",
                pos=(1, 2),
                states={"built": "b_built.png", "unbuilt": "b_unbuilt.png"},
            )
        ],
    )
    renderer = TownSceneRenderer(scene, assets)
    surface = DummySurface()

    renderer.draw(surface, {"b": "built"})
    assert surface.calls == [(bg1, (0, 0)), (bg2, (0, 0)), (built, (1, 2))]

    surface2 = DummySurface()
    renderer.draw(surface2, {"b": "unbuilt"})
    assert surface2.calls[-1] == (unbuilt, (1, 2))
