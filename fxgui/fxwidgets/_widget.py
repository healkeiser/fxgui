"""Base widget with UI loading support."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle, fxutils


class FXWidget(fxstyle.FXThemeAware, QWidget):
    def __init__(
        self,
        parent=None,
        ui_file: Optional[str] = None,
    ):
        super().__init__(parent)

        # Attributes
        self.ui_file: str = ui_file
        self.ui = None

        # Methods
        self._load_ui()
        self._set_layout()

    # Private methods
    def _load_ui(self) -> None:
        """Loads the UI from the specified UI file and sets it as the central
        widget of the main window.

        Warning:
            This method is intended for internal use only.
        """

        if self.ui_file is not None:
            self.ui = fxutils.load_ui(self, self.ui_file)

    def _set_layout(self) -> None:
        """Sets the layout of the widget.

        Warning:
            This method is intended for internal use only.
        """

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(9, 9, 9, 9)
        if self.ui:
            self.layout.addWidget(self.ui)

    def _on_theme_changed(self) -> None:
        """Apply theme-specific styles to the widget.

        This method is called automatically when the theme changes.

        Warning:
            This method is intended for internal use only.
        """
        self.setStyleSheet(fxstyle.load_stylesheet())


def example() -> None:
    import sys
    from qtpy.QtWidgets import QLabel, QPushButton
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXWidget Demo")

    # Create a simple FXWidget
    widget = FXWidget()
    widget.layout.addWidget(QLabel("This is an FXWidget with styled theme."))
    widget.layout.addWidget(QPushButton("Click Me"))

    window.setCentralWidget(widget)
    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
