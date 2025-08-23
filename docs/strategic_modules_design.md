# Future Strategic Modules

This document sketches the planned public API for three new subsystems: **siege**,
**diplomacy**, and **weather**.  They currently ship as lightweight placeholders
containing only data structures and hook registries so that future work can be
carried out incrementally.

## Siege Module

```python
from siege import SiegeEngine, register_hook, hooks
```

### Data Structures
- `SiegeEngine`
  - `name: str` – human readable identifier.
  - `damage: int` – base damage dealt against fortifications.
  - `range: int` – tactical attack range.  Defaults to `1`.

### Hooks
- `register_hook(func: SiegeHook) -> None`
  - Register a callback invoked with the active `SiegeEngine` during siege
    related events.
- `hooks: list[SiegeHook]`
  - Collection of registered callbacks.  Consumers may iterate over this list
    to trigger custom logic.

## Diplomacy Module

```python
from diplomacy import DiplomaticRelation, register_hook, hooks
```

### Data Structures
- `DiplomaticRelation`
  - `faction_a: str`
  - `faction_b: str`
  - `state: str = "neutral"`

### Hooks
- `register_hook(func: DiplomacyHook) -> None`
  - Register a callback invoked when the relation between two factions changes.
- `hooks: list[DiplomacyHook]`
  - Collection of registered diplomacy callbacks.

## Weather Module

```python
from weather import WeatherState, register_hook, hooks
```

### Data Structures
- `WeatherState`
  - `condition: str = "clear"` – textual description of the current weather.
  - `temperature: float = 20.0` – temperature in degrees Celsius.

### Hooks
- `register_hook(func: WeatherHook) -> None`
  - Register a callback run whenever the weather state updates.
- `hooks: list[WeatherHook]`
  - Collection of registered weather callbacks.

Each module uses Python protocols to describe the expected signature of a hook
and exposes a `register_hook` helper along with the backing `hooks` list.  Future
implementation work can expand on these structures while retaining backward
compatibility with code written against this specification.
