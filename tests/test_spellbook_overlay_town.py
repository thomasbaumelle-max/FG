from types import SimpleNamespace


def _make_event(t, **kw):
    return SimpleNamespace(type=t, **kw)


def test_town_mode_tabs(pygame_stub):
    pygame = pygame_stub(MOUSEBUTTONDOWN=1, KEYDOWN=2)
    import importlib
    import theme as theme_module
    importlib.reload(theme_module)
    import ui.spellbook_overlay as sb
    importlib.reload(sb)
    SpellbookOverlay = sb.SpellbookOverlay

    screen = pygame.Surface((200, 200))
    overlay = SpellbookOverlay(screen, town=True)

    # Initial draw populates tab rectangles
    overlay.draw()
    assert overlay.categories
