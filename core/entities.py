"""
Entity definitions for the graphical Heroes‑like game.

This module defines the basic statistics of unit types and the classes used
to represent units and the player's hero.  It does not depend on Pygame
directly, so the core combat and exploration logic can be tested without
graphics.
"""

from __future__ import annotations

import os
import random

from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Literal, Set, Protocol, runtime_checkable

import constants
from .faction import FactionDef
from tools.artifact_manifest import load_artifact_manifest
from tools.skill_manifest import load_skill_manifest


class EquipmentSlot(Enum):
    """Possible equipment locations for heroes and units."""

    HEAD = auto()
    NECK = auto()
    SHOULDERS = auto()
    TORSO = auto()
    LEGS = auto()
    WEAPON = auto()
    OFFHAND = auto()
    RING = auto()
    AMULET = auto()


@dataclass
class Modifier:
    stat: str
    value: float
    mode: Literal["flat", "percent"]


@dataclass
class Item:
    id: int
    name: str
    slot: Optional["EquipmentSlot"]
    rarity: str
    icon: str
    stackable: bool
    qty: int
    modifiers: HeroStats
    locked: bool = False


@dataclass
class SkillNode:
    id: str
    name: str
    desc: str
    cost: int
    requires: List[str]
    effects: List[Modifier | str]
    icon: str = ""
    branch: str = ""
    rank: str = ""
    coords: Tuple[int, int] | None = None


@dataclass
class UnitStats:
    """Base statistics shared by all creatures of a given type.

    The graphical representation of a unit is defined by a sprite sheet
    identifier and separate frame ranges for the hero and enemy sides.
    """

    name: str
    max_hp: int
    attack_min: int
    attack_max: int
    defence_melee: int
    defence_ranged: int
    defence_magic: int
    speed: int
    attack_range: int
    initiative: int
    sheet: str  # key of the sprite sheet within the assets dictionary
    hero_frames: Tuple[int, int]  # inclusive start/end frame indices
    enemy_frames: Tuple[int, int]  # inclusive start/end frame indices
    morale: int = 0
    luck: int = 0
    abilities: List[str] = field(default_factory=list)
    role: str = ""
    unit_type: str = "non-magic"
    mana: int = 0
    min_range: int = 1
    retaliations_per_round: int = 1


@dataclass
class UnitStack:
    """Lightweight representation of a stack for the army management tab."""

    unit_type: str
    count: int
    max_count: int
    icon: str


@dataclass
class HeroStats:
    pv: int
    dmg: int
    spd: int
    init: int
    def_melee: int
    def_ranged: int
    def_magic: int
    moral: int = 0
    luck: int = 0


class Unit:
    """
    Represents a stack of identical units in combat.  A stack has a fixed
    number of creatures (`count`), and damage is applied to the top creature
    first; when it dies the stack size is reduced by one.
    """

    def __init__(self, stats: UnitStats, count: int, side: str) -> None:
        self.stats = stats
        self.count = count
        self.current_hp = stats.max_hp
        self.max_mana = stats.mana
        self.mana = stats.mana
        self.side = side  # 'hero' or 'enemy'
        # Bonus to apply to each unit's attack (granted by hero skills)
        self.attack_bonus: int = 0
        # Bonus to initiative granted by hero skills
        self.initiative_bonus: int = 0
        # Position on combat grid; None when not on the grid
        self.x: Optional[int] = None
        self.y: Optional[int] = None
        # Flag set to True when the unit has acted this round
        self.acted: bool = False
        # Whether the unit should skip its turn this round
        self.skip_turn: bool = False
        # Number of additional turns the unit may immediately take
        self.extra_turns: int = 0
        # Remaining retaliations available this round
        self.retaliations_left: int = stats.retaliations_per_round
        # Direction the unit is facing as a (dx, dy) vector
        self.facing: Tuple[int, int] = (0, 1)
        # Arbitrary tags describing the unit (used for faction bonuses)
        self.tags: List[str] = []

    @property
    def is_alive(self) -> bool:
        return self.count > 0

    @property
    def initiative(self) -> int:
        return self.stats.initiative + self.initiative_bonus

    def damage_output(self, rng: random.Random | None = None) -> int:
        """Compute the raw damage dealt by this stack before defence is applied.

        The calculation rolls a base value from the unit's attack range and
        applies bonuses from hero skills. Luck modifies this base roll:

        * Positive luck normally doubles the damage but has a 10% chance per
          luck point to instead trigger a critical hit, which rerolls from a
          doubled attack range.
        * Negative luck halves the damage but has the same chance to degrade the
          attack into a minimal strike dealing only the unit's minimum attack
          value.

        Morale is then applied, doubling or nullifying the result.
        """

        rng = rng if rng is not None else random

        base = (
            rng.randint(self.stats.attack_min, self.stats.attack_max)
            + self.attack_bonus
        )
        damage = base * self.count

        if self.stats.luck > 0:
            if rng.random() < 0.1 * self.stats.luck:
                crit = rng.randint(
                    2 * self.stats.attack_min, 2 * self.stats.attack_max
                )
                damage = crit * self.count
            else:
                damage *= 2
        elif self.stats.luck < 0:
            if rng.random() < -0.1 * self.stats.luck:
                damage = self.stats.attack_min * self.count
            else:
                damage //= 2
        if self.stats.morale > 0:
            damage *= 2
        elif self.stats.morale < 0:
            damage = 0
        return damage



    def take_damage(self, dmg: int) -> None:
        """Apply damage to this stack and reduce creature count accordingly."""
        while dmg > 0 and self.count > 0:
            if dmg >= self.current_hp:
                dmg -= self.current_hp
                self.count -= 1
                if self.count > 0:
                    self.current_hp = self.stats.max_hp
            else:
                self.current_hp -= dmg
                dmg = 0


def apply_defence(damage: int, defender: Unit, attack_type: str) -> int:
    """Reduce ``damage`` based on the defender's appropriate defence stat.

    Parameters
    ----------
    damage:
        The incoming raw damage before mitigation.
    defender:
        The unit receiving the damage.
    attack_type:
        One of ``"melee"``, ``"ranged"`` or ``"magic"`` indicating which
        defence attribute to use.

    Returns
    -------
    int
        The resulting damage after defence is applied; always at least ``1``.
    """

    defence = getattr(defender.stats, f"defence_{attack_type}")
    return max(1, damage - defence * defender.count)


@runtime_checkable
class UnitCarrier(Protocol):
    """Common interface for objects that carry units on the world map."""

    x: int
    y: int
    ap: int
    units: List[Unit]
    name: str
    portrait: Any | None

    def apply_bonuses_to_army(self) -> None:
        """Recalculate bonuses affecting carried units."""
        ...


@dataclass
class Army(UnitCarrier):
    """Minimal representation of a stack of units roaming the world map."""

    x: int
    y: int
    units: List[Unit] = field(default_factory=list)
    ap: int = 0
    max_ap: int = 0
    name: str = "Army"
    portrait: Any | None = None

    def apply_bonuses_to_army(self) -> None:  # pragma: no cover - no bonuses yet
        """Placeholder to satisfy :class:`UnitCarrier` interface."""
        return None

    def update_portrait(self) -> None:
        """Update ``portrait`` to the strongest unit's portrait.

        The "power" of a unit is estimated from its count and attack range
        (``attack_min`` + ``attack_max``).  The portrait of the unit with the
        highest value is loaded from ``assets/units/portrait`` if available.
        """

        if not self.units:
            self.portrait = None
            return

        # Pick the unit with the highest estimated power value
        strongest = max(
            self.units,
            key=lambda u: u.count * (u.stats.attack_min + u.stats.attack_max),
        )

        unit_id = getattr(strongest.stats, "name", "").lower().replace(" ", "_")
        portrait_path = os.path.join(
            "assets", "units", "portrait", f"{unit_id}_portrait.png"
        )
        try:
            import pygame

            self.portrait = pygame.image.load(portrait_path).convert_alpha()
        except Exception:
            # Missing file or pygame not initialised – fall back to default icon
            self.portrait = None

    def __post_init__(self) -> None:
        """Ensure ``max_ap`` defaults to the initial action points.

        Also initialise ``portrait`` so armies immediately have a sprite.
        """
        if self.max_ap <= 0:
            self.max_ap = self.ap
        self.update_portrait()

    def reset_ap(self) -> None:
        """Restore the army's action points at day start."""
        self.ap = self.max_ap


@dataclass
class Boat(UnitCarrier):
    """Boat available on the world map that can carry units."""

    id: str
    x: int
    y: int
    movement: int
    capacity: int
    owner: int | None
    garrison: List[Unit] = field(default_factory=list)
    ap: int = 0
    name: str = "Boat"
    portrait: Any | None = None

    def __post_init__(self) -> None:
        self.ap = self.movement

    @property
    def units(self) -> List[Unit]:  # Alias required by UnitCarrier
        return self.garrison

    @units.setter
    def units(self, value: List[Unit]) -> None:
        self.garrison = value

    def apply_bonuses_to_army(self) -> None:  # pragma: no cover - no bonuses yet
        return None



class Hero:
    """Represents the player on the world map along with their army."""

    def __init__(
        self,
        x: int,
        y: int,
        army: Optional[List[Unit]] = None,
        base_stats: Optional[HeroStats] = None,
        portrait: Any | None = None,
        name: str = "Hero",
        colour: Tuple[int, int, int] = constants.BLUE,
        faction: FactionDef | None = None,
    ) -> None:
        self.x = x
        self.y = y
        self.portrait = portrait
        self.name = name
        self.colour = colour
        self.faction = faction
        self.gold = 0
        # Collected strategic resources such as wood, stone and mana crystals
        self.resources = {name: 0 for name in constants.RESOURCES}
        # Mana available per battle
        self.max_mana = 3
        self.mana = self.max_mana
        # Experience and leveling
        self.exp: int = 0
        self.level: int = 1
        self.skill_points: int = 0
        # Skill tree initialized from manifest
        self.skill_tree: Dict[str, int] = {skill_id: 0 for skill_id in SKILL_CATALOG}
        # Action points for exploration; consumed when moving during your turn
        self.max_ap = 4
        self.ap = self.max_ap
        # Type of boat currently owned/embarked by the hero, if any
        self.naval_unit: Optional[str] = None
        # Starting army; deep copies will be made when entering combat
        self.army: List[Unit] = army if army is not None else []
        # Items carried by the hero
        self.inventory: List[Unit] = []
        # Equipped items mapped by slot name
        self.equipment: Dict[str, Unit] = {}
        # Known spells and their levels
        self.spells: Dict[str, int] = {}
        # Base statistics for the hero
        self.base_stats = base_stats or HeroStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
        # Equipped items for each slot
        self.equipment: Dict[EquipmentSlot, Optional[Item]] = {
            slot: None for slot in EquipmentSlot
        }
        # Bag inventory
        self.inventory: List[Item] = []
        # Additional skill information
        self.tags: List[str] = []
        # Track learned skills per tree/school
        self.learned_skills: Dict[str, Set[str]] = {}
        # Ensure bonuses from skills are applied to the army at creation
        self.apply_bonuses_to_army()

    # Alias required by :class:`UnitCarrier`
    @property
    def units(self) -> List[Unit]:
        return self.army

    @units.setter
    def units(self, value: List[Unit]) -> None:
        self.army = value

    def get_total_stats(self) -> HeroStats:
        """Return hero statistics including bonuses from equipped items."""
        total_dict = asdict(self.base_stats)
        for item in self.equipment.values():
            if item is None:
                continue
            mods = asdict(item.modifiers)
            for key, value in mods.items():
                total_dict[key] += value
        return HeroStats(**total_dict)

    def alive(self) -> bool:
        return any(u.is_alive for u in self.army)

    def reset_ap(self) -> None:
        """Reset the hero's action points at the start of a new exploration turn."""
        self.ap = self.max_ap

    # ------------------------------------------------------------------
    # Experience and skills
    # ------------------------------------------------------------------

    def exp_to_next_level(self) -> int:
        """Experience required to reach the next level."""
        return self.level * 100

    def gain_exp(self, amount: int) -> None:
        """Gain experience and handle level ups."""
        self.exp += amount
        while self.exp >= self.exp_to_next_level():
            self.exp -= self.exp_to_next_level()
            self.level += 1
            self.skill_points += 1
            # Optionally restore mana on level up
            self.mana = self.max_mana

    def apply_bonuses_to_army(self) -> None:
        """Apply current skill bonuses to the hero's army."""
        attack_bonus = self.skill_tree.get("strength", 0)
        initiative_bonus = self.skill_tree.get("tactics", 0)
        for unit in self.army:
            unit.attack_bonus = attack_bonus
            unit.initiative_bonus = initiative_bonus

    def learn_skill(self, node: SkillNode | str, tree: str = "combat") -> bool:
        """Attempt to learn a skill node for a given tree and apply its effects."""
        if isinstance(node, str):
            node = SKILL_CATALOG.get(node)
            if node is None:
                return False
        learned = self.learned_skills.setdefault(tree, set())
        if node.id in learned:
            return False
        if self.skill_points < node.cost:
            return False
        if any(req not in learned for req in node.requires):
            return False
        self.skill_points -= node.cost
        learned.add(node.id)
        for eff in node.effects:
            if isinstance(eff, Modifier):
                current = getattr(self.base_stats, eff.stat, None)
                if current is not None:
                    if eff.mode == "flat":
                        setattr(self.base_stats, eff.stat, current + int(eff.value))
                    else:
                        setattr(
                            self.base_stats,
                            eff.stat,
                            int(current * (1 + eff.value / 100)),
                        )
                else:
                    # Try hero attributes directly (e.g. max_mana)
                    current = getattr(self, eff.stat, None)
                    if current is not None:
                        if eff.mode == "flat":
                            setattr(self, eff.stat, current + int(eff.value))
                        else:
                            setattr(self, eff.stat, int(current * (1 + eff.value / 100)))
            else:
                if eff not in self.tags:
                    self.tags.append(eff)
        self.apply_bonuses_to_army()
        return True

    def refund_skill(self, node: SkillNode | str, tree: str = "combat") -> bool:
        """Refund a learned skill and revert its effects."""
        if isinstance(node, str):
            node = SKILL_CATALOG.get(node)
            if node is None:
                return False
        learned = self.learned_skills.get(tree)
        if not learned or node.id not in learned:
            return False
        learned.remove(node.id)
        self.skill_points += node.cost
        for eff in node.effects:
            if isinstance(eff, Modifier):
                current = getattr(self.base_stats, eff.stat, None)
                if current is not None:
                    if eff.mode == "flat":
                        setattr(self.base_stats, eff.stat, current - int(eff.value))
                    else:
                        setattr(
                            self.base_stats,
                            eff.stat,
                            int(current / (1 + eff.value / 100)),
                        )
                else:
                    current = getattr(self, eff.stat, None)
                    if current is not None:
                        if eff.mode == "flat":
                            setattr(self, eff.stat, current - int(eff.value))
                        else:
                            setattr(self, eff.stat, int(current / (1 + eff.value / 100)))
            else:
                if eff in self.tags:
                    self.tags.remove(eff)
        self.apply_bonuses_to_army()
        return True

    def choose_skill(self, skill: str) -> bool:
        """Spend a skill point to improve a skill.

        Returns True if the skill was applied, False otherwise.
        """
        if self.skill_points <= 0 or skill not in self.skill_tree:
            return False
        self.skill_points -= 1
        self.skill_tree[skill] += 1
        if skill == "strength":
            # Increase attack bonus for all units
            self.apply_bonuses_to_army()
        elif skill == "wisdom":
            # Increase mana for casting spells
            self.max_mana += 1
            self.mana = self.max_mana
        elif skill == "tactics":
            # Improve initiative of all units
            self.apply_bonuses_to_army()
        elif skill == "logistics":
            # Increase action points for exploration
            self.max_ap += 1
            self.ap = self.max_ap
        return True


class EnemyHero(Hero):
    """Represents an AI-controlled hero on the world map."""

    def __init__(
        self,
        x: int,
        y: int,
        army: Optional[List[Unit]] = None,
        colour: Tuple[int, int, int] = constants.RED,
        faction: FactionDef | None = None,
    ) -> None:
        super().__init__(x, y, army, name="ordinateur", colour=colour, faction=faction)
        try:
            import pygame

            portrait_path = os.path.join("assets", constants.IMG_HERO_PORTRAIT)
            self.portrait = pygame.image.load(portrait_path).convert_alpha()
        except Exception:
            try:
                import pygame

                surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
                surf.fill(colour)
                self.portrait = surf
            except Exception:  # pragma: no cover - pygame missing
                self.portrait = None


###########################################################################
# Item definitions
###########################################################################

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
artifacts_manifest = load_artifact_manifest(REPO_ROOT)
ARTIFACT_ICONS: Dict[int, str] = {entry["id"]: entry["image"] for entry in artifacts_manifest}

ARTIFACT_CATALOG: List[Item] = []
for entry in artifacts_manifest:
    mods = entry.get("modifiers", {})
    modifiers = HeroStats(
        pv=mods.get("pv", 0),
        dmg=mods.get("dmg", 0),
        spd=mods.get("spd", 0),
        init=mods.get("init", 0),
        def_melee=mods.get("def_melee", 0),
        def_ranged=mods.get("def_ranged", 0),
        def_magic=mods.get("def_magic", 0),
        moral=mods.get("moral", 0),
        luck=mods.get("luck", 0),
    )
    slot_name = entry.get("slot")
    slot = EquipmentSlot[slot_name] if slot_name else None
    ARTIFACT_CATALOG.append(
        Item(
            id=entry.get("id"),
            name=entry.get("name", f"Artifact {entry.get('id')}") ,
            slot=slot,
            rarity=entry.get("rarity", "common"),
            icon=ARTIFACT_ICONS.get(entry.get("id"), ""),
            stackable=bool(entry.get("stackable", False)),
            qty=int(entry.get("qty", 1)),
            modifiers=modifiers,
        )
    )

STARTING_ARTIFACTS = ARTIFACT_CATALOG[:2]

skills_manifest = load_skill_manifest(REPO_ROOT)
SKILL_CATALOG: Dict[str, SkillNode] = {}
for entry in skills_manifest:
    effects: List[Modifier | str] = []
    for eff in entry.get("effects", []):
        if isinstance(eff, dict):
            effects.append(
                Modifier(
                    stat=eff.get("stat", ""),
                    value=eff.get("value", 0),
                    mode=eff.get("mode", "flat"),
                )
            )
        else:
            effects.append(eff)
    node = SkillNode(
        id=entry.get("id"),
        name=entry.get("name", entry.get("id")),
        desc=entry.get("desc", ""),
        cost=int(entry.get("cost", 1)),
        requires=entry.get("requires", []),
        effects=effects,
        icon=entry.get("icon", entry.get("image", "")),
        branch=entry.get("branch", ""),
        rank=entry.get("rank", ""),
        coords=tuple(entry.get("coords", [])) if entry.get("coords") else None,
    )
    SKILL_CATALOG[node.id] = node

###########################################################################
# Unit type definitions
###########################################################################

SWORDSMAN_STATS = UnitStats(
    name="Swordsman",
    max_hp=40,
    attack_min=4,
    attack_max=6,
    defence_melee=3,
    defence_ranged=3,
    defence_magic=0,
    speed=3,
    attack_range=1,
    initiative=5,
    sheet="units",
    hero_frames=(0, 0),
    enemy_frames=(3, 3),
    min_range=1,
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=["shield_block"],
    role="Sturdy melee combatant for the front line",
    unit_type="non-magic",
    mana=1,
)

ARCHER_STATS = UnitStats(
    name="Archer",
    max_hp=25,
    attack_min=3,
    attack_max=5,
    defence_melee=2,
    defence_ranged=2,
    defence_magic=0,
    speed=3,
    attack_range=3,
    min_range=2,
    initiative=7,
    sheet="units",
    hero_frames=(1, 1),
    enemy_frames=(4, 4),
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=["focus"],
    role="Mobile shooter, effective against low-Def. range targets",
    unit_type="non-magic",
    mana=1,
)

MAGE_STATS = UnitStats(
    name="Mage",
    max_hp=20,
    attack_min=5,
    attack_max=8,
    defence_melee=1,
    defence_ranged=1,
    defence_magic=0,
    speed=3,
    attack_range=4,
    min_range=1,
    initiative=6,
    sheet="units",
    hero_frames=(2, 2),
    enemy_frames=(5, 5),
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=["fireball", "chain_lightning", "ice_wall"],
    role="Versatile spellcaster wielding powerful magic",
    unit_type="magic",
    mana=10,
)

CAVALRY_STATS = UnitStats(
    name="Cavalry",
    max_hp=50,
    attack_min=6,
    attack_max=9,
    defence_melee=4,
    defence_ranged=4,
    defence_magic=0,
    speed=5,
    attack_range=1,
    min_range=1,
    initiative=8,
    sheet="units",
    hero_frames=(0, 0),
    enemy_frames=(0, 0),
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=["charge"],
    role="Fast attacker that excels at charging",
    unit_type="non-magic",
    mana=1,
)

DRAGON_STATS = UnitStats(
    name="Dragon",
    max_hp=200,
    attack_min=10,
    attack_max=10,
    defence_melee=8,
    defence_ranged=8,
    defence_magic=0,
    speed=4,
    attack_range=1,
    min_range=1,
    initiative=9,
    sheet="units",
    hero_frames=(0, 0),
    enemy_frames=(0, 0),
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=["flying", "multi_shot", "dragon_breath"],
    role="Flying powerhouse with devastating breath",
    unit_type="magic",
    mana=5,
)

PRIEST_STATS = UnitStats(
    name="Priest",
    max_hp=30,
    attack_min=4,
    attack_max=6,
    defence_melee=2,
    defence_ranged=2,
    defence_magic=0,
    speed=3,
    attack_range=3,
    min_range=1,
    initiative=7,
    sheet="units",
    hero_frames=(0, 0),
    enemy_frames=(0, 0),
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=["passive_heal", "heal"],
    role="Support caster able to heal allies",
    unit_type="magic",
    mana=10,
)

# Units that can be recruited in towns
RECRUITABLE_UNITS: Dict[str, UnitStats] = {
    SWORDSMAN_STATS.name: SWORDSMAN_STATS,
    ARCHER_STATS.name: ARCHER_STATS,
    MAGE_STATS.name: MAGE_STATS,
    CAVALRY_STATS.name: CAVALRY_STATS,
    DRAGON_STATS.name: DRAGON_STATS,
    PRIEST_STATS.name: PRIEST_STATS,
}


###########################################################################
# Creatures type definitions
###########################################################################

# Lézard Fumerolle — faible, rapide, affinité feu
FUMEROLLE_LIZARD_STATS = UnitStats(
    name="fumet_lizard",
    max_hp=22,
    attack_min=3,
    attack_max=5,
    defence_melee=2,
    defence_ranged=1,
    defence_magic=2,          # résistance feu via ability
    speed=4,
    attack_range=1,           # attaque de base en mêlée (crachat via ability)
    initiative=7,
    sheet="creatures",
    hero_frames=(0, 0),
    enemy_frames=(0, 0),
    min_range=1,
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=[
        "ember_spit(2, fire, cd=2)",      # petit projectile feu à 2 cases
        "fire_resistance(25%)",           # -25% dégâts feu reçus
        "heated_scales(burn_on_hit=20%)"  # 20% chance d’infliger Brûlure aux assaillants de mêlée
    ],
    role="Skirmisher rapide, harcèlement feu à courte portée",
    unit_type="beast-elemental",
    mana=1,
)

# Ombreloup des feuilles — faible, très mobile, embuscade
SHADOWLEAF_WOLF_STATS = UnitStats(
    name="shadowleaf_wolf",
    max_hp=28,
    attack_min=4,
    attack_max=6,
    defence_melee=2,
    defence_ranged=3,         # esquive meilleure vs projectiles
    defence_magic=1,
    speed=5,
    attack_range=1,
    initiative=8,
    sheet="creatures",
    hero_frames=(0, 0),
    enemy_frames=(0, 0),
    min_range=1,
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=[
        "pounce(bleed=2, bonus_vs_flanked)",    # bond : saignement léger + bonus si cible flanquée
        "forest_camouflage(+20% evade_in_forest)",
        "stalk(first_strike_if_undetected)"     # si non repéré ce tour, frappe d’abord
    ],
    role="Assassin de brousse, projection/embuscade",
    unit_type="beast",
    mana=0,
)

# Corbeau sanglier — plus fort, heurte/renverse
BOAR_RAVEN_STATS = UnitStats(
    name="boar_raven",
    max_hp=60,
    attack_min=7,
    attack_max=10,
    defence_melee=4,
    defence_ranged=3,
    defence_magic=1,
    speed=4,
    attack_range=1,
    initiative=6,
    sheet="creatures",
    hero_frames=(0, 0),
    enemy_frames=(0, 0),
    min_range=1,
    retaliations_per_round=1,
    morale=1,                 # un cran au-dessus
    luck=0,
    abilities=[
        "gore_charge(+50% dmg after_move>=2, knockback=1)",
        "thick_hide(-20% melee_damage_taken)",
        "scavenge_on_kill(heal=6)"            # se soigne légèrement après élimination
    ],
    role="Briseur de ligne, charge et repousser",
    unit_type="beast",
    mana=0,
)

# Hurlombe — faible en PV, esprit volant, cri terrifiant
HURLOMBE_STATS = UnitStats(
    name="hurlombe",
    max_hp=24,
    attack_min=4,
    attack_max=5,
    defence_melee=1,
    defence_ranged=2,
    defence_magic=4,          # esprit : bonne résistance magique
    speed=5,                  # vole/plane
    attack_range=1,
    initiative=9,
    sheet="creatures",
    hero_frames=(0, 0),
    enemy_frames=(0, 0),
    min_range=1,
    retaliations_per_round=1,
    morale=0,
    luck=0,
    abilities=[
        "wail(2, mind, fear=-1_morale, cd=2)",  # cri à 2 cases : -1 morale (test de peur)
        "incorporeal(20% miss_physical)",       # chance d’esquive « spectrale » vs physique
        "hover(ignore_terrain_penalties)"       # survole le terrain difficile
    ],
    role="Contrôle mental léger, harcèlement mobile",
    unit_type="undead-spirit",
    mana=2,
)


def create_random_enemy_army() -> List[Unit]:
    """Generate a random selection of enemy units for the world map."""
    stats_choices = list(RECRUITABLE_UNITS.values())
    num_stacks = random.randint(1, 3)
    units: List[Unit] = []
    for _ in range(num_stacks):
        stats = random.choice(stats_choices)
        count = random.randint(5, 12)
        units.append(Unit(stats, count, side="enemy"))
    return units
