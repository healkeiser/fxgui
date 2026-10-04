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
from fxgui.fxwidgets._severity import SEVERITIES, severity_icon


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
    }
    FXProgressCard QLabel#fxProgressCardDescription,
    FXProgressCard QLabel#fxProgressCardPercentage {
        color: @text_muted;
    }
    """
)


class FXProgressCard(QFrame):
    """A card showing a task's progress: a title, a bar, a status icon.

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

        progress = max(0, min(100, progress))
        self._progress = progress
        self._status = status

        self.setFrameShape(QFrame.StyledPanel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(fxstyle.PANE_GAP)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(fxstyle.PANE_GAP)

        if icon:
            # Beside the title, so in the title's own icon ink.
            task_icon = FXIconLabel(size=18)
            task_icon.setFixedSize(20, 20)
            task_icon.setIcon(fxicons.get_icon(icon, color="icon"))
            header_layout.addWidget(task_icon)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("fxProgressCardTitle")
        fxstyle.mark_as_title(self._title_label, rank="section")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        self._status_icon = FXIconLabel(size=18)
        self._status_icon.setFixedSize(20, 20)
        header_layout.addWidget(self._status_icon)

        main_layout.addLayout(header_layout)

        # Parented first: shown parentless, it would flash as a window.
        self._description_label = QLabel(description or "", self)
        self._description_label.setObjectName("fxProgressCardDescription")
        self._description_label.setWordWrap(True)
        self._description_label.setVisible(bool(description))
        main_layout.addWidget(self._description_label)

        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(fxstyle.PANE_GAP)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(progress)
        self._progress_bar.setTextVisible(False)
        progress_layout.addWidget(self._progress_bar, 1)

        self._percentage_label = None
        if show_percentage:
            self._percentage_label = QLabel(f"{progress}%")
            self._percentage_label.setObjectName("fxProgressCardPercentage")
            self._percentage_label.setFixedWidth(40)
            self._percentage_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            progress_layout.addWidget(self._percentage_label)

        fxutils.add_shadow(self)

        main_layout.addLayout(progress_layout)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._update_status_icon()

    def set_progress(self, value: int) -> None:
        """Set the progress value.

        Args:
            value: Progress value (0-100).
        """
        value = max(0, min(100, value))
        if value != self._progress:
            self._progress = value
            self._progress_bar.setValue(value)
            if self._percentage_label is not None:
                self._percentage_label.setText(f"{value}%")
            self.progress_changed.emit(value)

            if value >= 100:
                self.completed.emit()

    def set_title(self, title: str) -> None:
        """Set the card title.

        Args:
            title: The new title.
        """
        self._title_label.setText(title)

    def set_description(self, description: str) -> None:
        """Set the card description.

        Args:
            description: The new description.
        """
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
        if self._status not in SEVERITIES:
            self._status_icon.setIcon(None)
            self._status_icon.setVisible(False)
        else:
            self._status_icon.setIcon(severity_icon(self._status))
            self._status_icon.setVisible(True)
