"""Three things `FXMainWindow` did to every window it built, whether or
not the window wanted them.

- It built a toolbar, with no way to say no. An application with nothing
  to browse and nothing to refresh has no trigger for any of the four
  buttons, and a control that does nothing reads as broken.
- It resized every window to a fixed 500x600 in its own constructor,
  before the subclass had put anything inside it. Measured on a window
  with a log panel: 500x674 against a `sizeHint` of 506x931, which
  pinned every widget to its minimum and left the panel four lines tall.
- It stamped its own logo on every window unless handed a path to an icon
  FILE, overwriting an application icon set on the running
  `QApplication` -- so an application mark became a per-window accident.

The toolbar and the icon are fixed outright. The resize is opt-in, since
changing the opening size of every existing window silently is not a fix.
"""

# Third-party
from qtpy.QtCore import QSize
from qtpy.QtGui import QColor, QIcon, QPixmap
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

# Internal
from fxgui.fxwidgets import FXMainWindow


def _an_icon(color="#ff0000"):
    """A real, non-null `QIcon` that came from no file at all.

    Which is the whole point: `fxicons.get_icon` returns icons like this
    one, and a path on disk was the only shape these classes took.
    """
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


def test_a_window_can_decline_the_toolbar(qtbot):
    window = FXMainWindow(title="probe", toolbar=False)
    qtbot.addWidget(window)

    assert window.toolbar is None


def test_a_declined_toolbar_cannot_come_back_through_the_menu(qtbot):
    """Not built rather than built and hidden, which is the measured
    part: a hidden toolbar is still in the layout's own bookkeeping, so
    the menu bar's right-click "Toolbars" entry offers it back.

    With nothing left to offer, `createPopupMenu` answers with no menu
    at all rather than an empty one, so either is the pass here.
    """
    window = FXMainWindow(title="probe", toolbar=False)
    qtbot.addWidget(window)

    offered_menu = window.createPopupMenu()
    offered = (
        []
        if offered_menu is None
        else [action.text() for action in offered_menu.actions()]
    )

    assert "Toolbar" not in offered


def test_the_toolbar_is_still_the_default(qtbot):
    window = FXMainWindow(title="probe")
    qtbot.addWidget(window)

    assert window.toolbar is not None
    assert "Toolbar" in [
        action.text() for action in window.createPopupMenu().actions()
    ]


def test_a_window_opens_at_the_constants_size_by_default(qtbot):
    """The one behaviour here that must not change silently: it decides
    the opening size of every window already built on this class."""
    window = FXMainWindow(title="probe")
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert window.width() == 500
    assert window.height() == 600


class _Roomy(QWidget):
    """A widget that ASKS for more room than it insists on.

    Which is the shape the finding was measured in: every widget pinned
    to its own minimum, and a `sizeHint` far above that. A widget whose
    MINIMUM is large would be enlarged by Qt itself whatever this class
    resized to, and would prove nothing about the flag.
    """

    def sizeHint(self):
        return QSize(506, 931)


def _stuffed(fit):
    """A window that asks for more room than 500x600 without demanding
    it."""
    window = FXMainWindow(title="probe", fit_to_contents=fit)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.addWidget(_Roomy())
    window.setCentralWidget(body)
    return window


def test_fit_to_contents_opens_at_the_layouts_own_size(qtbot):
    window = _stuffed(True)
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window)

    assert window.height() >= min(
        window.sizeHint().height(),
        window.screen().availableGeometry().height(),
    ), "the window is not showing a clamped version of itself"


def test_without_the_flag_the_same_window_opens_clamped(qtbot):
    """The comparison that makes the flag worth having."""
    window = _stuffed(False)
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window)

    assert window.height() == 600
    assert window.sizeHint().height() > 600, "it did ask for more"


def test_fit_to_contents_only_grows(qtbot):
    """A caller that asked for a larger window keeps it."""
    window = FXMainWindow(title="probe", size=(900, 900), fit_to_contents=True)
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window)

    assert window.width() >= 900
    assert window.height() >= 900


def test_fit_to_contents_does_not_undo_a_later_resize(qtbot):
    """Once only. A window an artist has dragged smaller must not be
    pushed back out the next time it is shown."""
    window = _stuffed(True)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    window.hide()
    window.resize(400, 300)
    window.show()
    qtbot.waitExposed(window)

    assert window.size().height() == 300


def test_a_window_takes_a_qicon(qtbot):
    """An application whose mark comes out of an icon set rather than off
    disk has one in a `QIcon`, and a path was the only shape this took.
    """
    icon = _an_icon()
    window = FXMainWindow(title="probe", icon=icon)
    qtbot.addWidget(window)

    assert not window.windowIcon().isNull()
    assert window.windowIcon().cacheKey() == icon.cacheKey()


def test_a_window_leaves_the_applications_own_icon_alone(qtbot):
    """The defect: an icon set on the running application reaches every
    other window in the process and was overwritten on exactly these."""
    application = QApplication.instance()
    before = application.windowIcon()
    application.setWindowIcon(_an_icon("#00ff00"))
    try:
        window = FXMainWindow(title="probe")
        qtbot.addWidget(window)

        assert window.windowIcon().cacheKey() == (
            application.windowIcon().cacheKey()
        ), "the window wears the application's mark, not fxgui's logo"
    finally:
        application.setWindowIcon(before)


def test_fxguis_own_logo_is_still_the_last_resort(qtbot):
    """With no icon anywhere, a window is not left blank."""
    application = QApplication.instance()
    before = application.windowIcon()
    application.setWindowIcon(QIcon())
    try:
        window = FXMainWindow(title="probe")
        qtbot.addWidget(window)

        assert not window.windowIcon().isNull()
    finally:
        application.setWindowIcon(before)


def test_a_path_still_wins_over_the_applications_icon(qtbot):
    """An explicit icon is an explicit icon, whatever shape it came in."""
    application = QApplication.instance()
    before = application.windowIcon()
    application.setWindowIcon(_an_icon("#00ff00"))
    try:
        window = FXMainWindow(title="probe", icon=_an_icon("#0000ff"))
        qtbot.addWidget(window)

        assert window.windowIcon().cacheKey() != (
            application.windowIcon().cacheKey()
        )
    finally:
        application.setWindowIcon(before)


def test_the_system_tray_takes_a_qicon_too(qtbot):
    """An application whose mark comes out of fxgui's own icon set has it
    in a `QIcon`, and this class documented a path only.

    Measured before the signature was widened: it already worked.
    `QIcon(QIcon)` is Qt's own copy constructor, so the old expression
    accepted an icon it never said it would, cache key and all. This
    pins the shape so the promise and the behaviour cannot drift apart
    again -- it is not a regression test for a break.
    """
    from fxgui.fxwidgets import FXSystemTray

    icon = _an_icon("#123456")
    tray = FXSystemTray(icon=icon)

    assert not tray.tray_icon.icon().isNull()
    assert tray.tray_icon.icon().cacheKey() == icon.cacheKey()


def test_the_system_tray_still_takes_a_path(qtbot):
    from fxgui.fxwidgets import FXSystemTray

    tray = FXSystemTray()

    assert isinstance(tray.icon, str), "fxgui's own logo, as a path"
    assert not tray.tray_icon.icon().isNull()
