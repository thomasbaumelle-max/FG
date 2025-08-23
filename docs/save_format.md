# Save File Format

Game progress is stored as JSON.  The root object contains a `version` field
which indicates the format of the file.  The current version is `1`.

```json
{
  "version": 1,
  "hero": { ... },
  "world": { ... },
  "enemy_heroes": [ ... ],
  "event_queue": [ ... ]
}
```

The hero's inventory, equipment and skill tree are written to a separate
`save_profileXX.json` file.  When loading a game, these values are merged back
into the `hero` block before the dataclasses (`Hero`, `WorldMap`, etc.) are
hydrated.

Older saves that omit the `version` field are treated as version `0` and
upgraded automatically to the latest structure.
