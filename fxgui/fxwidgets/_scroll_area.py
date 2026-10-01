"""Custom scroll area widgets."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QSize, Signal
from qtpy.QtWidgets import QScrollArea, QWidget


class FXResizedScrollArea(QScrollArea):
    """A scroll area that says when it is resized, and can fit its content.

    Given a `floor` or a `cap`, its minimum height is its content's height,
    held between the two, and follows the content as rows come and go: the
    area grows with a short list and scrolls a long one. Qt loses the
    content's height a few layouts deep, so it is read here.

    Args:
        parent: Parent widget.
        floor: The least height, in pixels, however short the content.
        cap: The most height the content may ask for; past it, it scrolls.

    Signals:
        resized: Emitted when the scroll area is resized.

    Examples:
        >>> checks = FXResizedScrollArea(floor=60, cap=240)
        >>> checks.setWidgetResizable(True)
    """

    resized = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        floor: Optional[int] = None,
        cap: Optional[int] = None,
    ):
        super().__init__(parent)
        self._floor = floor
        self._cap = cap

    def minimumSizeHint(self) -> QSize:
        """Return the content's height between `floor` and `cap`, if set."""
        hint = super().minimumSizeHint()
        content = self.widget()
        if content is None or (self._floor is None and self._cap is None):
            return hint
        height = max(content.sizeHint().height(), self._floor or 0)
        if self._cap is not None:
            height = min(height, self._cap)
        return QSize(hint.width(), height)

    def viewportEvent(self, event: QEvent) -> bool:
        """Tell the layout outside when the content's height changes."""
        handled = super().viewportEvent(event)
        if event.type() == QEvent.LayoutRequest:
            self.updateGeometry()
        return handled

    def resizeEvent(self, event):
        """Emit the resized signal when the widget is resized."""
        self.resized.emit()
        return super().resizeEvent(event)


def example() -> None:
    import sys
    from qtpy.QtWidgets import (
        QGroupBox,
        QLabel,
        QVBoxLayout,
        QWidget,
    )
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXResizedScrollArea Demo")
    window.resize(400, 300)
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)

    # Status label to show resize events
    status_label = QLabel("Resize the window to see events")
    layout.addWidget(status_label)

    # Scroll area group
    scroll_group = QGroupBox("Resized Scroll Area")
    scroll_layout = QVBoxLayout(scroll_group)

    # Create the scroll area
    scroll_area = FXResizedScrollArea()
    scroll_area.setWidgetResizable(True)

    # Create content widget with many items
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    for i in range(20):
        content_layout.addWidget(
            QLabel(f"Item {i + 1}: Scroll down to see more content")
        )

    scroll_area.setWidget(content_widget)

    # Track resize count
    resize_count = 0

    def on_resized():
        nonlocal resize_count
        resize_count += 1
        status_label.setText(f"Scroll area resized {resize_count} times")

    scroll_area.resized.connect(on_resized)

    scroll_layout.addWidget(scroll_area)
    layout.addWidget(scroll_group)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
