from core.combat_render import handle_button_click


class DummyRect:
    def __init__(self, x=0, y=0, w=10, h=10):
        self.x, self.y, self.w, self.h = x, y, w, h

    def collidepoint(self, px, py):
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h


class DummyCombat:
    def __init__(self, hero_spells):
        self.action_buttons = {"spellbook": DummyRect(0, 0, 10, 10)}
        self.auto_button = None
        self.auto_mode = False
        self.selected_action = None
        self.hero_spells = hero_spells
        self.show_called = False

    def show_spellbook(self):
        self.show_called = True

    def advance_turn(self):
        pass


class DummyUnit:
    acted = False


def test_spellbook_opens_when_spells():
    combat = DummyCombat({"fire": object()})
    current_unit = DummyUnit()
    assert handle_button_click(combat, current_unit, (5, 5))
    assert combat.show_called


def test_spellbook_ignored_when_empty():
    combat = DummyCombat({})
    current_unit = DummyUnit()
    assert not handle_button_click(combat, current_unit, (5, 5))
    assert not combat.show_called
