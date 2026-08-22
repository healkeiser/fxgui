"""The breadcrumb has to look like something you can click, and the
editor it opens has to close when you click away from it.

Measured on the plain widget: every segment is a `QPushButton` and none
of them said so -- flat text on the window's own background, no cursor
change, nothing under the pointer. The one control that walks the
hierarchy read as a row of labels, and an artist had no reason to try it.

The second half is the editor. It exited on the line edit's `FocusOut`,
which covers a press that lands on something focusable and nothing else:
a press on a heading, a tree's own header or the window's background
moves no focus at all, so the editor stayed up with the artist looking at
a path they had already left.
"""

# Third-party
from qtpy.QtCore import QEvent, QPointF, Qt
from qtpy.QtGui import QEnterEvent, QMouseEvent
from qtpy.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXBreadcrumb


PATH = ["Projects", "MyShow", "Assets", "Hero"]


def _crumb(qtbot, path=PATH):
    """A breadcrumb on screen with a path in it.

    On screen because the segments are laid out when the widget is, and
    the strip's fill is read back off a real stylesheet.
    """
    crumb = FXBreadcrumb()
    qtbot.addWidget(crumb)
    crumb.resize(400, 32)
    crumb.set_path(path)
    crumb.show()
    qtbot.waitExposed(crumb)
    return crumb


def _segments(crumb):
    """The path's own buttons, in the order they are drawn.

    Read off the layout rather than through `findChildren`, because a
    rebuild retires the old buttons with `deleteLater` and they are
    still children until the event loop gets to them.
    """
    layout = crumb._layout
    drawn = []
    for index in range(layout.count()):
        widget = layout.itemAt(index).widget()
        if isinstance(widget, QPushButton):
            drawn.append(widget)
    return drawn


def test_a_clickable_segment_says_so_under_the_pointer(qtbot, qapp):
    """Every segment but the last carries a hover tint of its own."""
    crumb = _crumb(qtbot)

    for segment in _segments(crumb)[:-1]:
        assert "QPushButton:hover" in segment.styleSheet(), (
            f"{segment.text()} answers a hover"
        )
        assert "rgba(" in segment.styleSheet(), "with a tint, not a border"


def test_a_clickable_segment_says_so_with_its_cursor(qtbot, qapp):
    crumb = _crumb(qtbot)
    drawn = _segments(crumb)

    for segment in drawn[:-1]:
        assert segment.cursor().shape() == Qt.PointingHandCursor
    assert drawn[-1].cursor().shape() == Qt.ArrowCursor, (
        "the path is already here"
    )


def test_the_segment_the_path_is_already_at_promises_nothing(qtbot, qapp):
    """The last segment is connected to nothing, so a tint on it would
    offer a click that does nothing at all."""
    crumb = _crumb(qtbot)

    assert "QPushButton:hover" not in _segments(crumb)[-1].styleSheet()


def test_the_tint_is_the_themes_accent_rather_than_a_hex(qtbot, qapp):
    """A studio theme governs what a hovered segment looks like, which
    is the whole reason the tint is named as a token."""
    crumb = _crumb(qtbot)
    accent = fxstyle.get_theme_colors()[FXBreadcrumb.SEGMENT_HOVER_TOKEN]
    red = int(accent[1:3], 16)
    green = int(accent[3:5], 16)
    blue = int(accent[5:7], 16)

    rule = _segments(crumb)[0].styleSheet()

    assert f"rgba({red}, {green}, {blue}, {crumb.SEGMENT_HOVER_ALPHA})" in rule


def test_a_subclass_can_name_its_own_tokens(qtbot, qapp):
    """The drawing is fxgui's, the palette choice is the consumer's: a
    house style names tokens and reimplements nothing."""

    class HouseCrumb(FXBreadcrumb):
        STRIP_RESTING_TOKEN = "surface_alt"
        SEGMENT_HOVER_TOKEN = "accent_secondary"
        SEGMENT_HOVER_ALPHA = 120

    crumb = HouseCrumb()
    qtbot.addWidget(crumb)
    crumb.set_path(PATH)
    colors = fxstyle.get_theme_colors()

    assert colors["surface_alt"] in crumb._container.styleSheet()
    secondary = colors["accent_secondary"]
    expected = (
        f"rgba({int(secondary[1:3], 16)}, {int(secondary[3:5], 16)},"
        f" {int(secondary[5:7], 16)}, 120)"
    )
    assert expected in crumb._container.findChildren(QPushButton)[0].styleSheet()


def test_the_strip_is_drawn_before_any_event_loop_pass(qtbot, qapp):
    """A widget constructed and asserted on in the same breath is
    already right: the theme's own application runs on a
    `singleShot(0)`, which is one pass away."""
    crumb = FXBreadcrumb()
    qtbot.addWidget(crumb)

    assert "background-color" in crumb._container.styleSheet()


def test_the_strip_is_never_the_window_s_own_colour(qtbot, qapp):
    """A strip painted in `surface` is a strip nobody can see: in every
    theme fxgui ships that token is the window's colour to the byte."""
    colors = fxstyle.get_theme_colors()

    assert colors[FXBreadcrumb.STRIP_RESTING_TOKEN] != colors["surface"]
    assert colors[FXBreadcrumb.STRIP_HOVERED_TOKEN] != colors["surface"]


def _enter_event(widget):
    """The event Qt delivers when the pointer arrives over `widget`."""
    inside = QPointF(1.0, 1.0)
    return QEnterEvent(inside, inside, inside)


def test_the_strip_lights_on_enter_and_drops_on_leave(qtbot, qapp):
    """A `:hover` rule on the container cannot do this: once the path is
    drawn, the widget the pointer is directly over is a segment."""
    crumb = _crumb(qtbot)
    colors = fxstyle.get_theme_colors()
    resting = colors[FXBreadcrumb.STRIP_RESTING_TOKEN]
    lit = colors[FXBreadcrumb.STRIP_HOVERED_TOKEN]

    assert resting in crumb._container.styleSheet()

    QApplication.sendEvent(crumb, _enter_event(crumb))
    assert lit in crumb._container.styleSheet(), "lit while pointed at"

    QApplication.sendEvent(crumb, QEvent(QEvent.Type.Leave))
    assert resting in crumb._container.styleSheet(), "and back on leaving"


def test_the_marks_survive_a_theme_change(qtbot, qapp):
    """A theme change rebuilds the segments to restyle them, so a mark
    applied after `set_path` is on a button that no longer exists.
    Measured: such marks were still there and gone one pass later."""
    crumb = _crumb(qtbot)

    fxstyle.apply_theme("light")

    colors = fxstyle.get_theme_colors()
    assert colors[FXBreadcrumb.STRIP_RESTING_TOKEN] in (
        crumb._container.styleSheet()
    ), "the strip is re-read from the new theme"
    for segment in _segments(crumb)[:-1]:
        assert "QPushButton:hover" in segment.styleSheet()


def test_the_marks_survive_a_new_path(qtbot, qapp):
    crumb = _crumb(qtbot)

    crumb.set_path(["Somewhere", "Else", "Entirely"])

    drawn = _segments(crumb)
    # From the second: with a `home_icon` set, which is the default, the
    # first segment is drawn as that icon with its text as a tooltip.
    assert [segment.text() for segment in drawn[1:]] == ["Else", "Entirely"]
    assert drawn[0].toolTip() == "Somewhere"
    for segment in drawn[:-1]:
        assert "QPushButton:hover" in segment.styleSheet()


def _press_on(widget):
    """Deliver a real mouse press to `widget`, the way a click does."""
    # The local and global positions are the same point on purpose: what
    # the filter reads is which object the press reached, not where.
    inside = QPointF(1.0, 1.0)
    QApplication.sendEvent(
        widget,
        QMouseEvent(
            QEvent.Type.MouseButtonPress,
            inside,
            inside,
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        ),
    )


def test_a_press_that_moves_no_focus_closes_the_editor(qtbot, qapp):
    """The whole finding: a heading, a tree header or a window
    background takes no focus, so `FocusOut` never fires and the editor
    stayed open over a path the artist had already left."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    crumb = FXBreadcrumb()
    heading = QLabel("Takes no focus")
    layout.addWidget(crumb)
    layout.addWidget(heading)
    crumb.set_path(PATH)
    host.show()
    qtbot.waitExposed(host)

    crumb.enter_edit_mode()
    assert crumb.is_editing()

    _press_on(heading)

    assert not crumb.is_editing(), "the press outside closed it"


def test_a_press_inside_the_widget_leaves_the_editor_open(qtbot, qapp):
    """Selecting text in the editor is a press inside it, and it must
    not be the gesture that closes it."""
    crumb = _crumb(qtbot)

    crumb.enter_edit_mode()
    _press_on(crumb._line_edit)

    assert crumb.is_editing()


def test_the_filter_goes_when_the_editor_does(qtbot, qapp):
    """An application-wide filter sees every event in the process, so it
    has no business outliving the editor that needed it."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    crumb = FXBreadcrumb()
    heading = QLabel("Takes no focus")
    layout.addWidget(crumb)
    layout.addWidget(heading)
    crumb.set_path(PATH)
    host.show()
    qtbot.waitExposed(host)

    crumb.enter_edit_mode()
    crumb.exit_edit_mode()

    # With the filter gone, a press outside reaches its target
    # unmolested; with it still installed this would still be handled.
    _press_on(heading)
    assert not crumb.is_editing()

    crumb.enter_edit_mode()
    assert crumb.is_editing(), "and it can be installed again"


def test_exit_edit_mode_is_public(qtbot, qapp):
    """A window-level `Escape` shortcut is delivered BEFORE the focused
    widget sees the key, so this widget's own `Escape` never fires while
    such a shortcut exists. The window has to be able to ask, and to
    hand the key over."""
    crumb = _crumb(qtbot)

    crumb.enter_edit_mode()
    assert crumb.is_editing()

    crumb.exit_edit_mode()

    assert not crumb.is_editing()
