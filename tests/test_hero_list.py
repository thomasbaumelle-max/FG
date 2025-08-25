from types import SimpleNamespace

import pygame

from ui.widgets.hero_list import HeroList, MOUSEBUTTONDOWN, MOUSEWHEEL
from state.event_bus import EVENT_BUS, ON_SELECT_HERO


class DummyRenderer:
    def __init__(self):
        self.centered = None

    def center_on(self, tile):
        self.centered = tile


class DummyHero:
    def __init__(self, name, x, y, ap):
        self.name = name
        self.x = x
        self.y = y
        self.ap = ap
        self.army = []

    # ``Hero`` exposes units via the ``units`` property in real code
    @property
    def units(self):
        return self.army

    def apply_bonuses_to_army(self):
        pass


class DummyArmy:
    def __init__(self, name, x, y, ap, portrait=None):
        self.name = name
        self.x = x
        self.y = y
        self.ap = ap
        self.portrait = portrait
        self.units = []

    def apply_bonuses_to_army(self):
        pass


def make_heroes(n=6):
    return [DummyHero(f"H{i}", i, i + 1, i * 2) for i in range(n)]


def test_hero_list_scroll_and_select():
    renderer = DummyRenderer()
    widget = HeroList(renderer=renderer)
    heroes = make_heroes(6)
    widget.set_heroes(heroes)
    rect = pygame.Rect(0, 0, 100, HeroList.MAX_VISIBLE * (HeroList.CARD_SIZE + HeroList.PADDING))

    # Click the second hero
    card = widget._card_rect(1, rect)
    pos_mid = (card.x + card.width // 2, card.y + card.height // 2)
    evt = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=pos_mid, button=1)
    widget.handle_event(evt, rect)
    assert widget.selected_index == 1
    assert renderer.centered == (1, 2)

    # Scroll down using mouse wheel to reveal last hero
    evt_scroll = SimpleNamespace(type=MOUSEWHEEL, y=-1)
    widget.handle_event(evt_scroll, rect)
    assert widget.scroll == 1

    # Click the last visible hero (index 5)
    card_last = widget._card_rect(4, rect)
    pos_last = (card_last.x + card_last.width // 2, card_last.y + card_last.height // 2)
    evt2 = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=pos_last, button=1)
    widget.handle_event(evt2, rect)
    assert widget.selected_index == 5
    assert renderer.centered == (5, 6)

    # Tooltip for hovered hero
    tip = widget.get_tooltip(pos_last, rect)
    assert "H5" in tip and "(5, 6)" in tip and "Go to" in tip


def test_army_selection_publishes_event_and_displays_info():
    portrait = pygame.Surface((HeroList.CARD_SIZE, HeroList.CARD_SIZE))
    army = DummyArmy("A", 0, 0, 3, portrait=portrait)
    widget = HeroList()
    widget.set_heroes([army])
    assert widget._heroes[0].portrait is portrait

    class DummyFont:
        def __init__(self):
            self.texts = []

        def render(self, text, aa, colour):
            self.texts.append(text)
            return pygame.Surface((1, 1))

    widget.font = DummyFont()
    rect = pygame.Rect(0, 0, 100, HeroList.CARD_SIZE)
    surface = pygame.Surface((100, HeroList.CARD_SIZE))
    widget.draw(surface, rect)
    assert str(army.ap) in widget.font.texts

    selected = []

    def on_select(hero):
        selected.append(hero)

    EVENT_BUS.subscribe(ON_SELECT_HERO, on_select)
    card = widget._card_rect(0, rect)
    pos = (card.x + card.width // 2, card.y + card.height // 2)
    evt = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=pos, button=1)
    widget.handle_event(evt, rect)
    assert selected == [army]
