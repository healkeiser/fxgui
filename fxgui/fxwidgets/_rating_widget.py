"""Star/score rating widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._labels import FXIconLabel


class FXRatingWidget(QWidget):
    """A clickable star rating widget.

    This widget provides a configurable star rating with:
    - Configurable max stars
    - Half-star support (optional)
    - Hover preview
    - Theme-aware icons

    Args:
        parent: Parent widget.
        max_rating: Maximum number of stars.
        initial_rating: Initial rating value.
        allow_half: Whether to allow half-star ratings.
        icon_size: Size of star icons in pixels.
        filled_icon: Icon name for filled stars.
        empty_icon: Icon name for empty stars.
        half_icon: Icon name for half-filled stars.

    Signals:
        rating_changed: Emitted when the rating changes.

    Examples:
        >>> rating = FXRatingWidget(max_rating=5, initial_rating=3)
        >>> rating.rating_changed.connect(lambda r: print(f"Rating: {r}"))
    """

    rating_changed = Signal(float)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        max_rating: int = 5,
        initial_rating: float = 0,
        allow_half: bool = False,
        icon_size: int = 20,
        filled_icon: str = "star",
        empty_icon: str = "star_border",
        half_icon: str = "star_half",
    ):
        super().__init__(parent)

        self._max_rating = max_rating
        self._rating = 0
        self._allow_half = allow_half
        self._icon_size = icon_size
        self._filled_icon = filled_icon
        self._empty_icon = empty_icon
        self._half_icon = half_icon
        self._hover_rating: Optional[float] = None

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Create star labels
        self._stars: list = []
        for _ in range(max_rating):
            star = FXIconLabel(size=icon_size)
            star.setFixedSize(icon_size, icon_size)
            star.setAlignment(Qt.AlignCenter)
            self._stars.append(star)
            layout.addWidget(star)

        layout.addStretch()

        self._update_stars()
        # Through the setter, so it is clamped and rounded like any other.
        self.set_rating(initial_rating, emit=False)

        # Mouse tracking
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        # Keyboard: arrow keys adjust, digits set, Delete/Backspace clears
        self.setFocusPolicy(Qt.StrongFocus)
        fxstyle._watch_focus()

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def rating(self) -> float:
        """Return the current rating."""
        return self._rating

    def set_rating(self, rating: float, emit: bool = True) -> None:
        """Set the rating value.

        Args:
            rating: The rating value (0 to max_rating).
            emit: Whether to emit the rating_changed signal.
        """
        rating = max(0, min(rating, self._max_rating))
        if not self._allow_half:
            rating = round(rating)

        if rating != self._rating:
            self._rating = rating
            self._update_stars()
            if emit:
                self.rating_changed.emit(rating)

    def clear_rating(self) -> None:
        """Clear the rating (set to 0)."""
        self.set_rating(0)

    def _update_stars(self) -> None:
        """Update star icons based on current rating."""
        empty_color = "text_disabled"
        display_rating = (
            self._hover_rating
            if self._hover_rating is not None
            else self._rating
        )
        # The accent is the set value; a preview under the pointer is not.
        color = "text" if self._hover_rating is not None else "accent_primary"

        for i, star in enumerate(self._stars):
            star_value = i + 1

            if display_rating >= star_value:
                # Full star
                icon = fxicons.get_icon(self._filled_icon, color=color)
            elif self._allow_half and display_rating >= star_value - 0.5:
                # Half star
                icon = fxicons.get_icon(self._half_icon, color=color)
            else:
                # Empty star
                icon = fxicons.get_icon(self._empty_icon, color=empty_color)

            star.setIcon(icon)

    def _get_rating_from_pos(self, x: int) -> float:
        """Calculate rating from mouse x position."""
        star_width = self._icon_size + self.layout().spacing()
        total_width = star_width * self._max_rating

        if x < 0:
            return 0
        if x >= total_width:
            return self._max_rating

        # Calculate which star we're over
        star_index = x // star_width
        star_offset = (x % star_width) / star_width

        if self._allow_half:
            if star_offset < 0.5:
                return star_index + 0.5
            else:
                return star_index + 1
        else:
            return star_index + 1

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Adjust the rating from the keyboard.

        Left/Down decrease, Right/Up increase (by 0.5 when half stars are
        allowed), digit keys set the rating directly, Home/End jump to the
        extremes, and Delete/Backspace clear it.
        """
        step = 0.5 if self._allow_half else 1
        key = event.key()

        if key in (Qt.Key_Right, Qt.Key_Up):
            self.set_rating(self._rating + step)
        elif key in (Qt.Key_Left, Qt.Key_Down):
            self.set_rating(self._rating - step)
        elif key == Qt.Key_Home:
            self.set_rating(0)
        elif key == Qt.Key_End:
            self.set_rating(self._max_rating)
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.clear_rating()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            self.set_rating(key - Qt.Key_0)
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def paintEvent(self, event) -> None:
        """Paint a focus indicator under the star labels when focused."""
        super().paintEvent(event)
        if fxstyle.focus_visible(self):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(fxstyle.colors().accent_primary))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            radius = fxstyle.BUTTON_RADIUS
            painter.drawRoundedRect(
                self.rect().adjusted(0, 0, -1, -1), radius, radius
            )
            painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Preview the rating under the pointer."""
        self._hover(self._get_rating_from_pos(int(event.position().x())))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse click to set rating."""
        if event.button() == Qt.LeftButton:
            rating = self._get_rating_from_pos(int(event.position().x()))
            self.set_rating(rating)

    def leaveEvent(self, event) -> None:
        """Drop the hover preview."""
        self._hover(None)

    def _hover(self, rating: Optional[float]) -> None:
        """Preview `rating`, redrawing the stars only when it changes."""
        if rating != self._hover_rating:
            self._hover_rating = rating
            self._update_stars()
