from core.entities import EquipmentSlot, Hero, HeroStats, Item


def test_equip_swap():
    base = HeroStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
    hero = Hero(0, 0, [], base_stats=base)
    helm_a = Item(
        id=1,
        name="A",
        slot=EquipmentSlot.HEAD,
        rarity="common",
        icon="",
        stackable=False,
        qty=1,
        modifiers=HeroStats(0, 1, 0, 0, 0, 0, 0, 0, 0),
    )
    helm_b = Item(
        id=2,
        name="B",
        slot=EquipmentSlot.HEAD,
        rarity="common",
        icon="",
        stackable=False,
        qty=1,
        modifiers=HeroStats(0, 3, 0, 0, 0, 0, 0, 0, 0),
    )
    hero.equipment[EquipmentSlot.HEAD] = helm_a
    hero.inventory.append(helm_b)

    prev = hero.equipment.get(helm_b.slot)
    hero.equipment[helm_b.slot] = helm_b
    del hero.inventory[0]
    if prev:
        hero.inventory.append(prev)

    assert hero.equipment[EquipmentSlot.HEAD] is helm_b
    assert hero.inventory == [helm_a]
    total = hero.get_total_stats()
    assert total.dmg == 3
