"""A title rank sets a heading's size and weight from the theme, anywhere."""

import pytest
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QApplication, QLabel, QScrollArea, QVBoxLayout, QWidget

from fxgui import fxstyle


def _shown(qtbot, root, *labels):
    """Show `root`, then move `labels` in, as a page built late would be."""
    root.show()
    qtbot.waitExposed(root)
    page = QScrollArea()
    holder = QWidget()
    column = QVBoxLayout(holder)
    for label in labels:
        column.addWidget(label)
    page.setWidget(holder)
    root.layout().addWidget(page)
    QApplication.processEvents()
    for label in labels:
        label.ensurePolished()


@pytest.mark.parametrize("where", ["app_root", "host_root"])
def test_each_rank_takes_its_size_and_weight(qtbot, request, where):
    root = request.getfixturevalue(where)
    section, card, body = QLabel("Settings"), QLabel("Card"), QLabel("Row")
    fxstyle.mark_as_title(section, rank="section")
    fxstyle.mark_as_title(card, rank="card")
    _shown(qtbot, root, section, card, body)
    assert section.font().pixelSize() == 15
    assert card.font().pixelSize() == 16
    assert body.font().pixelSize() == fxstyle.FONT_SIZE
    assert section.font().weight() == QFont.DemiBold
    assert card.font().weight() == QFont.DemiBold
    assert body.font().weight() == QFont().weight()


def test_a_rank_wears_the_title_family(qapp):
    sheet = fxstyle._build_stylesheet("dark")
    start = sheet.index(f'[{fxstyle.TITLE_PROPERTY}="true"]')
    rule = sheet[start:sheet.index("}", start)]
    assert f'[{fxstyle.TITLE_PROPERTY}="section"]' in rule
    assert f"font-family: {fxstyle.get_font_family('title')}" in rule


def test_a_color_file_sets_its_own_rank_sizes(qtbot, host_root, monkeypatch):
    colors = fxstyle.get_colors()
    monkeypatch.setattr(fxstyle, "_colors", {**colors, "fonts": {
        **colors["fonts"], "ranks": {"section": {"size": 20}}}})
    section = QLabel("Settings")
    fxstyle.mark_as_title(section, rank="section")
    fxstyle._reapply_to_roots()
    _shown(qtbot, host_root, section)
    assert section.font().pixelSize() == 20
    assert section.font().weight() == QFont().weight()


def test_an_unknown_rank_is_refused(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    with pytest.raises(ValueError, match="section"):
        fxstyle.mark_as_title(label, rank="chapter")


def test_a_plain_title_keeps_the_true_mark(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    fxstyle.mark_as_title(label)
    assert label.property(fxstyle.TITLE_PROPERTY) is True
    fxstyle.mark_as_title(label, rank="card")
    assert label.property(fxstyle.TITLE_PROPERTY) == "card"
