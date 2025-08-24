"""
Shared configuration for the graphical version of the Heroes‑like game.

This module defines constants used throughout the project, such as tile
dimensions, colours and world sizes.  Keeping these values in one place
makes it easy to tweak the look and feel of the game or adjust the map
dimensions.
"""

try:  # pragma: no cover - constants don't require pygame unless rendering
    import pygame
except ImportError:  # pragma: no cover
    pygame = None

import json
import os
from typing import Dict, List

import settings
from loaders.i18n import load_locale

"""
Default screen settings.  When a custom map file is loaded, the actual
window size will be determined dynamically based on the map dimensions.
"""
# These values are used as a fallback when no map file is provided.
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Height reserved for the UI/hud at the bottom of the screen (in pixels)
UI_HEIGHT = 120

# Frames per second (controls update speed)
FPS = 30

# Difficulty levels for AI behaviour and default selection
# The list contains the canonical difficulty identifiers used internally.
# ``DIFFICULTY_LABELS`` provides human readable, translated labels for
# display purposes.  When a translation is missing the English text is used
# as a fallback.
AI_DIFFICULTIES = ["Novice", "Intermédiaire", "Avancé"]

_LOCALE_STRINGS = load_locale(settings.LANGUAGE)
DIFFICULTY_LABELS = {d: _LOCALE_STRINGS.get(d, d) for d in AI_DIFFICULTIES}
AI_DIFFICULTY = "Intermédiaire"

# Predefined world sizes exposed to the user when starting a new game.
# The current implementation maps simple labels to explicit width/height
# pairs.  The previous behaviour roughly corresponded to the ``s`` or
# ``m`` entries below.  ``DEFAULT_MAP_SIZE`` is used when no preference is
# given.
MAP_SIZE_PRESETS = {
    "xs": (16, 16),
    "s": (24, 24),
    "m": (32, 32),
    "l": (40, 40),
    "xl": (48, 48),
}
DEFAULT_MAP_SIZE = "m"

# World map settings
# ``WORLD_WIDTH`` and ``WORLD_HEIGHT`` are kept for backward compatibility but
# are no longer used when maps are generated procedurally.  Instead the map
# size is chosen randomly from ``WORLD_SIZE_RANGE`` unless explicitly
# specified.
WORLD_WIDTH = 8
WORLD_HEIGHT = 8
# Allow slightly larger automatically generated worlds so exploration feels
# less cramped.  The range is used when no explicit size is provided.
WORLD_SIZE_RANGE = (12, 20)
# Default distribution of biomes for purely random maps (non‑continent
# generation).  Additional terrains beyond the core four are included so the
# world contains a richer variety of regions to explore.
DEFAULT_BIOME_WEIGHTS = {
    "scarletia_echo_plain": 0.3,
    "scarletia_crimson_forest": 0.15,
    "scarletia_volcanic": 0.15,
    "mountain": 0.1,
    "hills": 0.1,
    "swamp": 0.08,
    "jungle": 0.07,
    "ice": 0.05,
}
"""Default distribution of biomes used for random map generation."""

# Relative priority of biomes when blending neighbouring tiles.  A higher
# value means the neighbouring biome overlays this tile during rendering.
BIOME_PRIORITY = {
    "scarletia_echo_plain": 0,
    "scarletia_crimson_forest": 1,
    "hills": 2,
    "swamp": 3,
    "jungle": 4,
    "scarletia_volcanic": 5,
    "ice": 6,
    "mountain": 7,
    "river": 8,
    "ocean": 9,
}

# Biomes that are inherently impassable regardless of the ``obstacle`` flag on a
# tile.  Units may never enter these terrains.
IMPASSABLE_BIOMES = {"mountain", "river"}

# Biomes that require a boat to traverse.  These are otherwise considered
# passable but movement is restricted to units currently embarked on a naval
# vessel.
WATER_BIOMES = {"ocean"}
ROAD_COST = 1  # AP cost when moving along a road
TILE_SIZE = 64  # pixel size of each square on the exploration map
# Rendering layers – lower indices are drawn first
LAYER_BIOME = 0
LAYER_DECALS = 1
LAYER_RESOURCES = 2
LAYER_OVERLAY = 3
LAYER_FLORA = 4
LAYER_OBJECTS = 5
LAYER_UNITS = 6
LAYER_UI = 7

# Resources available in the world.  These names are used as keys in the
# hero's resource dictionary and when generating resource buildings on the
# map.  Gold acts as the primary currency while ``treasure`` represents loose
# finds that heroes can gather on their travels.
RESOURCES = ["gold", "wood", "stone", "crystal", "treasure"]

# ---------------------------------------------------------------------------
# Town structure and unit recruitment costs
# ---------------------------------------------------------------------------

# Resources required to construct structures within a town.  Values are kept
# intentionally small for the lightweight test environment.
TOWN_STRUCTURE_COSTS = {
    "barracks": {"wood": 5, "stone": 5},
    "archery_range": {"wood": 3, "stone": 2},
}

# Gold (and optional resources) required to recruit units from a town.
UNIT_RECRUIT_COSTS = {
    "Swordsman": {"gold": 50},
    "Archer": {"gold": 75},
}
# for futur market rates and buildings
MARKET_RATES = {
    ("gold","wood"): 100, ("gold","stone"): 100, ("gold","crystal"): 250,
    ("wood","gold"): 8, ("stone","gold"): 8, ("crystal","gold"): 25,
}

# Combat settings
# Battlefield dimensions for tactical combat
# ``COMBAT_HEX_SIZE`` represents the width of a single hex cell in pixels.
COMBAT_HEX_SIZE = 64
COMBAT_GRID_WIDTH = 10
COMBAT_GRID_HEIGHT = 10
COMBAT_TILE_SIZE = 64

# Colours (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)
RED = (220, 20, 60)
BLUE = (65, 105, 225)
YELLOW = (238, 238, 0)
MAGENTA = (255, 0, 255)
GREY = (169, 169, 169)
DARK_GREY = (60, 60, 60)

# Additional colours used for rarity display
PURPLE = (128, 0, 128)

# Mapping of item rarity to frame colours
RARITY_COLOURS = {
    "common": GREY,
    "rare": BLUE,
    "epic": PURPLE,
    "legendary": YELLOW,
}

# File names for default images (see README for details)
IMG_OBSTACLE = "obstacle.png"
IMG_TREASURE = "resources/treasure.png"
IMG_HERO_PORTRAIT = "portrait_hero.png"
IMG_SKILL_COMBAT = "skill_combat.png"
IMG_SKILL_MAGIC = "skill_magic.png"


# ---------------------------------------------------------------------------
# Biome data derived from :class:`BiomeCatalog`
# ---------------------------------------------------------------------------

def build_biome_base_images() -> Dict[str, List[str]]:
    """Return mapping of biome id to list of tile variant image files.

    The ``path`` field of each :class:`biomes.Biome` points to a directory
    containing numbered variant images (``0.png`` .. ``N-1.png``).  Legacy
    biomes without catalogue entries are added separately below as a single
    variant based on their ``image`` field.
    """
    # Import locally to avoid circular dependency with :mod:`loaders.biomes`.
    from loaders.biomes import BiomeCatalog  # noqa: WPS433

    images: Dict[str, List[str]] = {}
    for biome in BiomeCatalog._biomes.values():
        variant_count = max(1, int(getattr(biome, "variants", 1)))
        base_path = biome.path
        files = [
            f"{base_path}_{i}.png" if not base_path.endswith(".png") else base_path
            for i in range(variant_count)
        ]
        images[biome.id] = files

    # Load legacy terrain tiles for backward compatibility
    manifest_path = os.path.join(
        os.path.dirname(__file__), "assets", "terrain", "legacy.json"
    )
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            entries = json.load(fh)
        for entry in entries:
            key = entry.get("id", "")
            img = entry.get("image", "")
            if key:
                images[key] = [img]
    except Exception:
        pass

    return images


# Populated at runtime via :func:`build_biome_base_images` after the biome
# manifest has been loaded.  Provide sensible defaults so terrain rendering
# never falls back to solid colour fills when the catalogue has not been
# initialised.  These paths point to the simple placeholder tiles shipped with
# the project.
BIOME_BASE_IMAGES: Dict[str, List[str]] = {
    "grass": ["terrain/grass.png"],
    "forest": ["terrain/forest.png"],
    "desert": ["terrain/desert.png"],
    "mountain": ["terrain/mountain.png"],
    "hills": ["terrain/hills.png"],
    "swamp": ["terrain/swamp.png"],
    "jungle": ["terrain/jungle.png"],
    "ice": ["terrain/ice.png"],
    "river": ["terrain/river.png"],
    "ocean": ["terrain/ocean.png"],
    # Fallbacks for the core Scarletiа biomes used in tests
    "scarletia_echo_plain": ["terrain/grass.png"],
    "scarletia_crimson_forest": ["terrain/forest.png"],
    "scarletia_volcanic": ["terrain/desert.png"],
}
