# Unit and Creature JSON Schema

Unit and creature definitions are stored under `assets/units/*.json` and loaded
through :func:`loaders.units_loader.load_units`.  Each manifest contains either a
`"units"` or `"creatures"` array with entries of the following form:

```json
{
  "id": "swordsman",          // unique identifier
  "name": "Swordsman",        // optional display name
  "image": "units/path.png",  // sprite relative to `assets/`
  "anchor_px": [32, 64],       // drawing anchor in pixels
  "shadow_baked": true,        // sprite already includes shadow
  "battlefield_scale": 1.0,    // optional render scale
  "abilities": {"Shield Block": 1}, // ability map or list
  "stats": {
    "name": "Swordsman",
    "max_hp": 40,
    "attack_min": 4,
    "attack_max": 6,
    "defence_melee": 3,
    "defence_ranged": 3,
    "defence_magic": 0,
    "speed": 3,
    "attack_range": 1,
    "initiative": 5,
    "sheet": "units",
    "hero_frames": [0, 0],
    "enemy_frames": [3, 3],
    "morale": 0,
    "luck": 0,
    "abilities": ["shield_block"],
    "role": "optional description",
    "unit_type": "non-magic",
    "mana": 1,
    "min_range": 1,
    "retaliations_per_round": 1,
    "battlefield_scale": 1.0
  }
}
```

The `stats` block corresponds to the :class:`core.entities.UnitStats` dataclass
and accepts any of its fields.  Values not supplied default to those of a
minimal unit (1 HP, speed 1, etc.).

Creature entries share the same structure and may include additional fields such
as:

* `biomes` – list of biome identifiers the creature can appear in.
* `behavior` – roaming AI behaviour (e.g. `"roamer"`, `"guardian"`).
* `guard_range` – tiles protected around the creature.

Manifests may also provide a `templates` mapping used to supply default values
for multiple units.  Each entry can reference a template via the `template`
field; values from the entry override those supplied by the template.
