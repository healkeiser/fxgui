"""Star/score rating widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

# Internal
from fxgui import fxicons, fxstyle


class FXRatingWidget(fxstyle.FXThemeAware, QWidget):
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
        self._rating = initial_rating
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
        for i in range(max_rating):
            star = QLabel()
            star.setFixedSize(icon_size, icon_size)
            star.setAlignment(Qt.AlignCenter)
            self._stars.append(star)
            layout.addWidget(star)

        layout.addStretch()

        # Initial update
        self._update_stars()

        # Mouse tracking
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    @property
    def rating(self) -> float:
        """Return the current rating."""
        return self._rating

    @rating.setter
    def rating(self, value: float) -> None:
        """Set the rating."""
        self.set_rating(value)

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

    def get_rating(self) -> float:
        """Return the current rating."""
        return self._rating

    def clear_rating(self) -> None:
        """Clear the rating (set to 0)."""
        self.set_rating(0)

    def _update_stars(self) -> None:
        """Update star icons based on current rating."""
        # Get current theme colors (dynamic for theme switching)
        empty_color = self.theme.text_disabled
        filled_color = self.theme.accent_primary
        hover_color = self.theme.accent_secondary

        display_rating = (
            self._hover_rating
            if self._hover_rating is not None
            else self._rating
        )
        color = hover_color if self._hover_rating is not None else filled_color

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

            star.setPixmap(icon.pixmap(self._icon_size, self._icon_size))

    def _get_rating_from_pos(self, x: int) -> float:
        """Calculate rating from mouse x position."""
        star_width = self._icon_size + 2  # spacing
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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for hover preview."""
        self._hover_rating = self._get_rating_from_pos(event.x())
        self._update_stars()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse click to set rating."""
        if event.button() == Qt.LeftButton:
            rating = self._get_rating_from_pos(event.x())
            self.set_rating(rating)

    def leaveEvent(self, event) -> None:
        """Handle mouse leave to clear hover."""
        self._hover_rating = None
        self._update_stars()

    def enterEvent(self, event) -> None:
        """Handle mouse enter."""
        pass  # Just to ensure tracking works


def example() -> None:
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QLabel, QHBoxLayout
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXRatingWidget Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Standard rating
    row1 = QHBoxLayout()
    label1 = QLabel("Standard (5 stars):")
    rating1 = FXRatingWidget(max_rating=5)
    rating1.set_rating(3)
    row1.addWidget(label1)
    row1.addWidget(rating1)
    row1.addStretch()
    layout.addLayout(row1)

    # Half stars
    row2 = QHBoxLayout()
    label2 = QLabel("Half stars:")
    rating2 = FXRatingWidget(max_rating=5, allow_half=True)
    rating2.set_rating(3.5)
    row2.addWidget(label2)
    row2.addWidget(rating2)
    row2.addStretch()
    layout.addLayout(row2)

    # 10 star rating
    row3 = QHBoxLayout()
    label3 = QLabel("10-star rating:")
    rating3 = FXRatingWidget(max_rating=10)
    rating3.set_rating(7)
    row3.addWidget(label3)
    row3.addWidget(rating3)
    row3.addStretch()
    layout.addLayout(row3)

    info_label = QLabel("Click to rate")
    rating1.rating_changed.connect(lambda r: info_label.setText(f"Rating: {r}"))
    rating2.rating_changed.connect(lambda r: info_label.setText(f"Rating: {r}"))
    rating3.rating_changed.connect(lambda r: info_label.setText(f"Rating: {r}"))

    layout.addWidget(info_label)
    layout.addStretch()

    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
