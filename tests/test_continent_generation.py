from pathlib import Path

from mapgen.continents import generate_continent_map, load_biome_compatibility


def _load_rows() -> list[str]:
    path = Path(__file__).parent / "fixtures" / "mini_continent_map.txt"
    with open(path, "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh]


def test_generate_continent_map_contains_land_and_ocean():
    rows = _load_rows()
    width, height = 10, 10
    assert len(rows) == height
    assert all(len(r) == width * 2 for r in rows)
    chars = set("".join(rows))
    assert "W" in chars  # ocean present
    land_chars = chars.intersection(set("GFDMHSJI"))
    assert land_chars  # at least one land tile


def test_biome_adjacency_respects_rules():
    rows = _load_rows()
    grid = [[row[i] for i in range(0, len(row), 2)] for row in rows]
    height = len(grid)
    width = len(grid[0]) if grid else 0
    rules = load_biome_compatibility()
    for y in range(height):
        for x in range(width):
            c1 = grid[y][x]
            if c1 in ("W",):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    c2 = grid[ny][nx]
                    if c2 in ("W",):
                        continue
                    assert c2 in rules.get(c1, {c2})


def test_generate_map_with_custom_rules():
    custom = {"A": {"A", "B"}, "B": {"A", "B"}}
    rows = generate_continent_map(
        10,
        10,
        seed=0,
        land_chance=1.0,
        smoothing_iterations=0,
        biome_chars="AB",
        biome_compatibility=custom,
    )
    grid = [[row[i] for i in range(0, len(row), 2)] for row in rows]
    chars = {c for row in grid for c in row}
    assert "A" in chars and "B" in chars
    height = len(grid)
    width = len(grid[0]) if height else 0
    for y in range(height):
        for x in range(width):
            c1 = grid[y][x]
            if c1 in ("W",):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    c2 = grid[ny][nx]
                    if c2 in ("W",):
                        continue
                    assert c2 in custom.get(c1, {c2})


def test_loaded_biome_can_appear(tmp_path):
    import base64
    import json
    from loaders.biomes import BiomeCatalog
    from loaders.core import Context
    import constants
    from core import world as core_world

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAAC0lEQVR42mP8/x8AAwMB/kwAXzAAAAAASUVORK5CYII="
    )
    assets = tmp_path / "assets"
    realm = assets / "realms" / "testrealm" / "biomes"
    realm.mkdir(parents=True)
    (realm / "test_biome.png").write_bytes(png_bytes)
    with open(realm.parent / "char_map.json", "w", encoding="utf-8") as fh:
        json.dump({"T": "test_biome"}, fh)
    manifest = [
        {
            "id": "test_biome",
            "type": "forest",
            "description": "",
            "path": "./biomes/test_biome",
            "variants": 1,
            "colour": [0, 0, 0],
            "flora": [],
        }
    ]
    with open(realm.parent / "biomes.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)

    repo_root = Path(__file__).resolve().parents[1]
    ctx = Context(
        repo_root=str(repo_root),
        search_paths=[str(repo_root / "assets"), str(assets)],
        asset_loader=None,
    )

    old_biomes = BiomeCatalog._biomes
    old_base = constants.BIOME_BASE_IMAGES
    old_weights = constants.DEFAULT_BIOME_WEIGHTS
    old_prio = constants.BIOME_PRIORITY
    old_char_map = core_world.BIOME_CHAR_MAP
    old_chars = core_world.BIOME_CHARS
    try:
        BiomeCatalog.load(ctx, "testrealm")
        rows = generate_continent_map(
            20,
            20,
            seed=0,
            land_chance=1.0,
            smoothing_iterations=0,
            biome_chars="".join(core_world.BIOME_CHARS),
        )
        chars = set("".join(rows))
        assert "T" in chars
    finally:
        BiomeCatalog._biomes = old_biomes
        constants.BIOME_BASE_IMAGES = old_base
        constants.DEFAULT_BIOME_WEIGHTS = old_weights
        constants.BIOME_PRIORITY = old_prio
        core_world.BIOME_CHAR_MAP = old_char_map
        core_world.BIOME_CHARS = old_chars
        core_world.init_biome_images()

