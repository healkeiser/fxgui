"""Animated toggle switch widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import (
    Property,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
)
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QAbstractButton, QSizePolicy, QWidget

# Internal
from fxgui import fxstyle

# The track's size, and the thumb's inset in it: a 16 px thumb.
_TRACK_WIDTH = 36
_TRACK_HEIGHT = 20
_INSET = 2


class FXToggleSwitch(QAbstractButton):
    """An on/off switch that slides, as tall as a push button.

    Its edge and thumb read at `fxstyle.CONTROL_CONTRAST` on every theme;
    hover, focus and disabled wear the push button's tokens.

    Args:
        parent: Parent widget.
        on_color: A theme token or a colour, when on. Defaults to the accent.
        off_color: A token or a colour, when off. Defaults to the sunken
            surface.
        thumb_color: A token or a colour for the thumb. Defaults to the muted
            text off and the on-accent text on.

    Signals:
        toggled: Emitted when the switch state changes.

    Examples:
        >>> switch = FXToggleSwitch()
        >>> switch.toggled.connect(lambda checked: print(f"Switch: {checked}"))
        >>> switch.setChecked(True)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_color: Optional[str] = None,
        off_color: Optional[str] = None,
        thumb_color: Optional[str] = None,
    ):
        super().__init__(parent)

        # None reads the theme's colour when painted.
        self._custom_on_color = on_color
        self._custom_off_color = off_color
        self._custom_thumb_color = thumb_color

        # Animation position (0.0 = off, 1.0 = on)
        self._position = 0.0

        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setEasingCurve(fxstyle.ease_out())
        self._animation.setDuration(fxstyle.MOTION_BASE)

        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        # QAbstractButton toggles on Space once it can take focus.
        self.setFocusPolicy(Qt.StrongFocus)

        self.toggled.connect(self._on_toggled)

    def sizeHint(self):
        """Return the preferred size of the switch."""
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        """Return the minimum size of the switch."""
        # A row's height, so it centres beside a button; the track inside
        # is its own size.
        return QSize(_TRACK_WIDTH, fxstyle.control_height(self))

    def hitButton(self, pos):
        """Return True if pos is inside the clickable area."""
        return self.rect().contains(pos)

    @Property(float)
    def position(self) -> float:
        """The current animation position (0.0-1.0)."""
        return self._position

    @position.setter
    def position(self, value: float) -> None:
        """Set the animation position and trigger repaint."""
        self._position = value
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        """Slide to the new state, or jump there while nobody sees it."""
        self._animation.stop()
        end = 1.0 if checked else 0.0
        if not self.isVisible() or not fxstyle.motion():
            self.position = end
            return
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(end)
        self._animation.start()

    def checkStateSet(self) -> None:
        """Follow a `setChecked` too, which says nothing with signals blocked."""
        super().checkStateSet()
        self._on_toggled(self.isChecked())

    def enterEvent(self, event) -> None:
        """Repaint to show the hover state."""
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:
        """Repaint to hide the hover state."""
        super().leaveEvent(event)
        self.update()

    def _inks(self):
        """Return the track fill, edge and thumb inks for the current state."""
        theme = fxstyle.colors()

        def reads(ink, on=theme.surface):
            return fxstyle.readable_ink(on, ink, fxstyle.CONTROL_CONTRAST)

        if not self.isEnabled():
            # As a disabled push button, and a disabled primary one when on.
            fill = theme.surface_alt if self.isChecked() else theme.surface
            return fill, theme.border, theme.text_disabled
        def custom(value):
            return fxstyle.qcolor(value).name() if value else None

        hovered = self.underMouse()
        on = custom(self._custom_on_color) or reads(
            theme.primary_button_hover if hovered else theme.accent_primary
        )
        off = custom(self._custom_off_color) or (
            theme.state_hover if hovered else theme.surface_sunken
        )
        position = self._position
        fill = fxstyle.mix(off, on, position)
        if fxstyle.focus_visible(self):
            edge = theme.text if self.isChecked() else reads(theme.accent_primary)
        else:
            edge = fxstyle.mix(theme.control_edge, on, position)
        thumb = custom(self._custom_thumb_color) or fxstyle.mix(
            reads(theme.text_muted, off),
            reads(theme.text_on_accent_primary, on),
            position,
        )
        return fill, edge, thumb

    def track_rect(self) -> QRect:
        """Return the track: `_TRACK_WIDTH` by `_TRACK_HEIGHT`, centred."""
        width = min(self.width(), _TRACK_WIDTH)
        height = min(self.height(), _TRACK_HEIGHT)
        return QRect(
            (self.width() - width) // 2,
            (self.height() - height) // 2,
            width,
            height,
        )

    def paintEvent(self, event) -> None:
        """Paint the track, its edge and the thumb."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        fill, edge, thumb = (QColor(ink) for ink in self._inks())

        box = self.track_rect()
        # Half a pixel in, so the whole 1 px edge is drawn; a pill.
        track = QRectF(box).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = track.height() / 2
        painter.setPen(edge)
        painter.setBrush(fill)
        painter.drawRoundedRect(track, radius, radius)

        size = box.height() - _INSET * 2
        x = box.left() + _INSET + self._position * (
            box.width() - size - _INSET * 2
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(thumb)
        painter.drawEllipse(QRectF(x, box.top() + _INSET, size, size))
        painter.end()
