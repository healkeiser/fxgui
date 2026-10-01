"""Floating popup dialog."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import (
    QCursor,
    QIcon,
    QMouseEvent,
    QPixmap,
)
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxdcc, fxicons, fxstyle, fxutils
from fxgui.fxwidgets._labels import FXIconLabel

# Title, body and buttons start on one left edge.
_GUTTER = 12

fxstyle.register_widget_style(
    """
    FXFloatingDialog {
        background: transparent;
    }
    #FXFloatingDialogContainer {
        background-color: @surface;
        border: 1px solid @border;
        border-radius: @card_radius;
    }
    #fxFloatingDialogTitle {
        background-color: @surface_sunken;
        border-top-left-radius: %(inner)dpx;
        border-top-right-radius: %(inner)dpx;
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
    # The title sits 1 px inside the frame's border.
    % {"inner": fxstyle.CARD_RADIUS - 1}
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

        # Window - frameless with transparent background for rounded corners
        self.setAttribute(Qt.WA_DeleteOnClose)
        if popup:
            self.setWindowFlags(
                Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
            )
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            # A shadow on a popup leaves artifacts.
            fxutils.add_shadows(self._container, self._container)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(200, 40)

        # Inside a DCC the host application carries no fxgui sheet.
        fxstyle.register_themed_root(self)

    # Private methods
    def _setup_title(self):
        """Sets up the title bar with icon and label.

        Warning:
            This method is intended for internal use only.
        """

        self._icon_label = FXIconLabel(parent=self, size=22)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setFixedSize(24, 24)
        self.title_widget = QWidget(self)
        self.title_widget.setObjectName("fxFloatingDialogTitle")

        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fxstyle.mark_as_title(self.title_label, rank="section")

        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setContentsMargins(_GUTTER, 8, _GUTTER, 8)
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
        self.main_layout.setContentsMargins(_GUTTER, 12, _GUTTER, 12)
        self.main_layout.setSpacing(8)

    def _setup_buttons(self):
        """Sets up the dialog button box with close button.

        Warning:
            This method is intended for internal use only.
        """

        self.button_box = QDialogButtonBox(self)
        self.button_box.setObjectName("fxFloatingDialogButtons")
        self.button_box.setContentsMargins(_GUTTER, 8, _GUTTER, _GUTTER)
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

        self._icon_label.setIcon(
            QIcon(icon) if icon else fxicons.get_icon("home"))
        self.dialog_icon = icon or self._icon_label.pixmap()

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
