# Modding Guide

This guide explains how to extend the game with custom content and behaviour.

## Asset Manifests

Game data is driven by JSON manifests located under `assets/<category>/<category>.json`. Each entry lists an `id`, image `path` and optional metadata. See [asset_manifests.md](asset_manifests.md) for full details on the format. To add new art, place images in the appropriate directory and reference them from the manifest.

## Plugin APIs

Several subsystems expose small plugin APIs through hook registries. Modules such as `siege`, `diplomacy` and `weather` provide a `register_hook` helper and a `hooks` list:

```python
from siege import register_hook

def my_siege_rule(engine):
    ...

register_hook(my_siege_rule)
```

Registered callbacks run whenever the game triggers that subsystem, allowing mods to inject custom logic.

## Scripting Hooks

Hooks make it possible to execute Python code at key moments without modifying core files. Common hook points include:

- `diplomacy.register_hook` – react to relation changes between factions.
- `siege.register_hook` – augment siege encounters.
- `weather.register_hook` – update weather effects.

Hook functions can import game types, adjust state or call back into the engine, enabling rich scripting capabilities.
