"""Focus and control states a settled picture never shows.

A ring round a control flush in a composite (a dialog's button box, a
path field, a tag field) was cut by that composite's edge down to one side
and two corner blobs; a joined group's child drew its ring inside the
group. A disabled control in a mixed state drew a tick, a disabled tab and
a disabled FXThumbnailDelegate row looked enabled.
"""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint, QRect, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import (
    FXFilePathWidget,
    FXJoinedGroup,
    FXTagInput,
    FXThumbnailDelegate,
)
from tests._helpers import themed_window


def _count(image, color: str) -> int:
    """How many pixels of `image` are exactly `color`."""
    target = QColor(color).rgb() & 0xFFFFFF
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixel(x, y) & 0xFFFFFF == target
    )


###### The focus ring round a flush control


def _box():
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    ok = box.button(QDialogButtonBox.Ok)
    return box, ok, ok


def _path():
    path = FXFilePathWidget(validate=False)
    field = path.findChild(QLineEdit)
    return path, field, field


def _tags():
    tags = FXTagInput()
    field = tags.findChild(QLineEdit)
    return tags, field, field


def _joined():
    group = FXJoinedGroup()
    combo = QComboBox()
    combo.addItem("Open")
    post = QPushButton("Post")
    group.add_widget(combo)
    group.add_widget(post)
    # The ring goes round the whole group, from its last child too.
    return group, post, group


_FLUSH = {"button_box": _box, "path_field": _path, "tag_field": _tags,
          "joined_group": _joined}


def _sides_lit(window, ringed, before, after) -> str:
    """Return the sides just outside `ringed` whose pixels focus changed."""
    corner = ringed.mapTo(window, QPoint(0, 0))
    width, height = ringed.width(), ringed.height()
    probes = {
        "L": (-2, height // 2),
        "R": (width + 1, height // 2),
        "T": (width // 2, -2),
        "B": (width // 2, height + 1),
    }
    return "".join(
        side for side, (x, y) in probes.items()
        if before.pixel(corner + QPoint(x, y))
        != after.pixel(corner + QPoint(x, y))
    )


@pytest.mark.parametrize("make", list(_FLUSH.values()), ids=list(_FLUSH))
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_flush_control_s_ring_shows_on_all_four_sides(qtbot, theme, make):
    holder, focus, ringed = make()
    window = themed_window(qtbot, theme, holder)
    before = window.grab().toImage()

    focus.setFocus(Qt.TabFocusReason)
    QApplication.processEvents()

    assert fxstyle._FocusRing._shown._target is ringed
    assert _sides_lit(window, ringed, before, window.grab().toImage()) == (
        "LRTB")


def _ring_place(ring) -> QRect:
    target = ring._target
    grow = fxstyle.FOCUS_RING_WIDTH
    return QRect(
        target.mapTo(ring.parentWidget(), QPoint(0, 0)), target.size()
    ).adjusted(-grow, -grow, grow, grow)


def test_a_ring_follows_its_control_when_the_composite_moves_or_hides(qtbot):
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    spacer = QPushButton("spacer")
    path = FXFilePathWidget(validate=False)
    layout.addWidget(spacer)
    layout.addWidget(path)
    window = themed_window(qtbot, "dark", row, size=(480, 120))
    field = path.findChild(QLineEdit)
    field.setFocus(Qt.TabFocusReason)
    QApplication.processEvents()
    ring = fxstyle._FocusRing._shown

    spacer.setFixedWidth(200)
    qtbot.waitUntil(lambda: path.x() >= 200)
    assert ring.geometry() == _ring_place(ring)

    # Focus leaves a hidden field; no ring stays standing where it was.
    path.hide()
    QApplication.processEvents()
    assert not [
        each for each in window.findChildren(fxstyle._FocusRing)
        if each.isVisible() and each._target is field
    ]



@pytest.mark.parametrize("theme", ["dark", "light"])
def test_a_flush_view_s_keyboard_focus_rings_its_inside(qtbot, theme):
    """A flush view has no edge to recolour: its current row is selected
    and nothing else showed which view had the keyboard."""
    tree = QTreeWidget()
    for name in ("sh0010", "sh0020"):
        QTreeWidgetItem(tree, [name])
    fxstyle.mark_flush(tree)
    window = themed_window(qtbot, theme, tree)
    tree.setCurrentItem(tree.topLevelItem(0))
    accent = QColor(fxstyle.colors().accent_primary).name()
    edge = (0, tree.height() // 2)

    tree.setFocus(Qt.TabFocusReason)
    QApplication.processEvents()
    assert tree.grab().toImage().pixelColor(*edge).name() == accent

    tree.setFocus(Qt.MouseFocusReason)
    window.setFocus(Qt.MouseFocusReason)
    tree.setFocus(Qt.MouseFocusReason)
    QApplication.processEvents()
    assert window.grab().toImage().pixelColor(
        tree.mapTo(window, QPoint(*edge))).name() != accent


def test_freeing_a_shown_window_with_a_focused_dialog_button_is_quiet(qtbot):
    """PySide6 6.5 raised from the focus watch: the OK button, made by Qt,
    lost focus inside its window's destructor."""
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    window = themed_window(qtbot, "dark", box)
    box.button(QDialogButtonBox.Ok).setFocus(Qt.TabFocusReason)
    QApplication.processEvents()

    window.deleteLater()
    del window, box
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)


###### Disabled and mixed marks


def test_a_disabled_mixed_check_box_draws_a_dash_not_a_tick(qtbot):
    mixed, ticked = QCheckBox(), QCheckBox()
    mixed.setTristate(True)
    mixed.setCheckState(Qt.PartiallyChecked)
    ticked.setChecked(True)
    for box in (mixed, ticked):
        box.setEnabled(False)
    window = themed_window(qtbot, "dark", mixed, ticked)  # noqa: F841

    assert mixed.grab().toImage() != ticked.grab().toImage()


def _checked_rows(delegate: bool) -> QTreeWidget:
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    if delegate:
        tree.setItemDelegate(FXThumbnailDelegate(tree))
    for state in (Qt.Checked, Qt.PartiallyChecked):
        item = QTreeWidgetItem(tree, ["sh0010"])
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, state)
        item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
    return tree


@pytest.mark.parametrize("delegate", [False, True], ids=["plain", "delegate"])
def test_a_disabled_row_s_check_box_wears_no_accent(qtbot, delegate):
    tree = _checked_rows(delegate)
    window = themed_window(qtbot, "dark", tree)  # noqa: F841

    image = tree.viewport().grab().toImage()

    assert _count(image, fxstyle.colors().accent_primary) == 0


def test_a_disabled_delegate_row_s_name_is_in_the_disabled_ink(qtbot):
    tree = _checked_rows(delegate=True)
    window = themed_window(qtbot, "dark", tree)  # noqa: F841
    theme = fxstyle.colors()

    image = tree.viewport().grab().toImage()

    assert _count(image, theme.text_strong) == 0
    assert _count(image, theme.text_disabled) > 0


def test_a_disabled_tab_is_in_the_disabled_ink(qtbot):
    tabs = QTabWidget()
    for name in ("One", "Two", "Three"):
        tabs.addTab(QWidget(), name)
    tabs.setTabEnabled(1, False)
    window = themed_window(qtbot, "dark", tabs)  # noqa: F841
    bar = tabs.tabBar()
    image = bar.grab().toImage()
    theme = fxstyle.colors()

    disabled = image.copy(bar.tabRect(1))
    enabled = image.copy(bar.tabRect(2))

    assert _count(disabled, theme.text_muted) == 0
    assert _count(disabled, theme.text_disabled) > 0
    assert _count(enabled, theme.text_muted) > 0
