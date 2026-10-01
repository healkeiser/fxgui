"""The focus look shows only when focus came by keyboard, as :focus-visible.

A click focuses what Qt focuses, but once the pointer leaves, the control
looks as it did at rest. Tab, Backtab and shortcuts show the focus look.
"""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXThumbnailDelegate, FXToggleSwitch


@pytest.fixture(autouse=True)
def _no_caret_blink(qapp):
    flash = qapp.cursorFlashTime()
    qapp.setCursorFlashTime(0)
    yield
    qapp.setCursorFlashTime(flash)


def _tree():
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    FXThumbnailDelegate.apply_transparent_selection(tree)
    for name in ("sh0010", "sh0020"):
        item = QTreeWidgetItem(tree, [name])
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    tree.setCurrentItem(tree.topLevelItem(0))
    tree.setFixedHeight(90)
    return tree


_KINDS = {
    "button": lambda: QPushButton("Publish"),
    "line_edit": QLineEdit,
    "check_box": lambda: QCheckBox("Notify"),
    "toggle": FXToggleSwitch,
    "tree": _tree,
}


def _window(qtbot, make):
    """Return a themed window: a sink, the widget, and an untouched twin."""
    window = QWidget()
    fxstyle.register_themed_root(window)
    layout = QVBoxLayout(window)
    sink = QPushButton("sink")
    widget, twin = make(), make()
    for each in (sink, widget, twin):
        layout.addWidget(each)
    window.resize(260, 320)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    QApplication.processEvents()
    sink.setFocus(Qt.TabFocusReason)
    QApplication.processEvents()
    widget.window_ = window  # pytest-qt holds the window weakly.
    return widget, twin, sink


def _accent(widget) -> int:
    image = widget.grab().toImage()
    target = QColor(fxstyle.colors().accent_primary).rgb() & 0xFFFFFF
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixel(x, y) & 0xFFFFFF == target
    )


def _click(widget, sink) -> None:
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, QPoint(6, 6))
    if isinstance(widget, (QCheckBox, FXToggleSwitch)):
        # A second click puts the state back, so only focus differs.
        QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, QPoint(6, 6))
        if isinstance(widget, FXToggleSwitch):
            for _ in range(100):
                if widget.position == 0.0:
                    break
                QTest.qWait(10)
    QTest.mouseMove(sink)
    widget.setAttribute(Qt.WA_UnderMouse, False)
    QApplication.processEvents()


def _tab_to(widget) -> None:
    widget.setFocus(Qt.TabFocusReason)
    QApplication.processEvents()


@pytest.mark.parametrize("kind", sorted(_KINDS))
def test_a_click_leaves_no_focus_look(qtbot, kind):
    widget, twin, sink = _window(qtbot, _KINDS[kind])
    _click(widget, sink)
    assert widget.hasFocus(), "the click still focuses"
    assert _accent(widget) == _accent(twin)


@pytest.mark.parametrize("kind", sorted(_KINDS))
def test_tab_shows_the_focus_look(qtbot, kind):
    widget, twin, _ = _window(qtbot, _KINDS[kind])
    _tab_to(widget)
    assert _accent(widget) > _accent(twin)


@pytest.mark.parametrize("kind", sorted(_KINDS))
def test_tab_away_and_back_after_a_click_shows_it(qtbot, kind):
    widget, twin, sink = _window(qtbot, _KINDS[kind])
    _click(widget, sink)
    _tab_to(sink)
    _tab_to(widget)
    assert _accent(widget) > _accent(twin)


def test_a_clicked_button_looks_untouched_once_the_pointer_leaves(qtbot):
    widget, twin, sink = _window(qtbot, _KINDS["button"])
    _click(widget, sink)
    assert widget.grab().toImage() == twin.grab().toImage()


def test_a_clicked_dialog_button_looks_untouched(qtbot):
    """Qt makes the last clicked push button of a dialog its default."""
    dialog = QDialog()
    fxstyle.register_themed_root(dialog)
    box = QDialogButtonBox(QDialogButtonBox.Ok)
    # Apply keeps the dialog open, and a click makes it the default.
    apply = box.addButton(QDialogButtonBox.Apply)
    QVBoxLayout(dialog).addWidget(box)
    qtbot.addWidget(dialog)
    qtbot.dialog = dialog
    dialog.show()
    qtbot.waitExposed(dialog)
    before = apply.grab().toImage()
    QTest.mouseClick(apply, Qt.LeftButton, Qt.NoModifier, QPoint(6, 6))
    QTest.mouseMove(box.button(QDialogButtonBox.Ok))
    apply.setAttribute(Qt.WA_UnderMouse, False)
    QApplication.processEvents()
    assert apply.hasFocus() and apply.isDefault()
    assert apply.grab().toImage() == before


def test_a_shortcut_focus_shows_the_look(qtbot):
    widget, twin, _ = _window(qtbot, QLineEdit)
    widget.setFocus(Qt.ShortcutFocusReason)
    QApplication.processEvents()
    assert _accent(widget) > _accent(twin)
