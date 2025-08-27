import pygame
from types import SimpleNamespace

from core.spell import Spell
from loaders.i18n import load_locale
import settings


class DummyCombat:
    def __init__(self):
        self.hero_spells = {f"spell{i}": 1 for i in range(12)}
        self.spell_defs = {
            f"spell{i}": Spell(
                id=f"spell{i}",
                school="", cost_mana=i,
                cooldown=i % 3, range=5,
                passive=False, data={}
            )
            for i in range(12)
        }


def _make_event(t, **kw):
    return SimpleNamespace(type=t, **kw)


def test_pagination_and_tooltip(pygame_stub):
    pygame = pygame_stub(KEYDOWN=1, MOUSEBUTTONDOWN=2, K_RIGHT=3, K_LEFT=4,
                         K_s=5, K_ESCAPE=6, K_PAGEDOWN=7, K_PAGEUP=8)
    from ui.spellbook_overlay import SpellbookOverlay
    screen = pygame.Surface((200, 200))
    combat = DummyCombat()
    overlay = SpellbookOverlay(screen, combat)

    assert overlay.num_pages == 2
    overlay.handle_event(_make_event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert overlay.page == 1
    overlay.handle_event(_make_event(pygame.MOUSEBUTTONDOWN, button=4))
    assert overlay.page == 0

    strings = load_locale(settings.LANGUAGE)
    lines = overlay._spell_tooltip("spell1")
    assert any(strings.get("Mana", "Mana") in ln for ln in lines)
    assert any(strings.get("Cooldown", "Cooldown") in ln for ln in lines)
