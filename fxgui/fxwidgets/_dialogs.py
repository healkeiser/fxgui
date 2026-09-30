"""Floating popup dialog."""

# Built-in
import os
from typing import Optional

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import (
    QColor,
    QCursor,
    QFont,
    QMouseEvent,
    QPixmap,
)
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxdcc, fxicons, fxstyle
from fxgui.fxwidgets._application import FXApplication

fxstyle.register_widget_style(
    """
    FXFloatingDialog {
        background: transparent;
    }
    #FXFloatingDialogContainer {
        background-color: @surface;
        border: 1px solid @border;
        border-radius: 12px;
    }
    #fxFloatingDialogTitle {
        background-color: @surface_sunken;
        border-top-left-radius: 11px;
        border-top-right-radius: 11px;
    }
    #fxFloatingDialogTitle QLabel {
        background: transparent;
        color: @text;
    }
    #fxFloatingDialogBody {
        background: transparent;
    }
    #fxFloatingDialogBody QLabel {
        background: transparent;
        color: @text_muted;
    }
    #fxFloatingDialogButtons {
        background: transparent;
    }
    #fxFloatingDialogButtons QPushButton {
        background-color: @surface_alt;
        color: @text;
        border: 1px solid @border;
        border-radius: 6px;
        padding: 6px 16px;
        min-width: 60px;
    }
    #fxFloatingDialogButtons QPushButton:hover,
    #fxFloatingDialogButtons QPushButton:pressed {
        background-color: @accent_primary;
        border-color: @accent_primary;
        color: @text_on_accent_primary;
    }
    #FXFloatingDialogContainer[houdini="true"] {
        border-radius: 0px;
        border-top: 1px solid @border_light;
        border-left: 1px solid @border_light;
        border-bottom: 1px solid @surface;
        border-right: 1px solid @surface;
    }
    #FXFloatingDialogContainer[houdini="true"] #fxFloatingDialogTitle {
        background-color: @surface_alt;
        border-radius: 0px;
    }
    """
)


class FXFloatingDialog(QDialog):
    """A floating dialog that appears at the cursor's position.
    It closes when any mouse button except the right one is pressed.

    Args:
        parent (QtWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (QPixmap): The QPixmap icon. Defaults to a home icon in the
            theme's icon color.
        title (str): The dialog title.

    Attributes:
        dialog_icon (QPixmap): The icon of the dialog.
        dialog_title (str): The title of the dialog.
        parent_package (int): Whether the dialog is standalone application, or belongs to a DCC parent.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[QPixmap] = None,
        title: Optional[str] = None,
        parent_package: Optional[int] = None,
        popup: bool = False,
    ):
        super().__init__(parent)

        # Attributes
        self._custom_icon: Optional[QPixmap] = icon
        self.dialog_icon: QPixmap = icon
        self.dialog_title: str = title
        self.parent_package = parent_package

        # Methods
        self._setup_title()
        self._setup_main_widget()
        self._setup_buttons()
        self._setup_layout()
        self.set_dialog_icon(self.dialog_icon)
        self.set_dialog_title(self.dialog_title)
        fxstyle.theme_changed.connect(self._on_theme_changed)

        # Window - frameless with transparent background for rounded corners
        self.setAttribute(Qt.WA_DeleteOnClose)
        if popup:
            self.setWindowFlags(
                Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
            )
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            # A shadow on a popup leaves artifacts.
            shadow = QGraphicsDropShadowEffect(self._container)
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 100))
            self._container.setGraphicsEffect(shadow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(200, 40)

        # Inside a DCC the host application carries no fxgui sheet.
        if not isinstance(QApplication.instance(), FXApplication):
            fxstyle.register_themed_root(self)

    def _on_theme_changed(self, _theme_name: Optional[str] = None) -> None:
        """Re-render the default icon in the new theme's color."""
        if self._custom_icon is None:
            self.set_dialog_icon(None)

    # Private methods
    def _setup_title(self):
        """Sets up the title bar with icon and label.

        Warning:
            This method is intended for internal use only.
        """

        self._icon_label = QLabel(self)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setFixedSize(24, 24)
        self.title_widget = QWidget(self)
        self.title_widget.setObjectName("fxFloatingDialogTitle")

        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title_label.setFont(font)

        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setContentsMargins(12, 10, 12, 10)
        self.title_layout.setSpacing(10)
        self.title_layout.addWidget(self._icon_label)
        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch()

    def _setup_main_widget(self):
        """Sets up the main content widget and layout.

        Warning:
            This method is intended for internal use only.
        """

        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("fxFloatingDialogBody")
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(8)

    def _setup_buttons(self):
        """Sets up the dialog button box with close button.

        Warning:
            This method is intended for internal use only.
        """

        self.button_box = QDialogButtonBox(self)
        self.button_box.setObjectName("fxFloatingDialogButtons")
        self.button_box.setContentsMargins(12, 8, 12, 12)
        self.button_close = self.button_box.addButton(QDialogButtonBox.Close)
        # reject() closes, and WA_DeleteOnClose deletes, the dialog.
        self.button_box.rejected.connect(self.reject)

    def _setup_layout(self):
        """Sets up the main dialog layout with title, content, and buttons.

        Warning:
            This method is intended for internal use only.
        """

        # Container frame for opaque background with rounded corners
        self._container = QFrame(self)
        self._container.setObjectName("FXFloatingDialogContainer")
        self._container.setProperty(
            "houdini", self.parent_package == fxdcc.HOUDINI
        )

        # Container layout
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.title_widget)
        container_layout.addWidget(self.main_widget, 1)
        container_layout.addWidget(self.button_box)

        # Main dialog layout (transparent, holds the container)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)  # Margin for shadow
        layout.addWidget(self._container)

    # Public methods
    def set_dialog_icon(self, icon: Optional[QPixmap] = None) -> None:
        """Sets the dialog's icon; `None` is the theme's home icon.

        Args:
            icon (QPixmap, optional): The QPixmap icon.
        """

        self._custom_icon = icon or None
        if not icon:
            icon = fxicons.get_icon(
                "home", color=fxstyle.colors().icon
            ).pixmap(32, 32)
        self._icon_label.setPixmap(
            icon.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.dialog_icon = icon

    def set_dialog_title(self, title: str = None) -> None:
        """Sets the dialog's title.

        Args:
            title (str): The title of the dialog.
        """

        self.title_label.setText(title if title else "Floating Dialog")

    def show_under_cursor(self) -> int:
        """Centre the dialog on the cursor at its final size and run it.

        Returns:
            int: The result of the `QDialog exec_()` method, which is an integer.
                It returns a `DialogCode` that can be `Accepted` or `Rejected`.
        """

        self.adjustSize()
        geometry = self.frameGeometry()
        geometry.moveCenter(QCursor.pos())
        self.move(geometry.topLeft())
        return self.exec_()

    # Events
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Closes the dialog when any mouse button except the right one is pressed.

        Args:
            event (QMouseEvent): The mouse press event.
        """

        if event.button() != Qt.RightButton:
            self.close()


def example() -> None:
    import sys
    from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget, QLabel
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXFloatingDialog Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    # Basic floating dialog
    def show_basic_dialog():
        dialog = FXFloatingDialog(window, title="Basic Dialog")
        dialog.main_layout.addWidget(QLabel("This is a basic floating dialog."))
        dialog.show_under_cursor()

    # Dialog with custom icon
    def show_icon_dialog():
        icon = fxicons.get_icon("settings").pixmap(32, 32)
        dialog = FXFloatingDialog(window, icon=icon, title="Settings")
        dialog.main_layout.addWidget(QLabel("Configure your settings here."))
        dialog.main_layout.addWidget(QLabel("Option 1: Enabled"))
        dialog.main_layout.addWidget(QLabel("Option 2: Disabled"))
        dialog.resize(250, 150)
        dialog.show_under_cursor()

    # Popup style dialog
    def show_popup_dialog():
        dialog = FXFloatingDialog(window, title="Quick Info", popup=True)
        dialog.main_layout.addWidget(
            QLabel("This is a popup dialog.\nClick outside to close.")
        )
        dialog.resize(200, 80)
        dialog.show_under_cursor()

    # Buttons to trigger dialogs
    btn_basic = QPushButton("Show Basic Dialog")
    btn_basic.clicked.connect(show_basic_dialog)
    layout.addWidget(btn_basic)

    btn_icon = QPushButton("Show Dialog with Icon")
    btn_icon.clicked.connect(show_icon_dialog)
    layout.addWidget(btn_icon)

    btn_popup = QPushButton("Show Popup Dialog")
    btn_popup.clicked.connect(show_popup_dialog)
    layout.addWidget(btn_popup)

    layout.addStretch()

    window.resize(300, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
