"""Task progress card widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._severity import SEVERITIES


fxstyle.register_widget_style(
    """
    FXProgressCard {
        background-color: @surface;
        border: 1px solid @border;
        border-radius: @card_radius;
    }
    FXProgressCard QLabel {
        background: transparent;
    }
    FXProgressCard QLabel#fxProgressCardTitle {
        color: @text;
        font-weight: bold;
        font-size: 14px;
    }
    FXProgressCard QLabel#fxProgressCardDescription,
    FXProgressCard QLabel#fxProgressCardPercentage {
        color: @text_muted;
        font-size: 12px;
    }
    FXProgressCard QProgressBar:horizontal {
        background-color: @surface_sunken;
        border: none;
        border-radius: 3px;
        padding: 0px;
    }
    FXProgressCard QProgressBar::chunk:horizontal {
        background-color: @accent_primary;
        /* The bar's own pill: it fills the bar edge to edge. */
        border-radius: 3px;
    }
    """
)


class FXProgressCard(QFrame):
    """A card widget showing task/step progress.

    This widget provides a styled card with:
    - Title and description
    - Progress bar or circular progress
    - Status icon
    - Perfect for pipeline tools and task tracking

    Args:
        parent: Parent widget.
        title: Card title.
        description: Optional description text.
        progress: Initial progress value (0-100).
        status: Status icon type (SUCCESS, ERROR, WARNING, INFO, etc.).
        show_percentage: Whether to show percentage text.
        icon: Optional icon name to display next to the title.

    Signals:
        progress_changed: Emitted when progress changes.
        completed: Emitted when progress reaches 100%.

    Examples:
        >>> card = FXProgressCard(
        ...     title="Rendering",
        ...     description="Frame 50/100",
        ...     progress=50
        ... )
        >>> card.set_progress(75)
    """

    progress_changed = Signal(int)
    completed = Signal()

    # Status icon names mapped to feedback color keys
    STATUS_ICONS = {
        level: (kind.icon, kind.feedback) for level, kind in SEVERITIES.items()
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Task",
        description: Optional[str] = None,
        progress: int = 0,
        status: Optional[int] = None,
        show_percentage: bool = True,
        icon: Optional[str] = None,
    ):
        super().__init__(parent)

        self._title = title
        self._description = description
        self._progress = progress
        self._status = status
        self._show_percentage = show_percentage
        self._icon = icon

        # Frame styling
        self.setFrameShape(QFrame.StyledPanel)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

        # Header row (icon + title + status icon)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Task icon
        self._icon_label = FXIconLabel(size=18)
        self._icon_label.setFixedSize(20, 20)
        if icon:
            header_layout.addWidget(self._icon_label)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setObjectName("fxProgressCardTitle")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        # Status icon
        self._status_icon = FXIconLabel(size=18)
        self._status_icon.setFixedSize(20, 20)
        header_layout.addWidget(self._status_icon)

        main_layout.addLayout(header_layout)

        # Description
        self._description_label = QLabel(description or "")
        self._description_label.setObjectName("fxProgressCardDescription")
        self._description_label.setWordWrap(True)
        self._description_label.setVisible(bool(description))
        main_layout.addWidget(self._description_label)

        # Progress row
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(progress)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        progress_layout.addWidget(self._progress_bar, 1)

        # Percentage label
        self._percentage_label = None
        if show_percentage:
            self._percentage_label = QLabel(f"{progress}%")
            self._percentage_label.setObjectName("fxProgressCardPercentage")
            self._percentage_label.setFixedWidth(40)
            self._percentage_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            progress_layout.addWidget(self._percentage_label)

        # Setup drop shadow effect
        self._shadow_effect = fxutils.add_shadows(self, self)

        main_layout.addLayout(progress_layout)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if self._icon:
            self._icon_label.setIcon(
                fxicons.get_icon(self._icon, color="text_muted"))
        self._update_status_icon()

    @property
    def progress(self) -> int:
        """Return the current progress value."""
        return self._progress

    @progress.setter
    def progress(self, value: int) -> None:
        """Set the progress value."""
        self.set_progress(value)

    def set_progress(self, value: int) -> None:
        """Set the progress value.

        Args:
            value: Progress value (0-100).
        """
        value = max(0, min(100, value))
        if value != self._progress:
            self._progress = value
            self._progress_bar.setValue(value)
            if self._show_percentage:
                self._percentage_label.setText(f"{value}%")
            self.progress_changed.emit(value)

            if value >= 100:
                self.completed.emit()

    def set_title(self, title: str) -> None:
        """Set the card title.

        Args:
            title: The new title.
        """
        self._title = title
        self._title_label.setText(title)

    def set_description(self, description: str) -> None:
        """Set the card description.

        Args:
            description: The new description.
        """
        self._description = description
        self._description_label.setText(description or "")
        self._description_label.setVisible(bool(description))

    def set_status(self, status: Optional[int]) -> None:
        """Set the status icon.

        Args:
            status: Status constant (SUCCESS, ERROR, WARNING, etc.) or None.
        """
        self._status = status
        self._update_status_icon()

    def _update_status_icon(self) -> None:
        """Update the status icon based on current status."""
        if self._status not in self.STATUS_ICONS:
            self._status_icon.setIcon(None)
            self._status_icon.setVisible(False)
        else:
            icon_name, feedback_key = self.STATUS_ICONS[self._status]
            self._status_icon.setIcon(fxicons.get_icon(
                icon_name, color=f"feedback_{feedback_key}_foreground"))
            self._status_icon.setVisible(True)

    def increment(self, amount: int = 1) -> None:
        """Increment the progress by a given amount.

        Args:
            amount: Amount to increment (default 1).
        """
        self.set_progress(self._progress + amount)

    def reset(self) -> None:
        """Reset progress to 0."""
        self.set_progress(0)
        self.set_status(None)
