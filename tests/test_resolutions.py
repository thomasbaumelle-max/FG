import pygame
from types import SimpleNamespace
from ui.main_screen import MainScreen


def _dummy_game(width, height):
    surface = SimpleNamespace(get_width=lambda: width, get_height=lambda: height)
    return SimpleNamespace(
        screen=surface,
        offset_x=0,
        offset_y=0,
        zoom=1.0,
        hover_probe=lambda x, y: None,
        _adjust_zoom=lambda delta, pos: None,
    )


def test_layout_16_9_and_16_10():
    game = _dummy_game(1280, 720)
    ms = MainScreen(game)
    assert len(ms.widgets) == 8
    side_w = max(260, int(0.23 * 1280))
    bar_h = 24
    margin = 8
    expected_w = 1280 - side_w - 2 * margin
    expected_h = 720 - 3 * bar_h - 3 * margin
    assert ms.widgets["1"].width == expected_w
    assert ms.widgets["1"].height == expected_h
    # hero list and buttons are the same height and directly adjacent
    hero_rect = ms.widgets["5"]
    buttons_rect = ms.widgets["6"]
    assert hero_rect.height == buttons_rect.height
    assert hero_rect.x + hero_rect.width == buttons_rect.x
    assert hero_rect.y == buttons_rect.y
    # Recompute for 16:10
    ms.compute_layout(1280, 800)
    expected_h = 800 - 3 * bar_h - 3 * margin
    assert ms.widgets["1"].height == expected_h


def test_buttons_stack_when_short_height():
    game = _dummy_game(1280, 600)
    ms = MainScreen(game)
    hero_rect = ms.widgets["5"]
    buttons_rect = ms.widgets["6"]
    army_rect = ms.widgets["7"]
    # Buttons should move below the army panel
    assert buttons_rect.y == army_rect.bottom
    assert buttons_rect.width == hero_rect.width
    expected_h = len(ms.buttons.buttons) * ms.buttons.BUTTON_SIZE[1] + (
        len(ms.buttons.buttons) - 1
    ) * ms.buttons.PADDING
    assert buttons_rect.height == expected_h
