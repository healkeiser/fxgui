"""VFXSplashscreen module.

This module contains the VFXSplashScreen class, a customized QSplashScreen class.
The VFXSplashScreen class provides a splash screen for your application. It allows
for customization of the splash screen image, title, information text, and more.
It also provides options for displaying a progress bar and applying a fade-in effect.

Classes:
    VFXSplashScreen: A class for creating a customized splash screen.
"""

# Built-in
import os
import time
from typing import Optional

# Third-party
from qtpy.QtWidgets import *
from qtpy.QtUiTools import *
from qtpy.QtCore import *
from qtpy.QtGui import *


# Internal
try:
    import utils, icons
except ModuleNotFoundError:
    utils, icons

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


class VFXFloatingDialog(QDialog):
    """A floating dialog that appears at the cursor's position.
    It closes when any mouse button except the right one is pressed.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
    ):
        """Constructor.

        Args:
            parent (QtWidget, optional): Parent widget. Defaults to `None`.
        """

        super().__init__(parent)

        # Attributes
        _icon = QPixmap(icons.get_icon_path("home"))
        _icon = icons.change_pixmap_color(_icon, "white")
        self._default_icon = _icon
        self.dialog_icon: QIcon = icon
        self.dialog_title: str = title

        self.drop_position = QCursor.pos()
        self.dialog_position = (
            self.drop_position.x() - (self.width() / 2),
            self.drop_position.y() - (self.height() / 2),
        )

        # Methods
        self._setup_title()
        self._setup_main_widget()
        self._setup_buttons()
        self._setup_layout()
        self._handle_connections()
        self.set_dialog_icon()
        self.set_dialog_title(self.dialog_title)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.resize(200, 40)
        self.setStyleSheet(
            """
            VFXFloatingDialog {
                border-top: 1px solid #949494;
                border-left: 1px solid #949494;
                border-bottom: 1px solid #262626;
                border-right: 1px solid #262626;
            }
        """
        )

    # - Private methods

    def _setup_title(self):
        """_summary_

        Warning:
            This method is intended for internal use only.
        """

        self._icon_label = QLabel(self)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title_widget = QWidget(self)
        self.title_widget.setStyleSheet("background-color: #2b2b2b;")

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignLeft)
        self.title_label.setFont(font)

        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setSpacing(10)
        self.title_layout.addWidget(self._icon_label)
        self.title_layout.addWidget(self.title_label)

    def _setup_main_widget(self):
        """_summary_

        Warning:
            This method is intended for internal use only.
        """

        self.main_widget = QWidget(self)
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

    def _setup_buttons(self):
        """_summary_

        Warning:
            This method is intended for internal use only.
        """

        self.button_box = QDialogButtonBox(self)
        self.button_box.setContentsMargins(10, 10, 10, 10)
        self.button_close = self.button_box.addButton(QDialogButtonBox.Close)

    def _setup_layout(self):
        """_summary_

        Warning:
            This method is intended for internal use only.
        """

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.addWidget(self.title_widget)
        self.layout.addWidget(self.main_widget)
        self.layout.addWidget(self.button_box)

    def _handle_connections(self) -> None:
        """Connects the dialog's slots."""

        self.button_box.rejected.connect(self.reject)
        self.button_box.rejected.connect(self.close)  # TODO: Check if needed

    # - Public methods

    def set_dialog_icon(self, icon: str = None) -> None:
        """Sets the dialog's icon.

        Args:
            icon (str): The path to the icon.
        """

        if self.dialog_icon is not None and os.path.isfile(self.dialog_icon):
            self._icon_label.setPixmap(
                QPixmap(self.dialog_icon).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self._icon_label.setPixmap(
                QPixmap(self._default_icon).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self.dialog_icon = icon

    def set_dialog_title(self, title: str = None) -> None:
        """Sets the dialog's title.

        Args:
            title (str): The title of the dialog.
        """

        if title is not None and len(title) >= 1:
            self.title_label.setText(title)
        else:
            self.title_label.setText("VFX | Floating Dialog")

    def show_under_cursor(self) -> int:
        """Moves the dialog to the current cursor position and displays it.

        Returns:
            int: The result of the `QDialog exec_()` method, which is an integer.
                It returns a `DialogCode` that can be `Accepted` or `Rejected`.
        """

        self.move(*self.dialog_position)
        return self.exec_()

    # - Events

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Closes the dialog when any mouse button except the right one is pressed.

        Args:
            event (QMouseEvent): The mouse press event.
        """

        if event.button() != Qt.RightButton:
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Removes the parent of the dialog and closes it.

        Args:
            event (QCloseEvent): The close event.
        """

        self.setParent(None)
        super().close()
