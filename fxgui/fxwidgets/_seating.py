"""Where a tray panel sits on screen, and how it arrives there."""

# Built-in
from typing import Optional, Tuple

# Third-party
from qtpy.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
)
from qtpy.QtGui import QGuiApplication, QScreen
from qtpy.QtWidgets import QWidget


class FXSeating:
    """Seat a panel in the screen corner nearest its tray icon; slide it in.

    The corner nearest the icon, else the pointer (the icon is in the
    overflow flyout), else the lower right; `EDGE_GAP` off both edges, as
    Windows seats its own flyouts. A panel not yet on screen rises into its
    seat while it fades up.

    Args:
        panel: The top-level widget to seat.

    Examples:
        >>> seating = FXSeating(panel)
        >>> tray.activated.connect(
        ...     lambda _r: seating.show_at(tray.geometry(), QCursor.pos())
        ... )
    """

    # Clear of the anchor and screen edges, with room for a shadow.
    EDGE_GAP = 12
    ENTRANCE_MS = 160
    ENTRANCE_SLIDE = 12

    def __init__(self, panel: QWidget):
        self._panel = panel
        # So a resize re-seats against the same icon or pointer.
        self._anchor: Optional[Tuple[QRect, Optional[QPoint]]] = None
        # One group so rise and fade cannot drift; OutCubic arrives slowing.
        self.entrance = QParallelAnimationGroup(panel)
        self._slide = QPropertyAnimation(panel, b"pos")
        self._fade = QPropertyAnimation(panel, b"windowOpacity")
        for step in (self._slide, self._fade):
            step.setDuration(self.ENTRANCE_MS)
            step.setEasingCurve(QEasingCurve.OutCubic)
            self.entrance.addAnimation(step)

    @staticmethod
    def anchor_point(tray: QRect, cursor: Optional[QPoint]) -> Optional[QPoint]:
        """Return the tray icon's middle, else `cursor`, else None."""
        if not tray.isEmpty():
            return tray.center()
        return cursor

    @classmethod
    def popup_corner(
        cls,
        size: QSize,
        tray: QRect,
        cursor: Optional[QPoint],
        screen: QRect,
    ) -> QPoint:
        """Return where a panel of `size` puts its top-left, inside `screen`.

        Args:
            size: The panel's real size; a never-shown panel's `sizeHint`
                is too small and spills off the corner.
            tray: `QSystemTrayIcon.geometry()`, possibly empty.
            cursor: The pointer for a clicked show, None for an automatic one.
            screen: The target screen's `availableGeometry()`.
        """
        point = cls.anchor_point(tray, cursor)
        if point is None:
            point = screen.bottomRight()
        # Pushed to the edge, so `clamp` leaves the same gap on both sides.
        x = screen.left() if point.x() < screen.center().x() else screen.right()
        y = screen.top() if point.y() < screen.center().y() else screen.bottom()
        return cls.clamp(QPoint(x, y), size, screen, cls.EDGE_GAP)

    @staticmethod
    def clamp(corner: QPoint, size: QSize, screen: QRect, gap: int = 0) -> QPoint:
        """Return `corner` moved so a `size` rect sits `gap` inside `screen`."""
        right = screen.right() - size.width() + 1 - gap
        bottom = screen.bottom() - size.height() + 1 - gap
        return QPoint(
            max(screen.left() + gap, min(corner.x(), right)),
            max(screen.top() + gap, min(corner.y(), bottom)),
        )

    def screen_for(self, tray: QRect, cursor: Optional[QPoint]) -> Optional[QScreen]:
        """Return the anchor's screen, else the panel's own.

        The anchor's, not the panel's: on two monitors the panel may be a
        screen away.
        """
        point = self.anchor_point(tray, cursor)
        screen = (
            QGuiApplication.primaryScreen()
            if point is None
            else QGuiApplication.screenAt(point)
        )
        return screen if screen is not None else self._panel.screen()

    def show_at(self, tray: QRect, cursor: Optional[QPoint]) -> None:
        """Seat the panel against this anchor and bring it to the front.

        A panel not on screen slides in; one already up is only raised.
        """
        entering = not self._panel.isVisible()
        self._anchor = (tray, cursor)
        self.seat()
        if entering:
            self._arm()
        self._panel.show()
        self._panel.raise_()
        self._panel.activateWindow()
        if entering:
            self.entrance.start()

    def seat(self) -> None:
        """Move the panel against its last anchor at its real size.

        Call from the panel's `resizeEvent` too. Does nothing before the
        first `show_at`.
        """
        if self._anchor is None:
            return
        tray, cursor = self._anchor
        screen = self.screen_for(tray, cursor)
        if screen is None:
            return
        self._panel.adjustSize()
        self._panel.move(
            self.popup_corner(
                self._panel.size(), tray, cursor, screen.availableGeometry()
            )
        )

    def stop(self) -> None:
        """Abandon an entrance and leave the panel opaque; call on hide."""
        self.entrance.stop()
        self._panel.setWindowOpacity(1.0)

    def center(self) -> None:
        """Centre the panel on its screen and forget the anchor."""
        self._anchor = None
        screen = self._panel.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self._panel.adjustSize()
        size = self._panel.size()
        self._panel.move(
            area.center().x() - size.width() // 2,
            area.center().y() - size.height() // 2,
        )

    def _arm(self) -> None:
        """Start the panel low and clear, aimed at where it was seated."""
        seated = self._panel.pos()
        start = QPoint(seated.x(), seated.y() + self.ENTRANCE_SLIDE)
        self._slide.setStartValue(start)
        self._slide.setEndValue(seated)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._panel.move(start)
        self._panel.setWindowOpacity(0.0)
