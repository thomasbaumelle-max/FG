from types import SimpleNamespace

import pygame as pg

from ui.widgets.icon_button import (
    IconButton,
    KEYDOWN,
    MOUSEBUTTONDOWN,
    MOUSEBUTTONUP,
)


def test_icon_button_click(monkeypatch):
    called = []
    rect = pg.Rect(0, 0, 32, 32)
    btn = IconButton(rect, "end_turn", lambda: called.append(True))
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    down = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=(1, 1), button=1)
    up = SimpleNamespace(type=MOUSEBUTTONUP, pos=(1, 1), button=1)
    btn.handle(down)
    btn.handle(up)
    assert called == [True]


def test_icon_button_hotkey():
    called = []
    rect = pg.Rect(0, 0, 32, 32)
    hotkey = 42
    btn = IconButton(rect, "end_turn", lambda: called.append(True), hotkey=hotkey)
    evt = SimpleNamespace(type=KEYDOWN, key=hotkey)
    btn.handle(evt)
    assert called == [True]
