from ui.widgets.buttons_column import ButtonsColumn


def test_journal_button_present():
    bc = ButtonsColumn()
    names = [b.name for b in bc.buttons]
    assert "journal" in names
    assert len(names) >= 4
