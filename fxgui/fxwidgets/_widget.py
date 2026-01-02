"""FXWidget - Base widget with UI loading support."""

from typing import Optional

from qtpy.QtWidgets import QVBoxLayout, QWidget

from fxgui import fxstyle, fxutils


class FXWidget(QWidget):
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

        # Styling
        self.setStyleSheet(fxstyle.load_stylesheet())

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
