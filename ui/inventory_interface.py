"""Simple inventory interface managing hero equipment slots."""
from __future__ import annotations

from typing import Optional

from core.entities import Hero, Item, EquipmentSlot


class InventoryInterface:
    """Provide basic operations for equipping and unequipping artifacts."""

    def __init__(self, hero: Hero) -> None:
        self.hero = hero

    def equip(self, item: Item) -> Optional[Item]:
        """Equip ``item`` and return previously equipped artifact, if any."""
        if item.slot is None:
            self.hero.inventory.append(item)
            return None
        previous = self.hero.equipment.get(item.slot)
        self.hero.equipment[item.slot] = item
        if previous is not None:
            self.hero.inventory.append(previous)
        return previous

    def unequip(self, slot: EquipmentSlot) -> Optional[Item]:
        """Unequip artifact from ``slot`` and return it."""
        item = self.hero.equipment.get(slot)
        if item is not None:
            self.hero.inventory.append(item)
            self.hero.equipment[slot] = None
        return item
