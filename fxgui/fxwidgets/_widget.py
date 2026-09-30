"""Base widget with UI loading support."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Internal
from fxgui import fxutils


class FXWidget(QWidget):
    """Widget holding an optional Designer UI file in a padded box layout."""

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

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(9, 9, 9, 9)
        if self.ui:
            self.main_layout.addWidget(self.ui)


def example() -> None:
    import sys
    from qtpy.QtWidgets import QLabel, QPushButton
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXWidget Demo")

    # Create a simple FXWidget
    widget = FXWidget()
    widget.main_layout.addWidget(QLabel("This is an FXWidget with styled theme."))
    widget.main_layout.addWidget(QPushButton("Click Me"))

    window.setCentralWidget(widget)
    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
