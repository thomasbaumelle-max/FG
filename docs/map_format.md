# ASCII Map Format

This project represents world maps as grids of characters.  Each tile is
encoded by a biome symbol optionally followed by a feature symbol.  When a
feature is omitted it defaults to `.` (an empty tile).  Unknown characters
default to empty grass.

## Biomes

| Char | Terrain            | Passable |
|------|--------------------|----------|
| `G`  | Grassland / plains | yes      |
| `F`  | Forest             | yes      |
| `H`  | Hills              | yes      |
| `M`  | Mountains          | no       |
| `D`  | Desert             | yes      |
| `S`  | Swamp              | yes      |
| `J`  | Jungle             | yes      |
| `I`  | Ice / tundra       | yes      |
| `W`  | Water / ocean      | no       |
| `O`  | Water / ocean      | no *(legacy)* |

## Features

| Char | Feature        | Notes                                     |
|------|----------------|-------------------------------------------|
| `#`  | Rock obstacle  | Impassable, blocks movement               |
| `T`  | Treasure chest | Awards a random amount of gold            |
| `E`  | Enemy group    | Triggers combat when the hero enters      |

Future extensions may introduce additional feature codes such as towns,
portals or resource nodes.  Characters not listed here are ignored and treated
as plain ground.

## Example: Continent Map


The following example illustrates two continents separated by ocean.  Forests,
mountain ranges and deserts are mixed in with treasures and enemy camps.

```
WWWWWWWWWWWWWW
WGGGGGF....FWW
WGGTTGF..E.FWW
WGGGGGF....FWW
WGGGGGGWWWWWWW
WDDDDDDWMMMMMW
WDDEDDDWMEEEMW
WDDDDDDWMMMMMW
WWWWWWWWWWWWWW
```

Legend:

* `W` – ocean (`O` also accepted)
* `G`/`.` – grassland (``.`` indicates an empty tile)
* `F` – forest
* `H` – hills
* `M` – mountains
* `D` – desert
* `S` – swamp
* `J` – jungle
* `I` – ice / tundra
* `T` – treasure
* `E` – enemy army

