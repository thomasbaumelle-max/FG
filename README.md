# Fantasy Strategy Game – Graphical Edition

This project is a graphical version of the simple Heroes‑like game.  It uses
the **Pygame** library for window management, image loading and event
handling, and replicates the same core gameplay loops: exploring a world map
and battling enemies on a tactical grid.

## Features

- **World exploration** on maps loaded from text files or generated
  procedurally with varied biomes.
- **Resource system** with wood, stone and crystal gathered from the map and
  from special buildings such as mines, sawmills and crystal mines.
- **Hero progression** including experience levels, skill points and mana
  management.
- **Turn‑based combat** on an 8×6 grid featuring unit stacks with unique
  stats and abilities (e.g. charge, flying, passive healing) and a simple
  fireball spell.
- **Saving and loading** of the current game state to continue later.
- **Start menu and UI** with zooming, panning and buttons for ending the turn
  or healing units.

## Requirements

* **Python 3.8+**

## Installation

The project now ships a `pyproject.toml` which declares runtime and developer
dependencies.  Install the game and its dependencies with **pip**:

```bash
pip install .
```

For an isolated environment you can use **pipx** instead:

```bash
pipx install .
```

After installation the game can be launched via the `fantaisie` command or by
running the module directly:

```bash
python -m main
```

Developers may wish to install the optional tooling extras which include
formatting and test utilities:

```bash
pip install -e .[dev]
```

## Getting Started

1. Make sure the `assets` folder contains the expected manifest files and
   images (see **Assets** section below).  You can add your own artwork by
   editing these manifests or dropping in additional PNGs referenced by them.

2. Run the game from a terminal:

   ```bash
   fantaisie
   ```

3. Use the arrow keys to move your hero around the world map.  Press the
   **+**/**-** keys to zoom in and out when exploring.  When you
   encounter an enemy, the game switches into tactical combat mode.  During
   combat, click on one of your units to select it, then click a target
   square within movement range to move, or click an enemy unit within
   attack range to attack.  Press the **space bar** to end a unit’s turn
   early.  There is also a simple fireball spell that can be cast with the
   **F** key when a hero unit is selected.

A status panel along the bottom of the window displays your hero's gold,
mana, army composition and remaining action points.  During exploration you
can click the on-screen **End Turn** and **Heal** buttons (or press **T** and
**H**) to manage your army.

## Assets

Game graphics and data are described through JSON *manifests* rather than a
fixed list of filenames.  Each manifest lives under `assets/<category>/` and
enumerates entries with metadata and image paths.  Dedicated loaders such as
`loaders.flora_loader.FloraLoader` and
`loaders.resources_loader.load_resources` parse these manifests, load the
referenced PNGs via the `AssetManager` and make them available to the rest of
the game.

This approach allows each asset to define variants, biome tags or spawn rules
without hard‑coding file names.  To add new artwork, place the image in the
appropriate directory and reference it from the corresponding manifest.

For a complete legacy listing of individual asset filenames, see
[docs/assets/README.md](docs/assets/README.md).  More details on the manifest
format are provided in [docs/asset_manifests.md](docs/asset_manifests.md).

## Asset Scaling

To keep graphics consistent, resize images via the helper function
`scale_surface` in `graphics/scale.py`.  High‑resolution illustrations
should pass `smooth=True` to leverage Pygame’s `smoothscale`, while pixel
art and tiles should use the default `smooth=False` to preserve crisp
edges.  When contributing new assets, select the scaling mode that best
matches the style of your artwork.

## Code Structure

The project is organised into a few subpackages:

* **`core/`** – gameplay logic including the world map, combat system,
  entities and buildings.
* **`loaders/`** – asset manifests, data loaders and the `AssetManager`.
* **`state/`** – global game state and a simple event bus.
* **`ui/`** – menu, town and main game screens plus reusable widgets.
* **`render/`** – helpers for drawing the world and layering elements.
* **`graphics/`** – utilities for scaling surfaces and working with
  spritesheets.
* **`mapgen/`** – procedural continent and biome generation tools.
* **`main.py`** – application entry point that creates the game and starts the
  main loop.

Feel free to extend or modify the packages to introduce more unit types,
different spells or additional map interactions.  The code is written to be
relatively easy to follow and expand.

## Workflow

On start‑up the game creates a `loaders.core.Context` describing the repository
root, search paths and an optional `AssetManager`.  Loader modules use this
context to read JSON manifests and register assets:

* `loaders.resources_loader.load_resources` imports resource definitions from
  `assets/resources/resources.json`.
* `loaders.flora_loader.FloraLoader` reads `assets/flora/flora.json` and can
  automatically scatter props across the map via `autoplace` using biome
  information and spawn rules.

Once the assets are prepared, `main.py` builds the initial game state and
enters the main loop.

## Procedural Map Generation

If no map file is supplied, a `WorldMap` is created procedurally.  Width and
height are chosen randomly from `constants.WORLD_SIZE_RANGE` unless explicitly
provided.  The distribution of biomes can be customised by passing a
`biome_weights` dictionary to `WorldMap`; the values act as weights and allow
one or more terrains to dominate the generated landscape.

The continent generator also enforces simple biome adjacency rules.  A
compatibility matrix controls which biome types may touch; for instance
scarletia crimson forests happily blend into scarletia echo plains while
scarletia volcanic terrain will never border ice fields.
Custom compatibility tables can be supplied to `generate_continent_map` to
override these defaults.

Additional world features such as resource nodes and special buildings can be
requested at map creation time using the `num_resources` and `num_buildings`
parameters of `WorldMap`.  The `num_resources` value represents a resource
density percentage (with values above 100 treated as a raw count) and defaults
to a visible 5–10% coverage. Resources and structures are themed to the biome
they appear in—for example forests yield wood while mountains may host mines.

## Map Format

Maps are stored as plain text files where each character represents a tile on
the world map.  The game currently understands the symbols `.` (grass), `#`
(obstacle), `T` (treasure) and `E` (enemy group).  An expanded set of biome and
feature codes—along with example continent layouts—is documented in
[docs/map_format.md](docs/map_format.md).

## Running Tests

The project includes a small automated test suite that exercises map
generation, combat rules and save/load behaviour.  Run the tests in
parallel with:

```bash
pytest -n auto
```

Slow tests that perform extensive world generation or long AI loops are marked with `slow` and either `worldgen` or `combat`. You can run a subset with:

```bash
pytest -m "not slow and not worldgen"
```


## Configuration

Runtime options are read from environment variables and the `settings.json`
file in the project root. Setting `FG_DEBUG_BUILDINGS=1` (or adding
`"debug_buildings": true` to `settings.json`) draws debug markers for building
positions in the world renderer.

## Roadmap and Ideas

There are many directions to expand the game.  Some possibilities include:

- Smarter enemy AI for both world exploration and tactical combat.
- Additional unit types, spells and status effects.
- Towns, markets and a more elaborate economy.
- Sound effects, music and richer graphical animation.
- Multiple heroes, fog of war and a quest system.
- Packaging the project so it can be installed as a Python package.

Contributions and suggestions are welcome!

