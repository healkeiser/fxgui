"""Custom scroll area widgets."""

# Built-in
import os

# Third-party
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QScrollArea


class FXResizedScrollArea(QScrollArea):
    """A custom scroll area that emits a signal when resized.

    This widget extends QScrollArea to emit a `resized` signal whenever
    the widget is resized, which is useful for responsive layouts.

    Signals:
        resized: Emitted when the scroll area is resized.

    Examples:
        >>> scroll_area = FXResizedScrollArea()
        >>> scroll_area.resized.connect(lambda: print("Resized!"))
    """

    resized = Signal()

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
