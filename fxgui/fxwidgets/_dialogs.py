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
from fxgui import fxicons, fxstyle, fxutils
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
    """
    # The title sits 1 px inside the frame's border.
    % {"inner": fxstyle.CARD_RADIUS - 1}
)


class FXFloatingDialog(QDialog):
    """A floating dialog that appears at the cursor's position.

    It closes when any mouse button except the right one is pressed, and
    is deleted once closed.

    Args:
        parent: Parent widget. Defaults to `None`.
        icon: The title's icon. Defaults to a home icon in the theme's
            icon color.
        title: The dialog title. Defaults to "Floating Dialog".
        popup: Whether it closes on a click outside, as a menu does.
            A popup casts no painted shadow. Defaults to `False`.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[QPixmap] = None,
        title: Optional[str] = None,
        popup: bool = False,
    ):
        super().__init__(parent)

        self._icon_label = FXIconLabel(parent=self, size=22)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setFixedSize(24, 24)
        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        fxstyle.mark_as_title(self.title_label, rank="section")
        self.title_widget = QWidget(self)
        self.title_widget.setObjectName("fxFloatingDialogTitle")
        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setContentsMargins(_GUTTER, 8, _GUTTER, 8)
        self.title_layout.setSpacing(fxstyle.PANE_GAP)
        self.title_layout.addWidget(self._icon_label)
        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch()

        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("fxFloatingDialogBody")
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(_GUTTER, 12, _GUTTER, 12)
        self.main_layout.setSpacing(fxstyle.PANE_GAP)

        self.button_box = QDialogButtonBox(self)
        self.button_box.setObjectName("fxFloatingDialogButtons")
        self.button_box.setContentsMargins(_GUTTER, 8, _GUTTER, _GUTTER)
        self.button_close = self.button_box.addButton(QDialogButtonBox.Close)
        # reject() closes, and WA_DeleteOnClose deletes, the dialog.
        self.button_box.rejected.connect(self.reject)

        # The opaque rounded card; the dialog around it is transparent.
        self._container = QFrame(self)
        self._container.setObjectName("FXFloatingDialogContainer")
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.title_widget)
        container_layout.addWidget(self.main_widget, 1)
        container_layout.addWidget(self.button_box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)  # Room for the shadow
        layout.addWidget(self._container)

        self.set_dialog_icon(icon)
        self.set_dialog_title(title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        if popup:
            self.setWindowFlags(
                Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
            )
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            # A shadow on a popup leaves artifacts.
            fxutils.add_shadow(self._container)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(200, 40)

        # Inside a DCC the host application carries no fxgui sheet.
        fxstyle.register_themed_root(self)

    def set_dialog_icon(self, icon: Optional[QPixmap] = None) -> None:
        """Set the title's icon; `None` is the theme's home icon."""
        self._icon_label.setIcon(
            QIcon(icon) if icon else fxicons.get_icon("home"))

    def set_dialog_title(self, title: Optional[str] = None) -> None:
        """Set the title; `None` or empty reads "Floating Dialog"."""
        self.title_label.setText(title if title else "Floating Dialog")

    def show_under_cursor(self) -> int:
        """Centre the dialog on the cursor at its final size and run it.

        Returns:
            int: `exec()`'s `DialogCode`, `Accepted` or `Rejected`.
        """
        self.adjustSize()
        geometry = self.frameGeometry()
        geometry.moveCenter(QCursor.pos())
        self.move(geometry.topLeft())
        return self.exec()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Close on a press of any button but the right one."""
        if event.button() != Qt.RightButton:
            self.close()
