"""This module provides functionality for handling icons in a VFX application."""

# Built-in
from typing import Optional, Callable
from pathlib import Path
from functools import lru_cache

# Third-party
from qtpy.QtWidgets import (
    QGridLayout,
    QPushButton,
    QStyle,
    QWidget,
)
from qtpy.QtGui import (
    QIcon,
    QColor,
    QPainter,
    QPixmap,
    QBitmap,
    QGuiApplication,
)
from qtpy.QtCore import Qt, qVersion

# Internal
from fxgui import fxwidgets


# Constants
LIBRARIES_ROOT = Path(__file__).parent / "icons" / "libraries"
DEFAULT_LIBRARY = "material-icons"
LIBRARIES_INFO = {
    "material-icons": {
        "pattern": "{root}/{library}/{extension}/{icon_name}/{style}.{extension}",
        "defaults": {
            "extension": "svg",
            "style": "round",
        },
    },
}


@lru_cache(maxsize=128)
def get_icon_path(
    icon_name: str,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
    verify: bool = True,
) -> str:
    """Get the path of the specified icon.

    Args:
        icon_name (str): The name of the icon.
        library (str, optional): The library of the icon. Defaults to `None`.
        style (str, optional): The style of the icon. Defaults to `None`.
        extension (str, optional): The extension of the icon.
            Defaults to `None`.
        verify (bool, optional): Whether to verify if the icon exists.
            Defaults to `True`.

    Raises:
        OSError: If verify is `True` and the icon does not exist.

    Returns:
        str: The path of the icon.
    """

    if library is None:
        library = DEFAULT_LIBRARY
    if style is None:
        style = LIBRARIES_INFO[library]["defaults"].get("style")
    if extension is None:
        extension = LIBRARIES_INFO[library]["defaults"].get("extension")

    pattern = LIBRARIES_INFO[library]["pattern"]
    path = pattern.format(
        icon_name=icon_name,
        style=style,
        library=library,
        extension=extension,
        root=LIBRARIES_ROOT,
    )
    if verify and not Path(path).exists():
        raise OSError(f"Icon path '{path}' does not exist.")
    return path


def has_transparency(mask: QBitmap) -> bool:
    """Check if a mask has any transparency.

    Args:
        mask (QBitmap): The mask to check.

    Returns:
        bool: `True` if the mask has transparency, `False` otherwise.
    """

    image = mask.toImage()
    size = mask.size()
    return any(
        image.pixelIndex(x, y) == 0
        for x in range(size.width())
        for y in range(size.height())
    )


@lru_cache(maxsize=128)
def change_pixmap_color(pixmap: QPixmap, color: str) -> QPixmap:
    """Change the color of a pixmap.

    Args:
        pixmap (QPixmap): The pixmap to change the color of.
        color (str): The color to apply.

    Returns:
        QPixmap: The pixmap with the new color applied.
    """

    mask = pixmap.createMaskFromColor(Qt.transparent)
    if not has_transparency(mask):
        return pixmap

    qcolor = QColor(color)
    if qVersion() < "4.8.0":
        pixmap.fill(qcolor)
        pixmap.setMask(mask)
        return pixmap

    if qVersion() < "5.6.0":
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.setPen(qcolor)
        painter.drawPixmap(pixmap.rect(), mask, mask.rect())
        painter.end()
        return pixmap

    qpixmap = pixmap.toImage()
    for y in range(qpixmap.height()):
        for x in range(qpixmap.width()):
            alpha = qpixmap.pixelColor(x, y).alpha()
            qcolor.setAlpha(alpha)
            qpixmap.setPixelColor(x, y, qcolor)
    pixmap = QPixmap().fromImage(qpixmap)
    return pixmap


@lru_cache(maxsize=128)
def get_pixmap(
    icon_name: str,
    width: int = 48,
    height: int = 48,
    color: Optional[str] = None,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
) -> QPixmap:
    """Get a QPixmap of the specified icon.

    Args:
        icon_name (str): The name of the icon.
        width (int, optional): The width of the pixmap. Defaults to 48.
        height (int, optional): The height of the pixmap. Defaults to 48.
        color (str, optional): The color to convert the pixmap to.
            Defaults to `None`.
        library (str, optional): The library of the icon. Defaults to `None`.
        style (str, optional): The style of the icon. Defaults to `None`.
        extension (str, optional): The extension of the icon.
            Defaults to `None`.

    Returns:
        QPixmap: The QPixmap of the icon.

    Examples:
        >>> get_pixmap("add", color="red")
    """

    path = get_icon_path(
        icon_name,
        library=library,
        style=style,
        extension=extension,
        verify=True,
    )
    qpixmap = QIcon(path).pixmap(width, height)
    if color is not None:
        qpixmap = change_pixmap_color(qpixmap, color)
    else:
        qpixmap = change_pixmap_color(qpixmap, "#b4b4b4")
    return qpixmap


@lru_cache(maxsize=128)
def get_icon(
    icon_name: str,
    width: int = 48,
    height: int = 48,
    color: Optional[str] = None,
    library: Optional[str] = None,
    style: Optional[str] = None,
    extension: Optional[str] = None,
) -> QIcon:
    """Get a QIcon of the specified icon.

    Args:
        icon_name (str): The name of the icon.
        width (int, optional): The width of the pixmap. Defaults to 48.
        height (int, optional): The height of the pixmap. Defaults to 48.
        color (str, optional): The color to convert the pixmap to.
            Defaults to `None`.
        library (str, optional): The library of the icon. Defaults to `None`.
        style (str, optional): The style of the icon. Defaults to `None`.
        extension (str, optional): The extension of the icon.
            Defaults to `None`.

    Returns:
        QIcon: The QIcon of the icon.

    Examples:
        >>> get_icon("add", color="red")
    """

    qpixmap = get_pixmap(
        icon_name, width, height, color, library, style, extension
    )
    return QIcon(qpixmap)


if __name__ == "__main__":

    class _FXBuiltInIcons(QWidget):
        def __init__(self):
            super().__init__()

            icons = sorted(
                [attr for attr in dir(QStyle) if attr.startswith("SP_")]
            )
            layout = QGridLayout()

            for number, name in enumerate(icons):
                button = QPushButton(name)

                pixmap = getattr(QStyle, name)
                icon = self.style().standardIcon(pixmap)
                button.setIcon(icon)
                button.setFixedSize(250, 25)
                button.clicked.connect(self.create_callback(name))
                layout.addWidget(button, number / 4, number % 4)

            self.setLayout(layout)

        def copy_to_clipboard(self, name: str):
            """Copy the given name to the clipboard.

            Args:
                name (str): The name to copy.
            """

            clipboard = QGuiApplication.clipboard()
            # clipboard.setText(f'QStyle.{name}: ("___", "white"),')
            clipboard.setText(f"self.style().standardIcon(QStyle.{name})")

        def create_callback(self, name: str) -> Callable[[bool], None]:
            """Create a callback function for a button click.

            Args:
                name (str): The name of the icon that will be copied to the
                    clipboard when the button is clicked.

            Returns:
                Callable[[bool], None]: A lambda function that takes a boolean
                    argument (indicating whether the button is checked) and
                    calls the `copy_to_clipboard` method with the given name as
                    an argument.
            """

            return lambda checked: self.copy_to_clipboard(name)

    application = fxwidgets.FXApplication()
    widget = _FXBuiltInIcons()
    window = fxwidgets.FXMainWindow()
    window.setCentralWidget(widget)
    window.menu_bar.hide()
    window.toolbar.hide()
    window.setWindowTitle("Built-in Icons")
    window.show()
    application.exec_()
