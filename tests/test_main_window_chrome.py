"""FXMainWindow's size, icon and toolbar follow what the caller asked for."""

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


class _Roomy(QWidget):
    """A widget that ASKS for more room than it insists on."""

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
    """Once only."""
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
    """FXSystemTray takes a `QIcon` as well as a path."""
    from fxgui.fxwidgets import FXSystemTray

    icon = _an_icon("#123456")
    tray = FXSystemTray(icon=icon)

    assert not tray.icon().isNull()
    assert tray.icon().cacheKey() == icon.cacheKey()


def test_the_system_tray_defaults_to_fxguis_logo(qtbot):
    from fxgui.fxwidgets import FXSystemTray

    tray = FXSystemTray()

    assert not tray.icon().isNull(), "fxgui's own logo"


def test_the_fit_is_still_bounded_by_the_screen(qtbot):
    """The guard must not have cost the bound: a layout may ask for more
    room than the display has, and a window taller than the desktop is
    worse than a scrollbar."""

    class _Enormous(QWidget):
        def sizeHint(self):
            return QSize(99999, 99999)

    window = FXMainWindow(title="probe", fit_to_contents=True)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.addWidget(_Enormous())
    window.setCentralWidget(body)
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window)

    available = window.screen().availableGeometry()
    assert window.height() <= available.height()
    assert window.width() <= available.width()
