"""Biological tick simulation for generated maps.

This module introduces a lightweight ecology pass that can be run over the
continent generator output.  It seeds pioneer species on favourable tiles,
then iterates a few simple rules for dispersal, competition, predation and
slow adaptation.  The end result is a per‑tile :class:`BioticProfile`
describing biomass, dominant vegetation, animal presence and the time of
colonisation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .continents import GeneratedMap, NodalTileData


@dataclass(slots=True)
class SpeciesType:
    """Configuration describing a coarse ecological guild.

    Attributes
    ----------
    name:
        Identifier for the species type (e.g. ``"pioneer_plants"``).
    category:
        Broad role of the species (``"flora"`` or ``"fauna"``).  Competition
        and predation are modelled using this attribute.
    preferred_biomes:
        Biome letters where this species thrives.
    temperature_range:
        Inclusive temperature range (in Celsius) considered optimal.
    humidity_range:
        Inclusive humidity range (0–1) considered optimal.
    dispersal_rate:
        Fraction of local biomass that attempts to migrate each tick.
    predation_pressure:
        How strongly the species impacts lower trophic levels when present.
    habitat:
        Either ``"land"`` or ``"aquatic"`` to determine obstacle handling.
    """

    name: str
    category: str
    preferred_biomes: Tuple[str, ...]
    temperature_range: Tuple[float, float]
    humidity_range: Tuple[float, float]
    dispersal_rate: float
    predation_pressure: float
    habitat: str = "land"


@dataclass(slots=True)
class TileEnvironment:
    """Physical conditions of a tile relevant to ecology."""

    biome: str
    temperature: float
    humidity: float
    soil: str
    distance_to_water: int
    altitude: float


@dataclass(slots=True)
class BioticProfile:
    """Summary of biological activity for a single tile."""

    biomass: float
    dominant_vegetation: str
    animal_presence: List[str]
    colonized_at: Optional[int]


_FERTILE_SOILS = {"loam", "humus", "alluvium", "silt"}
_OBSTACLE_BIOMES = {"W", "O", "M"}


class BiologySimulator:
    """Orchestrate biological ticks on a :class:`GeneratedMap`."""

    def __init__(self, generated_map: GeneratedMap):
        self.generated_map = generated_map
        self.rows = generated_map.rows
        self.metadata = getattr(generated_map, "metadata", None)
        self.height = len(self.rows)
        self.width = len(self.rows[0]) // 2 if self.rows else 0
        self.tick_index = 0
        self.species: Dict[str, SpeciesType] = self._default_species_types()
        self._adaptations: Dict[str, Dict[str, Tuple[float, float]]] = {}
        self.environment: List[List[TileEnvironment]] = self._build_environment()
        self._state: List[List[Dict[str, float]]] = [
            [dict() for _ in range(self.width)] for _ in range(self.height)
        ]
        self._colonization_age: List[List[Optional[int]]] = [
            [None for _ in range(self.width)] for _ in range(self.height)
        ]
        self._seed_initial()

    def _default_species_types(self) -> Dict[str, SpeciesType]:
        """Define the coarse species guilds used by the simulation."""

        return {
            "pioneer_plants": SpeciesType(
                name="pioneer_plants",
                category="flora",
                preferred_biomes=("G", "H", "R"),
                temperature_range=(5.0, 28.0),
                humidity_range=(0.2, 0.85),
                dispersal_rate=0.35,
                predation_pressure=0.0,
            ),
            "forest": SpeciesType(
                name="forest",
                category="flora",
                preferred_biomes=("F", "J", "S"),
                temperature_range=(8.0, 24.0),
                humidity_range=(0.35, 0.9),
                dispersal_rate=0.25,
                predation_pressure=0.0,
            ),
            "herbivores": SpeciesType(
                name="herbivores",
                category="fauna",
                preferred_biomes=("G", "F", "H", "J"),
                temperature_range=(0.0, 30.0),
                humidity_range=(0.15, 0.85),
                dispersal_rate=0.2,
                predation_pressure=0.25,
            ),
            "carnivores": SpeciesType(
                name="carnivores",
                category="fauna",
                preferred_biomes=("G", "F", "H", "J"),
                temperature_range=(0.0, 30.0),
                humidity_range=(0.1, 0.85),
                dispersal_rate=0.22,
                predation_pressure=0.4,
            ),
            "aquatic": SpeciesType(
                name="aquatic",
                category="fauna",
                preferred_biomes=("W", "O", "C", "R"),
                temperature_range=(-2.0, 22.0),
                humidity_range=(0.7, 1.0),
                dispersal_rate=0.3,
                predation_pressure=0.2,
                habitat="aquatic",
            ),
        }

    def _build_environment(self) -> List[List[TileEnvironment]]:
        """Translate map metadata into per-tile environmental attributes."""

        default_temp = {
            "G": 18.0,
            "F": 16.0,
            "D": 28.0,
            "M": 4.0,
            "H": 10.0,
            "S": 20.0,
            "J": 24.0,
            "I": -6.0,
            "R": 12.0,
            "W": 8.0,
            "O": 8.0,
        }
        default_humidity = {
            "G": 0.45,
            "F": 0.65,
            "D": 0.1,
            "M": 0.3,
            "H": 0.35,
            "S": 0.7,
            "J": 0.85,
            "I": 0.2,
            "R": 0.6,
            "W": 0.5,
            "O": 0.5,
        }

        env_grid: List[List[TileEnvironment]] = []
        for y in range(self.height):
            row_env: List[TileEnvironment] = []
            for x in range(self.width):
                biome_char = self.rows[y][2 * x]
                node: Optional[NodalTileData] = None
                if self.metadata and y < len(self.metadata) and x < len(self.metadata[y]):
                    node = self.metadata[y][x]
                temp = node.mean_temperature if node else default_temp.get(biome_char, 12.0)
                humidity = node.mean_humidity if node else default_humidity.get(biome_char, 0.45)
                soil = node.soil_type if node else "loam"
                row_env.append(
                    TileEnvironment(
                        biome=biome_char,
                        temperature=temp,
                        humidity=humidity,
                        soil=soil,
                        distance_to_water=node.coastal_proximity if node else 0,
                        altitude=node.altitude if node else 0.0,
                    )
                )
            env_grid.append(row_env)
        return env_grid

    def _seed_initial(self) -> None:
        """Seed pioneer vegetation and aquatic life on favourable tiles."""

        for y in range(self.height):
            for x in range(self.width):
                env = self.environment[y][x]
                if env.biome in {"W", "O", "R"}:
                    self._state[y][x]["aquatic"] = 3.0
                    self._colonization_age[y][x] = self.tick_index
                    continue
                fertile = env.soil in _FERTILE_SOILS
                temperate = 8.0 <= env.temperature <= 22.0
                humid = 0.3 <= env.humidity <= 0.75
                near_freshwater = env.distance_to_water <= 1
                if fertile and temperate and humid and near_freshwater:
                    self._state[y][x]["pioneer_plants"] = 4.0
                    self._state[y][x]["forest"] = 1.0
                    self._colonization_age[y][x] = self.tick_index

    def tick(self) -> None:
        """Advance the biological simulation by one step."""

        next_state: List[List[Dict[str, float]]] = [
            [dict() for _ in range(self.width)] for _ in range(self.height)
        ]

        for y in range(self.height):
            for x in range(self.width):
                env = self.environment[y][x]
                for species_name, biomass in self._state[y][x].items():
                    if biomass <= 0:
                        continue
                    species = self.species[species_name]
                    if self._is_obstacle(env, species):
                        continue
                    stay, dispersal = self._partition_biomass(biomass, species)
                    next_state[y][x][species_name] = next_state[y][x].get(species_name, 0.0) + stay
                    self._spread_to_neighbours(x, y, species, dispersal, next_state)

        for y in range(self.height):
            for x in range(self.width):
                env = self.environment[y][x]
                self._apply_predation_and_competition(x, y, env, next_state)
                total_biomass = sum(next_state[y][x].values())
                if total_biomass > 0 and self._colonization_age[y][x] is None:
                    self._colonization_age[y][x] = self.tick_index
                self._apply_adaptation(x, y, env, next_state)

        self._state = next_state
        self.tick_index += 1

    def run(self, steps: int) -> List[List[BioticProfile]]:
        """Run ``steps`` ticks and return the resulting biotic profiles."""

        for _ in range(steps):
            self.tick()
        return self.profiles()

    def profiles(self) -> List[List[BioticProfile]]:
        """Return current :class:`BioticProfile` grid."""

        grid: List[List[BioticProfile]] = []
        for y in range(self.height):
            row: List[BioticProfile] = []
            for x in range(self.width):
                tile = self._state[y][x]
                biomass = sum(tile.values())
                dominant = "barren"
                if tile:
                    flora = {k: v for k, v in tile.items() if self.species[k].category == "flora"}
                    if flora:
                        dominant = max(flora.items(), key=lambda kv: kv[1])[0]
                    elif biomass > 0:
                        dominant = max(tile.items(), key=lambda kv: kv[1])[0]
                animals = [
                    name
                    for name, amount in tile.items()
                    if self.species[name].category == "fauna" and amount >= 0.2
                ]
                row.append(
                    BioticProfile(
                        biomass=round(biomass, 2),
                        dominant_vegetation=dominant,
                        animal_presence=sorted(animals),
                        colonized_at=self._colonization_age[y][x],
                    )
                )
            grid.append(row)
        return grid

    def _spread_to_neighbours(
        self,
        x: int,
        y: int,
        species: SpeciesType,
        dispersal: float,
        next_state: List[List[Dict[str, float]]],
    ) -> None:
        neighbours = list(self._neighbouring_cells(x, y))
        suitability_scores = []
        for nx, ny in neighbours:
            env = self.environment[ny][nx]
            score = self._suitability(species, env)
            suitability_scores.append(score)
        total_score = sum(suitability_scores)
        if total_score <= 0:
            next_state[y][x][species.name] = next_state[y][x].get(species.name, 0.0) + dispersal
            return
        for (nx, ny), score in zip(neighbours, suitability_scores):
            if score <= 0:
                continue
            share = dispersal * (score / total_score)
            next_state[ny][nx][species.name] = next_state[ny][nx].get(species.name, 0.0) + share

    def _neighbouring_cells(self, x: int, y: int) -> Iterable[Tuple[int, int]]:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield nx, ny

    def _is_obstacle(self, env: TileEnvironment, species: SpeciesType) -> bool:
        if species.habitat == "aquatic":
            return False
        return env.biome in _OBSTACLE_BIOMES

    def _partition_biomass(self, biomass: float, species: SpeciesType) -> Tuple[float, float]:
        dispersal = biomass * species.dispersal_rate
        stay = biomass - dispersal
        return stay, dispersal

    def _suitability(self, species: SpeciesType, env: TileEnvironment) -> float:
        temp_min, temp_max = self._adapted_range(species, env.biome, species.temperature_range)
        hum_min, hum_max = self._adapted_range(species, env.biome, species.humidity_range)

        def _score(value: float, bounds: Tuple[float, float]) -> float:
            lower, upper = bounds
            if value < lower or value > upper:
                distance = min(abs(value - lower), abs(value - upper))
                return max(0.0, 1.0 - (distance / (upper - lower + 0.001)))
            span = upper - lower if upper != lower else 1.0
            return 1.0 - (abs((value - lower) - span / 2) / (span / 2 + 0.001))

        temp_score = _score(env.temperature, (temp_min, temp_max))
        humidity_score = _score(env.humidity, (hum_min, hum_max))
        biome_bonus = 1.1 if env.biome in species.preferred_biomes else 0.85
        return max(0.0, min(1.0, ((temp_score + humidity_score) / 2) * biome_bonus))

    def _apply_predation_and_competition(
        self,
        x: int,
        y: int,
        env: TileEnvironment,
        state: List[List[Dict[str, float]]],
    ) -> None:
        tile = state[y][x]
        flora_biomass = sum(v for k, v in tile.items() if self.species[k].category == "flora")
        herbivores = tile.get("herbivores", 0.0)
        carnivores = tile.get("carnivores", 0.0)
        aquatic = tile.get("aquatic", 0.0)

        # Predation and grazing
        if flora_biomass > 0 and herbivores > 0:
            loss = min(flora_biomass * 0.1, herbivores * 0.3)
            self._scale_group(tile, category="flora", factor=max(0.0, 1 - loss / max(flora_biomass, 0.001)))
        if herbivores > 0 and carnivores > 0:
            prey_loss = min(herbivores * 0.25, carnivores * 0.3)
            tile["herbivores"] = max(0.0, herbivores - prey_loss)
            tile["carnivores"] = max(0.0, carnivores - prey_loss * (1 - self.species["carnivores"].predation_pressure))

        # Resource limitation
        capacity = self._carrying_capacity(env)
        total = sum(tile.values())
        if total > capacity > 0:
            factor = capacity / total
            for k in list(tile.keys()):
                tile[k] *= factor

        # Aquatic species cannot remain on dry obstacles
        if env.biome in _OBSTACLE_BIOMES and aquatic > 0:
            tile["aquatic"] = 0.0

    def _apply_adaptation(
        self,
        x: int,
        y: int,
        env: TileEnvironment,
        state: List[List[Dict[str, float]]],
    ) -> None:
        tile = state[y][x]
        for species_name, biomass in tile.items():
            if biomass < 1.0:
                continue
            species = self.species[species_name]
            temp_shift, hum_shift = self._adaptations.get(species_name, {}).get(env.biome, (0.0, 0.0))
            target_temp = env.temperature
            base_min, base_max = species.temperature_range
            current_mid = (base_min + base_max) / 2 + temp_shift
            temp_shift += (target_temp - current_mid) * 0.05
            temp_shift = max(-5.0, min(5.0, temp_shift))

            target_h = env.humidity
            h_min, h_max = species.humidity_range
            h_mid = (h_min + h_max) / 2 + hum_shift
            hum_shift += (target_h - h_mid) * 0.05
            hum_shift = max(-0.2, min(0.2, hum_shift))

            self._adaptations.setdefault(species_name, {})[env.biome] = (temp_shift, hum_shift)

    def _adapted_range(
        self, species: SpeciesType, biome: str, base_range: Tuple[float, float]
    ) -> Tuple[float, float]:
        shift = self._adaptations.get(species.name, {}).get(biome, (0.0, 0.0))
        if base_range is species.temperature_range:
            delta = shift[0]
        else:
            delta = shift[1]
        return base_range[0] + delta, base_range[1] + delta

    def _carrying_capacity(self, env: TileEnvironment) -> float:
        base = 6.0 + env.humidity * 6.0
        if env.soil in _FERTILE_SOILS:
            base += 3.0
        if env.biome in {"D", "I", "M"}:
            base *= 0.6
        if env.biome in {"W", "O", "R"}:
            base += 4.0
        return max(1.0, base)

    def _scale_group(self, tile: Dict[str, float], category: str, factor: float) -> None:
        for key, value in list(tile.items()):
            if self.species[key].category == category:
                tile[key] = value * factor
