# Asset Manifest Structure

All game assets are described by JSON *manifest* files located under
`assets/<category>/<category>.json`.  Each manifest contains a list of entries
with at least the following fields:

* `id` – unique identifier used in code.
* `path` – base path to the asset image relative to the `assets/` directory.
* `variants` – optional number of variants. ``0`` or ``1`` resolves to
  ``<path>/base.png`` while higher counts use ``_<n>.png`` suffixes.
* additional rule-specific fields depending on the category (e.g. `income`
  for resources).

Example (`assets/resources/resources.json`):

```json
[
  {"id": "wood", "path": "resources/wood", "variants": 1}
]
```

Manifests can be read with the helper in `tools/load_manifest.py` which also
loads and caches the referenced images via the `AssetManager`::

    from tools.load_manifest import load_manifest
    entries = load_manifest(repo_root, "assets/overlays/overlays.json", asset_manager)

Current categories using this format include biomes, buildings, flora, items,
resources, units, overlays and vfx.  A legacy terrain
manifest (`assets/terrain/legacy.json`) lists the remaining standalone terrain
tiles such as `grass` or `forest` whose images live under `terrain/*.png`.  These entries are kept solely for
backward compatibility and will eventually be replaced by equivalent biome
definitions.

## Missing images

When an image referenced in a manifest is absent from disk, the
`AssetManager` emits a warning.  Building manifests loaded via
`BuildingAsset.file_list()` always trigger these warnings, even without the
`FG_DEBUG_ASSETS` environment variable.  Setting this variable instead raises
an exception on missing files to help catch mistakes during development.

## Adapter architecture

Asset manifests are now loaded through small *adapter* modules located under
`manifests/`.  Each adapter receives a :class:`manifests.core.Context` object
providing the repository root, search paths and the asset loader.  Helper
functions such as :func:`manifests.core.read_json` handle comment‑stripping and
path resolution while :func:`loaders.core.expand_variants` expands file
patterns.

This design allows game modules to load data via specialised helpers like
`manifests.flora_loader.FloraLoader` or `manifests.units_loader.load_units`
without hard‑coding asset locations.  Additional asset types can be supported by
dropping a new adapter into the `manifests/` package.

## Rendering layer order

To ensure consistent compositing across modules, map elements are grouped into
named layers.  Lower numbered layers are drawn first:

1. **Biome** – base terrain tiles.
2. **Decals** – roads and flat flora decals.
3. **Resources** – resource deposits such as wood or stone.
4. **Overlay** – world overlays like biome transitions.
5. **Flora** – collectible and tall flora props.
6. **Objects** – obstacles, treasures and buildings.
7. **Units** – enemy stacks and heroes.
8. **UI** – selection rectangles and other visual aids.

The numeric indices for these layers are available as ``LAYER_*`` constants in
`constants.py`.
