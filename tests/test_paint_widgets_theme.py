"""Custom-painted widgets take their colours from the running theme."""

# Third-party
from qtpy.QtCore import QEvent, QPoint, QPointF, Qt
from qtpy.QtGui import QColor, QMouseEvent
from qtpy.QtWidgets import QApplication
from qtpy.QtTest import QTest

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXRatingWidget, FXToggleSwitch


def test_rating_stars_follow_a_theme_switch(qtbot, qapp):
    rating = FXRatingWidget(initial_rating=3)
    qtbot.addWidget(rating)
    before = rating._stars[0].pixmap().toImage()
    fxstyle.apply_theme("dracula")
    assert rating._stars[0].pixmap().toImage() != before


def test_rating_click_sets_the_star_under_the_pointer(qtbot, qapp):
    rating = FXRatingWidget(icon_size=20)
    qtbot.addWidget(rating)
    rating.show()
    qtbot.waitExposed(rating)
    QTest.mouseClick(rating, Qt.LeftButton, Qt.NoModifier, QPoint(50, 10))
    assert rating.rating() == 3


def test_an_off_toggle_thumb_takes_the_theme_s_muted_ink(qtbot, qapp):
    fxstyle.apply_theme("dark")
    switch = FXToggleSwitch()
    qtbot.addWidget(switch)
    switch.show()
    qtbot.waitExposed(switch)
    image = switch.grab().toImage()
    height = switch.height()
    centre = QPoint(3 + (height - 6) // 2, height // 2)
    assert image.pixelColor(centre).name() == QColor(
        fxstyle.colors().text_muted
    ).name()


def test_rating_has_one_accessor_pair():
    assert not hasattr(FXRatingWidget, "get_rating")
    assert callable(FXRatingWidget.rating)


def test_rating_hover_redraws_only_when_the_star_changes(qtbot, monkeypatch):
    rating = FXRatingWidget(icon_size=20)
    qtbot.addWidget(rating)
    rating.show()
    qtbot.waitExposed(rating)
    drawn = []
    real = rating._update_stars
    monkeypatch.setattr(
        rating, "_update_stars", lambda: (drawn.append(1), real())
    )
    for x in (45, 47, 50, 52):
        at = QPointF(x, 10)
        QApplication.sendEvent(rating, QMouseEvent(
            QEvent.MouseMove, at, rating.mapToGlobal(at),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier,
        ))

    assert len(drawn) == 1
