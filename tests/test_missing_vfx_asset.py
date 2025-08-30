from core.spell import _trigger_fx
from core.fx import FXQueue, FXEvent


def test_trigger_fx_missing_asset(asset_manager):
    queue = FXQueue()
    _trigger_fx(queue, asset_manager, "missing_fx", (0, 0))
    assert len(queue._events) == 1
    event = queue._events[0]
    assert isinstance(event, FXEvent)


def test_combat_show_effect_missing_asset(asset_manager, simple_combat):
    combat = simple_combat(assets=asset_manager)
    combat.show_effect("missing_fx", (0, 0))
    assert len(combat.fx_queue._events) == 1
    event = combat.fx_queue._events[0]
    assert isinstance(event, FXEvent)
