from types import SimpleNamespace

from core.spell import Spell


class DummyCombat:
    def __init__(self):
        self.hero_spells = {"fireball": 1}
        self.spell_defs = {
            "fireball": Spell(
                id="fireball",
                school="",
                cost_mana=5,
                cooldown=0,
                range=5,
                passive=False,
                data={},
            )
        }


def _make_event(t, **kw):
    return SimpleNamespace(type=t, **kw)


def test_click_spell_opens_info(pygame_stub):
    pygame = pygame_stub(MOUSEBUTTONDOWN=1, KEYDOWN=2)
    pygame.Rect.collidepoint = lambda self, pos: self.x <= pos[0] < self.x + self.width and self.y <= pos[1] < self.y + self.height
    import importlib
    import ui.spell_info_overlay as sio
    import ui.spellbook_overlay as sb
    importlib.reload(sio)
    importlib.reload(sb)
    SpellbookOverlay = sb.SpellbookOverlay
    SpellInfoOverlay = sio.SpellInfoOverlay

    screen = pygame.Surface((200, 200))
    overlay = SpellbookOverlay(screen, DummyCombat())
    overlay.draw()
    rect, name = overlay._label_rects[0]

    closed = overlay.handle_event(
        _make_event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    )
    assert closed is False
    assert isinstance(overlay.info_overlay, SpellInfoOverlay)
    assert overlay.info_overlay.lines == overlay._spell_tooltip(name)
