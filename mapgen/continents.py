"""Procedural continent and biome generation."""

from __future__ import annotations

import json
import random
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import constants

Cell = Tuple[int, int]


def _cellular_automata_land_mask(width: int, height: int,
                                 land_chance: float,
                                 iterations: int) -> List[List[bool]]:
    """Return a boolean grid where ``True`` indicates land."""
    grid = [[random.random() < land_chance for _ in range(width)]
            for _ in range(height)]
    for _ in range(iterations):
        new_grid = [[False for _ in range(width)] for _ in range(height)]
        for y in range(height):
            for x in range(width):
                land_neigh = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and grid[ny][nx]:
                            land_neigh += 1
                if grid[y][x]:
                    new_grid[y][x] = land_neigh >= 4
                else:
                    new_grid[y][x] = land_neigh >= 5
        grid = new_grid
    return grid


def _label_continents(grid: List[List[bool]]) -> Dict[int, List[Cell]]:
    """Return a mapping of continent id to list of land cells."""
    height = len(grid)
    width = len(grid[0]) if height else 0
    continents: Dict[int, List[Cell]] = {}
    continent_id = [[-1 for _ in range(width)] for _ in range(height)]
    current = 0
    for y in range(height):
        for x in range(width):
            if grid[y][x] and continent_id[y][x] == -1:
                queue: deque[Cell] = deque([(x, y)])
                continent_id[y][x] = current
                cells: List[Cell] = []
                while queue:
                    cx, cy = queue.popleft()
                    cells.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < width and 0 <= ny < height and
                                grid[ny][nx] and continent_id[ny][nx] == -1):
                            continent_id[ny][nx] = current
                            queue.append((nx, ny))
                continents[current] = cells
                current += 1
    return continents


def _remove_small_continents(grid: List[List[bool]], min_size: int) -> None:
    """Convert tiny landmasses below ``min_size`` cells back into water."""
    for cells in _label_continents(grid).values():
        if len(cells) < min_size:
            for x, y in cells:
                grid[y][x] = False


def _generate_rivers(grid: List[List[bool]], biome_map: Dict[Cell, str]) -> None:
    """Carve simple rivers by replacing paths from mountains to oceans."""
    height = len(grid)
    width = len(grid[0]) if height else 0

    # Precompute distance from every cell to the nearest water cell
    dist = [[-1 for _ in range(width)] for _ in range(height)]
    q: deque[Cell] = deque()
    for y in range(height):
        for x in range(width):
            if not grid[y][x]:  # water
                dist[y][x] = 0
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] and dist[ny][nx] == -1:
                dist[ny][nx] = dist[y][x] + 1
                q.append((nx, ny))

    mountains = [cell for cell, b in biome_map.items() if b == "M"]
    if not mountains:
        return

    mountains.sort(key=lambda c: dist[c[1]][c[0]], reverse=True)
    num_rivers = max(1, len(mountains) // 4)
    for sx, sy in mountains[:num_rivers]:
        x, y = sx, sy
        while grid[y][x]:
            grid[y][x] = False
            biome_map[(x, y)] = "R"
            if dist[y][x] <= 1:
                break
            neighbours = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and dist[ny][nx] != -1:
                    neighbours.append((dist[ny][nx], nx, ny))
            if not neighbours:
                break
            min_d = min(n[0] for n in neighbours)
            candidates = [(nx, ny) for d, nx, ny in neighbours if d == min_d]
            x, y = random.choice(candidates)


def load_biome_compatibility(path: Optional[str] = None) -> Dict[str, set[str]]:
    """Return biome adjacency rules from ``path`` or the default JSON file."""
    if path is None:
        repo_root = Path(__file__).resolve().parents[1]
        path = repo_root / "assets" / "biome_compatibility.json"
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw: Dict[str, List[str]] = json.load(fh)
        data = {k: set(v) for k, v in raw.items()}
    except Exception:  # pragma: no cover - fallback to empty rules
        data = {}
    return data


def _assign_biomes(grid: List[List[bool]],
                   continents: Dict[int, List[Cell]],
                   biome_chars: str,
                   compatibility: Dict[str, set[str]]) -> Dict[Cell, str]:
    """Assign biome letters to each land cell respecting adjacency rules."""
    biome_map: Dict[Cell, str] = {}
    width = len(grid[0]) if grid else 0
    for cells in continents.values():
        if not cells:
            continue
        num_biomes = max(1, min(len(biome_chars), len(cells) // 20))
        seeds = random.sample(cells, num_biomes)
        queue: deque[Tuple[int, int, str]] = deque()
        for seed, char in zip(seeds, biome_chars):
            biome_map[seed] = char
            queue.append((seed[0], seed[1], char))
        visited = set(seeds)
        while queue:
            x, y, char = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < len(grid)):
                    continue
                if not grid[ny][nx] or (nx, ny) in visited:
                    continue
                # Determine allowed biomes based on already assigned neighbours
                neighbour_biomes = []
                for ndx, ndy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nnx, nny = nx + ndx, ny + ndy
                    if (nnx, nny) in biome_map:
                        neighbour_biomes.append(biome_map[(nnx, nny)])
                allowed = set(biome_chars)
                for nb in neighbour_biomes:
                    allowed &= compatibility.get(nb, set(biome_chars))
                chosen = char if char in allowed else (random.choice(list(allowed)) if allowed else char)
                biome_map[(nx, ny)] = chosen
                visited.add((nx, ny))
                queue.append((nx, ny, chosen))
    return biome_map


def generate_continent_map(
    width: int,
    height: int,
    seed: Optional[int] = None,
    map_type: str = "plaine",
    land_chance: Optional[float] = None,
    smoothing_iterations: int = 4,
    biome_chars: str = "GFDMHSI",
    ocean_char: str = "W",
    coast_char: str = "C",
    min_continent_size: Optional[int] = None,
    biome_compatibility: Optional[Dict[str, set[str]]] = None,
    num_players: int = 2,
) -> List[str]:
    """Generate map data with continents and biome regions.

    The returned list contains strings where every tile is encoded by two
    characters: a biome letter followed by a feature symbol.  Water tiles use
    ``ocean_char`` while land tiles are filled with letters from
    ``biome_chars``.  The ``coast_char`` parameter is retained for backward
    compatibility but is no longer emitted; coastlines are rendered via
    overlays on the natural biomes.  The feature symbol is always ``'.'`` as
    higher level code will place obstacles and items afterwards.
    ``map_type`` controls the overall ratio of land to water and defaults to
    ``"plaine"`` for land‑heavy maps.  Passing ``"marine"`` yields mostly
    water with a few larger islands preserved for starting areas.  When
    generating marine maps ``num_players`` landmasses are retained to host the
    starting areas for each player; all other continents are flooded.
    """
    if seed is not None:
        random.seed(seed)

    if land_chance is None:
        if map_type == "marine":
            land_chance = 0.2
        elif map_type == "plaine":
            land_chance = 0.7
        else:
            land_chance = 0.45

    if not biome_chars:
        repo_root = Path(__file__).resolve().parents[1]
        try:
            with open(repo_root / "assets" / "biomes" / "char_map.json", "r", encoding="utf-8") as fh:
                char_map = json.load(fh)
        except Exception:
            char_map = {}
        id_to_char = {v: k for k, v in char_map.items()}
        biome_chars = "".join(
            id_to_char[b]
            for b in constants.DEFAULT_BIOME_WEIGHTS.keys()
            if b in id_to_char
        )

    grid = _cellular_automata_land_mask(width, height, land_chance, smoothing_iterations)

    if min_continent_size is None:
        if map_type == "marine":
            min_continent_size = max(4, (width * height) // 200)
        else:
            min_continent_size = max(4, (width * height) // 100)

    if map_type == "marine":
        continents = _label_continents(grid)
        for cells in continents.values():
            if len(cells) < min_continent_size:
                for x, y in cells:
                    grid[y][x] = False
        continents = _label_continents(grid)
        largest = sorted(continents.values(), key=len, reverse=True)
        for cells in largest[num_players:]:
            for x, y in cells:
                grid[y][x] = False
        continents = _label_continents(grid)
    else:
        _remove_small_continents(grid, min_continent_size)
        continents = _label_continents(grid)
    if biome_compatibility is None:
        biome_compatibility = load_biome_compatibility()
    biome_map = _assign_biomes(grid, continents, biome_chars, biome_compatibility)
    _generate_rivers(grid, biome_map)
    rows: List[str] = []
    for y in range(height):
        row_chars: List[str] = []
        for x in range(width):
            if not grid[y][x]:
                char = biome_map.get((x, y))
                if char == "R":
                    row_chars.extend(["R", "."])
                else:
                    row_chars.extend([ocean_char, "."])
            else:
                char = biome_map.get((x, y), biome_chars[0])
                row_chars.extend([char, "."])
        rows.append("".join(row_chars))
    return rows


def required_coast_images() -> Set[str]:
    """Return the full set of coastline overlay image filenames.

    Earlier versions of the project analysed a map to determine which
    coastline graphics were needed.  The game now always ships with a fixed
    collection of edge and corner overlays, so this helper simply exposes
    that static set.
    """

    edges = {f"mask_{d}.png" for d in ("n", "e", "s", "w")}
    corners = {f"mask_{c}.png" for c in ("ne", "nw", "se", "sw")}
    return edges | corners
