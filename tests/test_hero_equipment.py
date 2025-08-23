from core.entities import EquipmentSlot, Hero, HeroStats, Item


def test_get_total_stats_with_equipment():
    base = HeroStats(10, 5, 3, 2, 1, 2, 3, 1, 1)
    hero = Hero(0, 0, [], base_stats=base)
    helmet = Item(
        id=1,
        name="Helmet",
        slot=EquipmentSlot.HEAD,
        rarity="common",
        icon="",
        stackable=False,
        qty=1,
        modifiers=HeroStats(2, 1, 0, 0, 0, 0, 0, 0, 0),
    )
    hero.equipment[EquipmentSlot.HEAD] = helmet
    total = hero.get_total_stats()
    assert total == HeroStats(12, 6, 3, 2, 1, 2, 3, 1, 1)
