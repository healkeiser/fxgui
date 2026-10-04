"""The breadcrumb has to look like something you can click, and the editor it
opens has to close when you click away from it.
"""

# Third-party
from qtpy.QtCore import QEvent, QPointF, Qt
from qtpy.QtGui import QColor, QEnterEvent, QMouseEvent
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

from _helpers import hover, unhover


PATH = ["Projects", "MyShow", "Assets", "Hero"]


def _crumb(qtbot, path=PATH):
    """A breadcrumb on screen with a path in it, its segments laid out."""
    crumb = FXBreadcrumb(home_icon="")
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


def _corner(qtbot, segment, hovered):
    """The colour a segment paints at its left edge, over its strip."""
    (hover if hovered else unhover)(qtbot, segment)
    image = segment.parentWidget().grab().toImage()
    box = segment.geometry()
    return image.pixelColor(box.left() + 3, box.center().y())


def _tinted(ground, token, alpha):
    """`token`'s colour laid over `ground` at `alpha` out of 255."""
    over, under = QColor(token), QColor(ground)
    mix = lambda a, b: round(b + (a - b) * alpha / 255)  # noqa: E731
    return (
        mix(over.red(), under.red()),
        mix(over.green(), under.green()),
        mix(over.blue(), under.blue()),
    )


def _close(color, rgb):
    return all(
        abs(a - b) <= 2
        for a, b in zip((color.red(), color.green(), color.blue()), rgb)
    )


def test_a_clickable_segment_says_so_under_the_pointer(qtbot, qapp):
    """Every segment but the last paints a tint under the pointer."""
    crumb = _crumb(qtbot)

    for segment in _segments(crumb)[:-1]:
        lit = _corner(qtbot, segment, True)
        assert lit != _corner(qtbot, segment, False), (
            f"{segment.text()} answers a hover"
        )


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
    last = _segments(crumb)[-1]

    # Under the pointer the strip wears its hover fill, and nothing over it.
    assert _corner(qtbot, last, True) == QColor(crumb._colors()[1])


def test_the_tint_is_a_neutral_theme_ink_rather_than_a_hex(qtbot, qapp):
    """A hovered segment is a neutral tint of the theme's text, never the
    accent, which marks focus and selection."""
    assert FXBreadcrumb.SEGMENT_HOVER_TOKEN == "text"
    crumb = _crumb(qtbot)
    colors = dict(vars(fxstyle.colors()))
    # The pointer over a segment is over the strip too.
    expected = _tinted(
        crumb._colors()[1],
        colors[FXBreadcrumb.SEGMENT_HOVER_TOKEN],
        FXBreadcrumb.SEGMENT_HOVER_ALPHA,
    )

    assert _close(_corner(qtbot, _segments(crumb)[0], True), expected)


def test_a_subclass_can_name_its_own_tokens(qtbot, qapp):
    """The drawing is fxgui's, the palette choice is the consumer's: a
    house style names tokens and reimplements nothing."""

    class HouseCrumb(FXBreadcrumb):
        STRIP_RESTING_TOKEN = "surface_alt"
        SEGMENT_HOVER_TOKEN = "accent_secondary"
        SEGMENT_HOVER_ALPHA = 120

    crumb = HouseCrumb(home_icon="")
    qtbot.addWidget(crumb)
    crumb.resize(400, 32)
    crumb.set_path(PATH)
    crumb.show()
    qtbot.waitExposed(crumb)
    colors = dict(vars(fxstyle.colors()))

    assert crumb._colors()[0] == colors["surface_alt"]
    expected = _tinted(
        crumb._colors()[1], colors["accent_secondary"], 120)
    assert _close(_corner(qtbot, _segments(crumb)[0], True), expected)


def _enter_event(widget):
    """The event Qt delivers when the pointer arrives over `widget`."""
    inside = QPointF(1.0, 1.0)
    return QEnterEvent(inside, inside, inside)


def _strip_fill(crumb):
    image = crumb._container.grab().toImage()
    return image.pixelColor(image.width() - 6, image.height() // 2).name()


def test_the_strip_lights_on_enter_and_drops_on_leave(qtbot, qapp):
    """A `:hover` rule on the container cannot do this: once the path is
    drawn, the widget the pointer is directly over is a segment."""
    crumb = _crumb(qtbot)
    resting, lit = (QColor(c).name() for c in crumb._colors()[:2])

    assert _strip_fill(crumb) == resting

    QApplication.sendEvent(crumb, _enter_event(crumb))
    assert _strip_fill(crumb) == lit, "lit while pointed at"

    QApplication.sendEvent(crumb, QEvent(QEvent.Type.Leave))
    assert _strip_fill(crumb) == resting, "and back on leaving"


def test_a_theme_change_keeps_the_segments_and_their_tint(qtbot, qapp):
    """Nothing is rebuilt: the same segments paint the new theme."""
    crumb = _crumb(qtbot)
    before = _segments(crumb)

    fxstyle.apply_theme("light")

    assert _segments(crumb) == before
    assert _strip_fill(crumb) == QColor(crumb._colors()[0]).name()
    first = before[0]
    assert _corner(qtbot, first, True) != _corner(qtbot, first, False)


def test_a_new_path_bolds_only_its_last_segment(qtbot, qapp):
    crumb = FXBreadcrumb()
    qtbot.addWidget(crumb)
    crumb.set_path(PATH)

    crumb.set_path(["Somewhere", "Else", "Entirely"])

    drawn = _segments(crumb)
    # With a `home_icon` set, which is the default, the first segment is
    # drawn as that icon with its text as a tooltip.
    assert [segment.text() for segment in drawn[1:]] == ["Else", "Entirely"]
    assert drawn[0].toolTip() == "Somewhere"
    assert [segment.font().bold() for segment in drawn] == [
        False, False, True
    ]


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
