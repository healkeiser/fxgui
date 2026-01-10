"""Task progress card widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qtpy.QtGui import QColor

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._constants import (
    CRITICAL,
    ERROR,
    WARNING,
    SUCCESS,
    INFO,
    DEBUG,
)


class FXProgressCard(fxstyle.FXThemeAware, QFrame):
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
        None: None,
        CRITICAL: ("cancel", "error"),
        ERROR: ("error", "error"),
        WARNING: ("warning", "warning"),
        SUCCESS: ("check_circle", "success"),
        INFO: ("info", "info"),
        DEBUG: ("bug_report", "debug"),
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
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setStyleSheet("background: transparent;")
        if icon:
            header_layout.addWidget(self._icon_label)

        # Title
        self._title_label = QLabel(title)
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        # Status icon
        self._status_icon = QLabel()
        self._status_icon.setFixedSize(20, 20)
        self._status_icon.setStyleSheet("background: transparent;")
        self._update_status_icon()
        header_layout.addWidget(self._status_icon)

        main_layout.addLayout(header_layout)

        # Description
        self._description_label = None
        if description:
            self._description_label = QLabel(description)
            self._description_label.setWordWrap(True)
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
            self._percentage_label.setFixedWidth(40)
            self._percentage_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            progress_layout.addWidget(self._percentage_label)

        # Setup drop shadow effect
        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setBlurRadius(20)
        self._shadow_effect.setOffset(0, 0)
        self._shadow_effect.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self._shadow_effect)

        main_layout.addLayout(progress_layout)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        # Frame styling
        self.setStyleSheet(
            f"""
            FXProgressCard {{
                background-color: {self.theme.surface};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """
        )

        # Task icon
        if self._icon:
            task_icon = fxicons.get_icon(
                self._icon, color=self.theme.text_muted
            )
            self._icon_label.setPixmap(task_icon.pixmap(18, 18))

        # Title label
        self._title_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self.theme.text};
                font-weight: bold;
                font-size: 14px;
                background: transparent;
            }}
        """
        )

        # Description label
        if self._description_label:
            self._description_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {self.theme.text_muted};
                    font-size: 12px;
                    background: transparent;
                }}
            """
            )

        # Progress bar
        self._progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {self.theme.surface_sunken};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {self.theme.accent_primary};
                border-radius: 2px;
            }}
        """
        )

        # Percentage label
        if self._percentage_label:
            self._percentage_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {self.theme.text_muted};
                    font-size: 12px;
                    background: transparent;
                }}
            """
            )

        # Update status icon
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
        if hasattr(self, "_description_label"):
            self._description_label.setText(description)

    def set_status(self, status: Optional[int]) -> None:
        """Set the status icon.

        Args:
            status: Status constant (SUCCESS, ERROR, WARNING, etc.) or None.
        """
        self._status = status
        self._update_status_icon()

    def _update_status_icon(self) -> None:
        """Update the status icon based on current status."""
        if self._status is None or self._status not in self.STATUS_ICONS:
            self._status_icon.clear()
            self._status_icon.setVisible(False)
        else:
            icon_name, feedback_key = self.STATUS_ICONS[self._status]
            colors = fxstyle.get_colors()
            color = colors["feedback"][feedback_key]["foreground"]
            icon = fxicons.get_icon(icon_name, color=color)
            self._status_icon.setPixmap(icon.pixmap(18, 18))
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


def example() -> None:
    import sys
    from qtpy.QtWidgets import (
        QVBoxLayout,
        QWidget,
        QPushButton,
        QHBoxLayout,
    )
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXProgressCard Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    card1 = FXProgressCard(
        title="Rendering Scene",
        description="Processing frames 1-100...",
        icon="movie",
    )
    card1.set_progress(35)

    card2 = FXProgressCard(
        title="Export Complete",
        description="All assets exported successfully.",
        icon="upload",
    )
    card2.set_progress(100)
    card2.set_status(SUCCESS)

    card3 = FXProgressCard(
        title="Texture Baking",
        description="Error: Out of memory",
        icon="texture",
    )
    card3.set_progress(67)
    card3.set_status(ERROR)

    # Control buttons
    controls = QHBoxLayout()
    inc_btn = QPushButton("Increment")
    reset_btn = QPushButton("Reset")
    inc_btn.clicked.connect(lambda: card1.increment(5))
    reset_btn.clicked.connect(card1.reset)
    controls.addWidget(inc_btn)
    controls.addWidget(reset_btn)

    layout.addWidget(card1)
    layout.addWidget(card2)
    layout.addWidget(card3)
    layout.addLayout(controls)
    layout.addStretch()

    window.resize(400, 350)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
