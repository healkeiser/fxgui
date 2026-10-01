"""set_widget_style gives one widget a sheet whose tokens follow the theme."""

from qtpy.QtGui import QColor, QPalette
from qtpy.QtWidgets import QFormLayout, QLabel, QLineEdit, QWidget

from fxgui import fxstyle


def test_the_sheet_is_resolved_now_and_at_each_switch(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    fxstyle.set_widget_style(label, "color: @text_muted;")
    assert label.styleSheet() == f"color: {fxstyle.colors().text_muted};"
    for theme in ("nord", "github_light"):
        fxstyle.apply_theme(theme)
        assert label.styleSheet() == (
            f"color: {fxstyle.colors().text_muted};"), theme


def test_the_drawn_ink_follows_a_switch(qtbot):
    label = QLabel("muted")
    qtbot.addWidget(label)
    fxstyle.set_widget_style(label, "color: @feedback_error_foreground;")
    label.ensurePolished()
    fxstyle.apply_theme("light")
    label.ensurePolished()
    assert label.palette().color(QPalette.WindowText).name() == QColor(
        fxstyle.colors().feedback_error_foreground).name()


def test_setting_again_keeps_only_the_last_sheet(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    for n in range(100):
        fxstyle.set_widget_style(label, f"margin: {n}px;")
    assert label.children() == []
    fxstyle.apply_theme("nord")
    assert label.styleSheet() == "margin: 99px;"


def test_a_label_qt_made_follows_once_its_wrapper_is_gone(qtbot):
    form = QWidget()
    qtbot.addWidget(form)
    field = QLineEdit()
    QFormLayout(form).addRow("Name", field)
    fxstyle.set_widget_style(form.layout().labelForField(field),
                             "color: @accent_primary;")
    fxstyle.apply_theme("dracula")
    label = form.layout().labelForField(field)
    assert label.styleSheet() == f"color: {fxstyle.colors().accent_primary};"


def test_an_empty_sheet_stops_following(qtbot):
    label = QLabel()
    qtbot.addWidget(label)
    fxstyle.set_widget_style(label, "color: @text;")
    fxstyle.set_widget_style(label, "")
    label.setStyleSheet("color: red;")
    fxstyle.apply_theme("nord")
    assert label.styleSheet() == "color: red;"


def test_a_deleted_widget_is_skipped(qtbot):
    label = QLabel()
    fxstyle.set_widget_style(label, "color: @text;")
    label.deleteLater()
    qtbot.wait(10)
    fxstyle.apply_theme("light")
