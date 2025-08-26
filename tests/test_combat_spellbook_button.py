from core.combat_render import handle_button_click
import pytest


pytestmark = pytest.mark.combat


class DummyCombat:
    def __init__(self, hero_spells):
        import pygame
        from ui.widgets.icon_button import IconButton

        self.hero_spells = hero_spells
        self.show_called = False

        def open_spellbook() -> None:
            if self.hero_spells:
                self.show_called = True

        self.action_buttons = {
            "spellbook": IconButton(
                pygame.Rect(0, 0, 10, 10),
                "action_cast",
                open_spellbook,
                enabled=bool(hero_spells),
            )
        }
        self.auto_button = None
        self.auto_mode = False
        self.selected_action = None

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

