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
