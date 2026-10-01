"""Let the user drag out a region of the screen and get it back as a pixmap."""

# Built-in
from typing import Callable, List, Optional

# Third-party
from qtpy.QtCore import QEventLoop, QPoint, QRect, Qt, QTimer
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QApplication, QRubberBand, QWidget


# The compositor keeps showing a hidden window until its next frame, so an
# immediate grab captures it; pumping events does not help.
# ponytail: a fixed wait, as in Qt's Screenshot example; no portable Qt API
# waits for the compositor.
HIDE_SETTLE_MS = 250


class _RegionGrabOverlay(QWidget):
    """A translucent full-screen overlay for picking a screen region.

    Crops from `screen`, grabbed before the overlay showed, so its own fill
    never lands in the capture. `on_result` fires before `close()`, since
    `WA_DeleteOnClose` deletes the object.
    """

    def __init__(
        self,
        screen: QPixmap,
        on_result: Callable[[Optional[QPixmap]], None],
    ):
        super().__init__(
            None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._pixmap = screen
        self._on_result = on_result
        self.setWindowOpacity(0.3)
        self.setCursor(Qt.CrossCursor)
        self._origin = QPoint()
        self._band = QRubberBand(QRubberBand.Rectangle, self)

    def mousePressEvent(self, event) -> None:
        """Start the band where the press landed."""
        self._origin = event.pos()
        self._band.setGeometry(QRect(self._origin, self._origin))
        self._band.show()

    def mouseMoveEvent(self, event) -> None:
        """Stretch the band to the pointer."""
        if self._band.isVisible():
            self._band.setGeometry(
                QRect(self._origin, event.pos()).normalized()
            )

    def mouseReleaseEvent(self, event) -> None:
        """Hand back the dragged region, or None for a click."""
        rect = QRect(self._origin, event.pos()).normalized()
        self._band.hide()
        picked = None
        if rect.width() > 2 and rect.height() > 2:
            # The rect is logical; the grabbed screen is in device pixels.
            ratio = self._pixmap.devicePixelRatio()
            picked = self._pixmap.copy(QRect(
                round(rect.x() * ratio),
                round(rect.y() * ratio),
                round(rect.width() * ratio),
                round(rect.height() * ratio),
            ))
        self._on_result(picked)
        self.close()

    def keyPressEvent(self, event) -> None:
        """Cancel on Escape."""
        if event.key() == Qt.Key_Escape:
            self._on_result(None)
            self.close()


def _wait(milliseconds: int) -> None:
    """Run the event loop for `milliseconds`."""
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def grab_screen_region(window: QWidget) -> Optional[QPixmap]:
    """Let the user drag out a region of `window`'s screen; None on Escape.

    `window` is hidden for the grab and shown again afterwards, whatever
    happens. Closing the last window is kept from quitting the
    application meanwhile: with `window` hidden, the overlay is the last.

    Args:
        window: The window to take out of the picture.

    Returns:
        The region as a pixmap, or None when cancelled or no screen exists.
    """
    screen = window.screen() or QApplication.primaryScreen()
    if screen is None:
        return None
    was_visible = window.isVisible()
    quit_on_last = QApplication.quitOnLastWindowClosed()
    outcome: List[Optional[QPixmap]] = [None]
    try:
        QApplication.setQuitOnLastWindowClosed(False)
        if was_visible:
            window.hide()
            _wait(HIDE_SETTLE_MS)
        overlay = _RegionGrabOverlay(
            screen.grabWindow(0),
            lambda picked: outcome.__setitem__(0, picked),
        )
        overlay.setGeometry(screen.geometry())
        overlay.showFullScreen()
        loop = QEventLoop()
        overlay.destroyed.connect(loop.quit)
        loop.exec()
    finally:
        if was_visible:
            window.show()
        QApplication.setQuitOnLastWindowClosed(quit_on_last)
    return outcome[0]
