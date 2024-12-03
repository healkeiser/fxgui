"""Custom widgets for the `fxgui` package."""

# Built-in
import os
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime
from webbrowser import open_new_tab
import re
import time
from urllib.parse import urlparse

# Third-party
from qtpy.QtCore import (
    QObject,
    QPoint,
    QRect,
    QSize,
    QTimer,
    Qt,
    QModelIndex,
    QCollator,
)
from qtpy.QtGui import (
    QColor,
    QCursor,
    QCloseEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QMouseEvent,
    QPainter,
    QPixmap,
)
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplashScreen,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QSystemTrayIcon,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

# Conditional import based on Qt version
from qtpy import QT_VERSION

QT_VERSION_MAJOR = int(QT_VERSION.split(".")[0])
if QT_VERSION_MAJOR >= 6:
    from qtpy.QtGui import QScreen
else:
    from qtpy.QtWidgets import QDesktopWidget

# Internal
from fxgui import fxicons, fxstyle, fxutils, fxdcc


# Constants
CRITICAL = 0
ERROR = 1
WARNING = 2
SUCCESS = 3
INFO = 4
DEBUG = 5


# XXX: Not sure if this is needed
class _FXTreeWidget(QTreeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sizeHintForRow(self, row: int) -> int:
        """Override the size hint for each row to set a specific height.

        Args:
            row: The row index.

        Returns:
            The height for the specified row.
        """

        return 20  # Row height


# ? Keeping for reference
class _FXColorLabelDelegate(QStyledItemDelegate):
    """A custom delegate to paint items with specific colors and icons based
    on their text content."""

    # Custom role to skip delegate
    SKIP_DELEGATE_ROLE = Qt.UserRole + 5

    def __init__(
        self,
        colors_icons: Dict[str, Tuple[QColor, QColor, QColor, QIcon, bool]],
        parent=None,
    ):
        """Initializes the delegate with a dictionary of colors and icons.

        Args:
            colors_icons: A dictionary where keys are text patterns and values
                are tuples containing background color, border color,
                text/icon color, icon, and a boolean indicating if the icon
                should be colored.
            parent: The parent object.
        """

        super().__init__(parent)
        self.colors_icons = colors_icons

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paints the item with the specified colors and icons.

        Args:
            painter: The painter used to draw the item.
            option: The style options for the item.
            index: The model index of the item.
        """

        skip_delegate = index.data(FXColorLabelDelegate.SKIP_DELEGATE_ROLE)
        if skip_delegate:
            super().paint(painter, option, index)
            return

        super().paint(painter, option, index)

        text = index.data()
        if not text:
            super().paint(painter, option, index)
            return

        # Default colors and icon
        background_color, border_color, text_icon_color, icon, color_icon = (
            QColor("#212121"),
            QColor("#212121"),
            QColor("#b4b4b4"),
            fxicons.get_icon("drag_indicator"),
            False,
        )

        # Find the best match for the text in the colors_icons dictionary
        best_match_length = 0
        best_match = None

        for key, value in self.colors_icons.items():
            if key in text.lower() and len(key) > best_match_length:
                best_match = value
                best_match_length = len(key)

        if best_match:
            (
                background_color,
                border_color,
                text_icon_color,
                icon,
                color_icon,
            ) = best_match

        # Adjust colors based on item state
        if option.state & QStyle.State_Selected:
            background_color = background_color.lighter(125)
            border_color = border_color.lighter(125)
        elif option.state & QStyle.State_MouseOver:
            background_color = background_color.darker(125)
            border_color = border_color.darker(125)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipRect(option.rect)

        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        rect = option.rect
        icon_size = QSize(15, 15)
        padding = 2

        # Calculate the rectangles for text and icon
        text_rect, icon_rect = self.calculate_rects(
            rect, text_width, text_height, icon_size, padding
        )

        # Draw the background rectangle
        painter.setBrush(background_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(
            text_rect.adjusted(-icon_size.width() - 10, -padding, 0, padding),
            2,
            2,
        )

        # Draw the icon
        if color_icon:
            pixmap = icon.pixmap(icon_size)
            colored_pixmap = QPixmap(pixmap.size())
            colored_pixmap.fill(Qt.transparent)

            painter2 = QPainter(colored_pixmap)
            painter2.setCompositionMode(QPainter.CompositionMode_Source)
            painter2.drawPixmap(0, 0, pixmap)
            painter2.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter2.fillRect(colored_pixmap.rect(), text_icon_color)
            painter2.end()

            painter.drawPixmap(icon_rect, colored_pixmap)
        else:
            icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )

        # Draw the text
        painter.setPen(text_icon_color)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        painter.restore()

    def calculate_rects(
        self,
        rect: QRect,
        text_width: int,
        text_height: int,
        icon_size: QSize,
        padding: int,
    ) -> Tuple[QRect, QRect]:
        """Calculates the rectangles for the text and icon.

        Args:
            rect: The bounding rectangle of the item.
            text_width: The width of the text.
            text_height: The height of the text.
            icon_size: The size of the icon.
            padding: The padding around the text and icon.

        Returns:
            A tuple containing the text rectangle and the icon rectangle.
        """

        text_rect = QRect(
            rect.left() + icon_size.width() + 12,
            rect.top() + (rect.height() - text_height) // 2,
            text_width + 10,
            text_height,
        )

        icon_rect = QRect(
            rect.left() + 8,
            rect.top() + (rect.height() - icon_size.height()) // 2,
            icon_size.width(),
            icon_size.height(),
        )

        # Adjust the text_rect to be `padding` pixels away from the item border
        text_rect = text_rect.adjusted(padding, padding, -padding, -padding)

        return text_rect, icon_rect

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        """
        Provides the size hint for the item.

        Args:
            option: The style options for the item.
            index: The model index of the item.

        Returns:
            The size hint for the item.
        """

        text = index.data()
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        icon_size = 15
        padding = 4
        return QSize(
            text_width + icon_size + 20,
            max(text_height, icon_size) + 2 * padding,
        )


class FXColorLabelDelegate(QStyledItemDelegate):
    """A custom delegate to paint items with specific colors and icons based
    on their text content."""

    # Custom role to skip delegate
    SKIP_DELEGATE_ROLE = Qt.UserRole + 5

    def __init__(
        self,
        colors_icons: Dict[str, Tuple[QColor, QColor, QColor, QIcon, bool]],
        parent: Optional[QWidget] = None,
        margin_left: int = 2,
        margin_top: Optional[int] = None,
        margin_bottom: Optional[int] = None,
    ):
        """Initializes the delegate with a dictionary of colors and icons.

        Args:
            colors_icons: A dictionary where keys are text patterns and values
                are tuples containing background color, border color,
                text/icon color, icon, and a boolean indicating if the icon
                should be colored.
            parent: The parent object.
            margin_left: The left margin for the text and icon. Defaults to 2.
            margin_top: The top margin for the text and icon. Defaults to
                `margin_left`.
            margin_bottom: The bottom margin for the text and icon. Defaults to
                `margin_left`.
        """

        super().__init__(parent)

        # Dictionary mapping item texts to (background_color, border_color,
        # text_icon_color, icon, color_icon)
        self.colors_icons = colors_icons

        # Margins
        self.margin_left = margin_left
        self.margin_top = (
            self.margin_left if margin_top is None else margin_top
        )
        self.margin_bottom = (
            self.margin_left if margin_bottom is None else margin_bottom
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paints the item with the specified colors and icons.

        Args:
            painter: The painter used to draw the item.
            option: The style options for the item.
            index: The model index of the item.
        """

        # Check if the delegate should skip drawing
        skip_delegate = index.data(FXColorLabelDelegate.SKIP_DELEGATE_ROLE)
        if skip_delegate:
            super().paint(painter, option, index)
            return

        # Retrieve the text and associated colors and icon
        text = index.data()
        if not text:
            return  # No need to paint anything if there's no text

        # Create a copy of the option to modify to clear the text and icon
        # XXX: Not working, need to investigate
        option_modified = QStyleOptionViewItem(option)
        option_modified.text = ""
        option_modified.icon = QIcon()

        # Call the base class paint method to draw selection and hover effects
        super().paint(painter, option_modified, index)

        # Set the default colors and icon
        background_color, border_color, text_icon_color, icon, color_icon = (
            QColor("#212121"),
            QColor("#6d6d6d"),
            QColor("#ffffff"),
            fxicons.get_icon("drag_indicator"),
            False,  # Default to not coloring the icon
        )

        # Find the best match for the text in the colors_icons dictionary
        best_match_length = 0
        best_match = None

        for key, value in self.colors_icons.items():
            if key in text.lower() and len(key) > best_match_length:
                best_match = value
                best_match_length = len(key)

        if best_match:
            (
                background_color,
                border_color,
                text_icon_color,
                icon,
                color_icon,
            ) = best_match

        # Adjust colors based on item state
        if option.state & QStyle.State_Selected:
            background_color = background_color.lighter(125)
            border_color = border_color.lighter(125)
        elif option.state & QStyle.State_MouseOver:
            background_color = background_color.darker(125)
            border_color = border_color.darker(125)

        # Save painter state
        painter.save()

        # Anti-aliasing for smoother rendering
        painter.setRenderHint(QPainter.Antialiasing)

        # Set the clipping region to the column's rectangle
        painter.setClipRect(option.rect)

        # Adjust the rectangle to be away from the border using margins
        rect = option.rect.adjusted(
            self.margin_left,
            self.margin_top,
            -self.margin_left,
            -self.margin_bottom,
        )

        # Use the default font and measure text size
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        # Define the rectangle around the text, aligned to the left
        icon_size = QSize(14, 14)  # Icon size
        text_rect = QRect(
            rect.left() + icon_size.width() + 2,  # Space between icon and text
            rect.top() + (rect.height() - text_height) // 2,
            text_width + 10,
            text_height + 0,
        )

        # Draw custom label with border and background colors from the mapping
        painter.setBrush(background_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(
            text_rect.adjusted(-icon_size.width() - 2, 0, 0, 0), 2, 2
        )

        # Draw the icon inside the rectangle, on the left of the text
        icon_rect = QRect(
            rect.left() + 2,
            rect.top() + (rect.height() - icon_size.height()) // 2,
            icon_size.width(),
            icon_size.height(),
        )

        if color_icon:
            # Convert the icon to a QPixmap and apply the text/icon color
            colored_pixmap = fxicons.change_pixmap_color(
                icon.pixmap(icon_size), text_icon_color
            )
            painter.drawPixmap(icon_rect, colored_pixmap)
        else:
            # Draw the original icon without coloring
            icon.paint(
                painter, icon_rect, Qt.AlignCenter, QIcon.Normal, QIcon.On
            )

        # Draw the text inside the rectangle
        painter.setPen(text_icon_color)
        painter.drawText(text_rect, Qt.AlignCenter, text)

        # Restore painter state
        painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        """Provides the size hint for the item.

        Args:
            option: The style options for the item.
            index: The model index of the item.

        Returns:
            The size hint for the item.
        """

        text = index.data()
        if not text:
            return QSize()
        metrics = QFontMetrics(option.font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        icon_size = 14
        width = (
            text_width
            + icon_size
            + 20
            + self.margin_left * 2  # Add horizontal margins
        )
        height = (
            max(text_height, icon_size)
            + 2
            + self.margin_top
            + self.margin_bottom  # Add vertical margins
        )
        return QSize(width, height)


# ? Keeping for reference
class _FXSortedTreeWidgetItem(QTreeWidgetItem):
    """Custom `QTreeWidgetItem` that provides natural sorting for strings
    containing numbers using QCollator for locale-aware sorting.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collator = QCollator()
        self.collator.setNumericMode(True)

    def __lt__(self, other: "FXSortedTreeWidgetItem") -> bool:
        """Override the less-than operator to provide a custom sorting logic.

        Args:
            other: Another instance of `FXSortedTreeWidgetItem` to compare with.

        Returns:
            `True` if the current item is less than the other item according to
            the natural sort order, `False` otherwise.
        """

        # Get the index of the column currently being used for sorting
        column = self.treeWidget().sortColumn()

        # Compare the items using QCollator
        return self.collator.compare(self.text(column), other.text(column)) < 0


class FXSortedTreeWidgetItem(QTreeWidgetItem):
    """Custom `QTreeWidgetItem` that provides natural sorting for strings
    containing numbers. This is useful for sorting items like version numbers
    or other strings where numeric parts should be ordered numerically.

    For example, this class will sort the following strings in the correct
    human-friendly order:

    - "something1"
    - "something9"
    - "something17"
    - "something25"

    Instead of the default sorting order:

    - "something1"
    - "something17"
    - "something25"
    - "something9"
    """

    def __lt__(self, other: "FXSortedTreeWidgetItem") -> bool:
        """Override the less-than operator to provide a custom sorting logic.

        Args:
            other: Another instance of `FXSortedTreeWidgetItem` to compare with.

        Returns:
            `True` if the current item is less than the other item according to
            the natural sort order, `False` otherwise.
        """

        # Get the index of the column currently being used for sorting
        column = self.treeWidget().sortColumn()

        # Compare the items using the custom natural sort key
        return self._generate_natural_sort_key(
            self.text(column)
        ) < self._generate_natural_sort_key(other.text(column))

    def _generate_natural_sort_key(self, s: str) -> list:
        """Generate a sort key for natural sorting of strings containing
        numbers in a human-friendly way.

        Args:
            s: The string to sort.

        Returns:
            A list of elements where numeric parts are converted to integers
            and other parts are converted to lowercase strings.
        """

        # Split the string into parts, converting numeric parts to integers
        # and non-numeric parts to lowercase strings
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split("([0-9]+)", s)
        ]


class FXApplication(QApplication):
    """Customized QApplication class."""

    _instance = None  # Private class attribute to hold the singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:

            # Create the instance if it doesn't exist
            cls._instance = super(FXApplication, cls).__new__(cls)

            # Initialize the instance once
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
        if not self.__initialized:
            super().__init__(*args, **kwargs)

            fxstyle.set_style(self)
            self.setStyleSheet(fxstyle.load_stylesheet())

            # Mark the instance as initialized
            self.__initialized = True

    @classmethod
    def instance(cls, *args, **kwargs):
        """Return the existing instance or create a new one if it doesn't
        exist.
        """

        # This ensures that `__new__` and `__init__` are called if the instance
        # doesn't exist
        return cls(*args, **kwargs)


class FXSplashScreen(QSplashScreen):
    """Customized QSplashScreen class.

    Args:
        image_path (str): Path to the image to be displayed on the splash
            screen.
        icon (str, optional): Path to the icon to be displayed on the splash
            screen.
        title (str, optional): Title text to be displayed. Defaults to
            `Untitled`.
        information (str, optional): Information text to be displayed.
            Defaults to a placeholder text.
        show_progress_bar (bool, optional): Whether to display a progress bar.
            Defaults to False.
        project (str, optional): Project name. Defaults to `Project`.
        version (str, optional): Version information. Defaults to `0.0.0`.
        company (str, optional): Company name. Defaults to `Company`.
        color_a (str, optional): Color A to be applied to the splash
            screen. Defaults to `#649eff`.
        color_b (str, optional): Color B to be applied to the splash
            screen. Defaults to `#4188ff`.
        fade_in (bool, optional): Whether to apply a fade-in effect on the
            splash screen. Defaults to False.

    Attributes:
        pixmap (QPixmap): The image on the splash screen. Dewfaults to
            `splash.png`.
        icon (QIcon): The icon of the splash screen. Defaults to `favicon.png`.
        title (str): Title text to be displayed. Defaults to `Untitled`.
        information (str): Information text to be displayed. Defaults to a
            placeholder Lorem Ipsum text.
        show_progress_bar (bool): Whether to display a progress bar.
            Defaults to `False`.
        project (str): Project name. Defaults to `Project`.
        version (str): Version information. Defaults to `v0.0.0`.
        company (str): Company name. Defaults to `Company`.
        color_a (str): Color A applied to the splash screen.
        color_b (str): Color B applied to the splash screen.
        fade_in (bool): Whether to apply a fade-in effect on the
            splash screen. Defaults to `False`.
        title_label (QLabel): Label for the title text.
        info_label (QLabel): Label for the information text.
        progress_bar (QProgressBar): Progress bar widget. Only created if
            `show_progress_bar` is `True`.
        copyright_label (QLabel): Label for the copyright information.
        fade_timer (QTimer): Timer for the fade-in effect. Only created if
            `fade_in` is `True`.

    Examples:
        >>> app = QApplication(sys.argv)
        >>> splash = FXSplashScreen(
        ...     image_path="path_to_your_image.png",
        ...     title="My Awesome App",
        ...     information="Loading...",
        ...     show_progress_bar=True,
        ...     project="Cool Project",
        ...     version="v1.2.3",
        ...     company="My Company Ltd.",
        ...     fade_in=True,
        ... )
        >>> splash.progress(50)
        >>> splash.show()
        >>> splash.progress(100)
        >>> splash.close()
        >>> sys.exit(app.exec_())
    """

    def __init__(
        self,
        image_path: Optional[str] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        information: Optional[str] = None,
        show_progress_bar: bool = False,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        color_a: str = fxstyle._COLOR_A_DEFAULT,
        color_b: str = fxstyle._COLOR_B_DEFAULT,
        fade_in: bool = False,
    ):
        # Load the image using image_path and redirect as the original pixmap
        # argument from `QSplashScreen`
        if image_path is None:
            image = os.path.join(
                os.path.dirname(__file__), "images", "snap.png"
            )
        elif os.path.isfile(image_path):
            image = self._resize_image(image_path)
        else:
            raise ValueError(f"Invalid image path: {image_path}")

        super().__init__(image)

        # Attributes
        self.pixmap: QPixmap = image
        self._default_icon = os.path.join(
            os.path.dirname(__file__), "icons", "favicon_light.png"
        )
        self.icon: QIcon = icon
        self.title: str = title
        self.information: str = information
        self.show_progress_bar: bool = show_progress_bar
        self.project: str = project
        self.version: str = version
        self.company: str = company
        self.color_a: str = color_a
        self.color_b: str = color_b
        self.fade_in: bool = fade_in

        # Methods
        self._grey_overlay()

        # Styling
        self.setStyleSheet(fxstyle.load_stylesheet())

    def progress(self, value, max_range=100):
        for value in range(max_range):
            time.sleep(0.25)
            self.progress_bar.setValue(value)

    def showMessage(self, message: str) -> None:
        # Fake signal to trigger the `messageChanged` event
        super().showMessage(" ")

        self.message_label.setText(message)

    # - Private methods

    def _resize_image(
        self, image_path: str, ideal_width: int = 800, ideal_height: int = 450
    ) -> QPixmap:
        pixmap = QPixmap(image_path)
        width = pixmap.width()
        height = pixmap.height()

        aspect = width / float(height)
        ideal_aspect = ideal_width / float(ideal_height)

        if aspect > ideal_aspect:
            # Then crop the left and right edges
            new_width = int(ideal_aspect * height)
            offset = (width - new_width) / 2
            crop_rect = QRect(offset, 0, new_width, height)
        else:
            # Crop the top and bottom
            new_height = int(width / ideal_aspect)
            offset = (height - new_height) / 2
            crop_rect = QRect(0, int(offset), width, new_height)

        cropped_pixmap = pixmap.copy(crop_rect)
        resized_pixmap = cropped_pixmap.scaled(
            ideal_width,
            ideal_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        return resized_pixmap

    def _grey_overlay(self) -> None:
        lorem_ipsum = (
            "At vero eos et accusamus et iusto odio dignissimos ducimus qui "
            "blanditiis praesentium voluptatum deleniti atque corrupti quos "
            "dolores et quas molestias excepturi sint occaecati cupiditate non "
            "provident, similique sunt in culpa qui officia deserunt mollitia "
            "animi, id est laborum et dolorum fuga. Et harum quidem rerum facilis "
            "est et expedita distinctio. Nam libero tempore, cum soluta nobis est "
            "eligendi optio cumque nihil impedit quo minus id quod maxime placeat "
            "facere possimus, omnis voluptas assumenda est, omnis dolor "
            "repellendus. Temporibus autem quibusdam et aut officiis debitis aut "
            "rerum necessitatibus saepe eveniet ut et voluptates repudiandae sint "
            "et molestiae non recusandae. Itaque earum rerum hic tenetur a "
            "sapiente delectus, ut aut reiciendis voluptatibus maiores alias "
            "consequatur aut perferendis doloribus asperiores repellat."
        )

        # Main QFrame
        frame = QFrame(self)
        frame.setGeometry(0, 0, self.pixmap.width() // 2, self.pixmap.height())
        # frame.setStyleSheet("background-color: #232323; color: #f1f3f9;")
        fxutils.add_shadows(self, frame)

        # Create a vertical layout for the QFrame
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(50, 50, 50, 50)

        # Icon QLabel
        self.icon_label = QLabel()
        if self.icon:
            pixmap = QPixmap(self.icon)
        else:
            pixmap = QPixmap(self._default_icon)

        pixmap = pixmap.scaledToHeight(32, Qt.SmoothTransformation)
        self.icon_label.setPixmap(pixmap)

        # Title QLabel with a slightly bigger font and bold
        self.title_label = QLabel(self.title if self.title else "Untitled")
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("font-size: 18pt;")

        # Horizontal layout for title and icon
        title_icon_layout = QHBoxLayout()
        title_icon_layout.addWidget(self.icon_label)
        title_icon_layout.addWidget(self.title_label)
        title_icon_layout.setSpacing(10)
        title_icon_layout.addStretch()
        layout.addLayout(title_icon_layout)

        # Spacer
        spacer_a = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer_a)

        # Information
        self.info_label = QLabel(
            self.information
            if self.information is not None and len(self.information) >= 1
            else lorem_ipsum
        )
        self.info_label.setAlignment(Qt.AlignJustify)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 10pt;")
        layout.addWidget(self.info_label)

        # Spacer
        spacer_b = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer_b)

        # Message
        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignLeft)
        self.message_label.setStyleSheet("font-size: 10pt;")
        layout.addWidget(self.message_label)

        # Spacer
        spacer_c = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer_c)

        # Progress Bar
        if self.show_progress_bar:
            self.progress_bar = QProgressBar()
            layout.addWidget(self.progress_bar)

        # Spacer
        spacer_d = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer_d)

        # Copyright QLabel
        project = (
            self.project
            if self.project and len(self.project) >= 1
            else "Project"
        )
        version = (
            self.version
            if self.version and len(self.version) >= 1
            else "0.0.0"
        )
        company = (
            self.company
            if self.company and len(self.company) >= 1
            else "\u00A9 Company"
        )

        self.copyright_label = QLabel(
            f"{project} | {version} | \u00A9 {company}"
        )
        self.copyright_label.setStyleSheet(
            "font-size: 8pt; qproperty-alignment: AlignBottom;"
        )
        layout.addWidget(self.copyright_label)

    def _fade_in(self) -> None:
        opaqueness = 0.0
        step = 0.001
        self.setWindowOpacity(opaqueness)
        self.show()

        def update_opacity():
            nonlocal opaqueness
            if opaqueness < 1:
                self.setWindowOpacity(opaqueness)
                opaqueness += step * 100
            else:
                self.fade_timer.stop()

        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(update_opacity)
        self.fade_timer.start(100)

    # - Events

    def mousePressEvent(self, event):
        pass
        # self.close()
        # self.setParent(None)

    def showEvent(self, event):
        if self.fade_in:
            super().showEvent(event)
            self._fade_in()


class FXStatusBar(QStatusBar):
    """Customized QStatusBar class.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `None`.
        project (str, optional): Project name. Defaults to `None`.
        version (str, optional): Version information. Defaults to `None`.
        company (str, optional): Company name. Defaults to `None`.

    Attributes:
        project (str): The project name.
        version (str): The version string.
        company (str): The company name.
        icon_label (QLabel): The icon label.
        message_label (QLabel): The message label.
        project_label (QLabel): The project label.
        version_label (QLabel): The version label.
        company_label (QLabel): The company label.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
    ):

        super().__init__(parent)

        # Attributes
        self.project = project or "Project"
        self.version = version or "0.0.0"
        self.company = company or "\u00A9 Company"
        self.icon_label = QLabel()
        self.message_label = QLabel()
        self.project_label = QLabel(self.project)
        self.version_label = QLabel(self.version)
        self.company_label = QLabel(self.company)

        self.message_label.setTextFormat(Qt.RichText)

        left_widgets = [
            self.icon_label,
            self.message_label,
        ]

        right_widgets = [
            self.project_label,
            self.version_label,
            self.company_label,
        ]

        for widget in left_widgets:
            self.addWidget(widget)
            widget.setVisible(False)  # Hide if no message is shown

        for widget in right_widgets:
            self.addPermanentWidget(widget)

        self.messageChanged.connect(self._on_status_message_changed)

    def showMessage(
        self,
        message: str,
        severity_type: int = 4,
        duration: float = 2.5,
        time: bool = True,
        logger: Optional[logging.Logger] = None,
        set_color: bool = True,
        pixmap: Optional[QPixmap] = None,
        background_color: Optional[str] = None,
    ):
        """Display a message in the status bar with a specified severity.

        Args:
            message (str): The message to be displayed.
            severity_type (int, optional): The severity level of the message.
                Should be one of `CRITICAL`, `ERROR`, `WARNING`, `SUCCESS`,
                `INFO`, or `DEBUG`. Defaults to `INFO`.
            duration (float, optional): The duration in seconds for which
                the message should be displayed. Defaults to` 2.5`.
            time (bool, optional): Whether to display the current time before
                the message. Defaults to `True`.
            logger (Logger, optional): A logger object to log the message.
                Defaults to `None`.
            set_color (bool): Whether to set the status bar color depending on
                the log verbosity. Defaults to `True`.
            pixmap (QPixmap, optional): A custom pixmap to be displayed in the
                status bar. Defaults to `None`.
            background_color (str, optional): A custom background color for
                the status bar. Defaults to `None`.

        Examples:
            To display a critical error message with a red background
            >>> self.showMessage(
            ...     "Critical error occurred!",
            ...     severity_type=self.CRITICAL,
            ...     duration=5,
            ...     logger=my_logger,
            ... )

        Note:
            You can either use the `FXMainWindow` instance to retrieve the
            verbosity constants, or the `fxwidgets` module.
            Overrides the base class method.
        """

        # Send fake signal to trigger the `messageChanged` event
        super().showMessage(" ", timeout=duration * 1000)

        # Show the icon and message label which were hidden at init time
        self.icon_label.setVisible(True)
        self.message_label.setVisible(True)

        colors_dict = fxstyle.load_colors_from_jsonc()
        severity_mapping = {
            0: (
                "Critical",
                fxicons.get_icon(
                    "cancel",
                    color=colors_dict["feedback"]["error"]["light"],
                ).pixmap(14, 14),
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            1: (
                "Error",
                fxicons.get_icon(
                    "error",
                    color=colors_dict["feedback"]["error"]["light"],
                ).pixmap(14, 14),
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            2: (
                "Warning",
                fxicons.get_icon(
                    "warning",
                    color=colors_dict["feedback"]["warning"]["light"],
                ).pixmap(14, 14),
                colors_dict["feedback"]["warning"]["background"],
                colors_dict["feedback"]["warning"]["dark"],
            ),
            3: (
                "Success",
                fxicons.get_icon(
                    "check_circle",
                    color=colors_dict["feedback"]["success"]["light"],
                ).pixmap(14, 14),
                colors_dict["feedback"]["success"]["background"],
                colors_dict["feedback"]["success"]["dark"],
            ),
            4: (
                "Info",
                fxicons.get_icon(
                    "info",
                    color=colors_dict["feedback"]["info"]["light"],
                ).pixmap(14, 14),
                colors_dict["feedback"]["info"]["background"],
                colors_dict["feedback"]["info"]["dark"],
            ),
            5: (
                "Debug",
                fxicons.get_icon(
                    "bug_report",
                    color=colors_dict["feedback"]["debug"]["light"],
                ).pixmap(14, 14),
                colors_dict["feedback"]["debug"]["background"],
                colors_dict["feedback"]["debug"]["dark"],
            ),
        }

        (
            severity_prefix,
            severity_icon,
            status_bar_color,
            status_bar_border_color,
        ) = severity_mapping[severity_type]

        # Use custom pixmap if provided
        if pixmap is not None:
            severity_icon = pixmap

        # Use custom background color if provided
        if background_color is not None:
            status_bar_color = background_color

        # Message
        message_prefix = (
            f"<b>{severity_prefix}</b>: {self._get_current_time()} - "
            if time
            else f"{severity_prefix}: "
        )
        notification_message = f"{message_prefix} {message}"
        self.icon_label.setPixmap(severity_icon)
        self.message_label.setText(notification_message)
        # self.clearMessage()

        if set_color:
            self.setStyleSheet(
                """QStatusBar {
                background: """
                + status_bar_color
                + """;
                border-top: 1px solid"""
                + status_bar_border_color
                + """;
                }
                """
            )

        # Link `Logger` object
        if logger is not None:
            # Modify log level according to severity_type
            if severity_type == 0:
                logger.critical(message)
            if severity_type == 1:
                logger.error(message)
            elif severity_type == 2:
                logger.warning(message)
            elif severity_type == 3:
                logger.info(message)
            elif severity_type == 4:
                logger.info(message)
            elif severity_type == 5:
                logger.debug(message)

    def clearMessage(self):
        """Clears the message from the status bar.

        Note:
            Overrides the base class method.
        """

        self.icon_label.clear()
        self.icon_label.setVisible(False)
        self.message_label.clear()
        self.message_label.setVisible(False)
        super().clearMessage()

    def _get_current_time(
        self, display_seconds: bool = False, display_date: bool = False
    ) -> str:
        """Returns the current time as a string.

        Args:
            display_seconds (bool, optional): Whether to display the seconds.
                Defaults to `False`.
            display_date (bool, optional): Whether to display the date.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        format_string = "%H:%M:%S" if display_seconds else "%H:%M"
        if display_date:
            format_string = "%Y-%m-%d " + format_string
        return datetime.now().strftime(format_string)

    def _on_status_message_changed(self, args):
        """If there are no arguments, which means the message is being removed,
        then change the status bar background back to black.
        """

        if not args:
            self.clearMessage()
            self.setStyleSheet(
                """
                QStatusBar {
                    border: 0px solid transparent;
                    background: #201f1f;
                    border-top: 1px solid #2a2929;
                }
            """
            )


class FXMainWindow(QMainWindow):
    """Customized QMainWindow class.

    Args:
        parent (QWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (str, optional): Path to the window icon image. Defaults to `None`.
        title (str, optional): Title of the window. Defaults to `None`.
        size (Tuple[int, int], optional): Window size as width and height.
            Defaults to `None`.
        documentation (str, optional): URL to the tool's documentation.
            Defaults to `None`.
        version (str, optional): Version label for the window.
            Defaults to `None`.
        company (str, optional): Company name for the window.
            Defaults to `Company`.
        color_a (str, optional):Color to be applied to the window.
            Defaults to `#649eff`.
        color_b (str, optional): Color to be applied to the window.
            Defaults to `#4188ff`.
        ui_file (str, optional): Path to the UI file for loading.
            Defaults to `None`.
        set_stylesheet (bool, optional): Whether to set the default stylesheet.
            Defaults to `True`.

    Attributes:
        _default_icon (str): Path to the default icon image.
        window_icon (QIcon): The window icon.
        window_title (str): The window title.
        window_size (QSize): The window size.
        documentation (str): URL to the tool's documentation.
        project (str): The project name.
        version (str): The version label.
        company (str): The company name.
        color_a (str): The first color to be applied to the window.
        color_b (str): The second color to be applied to the window.
        ui_file (str): Path to the UI file for loading.
        ui (Optional[QWidget]): The loaded UI widget.
        CRITICAL (int): Constant for critical severity level.
        ERROR (int): Constant for error severity level.
        WARNING (int): Constant for warning severity level.
        SUCCESS (int): Constant for success severity level.
        INFO (int): Constant for info severity level.
        about_action (QAction): Action for the "About" menu item.
        check_updates_action (QAction): Action for the "Check for Updates" menu item.
        hide_action (QAction): Action for the "Hide" menu item.
        hide_others_action (QAction): Action for the "Hide Others" menu item.
        close_action (QAction): Action for the "Close" menu item.
        settings_action (QAction): Action for the "Settings" menu item.
        window_on_top_action (QAction): Action for the "Always On Top" menu item.
        minimize_window_action (QAction): Action for the "Minimize" menu item.
        maximize_window_action (QAction): Action for the "Maximize" menu item.
        open_documentation_action (QAction): Action for the "Documentation" menu item.
        home_action (QAction): Action for the "Home" toolbar item.
        previous_action (QAction): Action for the "Previous" toolbar item.
        next_action (QAction): Action for the "Next" toolbar item.
        refresh_action (QAction): Action for the "Refresh" toolbar item.
        menu_bar (QMenuBar): The menu bar of the window.
        main_menu (QMenu): The main menu of the window.
        about_menu (QAction): The "About" menu item.
        check_updates_menu (QAction): The "Check for Updates" menu item.
        close_menu (QAction): The "Close" menu item.
        hide_main_menu (QAction): The "Hide" menu item.
        hide_others_menu (QAction): The "Hide Others" menu item.
        edit_menu (QMenu): The edit menu of the window.
        settings_menu (QAction): The "Settings" menu item.
        window_menu (QMenu): The window menu of the window.
        minimize_menu (QAction): The "Minimize" menu item.
        maximize_menu (QAction): The "Maximize" menu item.
        on_top_menu (QAction): The "Always On Top" menu item.
        help_menu (QMenu): The help menu of the window.
        open_documentation_menu (QAction): The "Documentation" menu item.
        toolbar (QToolBar): The toolbar of the window.
        home_toolbar (QAction): The "Home" toolbar item.
        previous_toolbar (QAction): The "Previous" toolbar item.
        next_toolbar (QAction): The "Next" toolbar item.
        refresh_toolbar (QAction): The "Refresh" toolbar item.
        banner (QLabel): The banner label.
        status_line (QFrame): The status line frame.
        status_bar (FXStatusBar): The status bar of the window.
        about_dialog (QDialog): The "About" dialog.

    Examples:
        Outside a DCC (standalone)
        >>> application = fxgui.FXApplication()
        >>> window = fxwidgets.FXMainWindow(
        ...     icon="path/to/icon.png",
        ...     title="My Custom Window",
        ...     size=(800, 600),
        ...     documentation="https://my_tool_docs.com",
        ...     project="Awesome Project",
        ...     version="v1.0.0",
        ...     company="\u00A9 Super Company",
        ...     version="v1.0.0",
        ...     ui_file="path/to/ui_file.ui",
        ... )
        >>> window.show()
        >>> window.set_statusbar_message("Window initialized", window.INFO)
        >>> sys.exit(app.exec_())

        Inside a DCC (Houdini)
        >>> houdini_window = fxdcc.get_houdini_main_window()
        >>> window = fxwidgets.FXMainWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...   )
        >>> window.show()
        >>> window.set_statusbar_message("Window initialized", window.INFO)

        Inside a DCC (Houdini), hide toolbar, menu bar ans status bar
        >>> houdini_window = fxdcc.get_houdini_main_window()
        >>> window = fxwidgets.FXMainWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...   )
        >>> window.toolbar.hide()
        >>> window.menu_bar.hide()
        >>> window.status_bar.hide()
        >>> window.show()

        Inside a DCC (Houdini), override the `fxgui` stylesheet with the Houdini
        one
        >>> houdini_window = fxdcc.get_houdini_main_window()
        >>> window = fxwidgets.FXMainWindow(
        ...    parent=houdini_window,
        ...    ui_file="path/to/ui_file.ui",
        ...   )
        >>> window.setStyleSheet(hou.qt.styleSheet())
        >>> window.show()
        >>> window.set_statusbar_message("Window initialized", window.INFO)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        size: Optional[int] = None,
        documentation: Optional[str] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        color_a: Optional[str] = None,
        color_b: Optional[str] = None,
        ui_file: Optional[str] = None,
        set_stylesheet: bool = True,
    ):
        super().__init__(parent)

        # Attributes
        self._default_icon = os.path.join(
            os.path.dirname(__file__),
            "images",
            "fxgui_logo_background_dark.svg",
        )
        self.window_icon: QIcon = icon
        self.window_title: str = title
        self.window_size: QSize = size
        self.documentation: str = documentation
        self.project: str = project or "Project"
        self.version: str = version or "0.0.0"
        self.company: str = company or "\u00A9 Company"
        self.color_a: str = color_a or fxstyle._COLOR_A_DEFAULT
        self.color_b: str = color_b or fxstyle._COLOR_B_DEFAULT
        self.ui_file: str = ui_file
        self.ui = None

        self.CRITICAL: int = CRITICAL
        self.ERROR: int = ERROR
        self.WARNING: int = WARNING
        self.SUCCESS: int = SUCCESS
        self.INFO: int = INFO

        # Methods
        self._create_actions()
        self._create_banner()
        self._create_status_line()
        self._load_ui()
        self.setWindowTitle(self.window_title)
        self._set_window_icon()
        self._set_window_size()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._check_documentation()
        self._add_shadows()

        # Styling
        if set_stylesheet:
            self.setStyleSheet(
                fxstyle.load_stylesheet(
                    color_a=self.color_a, color_b=self.color_b
                )
            )

    # - Private methods

    def _load_ui(self) -> None:
        """Loads the UI from the specified UI file and sets it as the central
        widget of the main window.

        Warning:
            This method is intended for internal use only.
        """

        if self.ui_file is not None:
            self.ui = fxutils.load_ui(self, self.ui_file)

            # Add the loaded UI to the main window
            self.setCentralWidget(self.ui)

    def _set_window_icon(self) -> None:
        """Sets the window icon from the specified icon path.

        Warning:
            This method is intended for internal use only.
        """

        icon_path = (
            self.window_icon
            if self.window_icon and os.path.isfile(self.window_icon)
            else self._default_icon
        )
        self.setWindowIcon(QIcon(icon_path))

    def _set_window_size(self) -> None:
        """Sets the window size from the specified size.

        Warning:
            This method is intended for internal use only.
        """

        self.resize(
            QSize(*self.window_size)
            if self.window_size and len(self.window_size) >= 1
            else QSize(500, 600)
        )

    def _create_actions(self) -> None:
        """Creates the actions for the window.

        Warning:
            This method is intended for internal use only.
        """

        # Main menu
        self.about_action = fxutils.create_action(
            self,
            "About",
            fxicons.get_icon("help"),  # About icon
            self._show_about_dialog,
            enable=True,
            visible=True,
        )

        self.check_updates_action = fxutils.create_action(
            self,
            "Check for Updates...",
            fxicons.get_icon("update"),  # Update icon
            None,
            enable=False,
            visible=True,
        )

        self.hide_action = fxutils.create_action(
            self,
            "Hide",
            fxicons.get_icon("visibility_off"),  # Visibility off icon
            self.hide,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+h",
        )

        self.hide_others_action = fxutils.create_action(
            self,
            "Hide Others",
            fxicons.get_icon("disabled_visible"),  # Disabled visible icon
            None,
            enable=False,
            visible=True,
        )

        self.close_action = fxutils.create_action(
            self,
            "Close",
            fxicons.get_icon("close"),  # Close icon
            self.close,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+q",
        )

        # Edit menu
        self.settings_action = fxutils.create_action(
            self,
            "Settings",
            fxicons.get_icon("settings"),  # Settings icon
            None,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+s",
        )

        # Window menu
        self.window_on_top_action = fxutils.create_action(
            self,
            "Always On Top",
            fxicons.get_icon("hdr_strong"),  # Always on top icon
            self._window_on_top,
            enable=True,
            visible=True,
            shortcut="Ctrl+Shift+t",
        )

        self.minimize_window_action = fxutils.create_action(
            self,
            "Minimize",
            fxicons.get_icon("minimize"),  # Minimize icon
            self.showMinimized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+m",
        )

        self.maximize_window_action = fxutils.create_action(
            self,
            "Maximize",
            fxicons.get_icon("maximize"),  # Maximize icon
            self.showMaximized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+f",
        )

        # Help menu
        self.open_documentation_action = fxutils.create_action(
            self,
            "Documentation",
            fxicons.get_icon("menu_book"),  # Documentation icon
            lambda: open_new_tab(self.documentation),
            enable=True,
            visible=True,
        )

        # Toolbar
        self.home_action = fxutils.create_action(
            self,
            "Home",
            fxicons.get_icon("home"),  # Home icon
            None,
            enable=False,
            visible=True,
        )

        self.previous_action = fxutils.create_action(
            self,
            "Previous",
            fxicons.get_icon("arrow_back"),  # Previous icon
            None,
            enable=False,
            visible=True,
        )

        self.next_action = fxutils.create_action(
            self,
            "Next",
            fxicons.get_icon("arrow_forward"),  # Next icon
            None,
            enable=False,
            visible=True,
        )

        self.refresh_action = fxutils.create_action(
            self,
            "Refresh",
            fxicons.get_icon("refresh"),  # Refresh icon
            None,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+r",
        )

    def _create_menu_bar(
        self,
        native_menu_bar: bool = False,
    ) -> None:
        """Creates the menu bar for the window.

        Args:
            native_menu_bar (bool, optional): Whether to use the native menu
                bar. Defaults to `False`.
            enable_logo_menu_bar (bool, optional): Whether to enable the logo
                menu bar. Defaults to `True`.

        Warning:
            This method is intended for internal use only.
        """

        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(native_menu_bar)  # Mostly for macOS

        # Main menu
        self.main_menu = self.menu_bar.addMenu("&File")
        self.about_menu = self.main_menu.addAction(self.about_action)
        self.main_menu.addSeparator()
        self.check_updates_menu = self.main_menu.addAction(
            self.check_updates_action
        )
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)
        self.hide_main_menu = self.main_menu.addAction(self.hide_action)
        self.hide_others_menu = self.main_menu.addAction(
            self.hide_others_action
        )
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)

        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("&Edit")
        self.settings_menu = self.edit_menu.addAction(self.settings_action)

        # Window menu
        self.window_menu = self.menu_bar.addMenu("&Window")
        self.minimize_menu = self.window_menu.addAction(
            self.minimize_window_action
        )
        self.maximize_menu = self.window_menu.addAction(
            self.maximize_window_action
        )
        self.window_menu.addSeparator()
        self.on_top_menu = self.window_menu.addAction(
            self.window_on_top_action
        )
        self.window_menu.addSeparator()

        # Help menu
        self.help_menu = self.menu_bar.addMenu("&Help")
        self.open_documentation_menu = self.help_menu.addAction(
            self.open_documentation_action
        )

    def _create_toolbars(self) -> None:
        """Creates the toolbar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setIconSize(QSize(17, 17))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.home_toolbar = self.toolbar.addAction(self.home_action)
        self.previous_toolbar = self.toolbar.addAction(self.previous_action)
        self.next_toolbar = self.toolbar.addAction(self.next_action)
        self.refresh_toolbar = self.toolbar.addAction(self.refresh_action)
        self.toolbar.setMovable(True)

    def _generate_label(self, attribute: str, default: str) -> QLabel:
        """Generates a label for the status bar.

        Args:
            attribute (str): The attribute to be displayed.
            default (str): The default value to be displayed if the attribute
                is not set.

        Warning:
            This method is intended for internal use only.
        """

        if attribute is not None and len(attribute) >= 1:
            return QLabel(attribute)
        else:
            return QLabel(default)

    def _create_banner(self) -> None:
        """Creates a banner with the window title for the window.

        Note:
            This method is intended for internal use only.
        """

        self.banner = QLabel("Banner", self)
        self.banner.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.banner.setStyleSheet(
            "color: white; font-size: 16px; padding: 10px; border-bottom: 1px solid #3A3939;"
        )
        self.banner.setFixedHeight(50)

        central_widget = self.centralWidget()
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.banner)

        if central_widget is not None:
            layout.addWidget(central_widget)
        else:
            central_widget = QWidget()
            layout.addWidget(central_widget)

        self.setCentralWidget(widget)

    def _create_status_line(
        self,
        color_a: str = fxstyle._COLOR_A_DEFAULT,
        color_b: str = fxstyle._COLOR_A_DEFAULT,
    ) -> None:
        """Creates a custom status line for the window.

        Args:
            color_a (str, optional): The first color of the gradient. Defaults to `#cc00cc`.
            color_b (str, optional): The second color of the gradient. Defaults to `#4ab5cc`.

        Note:
            This method is intended for internal use only.
        """

        self.status_line = QFrame(self)
        self.status_line.setFrameShape(QFrame.HLine)
        self.status_line.setFrameShadow(QFrame.Sunken)
        self.status_line.setFixedHeight(3)
        self.status_line.setSizePolicy(
            QSizePolicy.Expanding,
            self.status_line.sizePolicy().verticalPolicy(),
        )
        self.set_status_line_colors(color_a, color_b)

        central_widget = self.centralWidget()
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        if central_widget is not None:
            layout.addWidget(central_widget)
        else:
            central_widget = QWidget()
            layout.addWidget(central_widget)

        layout.addWidget(self.status_line)
        self.setCentralWidget(widget)

    def _create_status_bar(self) -> None:
        """Creates the status bar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.status_bar = FXStatusBar(
            parent=self,
            project=self.project,
            version=self.version,
            company=self.company,
        )
        self.setStatusBar(self.status_bar)

    def _show_about_dialog(self) -> None:
        """Shows the "About" dialog.

        Warning:
            This method is intended for internal use only.
        """

        # ! Repetition from `_create_status_bar` is necessary to create new
        # ! objects
        # If the dialog already exists and is open, close it
        if hasattr(self, "about_dialog") and self.about_dialog is not None:
            self.about_dialog.close()

        # Create a new dialog with self (window) as the parent
        self.about_dialog = QDialog(self)
        self.about_dialog.setWindowTitle("About")

        project_label = self._generate_label(self.project, "Project")
        project_label.setAlignment(Qt.AlignCenter)
        version_label = self._generate_label(self.version, "0.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        company_label = self._generate_label(self.company, "\u00A9 Company")
        company_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(project_label)
        layout.addWidget(version_label)
        layout.addWidget(company_label)

        self.about_dialog.setFixedSize(200, 150)
        self.about_dialog.setLayout(layout)
        self.about_dialog.exec_()

    def _window_on_top(self) -> None:
        """Sets the window on top of all other windows or not.

        Warning:
            This method is intended for internal use only.
        """

        flags = self.windowFlags()
        action_values = {
            True: (
                "Always on Top",
                fxicons.get_icon("hdr_strong", color="white").pixmap(14, 14),
            ),
            False: (
                "Regular Position",
                fxicons.get_icon("hdr_weak", color="white").pixmap(14, 14),
            ),
        }
        stays_on_top = bool(flags & Qt.WindowStaysOnTopHint)
        # text, icon, window_title = action_values[stays_on_top]
        text, icon = action_values[stays_on_top]

        flags ^= Qt.WindowStaysOnTopHint
        self.window_on_top_action.setText(text)
        if icon is not None:
            self.window_on_top_action.setIcon(icon)
        self.setWindowFlags(flags)
        # self.setWindowTitle(window_title)
        self.show()

    def _move_window(self) -> None:
        """Moves the window to the selected area of the screen.

        Warning:
            This method is intended for internal use only.
        """

        frame_geo = self.frameGeometry()

        if QT_VERSION_MAJOR >= 6:
            screen: QScreen = QApplication.primaryScreen()
            desktop_geometry = screen.availableGeometry()
        else:
            desktop_geometry: QRect = QDesktopWidget().availableGeometry()

        center_point = desktop_geometry.center()
        left_top_point = QPoint(
            desktop_geometry.left(), desktop_geometry.top()
        )
        right_top_point = QPoint(
            desktop_geometry.right(), desktop_geometry.top()
        )
        left_bottom_point = QPoint(
            desktop_geometry.left(), desktop_geometry.bottom()
        )
        right_bottom_point = QPoint(
            desktop_geometry.right(), desktop_geometry.bottom()
        )

        moving_position = {
            1: center_point,
            2: left_top_point,
            3: right_top_point,
            4: left_bottom_point,
            5: right_bottom_point,
        }.get(3, center_point)

        moving_position.setX(moving_position.x() + 0)
        moving_position.setY(moving_position.y() + 0)
        frame_geo.moveCenter(moving_position)
        self.move(frame_geo.topLeft())

    def _is_valid_url(self, url: str) -> bool:
        """Checks if the specified URL is valid.

        Args:
            url (str): The URL to check.

        Warning:
            This method is intended for internal use only.
        """

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _check_documentation(self):
        """Checks if the documentation URL is valid and enables/disables the
        action accordingly.

        Warning:
            This method is intended for internal use only.
        """

        pass
        if self._is_valid_url(self.documentation):
            self.open_documentation_action.setEnabled(True)
        else:
            self.open_documentation_action.setEnabled(False)

    def _add_shadows(
        self,
        menu_bar: bool = False,
        toolbar: bool = False,
        status_bar: bool = False,
    ) -> None:
        """Adds shadows to the window elements.

        Args:
            menu_bar (bool, optional): Whether to add shadows to the menu bar.
                Defaults to `False`.
            toolbar (bool, optional): Whether to add shadows to the toolbar.
                Defaults to `False`.
            status_bar (bool, optional): Whether to add shadows to the status bar.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        if menu_bar:
            fxutils.add_shadows(self, self.menu_bar)
        if toolbar:
            fxutils.add_shadows(self, self.toolbar)
        if status_bar:
            fxutils.add_shadows(self, self.statusBar())

    def _get_current_time(
        self, display_seconds: bool = False, display_date: bool = False
    ) -> str:
        """Returns the current time as a string.

        Args:
            display_seconds (bool, optional): Whether to display the seconds.
                Defaults to `False`.
            display_date (bool, optional): Whether to display the date.
                Defaults to `False`.

        Warning:
            This method is intended for internal use only.
        """

        format_string = "%H:%M:%S" if display_seconds else "%H:%M"
        if display_date:
            format_string = "%Y-%m-%d " + format_string
        return datetime.now().strftime(format_string)

    # - Public methods (Overrides)

    def statusBar(self) -> FXStatusBar:
        """Returns the FXStatusBar instance associated with this window.

        Returns:
            FXStatusBar: The FXStatusBar instance associated with this window.

        Note:
            Overrides the base class method.
        """

        return self.status_bar

    def setCentralWidget(self, widget):
        """Overrides the QMainWindow's setCentralWidget method to ensure that the
        status line is always at the bottom of the window and the banner is always at the top.

        Args:
            widget (QWidget): The widget to set as the central widget.

        Note:
            Overrides the base class method.
        """

        # Create a new QWidget to hold the banner, widget, and the status line
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add the banner first (top)
        if hasattr(self, "banner") and self.banner is not None:
            layout.addWidget(self.banner)

        # Add the widget to the new layout
        layout.addWidget(widget)

        # Add the status line last (bottom)
        if hasattr(self, "status_line") and self.status_line is not None:
            layout.addWidget(self.status_line)

        # Call the parent's setCentralWidget method with the new central widget
        super().setCentralWidget(central_widget)

    def setWindowTitle(self, title: str) -> None:
        """Override the `setWindowTitle` method to use `_set_window_title`.

        Args:
            title (str): The new window title.
        """

        title = f"{title if title else 'Window'}"
        super().setWindowTitle(title)

    # - Public methods

    def set_colors(self, color_a: str, color_b: str) -> None:
        """Sets the accent color of the window.

        Args:
            color_a (str): The first color.
            color_b (str): The second color.
        """

        self.color_a = color_a
        self.color_b = color_b
        self.setStyleSheet(
            fxstyle.load_stylesheet(color_a=color_a, color_b=color_b)
        )

    def set_banner_text(self, text: str) -> None:
        """Sets the text of the banner.

        Args:
            text (str): The text to set in the banner.
        """

        self.banner.setText(text)

    def set_status_line_colors(self, color_a: str, color_b: str) -> None:
        """Set the colors of the status line.

        Args:
            color_a (str): The first color of the gradient.
            color_b (str): The second color of the gradient.
        """

        self.status_line.setStyleSheet(
            f"""
            QFrame {{
                background-color: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0, stop:0 {color_a}, stop:1 {color_b});
                border: 0px solid transparent;
                border-radius: 0px;
            }}
        """
        )

    def set_ui_file(self, ui_file: str) -> None:
        """Sets the UI file and loads the UI."""

        self.ui_file = ui_file
        self._load_ui()

    def set_project_label(self, project: str) -> None:
        """Sets the project label in the status bar.

        Args:
            project (str): The project name.

        Note:
            Overrides the base class method.
        """

        self.statusBar().project_label.setText(project)

    def set_company_label(self, company: str) -> None:
        """Sets the company label in the status bar.

        Args:
            company (str): The company name.

        Note:
            Overrides the base class method.
        """

        self.statusBar().company_label.setText(company)

    def set_version_label(self, version: str) -> None:
        """Sets the version label in the status bar.

        Args:
            version (str): The version string.

        Note:
            Overrides the base class method.
        """

        self.statusBar().version_label.setText(version)

    # - Events

    def closeEvent(self, event) -> None:
        self.setParent(None)


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

    # - Private methods

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


class FXFloatingDialog(QDialog):
    """A floating dialog that appears at the cursor's position.
    It closes when any mouse button except the right one is pressed.

    Args:
        parent (QtWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
        icon (QPixmap): The QPixmap icon.
        title (str): The dialog title.

    Attributes:
        dialog_icon (QIcon): The icon of the dialog.
        dialog_title (str): The title of the dialog.
        drop_position (QPoint): The drop position of the dialog.
        dialog_position (Tuple[int, int]): The position of the dialog.
        parent_package (int): Whether the dialog is standalone application, or belongs to a DCC parent.
        popup (bool): Whether the dialog is a popup or not.
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
        _icon = fxicons.get_icon("home", color="#b4b4b4").pixmap(32, 32)
        self._default_icon = _icon
        self.dialog_icon: QIcon = icon
        self.dialog_title: str = title

        self.drop_position = QCursor.pos()
        self.dialog_position = (
            self.drop_position.x() - (self.width() / 2),
            self.drop_position.y() - (self.height() / 2),
        )

        self.parent_package = parent_package

        # Methods
        self._setup_title()
        self._setup_main_widget()
        self._setup_buttons()
        self._setup_layout()
        self._handle_connections()
        self.set_dialog_icon(self.dialog_icon)
        self.set_dialog_title(self.dialog_title)

        # Window
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(200, 40)

        if popup:
            self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        if (
            self.parent_package == fxdcc.STANDALONE
            or self.parent_package == None
        ):
            pass

        elif self.parent_package == fxdcc.HOUDINI:
            # Custom stylesheet for Houdini
            self.title_widget.setStyleSheet("background-color: #2b2b2b;")
            self.setStyleSheet(
                """
                FXFloatingDialog {
                    border-top: 1px solid #949494;
                    border-left: 1px solid #949494;
                    border-bottom: 1px solid #262626;
                    border-right: 1px solid #262626;
                }
            """
            )

        elif self.parent_package == fxdcc.MAYA:
            pass

        elif self.parent_package == fxdcc.NUKE:
            pass

        else:
            pass

    # - Private methods

    def _setup_title(self):
        """_summary_

        Warning:
            This method is intended for internal use only.
        """

        self._icon_label = QLabel(self)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title_widget = QWidget(self)

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
        self.main_layout = QVBoxLayout(self.main_widget)
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

    def set_dialog_icon(self, icon: Optional[QPixmap] = None) -> None:
        """Sets the dialog's icon.

        Args:
            icon (QPixmap, optional): The QPixmap icon.
        """

        icon = icon if icon else self._default_icon
        self._icon_label.setPixmap(
            icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.dialog_icon = icon

    def set_dialog_title(self, title: str = None) -> None:
        """Sets the dialog's title.

        Args:
            title (str): The title of the dialog.
        """

        self.title_label.setText(title if title else "Floating Dialog")

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


class FXSystemTray(QObject):
    """A system tray icon with a context menu.

    Args:
        parent (QWidget, optional): The parent widget. Defaults to None.
        icon (str, optional): The icon path. Defaults to None.

    Attributes:
        tray_icon (QSystemTrayIcon): The system tray icon.
        quit_action (QAction): The action to quit the application.
        tray_menu (QMenu): The tray menu.

    Methods:
        show: Shows the system tray icon.
        on_tray_icon_activated: Shows the tray menu above the taskbar.
        closeEvent: Closes the application.

    Examples:
        >>> app = FXApplication()
        >>> system_tray = FXSystemTray()
        >>> hello_action = QAction(
        ...     fxicons.get_icon("visibility"), "Set Project", system_tray
        ... )
        >>> system_tray.tray_menu.insertAction(
        ...     system_tray.quit_action, hello_action
        ... )
        >>> system_tray.tray_menu.insertSeparator(system_tray.quit_action)
        >>> system_tray.show()
        >>> app.exec_()

    Note:
        Inherits from QObject, not QSystemTrayIcon.
    """

    def __init__(self, parent=None, icon=None):
        super().__init__(parent)

        self.icon = (
            icon
            or (
                Path(__file__).parent / "images" / "fxgui_logo_light.svg"
            ).as_posix()
        )
        self.tray_icon = QSystemTrayIcon(QIcon(self.icon), parent)

        # Methods
        self._create_actions()
        self._create_menu()
        self._handle_connections()

    # - Private methods

    def _create_actions(self) -> None:
        """Creates the actions for the window.

        Warning:
            This method is intended for internal use only.
        """

        # Main menu
        self.quit_action = fxutils.create_action(
            self,
            "Quit",
            fxicons.get_icon("close"),
            self.closeEvent,
            enable=True,
            visible=True,
        )

    def _create_menu(self) -> None:
        self.tray_menu = QMenu(self.parent())
        self.tray_menu.addAction(self.quit_action)

        # Styling
        self.tray_menu.setStyleSheet(fxstyle.load_stylesheet())

    def _handle_connections(self) -> None:
        # Right-click
        # self.tray_icon.setContextMenu(self.tray_menu)

        # Left-click
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    # - Public methods

    def show(self):
        """Shows the system tray icon."""

        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        """Shows the tray menu at the cursor's position.

        Args:
            reason (QSystemTrayIcon.ActivationReason): The reason for the tray
                icon activation.
        """

        if reason == QSystemTrayIcon.Trigger:
            # Calculate taskbar position
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()
            available_geometry = screen.availableGeometry()
            tray_icon_geometry = self.tray_icon.geometry()

            # Calculate the center position of the tray icon
            tray_icon_center = tray_icon_geometry.center()

            menu_width = self.tray_menu.sizeHint().width()
            menu_height = self.tray_menu.sizeHint().height()

            margin = 20  # Margin between the taskbar and the system tray menu

            if available_geometry.y() > screen_geometry.y():
                # Taskbar is on the top
                pos = QPoint(
                    tray_icon_center.x() - menu_width / 2,
                    tray_icon_geometry.bottom() + margin,
                )
            elif available_geometry.x() > screen_geometry.x():
                # Taskbar is on the left
                pos = QPoint(
                    tray_icon_geometry.right() + margin,
                    tray_icon_center.y() - menu_height / 2,
                )
            elif available_geometry.height() < screen_geometry.height():
                # Taskbar is on the bottom
                pos = QPoint(
                    tray_icon_center.x() - menu_width / 2,
                    tray_icon_geometry.top() - menu_height - margin,
                )
            else:
                # Taskbar is on the right or default position
                pos = QPoint(
                    tray_icon_geometry.left() - menu_width - margin,
                    tray_icon_center.y() - menu_height / 2,
                )

            # Ensure the menu is completely visible
            if pos.x() < available_geometry.x():
                pos.setX(available_geometry.x())
            if pos.y() < available_geometry.y():
                pos.setY(available_geometry.y())
            if pos.x() + menu_width > available_geometry.right():
                pos.setX(available_geometry.right() - menu_width)
            if pos.y() + menu_height > available_geometry.bottom():
                pos.setY(available_geometry.bottom() - menu_height)

            self.tray_menu.exec_(pos)

    def closeEvent(self, event) -> None:
        FXApplication.instance().quit()
        QApplication.instance().quit()
        self.setParent(None)


class FXPasswordLineEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_edit = QLineEdit()
        self.line_edit.setEchoMode(QLineEdit.Password)

        # Show/hide button
        self.reveal_button = QPushButton("Show")
        self.reveal_button.setIcon(fxicons.get_icon("visibility"))
        self.reveal_button.clicked.connect(self.toggle_reveal)

        # Layout for lineEdit and button
        layout = QHBoxLayout()
        layout.addWidget(self.line_edit)
        layout.addWidget(self.reveal_button)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def toggle_reveal(self):
        """Toggles the echo mode between password and normal."""

        if self.line_edit.echoMode() == QLineEdit.Password:
            self.line_edit.setEchoMode(QLineEdit.Normal)
            self.reveal_button.setText("Hide")
            self.reveal_button.setIcon(fxicons.get_icon("disabled_visible"))
        else:
            self.line_edit.setEchoMode(QLineEdit.Password)
            self.reveal_button.setText("Show")
            self.reveal_button.setIcon(fxicons.get_icon("visibility"))


if __name__ == "__main__":
    _application = FXApplication()
    window = FXMainWindow()
    window.show()
    _application.exec_()
