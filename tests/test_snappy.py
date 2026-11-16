"""A row size, column lines, theme and tip change cost only what they must.

Each restyled every widget of the application: a row size or column lines
change re-set the whole application sheet and emitted ``theme_changed``
(a consumer rebuilt on it), a theme switch set an unchanged font and
palette, every elided label cut its text again, and a tip on a tree row
measured the row once per role and column.
"""

# Third-party
import pytest
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import (
    QApplication,
    QLabel,
    QStyledItemDelegate,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXElidedLabel, apply_tip


@pytest.fixture
def restyles(monkeypatch):
    """Count every sheet, palette and font set on a widget or the app."""
    calls = []
    for owner in (QWidget, QApplication):
        for name in ("setStyleSheet", "setPalette", "setFont"):
            real = getattr(owner, name)

            def spy(*args, _real=real, _name=name):
                calls.append(_name)
                return _real(*args)

            # QApplication's font and palette setters are static.
            static = owner is QApplication and name != "setStyleSheet"
            monkeypatch.setattr(owner, name, staticmethod(spy) if static else spy)
    return calls


@pytest.fixture
def heard():
    """Record what fxstyle's signals emit."""
    seen = []
    slots = {
        signal: (lambda value, name=name: seen.append((name, value)))
        for name, signal in (
            ("theme", fxstyle.theme_changed),
            ("rows", fxstyle.row_size_changed),
            ("lines", fxstyle.column_lines_changed),
        )
    }
    for signal, slot in slots.items():
        signal.connect(slot)
    yield seen
    for signal, slot in slots.items():
        signal.disconnect(slot)


@pytest.fixture
def tree(qtbot, app_root):
    view = QTreeWidget()
    view.setColumnCount(4)
    item = QTreeWidgetItem(view, ["a", "b", "c", "d"])
    app_root.layout().addWidget(view)
    app_root.resize(400, 300)
    app_root.show()
    qtbot.waitExposed(app_root)
    return view, item


def _settle():
    for _ in range(3):
        QApplication.processEvents()


def test_a_row_size_change_restyles_nothing(tree, restyles, heard):
    view, item = tree

    fxstyle.apply_row_size("big", save=False)
    _settle()

    assert restyles == []
    assert heard == [("rows", "big")]
    assert view.visualItemRect(item).height() == fxstyle.ROW_SIZES["big"]
    fxstyle.apply_row_size("normal", save=False)


def test_column_lines_restyle_nothing_and_repaint_the_views(
    qtbot, tree, restyles, heard
):
    view, _item = tree
    painted = []

    class Watch(QWidget):
        def eventFilter(self, watched, event):
            if event.type() == QEvent.Paint:
                painted.append(watched)
            return False

    watch = Watch()
    view.viewport().installEventFilter(watch)

    fxstyle.apply_column_lines(True, save=False)
    qtbot.waitUntil(lambda: bool(painted))

    assert restyles == []
    assert heard == [("lines", True)]
    fxstyle.apply_column_lines(False, save=False)


def test_a_theme_applied_again_sets_nothing(tree, restyles, heard):
    fxstyle.apply_theme("dark", save=False)

    assert restyles == []
    assert heard == [("theme", "dark")]


def test_a_theme_switch_keeps_the_font_it_shares(tree, restyles):
    same = [
        theme for theme in fxstyle.get_available_themes()
        if theme != "dark" and fxstyle.font(theme) == fxstyle.font("dark")
    ]
    assert same, "a theme sharing dark's font"

    fxstyle.apply_theme(same[0], save=False)

    assert "setFont" not in restyles
    assert restyles.count("setStyleSheet") == 1


def test_an_elided_label_cuts_again_only_when_its_font_or_width_changes(
    qtbot, monkeypatch
):
    label = FXElidedLabel("a long text that does not fit the label at all")
    qtbot.addWidget(label)
    label.resize(80, 20)
    label.show()
    qtbot.waitExposed(label)
    cuts = []
    real = QLabel.setText
    monkeypatch.setattr(
        QLabel, "setText", lambda self, text: cuts.append(text) or real(self, text)
    )

    # What a restyle sends every label, its font the same.
    QApplication.sendEvent(label, QEvent(QEvent.FontChange))
    assert cuts == []

    font = label.font()
    font.setPixelSize(font.pixelSize() * 2 if font.pixelSize() > 0 else 26)
    label.setFont(font)
    assert len(cuts) == 1
    label.resize(120, 20)
    assert len(cuts) == 2


def test_a_tip_on_a_tree_row_measures_nothing(tree):
    view, item = tree
    measured = []

    class Counting(QStyledItemDelegate):
        def sizeHint(self, option, index):
            measured.append(index.column())
            return super().sizeHint(option, index)

    delegate = Counting(view)
    view.setItemDelegate(delegate)
    _settle()
    changed = []
    view.itemChanged.connect(lambda *args: changed.append(args))
    measured.clear()

    apply_tip(item, "Asset", "A character", facts=[("Files", "8")])

    assert measured == []
    assert changed == []
    for column in range(4):
        assert "Asset" in item.toolTip(column)
        assert item.statusTip(column) == "Asset - A character"
