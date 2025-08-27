from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, Set, List, Tuple

import constants
from loaders import building_loader
from loaders.building_loader import BuildingAsset
from loaders.core import Context
from loaders.town_building_loader import load_faction_town_buildings

if TYPE_CHECKING:  # pragma: no cover
    from core.entities import Hero, Unit
    from core import economy
    from core.world import WorldMap


@dataclass
class Caravan:
    """Représente un convoi de troupes se dirigeant vers une autre ville."""

    dest: "Town"
    units: List["Unit"]
    remaining: int


class Building:
    """Base class for world map buildings (resource nodes, towns…)."""

    id: str = ""
    name: str = "Building"
    image: str = ""
    income: Dict[str, int] = {}
    level: int = 1
    upgrade_cost: Dict[str, int] = {}
    production_per_level: Dict[str, int] = {}

    def __init__(self) -> None:
        self.id = ""
        self.owner: Optional[int] = None
        self.footprint: List[Tuple[int, int]] = [(0, 0)]
        self.anchor: Tuple[int, int] = (constants.TILE_SIZE // 2, constants.TILE_SIZE)
        self.passable: bool = False
        self.occludes: bool = True
        self.origin: Tuple[int, int] = (0, 0)
        self.garrison: List["Unit"] = []
        self.growth_per_week: Dict[str, int] = {}
        self.stock: Dict[str, int] = {}
        self.level = 1
        self.upgrade_cost = {}
        self.production_per_level = {}
        self.requires: List[str] = []

    def interact(self, hero: "Hero") -> None:
        self.owner = 0
        for res in self.income:
            hero.resources[res] = hero.resources.get(res, 0) + 5

    def upgrade(self, hero: "Hero", econ_building: Optional["economy.Building"] = None) -> bool:
        """Upgrade the building if ``hero`` can afford it.

        The hero's resources are deducted according to ``upgrade_cost`` and the
        building's level and income are increased based on
        ``production_per_level``.  When ``econ_building`` is provided, the
        associated economy state is kept in sync.
        """

        if not self.upgrade_cost:
            return False
        # Verify resources
        for res, amt in self.upgrade_cost.items():
            if res == "gold":
                if hero.gold < amt:
                    return False
            elif hero.resources.get(res, 0) < amt:
                return False
        # Deduct cost
        hero.gold -= self.upgrade_cost.get("gold", 0)
        for res, amt in self.upgrade_cost.items():
            if res == "gold":
                continue
            hero.resources[res] = hero.resources.get(res, 0) - int(amt)
        self.level += 1
        if self.production_per_level:
            self.income = {
                res: val * self.level for res, val in self.production_per_level.items()
            }
        if econ_building is not None:
            econ_building.level = self.level
            if self.production_per_level:
                econ_building.provides = dict(self.income)
        return True


class Shipyard(Building):
    """Allows heroes to acquire and upgrade boats for naval travel."""

    def __init__(self) -> None:
        super().__init__()
        path = os.path.join(os.path.dirname(__file__), "..", "assets", "boats.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.boats = [entry.get("id", "") for entry in data if isinstance(entry, dict)]
        except Exception:
            self.boats = ["barge"]

    def interact(self, hero: "Hero") -> None:
        if hero.naval_unit is None and getattr(self, "boats", None):
            index = min(self.level - 1, len(self.boats) - 1)
            hero.naval_unit = self.boats[index]


class SeaSanctuary(Building):
    """Building that revives a fallen unit stack when visited."""

    def interact(self, hero: "Hero") -> None:
        super().interact(hero)
        for unit in hero.army:
            if unit.count <= 0:
                unit.count = 1
                unit.current_hp = unit.stats.max_hp
                break


class Lighthouse(Building):
    """Grants a vision range bonus to the visiting hero."""

    def interact(self, hero: "Hero") -> None:
        super().interact(hero)
        current = getattr(hero, "vision_bonus", 0)
        hero.vision_bonus = max(current, 2)

def create_building(bid: str, defs: Optional[Dict[str, BuildingAsset]] = None) -> Building:
    asset = (defs or building_loader.BUILDINGS)[bid]
    b: Building
    if bid == "shipyard":
        b = Shipyard()
    elif bid == "sea_sanctuary":
        b = SeaSanctuary()
    elif bid == "lighthouse":
        b = Lighthouse()
    else:
        b = Building()
    b.id = asset.id
    b.name = asset.id.replace("_", " ").title()
    files = asset.file_list()
    b.image = files[0] if files else asset.id
    if asset.provides and isinstance(asset.provides, dict):
        res = asset.provides.get("resource")
        per_day = int(asset.provides.get("per_day", 0))
        b.production_per_level = {res: per_day} if res else {}
    else:
        b.production_per_level = {}
    b.level = 1
    b.income = {
        res: val * b.level for res, val in b.production_per_level.items()
    }
    b.upgrade_cost = dict(getattr(asset, "upgrade_cost", {}))
    b.footprint = [tuple(p) for p in asset.footprint]
    scale = getattr(asset, "scale", 1.0)
    ax, ay = asset.anchor_px
    b.anchor = (int(ax * scale), int(ay * scale))
    b.passable = bool(asset.passable)
    b.occludes = bool(asset.occludes)
    b.growth_per_week = dict(getattr(asset, "growth_per_week", {}))
    b.requires = list(getattr(asset, "requires", []))
    return b


def register_faction_buildings(ctx: Context, manifests: List[str]) -> None:
    """Register additional buildings defined for specific factions."""

    for path in manifests:
        building_loader.register_buildings(ctx, path)


class Town(Building):
    """Town (city) providing recruitment & buildings management."""

    image = "town"
    _counter = 0

    def __init__(self, name: Optional[str] = None, faction_id: Optional[str] = None) -> None:
        super().__init__()
        self.faction_id = faction_id
        if name is None:
            Town._counter += 1
            self.name = f"Town {Town._counter}"
        else:
            self.name = name

        path = os.path.join(os.path.dirname(__file__), "..", "assets", "town_buildings.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # pragma: no cover - fallback if file missing
            data = []

        self.structures: Dict[str, Dict[str, object]] = {}
        order: List[str] = []
        for entry in data:
            sid = entry.get("id")
            if not sid:
                continue
            order.append(sid)
            self.structures[sid] = {
                "cost": entry.get("cost", {}),
                "desc": entry.get("desc", ""),
                "prereq": entry.get("prereq", []),
                "image": entry.get("image", ""),
                # dwelling dict: {unit_id: growth_per_week}
                "dwelling": entry.get("dwelling", {}),
            }
        self.ui_order = order

        if faction_id:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            ctx = Context(
                repo_root=repo_root,
                search_paths=[os.path.join(repo_root, "assets")],
                asset_loader=None,
            )
            extras = load_faction_town_buildings(ctx, faction_id)
            for sid, info in extras.items():
                self.structures[sid] = info
                self.ui_order.append(sid)

        # Tavern is present by default in every town
        self.built_structures: Set[str] = {"tavern"}
        self.garrison: List["Unit"] = []
        self.stock: Dict[str, int] = {}

        # File d'ordres pour les caravanes en transit
        self.caravan_orders: List[Caravan] = []

        DEFAULT_MARKET_RATES = {
            ("gold", "wood"): 100,
            ("gold", "stone"): 100,
            ("gold", "crystal"): 250,
            ("wood", "gold"): 8,
            ("stone", "gold"): 8,
            ("crystal", "gold"): 25,
        }
        self.market_rates = getattr(constants, "MARKET_RATES", DEFAULT_MARKET_RATES)
        self.built_today = False

    # ------------------------------ Helpers UI ------------------------------
    def is_structure_built(self, name: str) -> bool:
        return name in self.built_structures

    def structure_cost(self, name: str) -> Dict[str, int]:
        info = self.structures.get(name, {})
        return dict(info.get("cost", {})) if isinstance(info, dict) else {}

    def recruitable_units(self, name: str) -> List[str]:
        info = self.structures.get(name)
        growth = {}
        reqs: List[str] = []
        if isinstance(info, dict):
            growth = info.get("dwelling", {})
            r = info.get("requires", [])
            if isinstance(r, list):
                reqs.extend(r)
        asset = building_loader.BUILDINGS.get(name)
        if asset is not None:
            if not growth:
                growth = getattr(asset, "growth_per_week", {})
            reqs.extend(getattr(asset, "requires", []))
        if any(r not in self.built_structures for r in reqs):
            return []
        if isinstance(growth, dict):
            return list(growth.keys())
        return list(growth) if isinstance(growth, list) else []

    def available_units(self, name: str) -> Dict[str, int]:
        info = self.structures.get(name, {})
        growth = info.get("dwelling", {}) if isinstance(info, dict) else {}
        if not isinstance(growth, dict):
            return {}
        return {uid: self.stock.get(uid, 0) for uid in growth.keys()}

    def list_all_recruitables(self) -> List[str]:
        """Toutes les unités débloquées par les structures construites."""
        out: List[str] = []
        for s in self.built_structures:
            out.extend(self.recruitable_units(s))
        # ordre stable + sans doublons
        seen = set()
        ordered = []
        for u in out:
            if u not in seen:
                ordered.append(u)
                seen.add(u)
        return ordered

    # --------------------------- Caravan management ------------------------
    def send_caravan(
        self,
        dest: "Town",
        units: List["Unit"],
        world: Optional["WorldMap"] = None,
    ) -> bool:
        """Créer une caravane vers ``dest`` transportant ``units``.

        Les unités sont retirées de la garnison locale et voyageront un nombre
        de jours correspondant à la distance de Manhattan entre les villes.
        """

        if not units:
            return False
        # Retire de la garnison les unités envoyées
        sent: List["Unit"] = []
        for u in units:
            if u in self.garrison:
                self.garrison.remove(u)
                sent.append(u)
        if not sent:
            return False

        distance = 1
        if world is not None:
            from_pos = world.find_building_pos(self)
            to_pos = world.find_building_pos(dest)
            if from_pos and to_pos:
                distance = abs(from_pos[0] - to_pos[0]) + abs(from_pos[1] - to_pos[1])
                if distance <= 0:
                    distance = 1
        self.caravan_orders.append(Caravan(dest, sent, distance))
        return True

    def advance_day(self) -> None:
        """Fait progresser les caravanes d'une journée et fusionne à l'arrivée."""

        arrived: List[Caravan] = []
        for order in self.caravan_orders:
            order.remaining -= 1
            if order.remaining <= 0:
                order.dest.garrison.extend(order.units)
                arrived.append(order)
        for order in arrived:
            self.caravan_orders.remove(order)
        self.built_today = False

    # --------------------------- Town management ----------------------------
    def build_structure(
        self,
        structure: str,
        hero: "Hero",
        econ_building: Optional["economy.Building"] = None,
    ) -> bool:
        info = self.structures.get(structure)
        if (
            info is None
            or structure in self.built_structures
            or self.built_today
            or (econ_building is not None and econ_building.construction_done)
        ):
            return False
        prereq = info.get("prereq", []) if isinstance(info, dict) else []
        if any(p not in self.built_structures for p in prereq):
            return False
        cost: Dict[str, int] = info.get("cost", {})  # type: ignore[assignment]
        for res, amount in cost.items():
            if res == "gold":
                if hero.gold < amount:
                    return False
            elif hero.resources.get(res, 0) < amount:
                return False
        # pay
        hero.gold -= cost.get("gold", 0)
        for res, amount in cost.items():
            if res == "gold":
                continue
            hero.resources[res] = hero.resources.get(res, 0) - amount
        self.built_structures.add(structure)
        self.built_today = True
        if econ_building is not None:
            from core import economy as econ
            econ.build_structure(econ_building, structure)
        growth = info.get("dwelling", {}) if isinstance(info, dict) else {}
        if isinstance(growth, dict):
            for uid, amount in growth.items():
                self.stock[uid] = self.stock.get(uid, 0) + int(amount)
        return True

    def recruit_units(
        self,
        unit_type: str,
        hero: "Hero",
        count: int = 1,
        target_units: Optional[List["Unit"]] = None,
    ) -> bool:
        """Recruit ``count`` units of type ``unit_type``.

        Parameters
        ----------
        unit_type:
            Identifier of the unit to recruit.
        hero:
            Hero paying for the recruitment.  Resources are always deducted
            from this hero regardless of ``target_units``.
        count:
            Number of units to recruit.
        target_units:
            List of :class:`Unit` stacks where the recruited units should be
            added.  When ``None`` (default) the units are added to the town
            garrison.
        """

        unlocked = set(self.list_all_recruitables())
        if unit_type not in unlocked:
            return False

        available = self.stock.get(unit_type, 0)
        if available < count:
            return False

        cost_all = getattr(constants, "UNIT_RECRUIT_COSTS", {})
        base = cost_all.get(unit_type, {})
        gold_cost = int(base.get("gold", 0)) * count
        if hero.gold < gold_cost:
            return False
        for res, amount in base.items():
            if res == "gold":
                continue
            if hero.resources.get(res, 0) < amount * count:
                return False
        # pay
        hero.gold -= gold_cost
        for res, amount in base.items():
            if res == "gold":
                continue
            hero.resources[res] = hero.resources.get(res, 0) - amount * count

        from core.entities import Unit, RECRUITABLE_UNITS  # late import to avoid cycles
        stats = RECRUITABLE_UNITS.get(unit_type)
        if stats is None:
            return False

        dest = target_units if target_units is not None else self.garrison
        for stack in dest:
            if stack.stats is stats:
                stack.count += count
                break
        else:
            dest.append(Unit(stats, count, "hero"))

        if dest is hero.army:
            hero.apply_bonuses_to_army()

        self.stock[unit_type] = available - count
        return True

    # ----------------------------- Garrison I/O -----------------------------
    def transfer_to_garrison(self, hero: "Hero", index: int) -> bool:
        if not (0 <= index < len(hero.army)):
            return False
        unit = hero.army[index]
        for g in self.garrison:
            if g.stats is unit.stats:
                g.count += unit.count
                hero.army.pop(index)
                return True
        if len(self.garrison) >= 7:
            return False
        self.garrison.append(hero.army.pop(index))
        return True

    def transfer_from_garrison(self, hero: "Hero", index: int) -> bool:
        if not (0 <= index < len(self.garrison)):
            return False
        unit = self.garrison[index]
        for h in hero.army:
            if h.stats is unit.stats:
                h.count += unit.count
                self.garrison.pop(index)
                hero.apply_bonuses_to_army()
                return True
        if len(hero.army) >= 7:
            return False
        hero.army.append(self.garrison.pop(index))
        hero.apply_bonuses_to_army()
        return True

    def next_week(self) -> None:
        for s in self.built_structures:
            info = self.structures.get(s, {})
            growth = info.get("dwelling", {}) if isinstance(info, dict) else {}
            if isinstance(growth, dict):
                for uid, amount in growth.items():
                    self.stock[uid] = self.stock.get(uid, 0) + int(amount)

    def recruit(self, player: "economy.PlayerEconomy") -> None:
        """Recruit available units into the garrison using player resources.

        This helper is primarily used by the AI which relies on
        :class:`economy.PlayerEconomy` to track its resource pool.  It will
        purchase as many units as possible from the town's ``stock`` and add
        them to the local ``garrison``.
        """

        from core.entities import Unit, RECRUITABLE_UNITS  # late import
        from core import economy

        cost_all = getattr(constants, "UNIT_RECRUIT_COSTS", {})
        for unit_id in self.list_all_recruitables():
            available = int(self.stock.get(unit_id, 0))
            if available <= 0:
                continue

            base_cost = cost_all.get(unit_id, {})
            max_count = available
            for res, amount in base_cost.items():
                if amount <= 0:
                    continue
                res_amt = player.resources.get(res, 0)
                max_count = min(max_count, res_amt // int(amount))
            if max_count <= 0:
                continue

            total_cost = {k: int(v) * max_count for k, v in base_cost.items()}
            economy.pay(player, total_cost)

            stats = RECRUITABLE_UNITS.get(unit_id)
            if stats is None:
                continue
            for g in self.garrison:
                if g.stats is stats:
                    g.count += max_count
                    break
            else:
                self.garrison.append(Unit(stats, max_count, "enemy"))

            self.stock[unit_id] = available - max_count

    # ------------------------------- Market ---------------------------------
    def can_trade(self, give_res: str, take_res: str, amount_take: int, hero: "Hero") -> bool:
        rate = self.market_rates.get((give_res, take_res))
        if rate is None or amount_take <= 0:
            return False
        # coût à payer dans give_res
        cost = rate * amount_take
        if give_res == "gold":
            return hero.gold >= cost
        return hero.resources.get(give_res, 0) >= cost

    def trade(self, give_res: str, take_res: str, amount_take: int, hero: "Hero") -> bool:
        """Échange amount_take de take_res contre give_res selon les taux."""
        rate = self.market_rates.get((give_res, take_res))
        if rate is None or amount_take <= 0:
            return False
        cost = rate * amount_take
        # payer
        if give_res == "gold":
            if hero.gold < cost: 
                return False
            hero.gold -= cost
        else:
            if hero.resources.get(give_res, 0) < cost:
                return False
            hero.resources[give_res] = hero.resources.get(give_res, 0) - cost
        # recevoir
        if take_res == "gold":
            hero.gold += amount_take
        else:
            hero.resources[take_res] = hero.resources.get(take_res, 0) + amount_take
        return True
