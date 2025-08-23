from types import SimpleNamespace

import pygame

from state.game_state import GameCalendar
from ui.widgets.turn_bar import TurnBar, MOUSEBUTTONDOWN


def test_game_calendar_conversion():
    cal = GameCalendar()
    assert (cal.month, cal.week, cal.day) == (1, 1, 1)
    cal.turn_index = 27
    assert (cal.month, cal.week, cal.day) == (1, 4, 7)
    cal.turn_index = 28
    assert (cal.month, cal.week, cal.day) == (2, 1, 1)


def test_turn_bar_animation_and_click():
    cal = GameCalendar()
    clicked: list[str] = []

    def on_click(calendar: GameCalendar) -> None:
        clicked.append(calendar.label())

    bar = TurnBar(cal, on_click=on_click)
    rect = pygame.Rect(0, 0, 100, 20)
    surf = pygame.Surface((100, 20))

    # Draw should not raise and display current label
    bar.draw(surf, rect)

    # Trigger end turn animation
    bar.on_turn_end()
    assert bar._flash_time > 0
    bar.update(0.25)
    assert 0 < bar._flash_time < 0.5
    bar.update(1.0)
    assert bar._flash_time == 0

    # Click inside the bar
    event = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=(10, 10), button=1)
    assert bar.handle_event(event, rect)
    assert clicked and clicked[0] == cal.label()
