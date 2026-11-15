"""`FXEmptyState` prompts for what to do next; `FXScrollShadow` marks a cut."""

from qtpy.QtCore import QPoint, QRect, QSize
from qtpy.QtGui import QColor, QFont, QIcon, QPalette
from qtpy.QtWidgets import QApplication, QScrollArea, QWidget

from fxgui import fxstyle
from fxgui.fxwidgets import FXEmptyState, FXScrollShadow


def _show(qtbot, root):
    root.resize(300, 300)
    root.show()
    qtbot.waitExposed(root)
    QApplication.processEvents()


def _token(name) -> str:
    return QColor(getattr(fxstyle.colors(), name)).name()


def _ink_of(label) -> str:
    label.ensurePolished()
    return label.palette().color(QPalette.WindowText).name()


def _inks(icon: QIcon, mode) -> set:
    image = icon.pixmap(QSize(32, 32), mode).toImage()
    return {
        image.pixelColor(x, y).name()
        for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }


# ' FXEmptyState


def test_the_prompt_shows_icon_medium_action_and_muted_detail(qtbot, host_root):
    empty = FXEmptyState("inbox", "Pick a task", "Its files show here")
    host_root.layout().addWidget(empty)
    _show(qtbot, host_root)

    assert not empty.icon.icon().isNull()
    assert empty.action.text() == "Pick a task"
    assert empty.action.font().weight() == QFont.Medium
    assert _ink_of(empty.action) == _token("text")
    assert empty.detail.isVisible()
    assert _ink_of(empty.detail) == _token("text_muted")
    assert empty.prompt() == ("Pick a task", "Its files show here")


def test_the_text_is_16_and_14_px_at_most_384_wide_and_centred(
        qtbot, host_root):
    long = "Every file the task published shows here, newest first " * 3
    empty = FXEmptyState("inbox", "Pick a task", long)
    host_root.layout().addWidget(empty)
    _show(qtbot, host_root)
    host_root.resize(900, 400)
    QApplication.processEvents()

    assert empty.layout().spacing() == 16
    assert empty.action.font().pixelSize() == 16
    assert empty.action.font().weight() == QFont.Medium
    assert empty.detail.font().pixelSize() == 14
    for label in (empty.action, empty.detail):
        box = label.geometry()
        assert box.width() == 384
        assert abs(box.center().x() - empty.rect().center().x()) <= 1
    # Wrapped to its width, not clipped to a one-line height.
    assert empty.detail.height() >= empty.detail.heightForWidth(384)

    host_root.resize(200, 400)
    QApplication.processEvents()
    assert empty.detail.geometry().left() == fxstyle.PANE_GAP


def test_an_empty_detail_hides_its_line(qtbot, host_root):
    empty = FXEmptyState("inbox", "Pick a task")
    host_root.layout().addWidget(empty)
    _show(qtbot, host_root)

    assert not empty.detail.isVisible()
    assert empty.prompt() == ("Pick a task", "")


def test_set_prompt_replaces_all_three(qtbot, host_root):
    empty = FXEmptyState("inbox", "Pick a task")
    host_root.layout().addWidget(empty)
    _show(qtbot, host_root)
    before = empty.icon.icon().cacheKey()

    empty.set_prompt("search", "Search again", "Nothing matched")

    assert empty.icon.icon().cacheKey() != before
    assert empty.detail.isVisible()
    assert empty.prompt() == ("Search again", "Nothing matched")


def test_a_disabled_empty_state_keeps_its_icon_muted(qtbot):
    empty = FXEmptyState("inbox", "Pick a task")
    qtbot.addWidget(empty)
    empty.setEnabled(False)

    icon = empty.icon.icon()
    muted = {_token("text_muted")}
    assert _inks(icon, QIcon.Disabled) == muted
    assert _inks(icon, QIcon.Normal) == muted


# ' FXScrollShadow


def _area(qtbot, root, content_height=1000):
    area = QScrollArea()
    content = QWidget()
    content.setFixedSize(150, content_height)
    area.setWidget(content)
    area.setFixedSize(200, 150)
    root.layout().addWidget(area)
    shadow = FXScrollShadow(area)
    _show(qtbot, root)
    return area, shadow


def _cut(area) -> QRect:
    view = area.viewport().geometry()
    return QRect(view.left(), view.bottom() - 9, view.width(), 10)


def test_the_shadow_sits_on_the_viewport_bottom(qtbot, host_root):
    area, shadow = _area(qtbot, host_root)

    assert shadow.isVisible()
    assert shadow.geometry() == _cut(area)


def test_the_shadow_hides_at_the_end(qtbot, host_root):
    area, shadow = _area(qtbot, host_root)
    bar = area.verticalScrollBar()

    bar.setValue(bar.maximum())
    assert not shadow.isVisible()
    bar.setValue(0)
    assert shadow.isVisible()


def test_the_shadow_hides_with_nothing_to_scroll(qtbot, host_root):
    _, shadow = _area(qtbot, host_root, content_height=50)

    assert not shadow.isVisible()


def test_the_shadow_follows_a_resize(qtbot, host_root):
    area, shadow = _area(qtbot, host_root)

    area.setFixedSize(260, 120)
    QApplication.processEvents()

    assert shadow.geometry() == _cut(area)
    assert shadow.isVisible()


def test_the_shadow_line_takes_each_theme_border(qtbot, host_root):
    area, shadow = _area(qtbot, host_root)
    bottom = shadow.mapTo(area, QPoint(shadow.width() // 2, shadow.height() - 1))

    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        QApplication.processEvents()
        assert area.grab().toImage().pixelColor(bottom).name() == _token(
            "border"), theme
