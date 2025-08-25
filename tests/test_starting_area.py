import random

import pytest
from mapgen.continents import generate_continent_map
from core.world import WorldMap


@pytest.fixture(scope="module")
def plaine_world() -> WorldMap:
    random.seed(0)
    rows = generate_continent_map(30, 30, seed=0)
    return WorldMap(map_data=rows)


@pytest.fixture(scope="module")
def marine_world() -> WorldMap:
    random.seed(0)
    rows = generate_continent_map(30, 30, seed=0, map_type="marine")
    return WorldMap(map_data=rows)


@pytest.mark.slow
def test_starting_area_has_buildings_and_town(plaine_world):
    world = plaine_world
    assert world.starting_area is not None
    x0, y0, size = world.starting_area
    assert 5 <= size <= 10
    biome = world.grid[y0][x0].biome
    for y in range(y0, y0 + size):
        for x in range(x0, x0 + size):
            assert world.grid[y][x].biome == biome
    def base(name: str) -> str:
        return "Town" if name.startswith("Town") else name

    buildings = {
        base(world.grid[y][x].building.name)
        for y in range(y0, y0 + size)
        for x in range(x0, x0 + size)
        if world.grid[y][x].building
    }
    assert {"Town", "Mine", "Crystal Mine", "Sawmill"} <= buildings
    assert world.hero_town in {
        (x, y)
        for y in range(y0, y0 + size)
        for x in range(x0, x0 + size)
        if world.grid[y][x].building and world.grid[y][x].building.name.startswith("Town")
    }
    assert world.hero_start is not None and world.hero_town is not None
    sx, sy = world.hero_start
    tx, ty = world.hero_town
    assert abs(sx - tx) + abs(sy - ty) == 1
    assert world.grid[sy][sx].building is None

@pytest.mark.slow
def test_building_images_loaded(plaine_world):
    import sys
    import types

    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h
            self.bottom = y + h

        def collidepoint(self, pos):
            return False

    class DummySurface:
        def convert_alpha(self):
            return self

        def get_width(self):
            return 10

        def get_height(self):
            return 10

        def get_rect(self):
            return Rect(0, 0, 10, 10)

        def blit(self, *args, **kwargs):
            pass

        def fill(self, *args, **kwargs):
            pass

    def load(path):
        return DummySurface()

    pygame_stub = types.SimpleNamespace(
        image=types.SimpleNamespace(load=load),
        transform=types.SimpleNamespace(scale=lambda surf, size: surf, smoothscale=lambda surf, size: surf),
        Surface=lambda size, flags=0: DummySurface(),
        SRCALPHA=1,
        Rect=Rect,
        draw=types.SimpleNamespace(ellipse=lambda surf, color, rect: None),
        time=types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda fps: None)),
        event=types.SimpleNamespace(get=lambda: []),
        display=types.SimpleNamespace(flip=lambda: None),
        init=lambda: None,
        quit=lambda: None,
    )

    real_pygame = sys.modules.get("pygame")
    sys.modules["pygame"] = pygame_stub
    sys.modules["pygame.draw"] = pygame_stub.draw

    try:
        from loaders.asset_manager import AssetManager
        from loaders.building_loader import BUILDINGS
        world = plaine_world
        assets = AssetManager(repo_root=".")
        for asset in BUILDINGS.values():
            files = asset.file_list()
            if files:
                assets.get(files[0])
        assert world.starting_area is not None
        x0, y0, size = world.starting_area
        images = {
            world.grid[y][x].building.image
            for y in range(y0, y0 + size)
            for x in range(x0, x0 + size)
            if world.grid[y][x].building
        }
        for img in images:
            assert assets.get(img) is not None
    finally:
        if real_pygame is not None:
            sys.modules["pygame"] = real_pygame
        else:
            del sys.modules["pygame"]
        sys.modules.pop("pygame.draw", None)


@pytest.mark.slow
def test_marine_islands_have_required_buildings(marine_world):
    world = marine_world
    assert world.starting_area is not None
    assert world.enemy_starting_area is not None
    continents = world._find_continents()
    assert len(continents) == 2
    for continent in continents:
        buildings = [
            world.grid[y][x].building
            for x, y in continent
            if world.grid[y][x].building is not None
        ]
        names = {b.name for b in buildings}
        assert any(name.startswith("Town") for name in names)
        assert any(
            n in {"Mine", "Crystal Mine", "Sawmill"} for n in names
        )
        assert "Shipyard" in names

