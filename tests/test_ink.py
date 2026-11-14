"""`fxstyle.ink` writes a widget's text in one theme colour."""

import pytest
from qtpy.QtCore import QPoint
from qtpy.QtGui import QColor, QPalette
from qtpy.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout

from fxgui import fxstyle


def _ink_of(label) -> str:
    label.ensurePolished()
    return label.palette().color(QPalette.WindowText).name()


def _token(name) -> str:
    return QColor(getattr(fxstyle.colors(), name)).name()


@pytest.mark.parametrize("where", ["app_root", "host_root"])
def test_an_inked_label_follows_each_theme(qtbot, request, where):
    root = request.getfixturevalue(where)
    label = QLabel("hint", root)
    root.layout().addWidget(label)
    fxstyle.ink(label, "text_muted")
    root.show()
    qtbot.waitExposed(root)
    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        QApplication.processEvents()
        assert _ink_of(label) == _token("text_muted"), theme
    assert _token("text_muted") != _token("text")


def test_no_ink_returns_to_the_default(qtbot, app_root):
    label = QLabel("hint", app_root)
    app_root.layout().addWidget(label)
    fxstyle.ink(label, "accent_primary")
    assert _ink_of(label) == _token("accent_primary")
    fxstyle.ink(label, None)
    assert _ink_of(label) == _token("text")


def test_every_ink_is_a_theme_token(qtbot, app_root):
    label = QLabel("hint", app_root)
    for token in fxstyle.INKS:
        fxstyle.ink(label, token)
        assert _ink_of(label) == _token(token), token


def test_an_unknown_ink_names_the_inks(qtbot):
    label = QLabel("hint")
    with pytest.raises(ValueError, match="text_muted"):
        fxstyle.ink(label, "purple")


@pytest.mark.parametrize("where", ["app_root", "host_root"])
def test_an_inked_label_has_no_fill_of_its_own(qtbot, request, where):
    root = request.getfixturevalue(where)
    card = QFrame(root)
    card.setObjectName("card")
    card.setStyleSheet("QFrame#card { background: #7a3b8f; }")
    label = QLabel("on the card", card)
    QVBoxLayout(card).addWidget(label)
    root.layout().addWidget(card)
    fxstyle.ink(label, "text_muted")
    root.resize(300, 200)
    root.show()
    qtbot.waitExposed(root)
    QApplication.processEvents()
    image = root.grab().toImage()
    fill = image.pixelColor(label.mapTo(root, QPoint(label.width() - 2, 1)))
    assert fill.name() == "#7a3b8f"
