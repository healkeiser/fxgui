"""Styling, theming, and color management for `fxgui`.

This module provides comprehensive styling functionality including:
    - Dark and light theme support with palette management
    - QSS stylesheet loading with dynamic color replacement
    - Custom QProxyStyle for standard icon overrides
    - Theme toggling with icon cache invalidation
    - Color loading from JSONC configuration files

Classes:
    FXProxyStyle: Custom style providing Material Design icons for Qt standard icons.

Functions:
    load_stylesheet: Load and customize QSS stylesheets.
    load_colors_from_jsonc: Load color definitions from JSONC files.
    toggle_theme: Switch between dark and light themes.
    set_dark_palette: Apply dark theme palette to a widget.
    set_light_palette: Apply light theme palette to a widget.
    set_style: Apply custom style to a widget.
    get_theme: Get the current theme of a widget.
    get_theme_colors: Get the color palette for the current theme.

Constants:
    STYLE_FILE: Path to the default QSS stylesheet.
    COLOR_FILE: Path to the default color configuration.

Examples:
    Loading a stylesheet with custom colors:

    >>> from fxgui import fxstyle
    >>> stylesheet = fxstyle.load_stylesheet(
    ...     color_a="#FF5722",
    ...     color_b="#E64A19",
    ...     theme="dark"
    ... )
    >>> widget.setStyleSheet(stylesheet)

    Toggling theme on a window:

    >>> new_theme = fxstyle.toggle_theme(window)
    >>> print(f"Switched to {new_theme} theme")
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
import os
import re
import json
import sys
from pathlib import Path
from typing import Optional

# Third-party
from qtpy.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleOption,
    QWidget,
    QStyleFactory,
)
from qtpy.QtGui import QIcon, QPalette, QColor, QFontDatabase

# Internal
from fxgui import fxicons


# Constants
_parent_directory = Path(__file__).parent
STYLE_FILE = _parent_directory / "qss" / "style.qss"
COLOR_FILE = _parent_directory / "style.jsonc"

# Colors
_COLOR_A_DEFAULT = "#007ACC"  # Lighter
_COLOR_B_DEFAULT = "#005A9E"  # Darker

# Globals
_colors = None
_theme = "dark"
_standard_icon_map = None  # Lazy-loaded icon map cache


def get_theme_colors() -> dict:
    """Get the color palette for the current theme.

    Returns:
        dict: Dictionary containing theme-specific colors like background,
        text, border, etc.

    Examples:
        >>> colors = get_theme_colors()
        >>> bg = colors["background"]  # "#201f1f" for dark, "#f0f0f0" for light
    """

    colors_dict = load_colors_from_jsonc()
    return colors_dict["theme"].get(_theme, colors_dict["theme"]["dark"])


def _get_standard_icon_map() -> dict:
    """Get the standard icon map, creating it lazily on first access.

    Returns:
        dict: Mapping of QStyle.StandardPixmap to QIcon.
    """

    global _standard_icon_map
    if _standard_icon_map is not None:
        return _standard_icon_map

    colors_dict = load_colors_from_jsonc()

    # fmt: off
    _standard_icon_map = {
        QStyle.SP_ArrowBack: fxicons.get_icon("arrow_back"),
        QStyle.SP_ArrowDown: fxicons.get_icon("arrow_downward"),
        QStyle.SP_ArrowForward: fxicons.get_icon("arrow_forward"),
        QStyle.SP_ArrowLeft: fxicons.get_icon("arrow_left"),
        QStyle.SP_ArrowRight: fxicons.get_icon("arrow_right"),
        QStyle.SP_ArrowUp: fxicons.get_icon("arrow_upward"),
        QStyle.SP_BrowserReload: fxicons.get_icon("refresh"),
        QStyle.SP_BrowserStop: fxicons.get_icon("block"),
        QStyle.SP_CommandLink: fxicons.get_icon("arrow_forward"),
        QStyle.SP_ComputerIcon: fxicons.get_icon("desktop_windows"),
        QStyle.SP_CustomBase: fxicons.get_icon("tune"),
        QStyle.SP_DesktopIcon: fxicons.get_icon("desktop_mac"),
        QStyle.SP_DialogAbortButton: fxicons.get_icon("cancel"),
        QStyle.SP_DialogApplyButton: fxicons.get_icon("check"),
        QStyle.SP_DialogCancelButton: fxicons.get_icon("cancel"),
        QStyle.SP_DialogCloseButton: fxicons.get_icon("close"),
        QStyle.SP_DialogDiscardButton: fxicons.get_icon("delete"),
        QStyle.SP_DialogHelpButton: fxicons.get_icon("help"),
        QStyle.SP_DialogIgnoreButton: fxicons.get_icon("notifications_off"),
        QStyle.SP_DialogNoButton: fxicons.get_icon("cancel"),
        QStyle.SP_DialogNoToAllButton: fxicons.get_icon("do_not_disturb"),
        QStyle.SP_DialogOkButton: fxicons.get_icon("check"),
        QStyle.SP_DialogOpenButton: fxicons.get_icon("open_in_new"),
        QStyle.SP_DialogResetButton: fxicons.get_icon("cleaning_services"),
        QStyle.SP_DialogRetryButton: fxicons.get_icon("restart_alt"),
        QStyle.SP_DialogSaveAllButton: fxicons.get_icon("save_all"),
        QStyle.SP_DialogSaveButton: fxicons.get_icon("save"),
        QStyle.SP_DialogYesButton: fxicons.get_icon("check"),
        QStyle.SP_DialogYesToAllButton: fxicons.get_icon("done_all"),
        QStyle.SP_DirClosedIcon: fxicons.get_icon("folder"),
        QStyle.SP_DirHomeIcon: fxicons.get_icon("home"),
        QStyle.SP_DirIcon: fxicons.get_icon("folder_open"),
        QStyle.SP_DirLinkIcon: fxicons.get_icon("link"),
        QStyle.SP_DirLinkOpenIcon: fxicons.get_icon("folder_open"),
        QStyle.SP_DockWidgetCloseButton: fxicons.get_icon("close"),
        QStyle.SP_DirOpenIcon: fxicons.get_icon("folder_open"),
        QStyle.SP_DriveCDIcon: fxicons.get_icon("album"),
        QStyle.SP_DriveDVDIcon: fxicons.get_icon("album"),
        QStyle.SP_DriveFDIcon: fxicons.get_icon("usb"),
        QStyle.SP_DriveHDIcon: fxicons.get_icon("usb"),
        QStyle.SP_DriveNetIcon: fxicons.get_icon("cloud"),
        QStyle.SP_FileDialogBack: fxicons.get_icon("arrow_back"),
        QStyle.SP_FileDialogContentsView: fxicons.get_icon("find_in_page"),
        QStyle.SP_FileDialogDetailedView: fxicons.get_icon("description"),
        QStyle.SP_FileDialogEnd: fxicons.get_icon("check_circle"),
        QStyle.SP_FileDialogInfoView: fxicons.get_icon("info"),
        QStyle.SP_FileDialogListView: fxicons.get_icon("view_list"),
        QStyle.SP_FileDialogNewFolder: fxicons.get_icon("create_new_folder"),
        QStyle.SP_FileDialogStart: fxicons.get_icon("insert_drive_file"),
        QStyle.SP_FileDialogToParent: fxicons.get_icon("file_upload"),
        QStyle.SP_FileIcon: fxicons.get_icon("insert_drive_file"),
        QStyle.SP_FileLinkIcon: fxicons.get_icon("link"),
        QStyle.SP_LineEditClearButton: fxicons.get_icon("close"),
        QStyle.SP_MediaPause: fxicons.get_icon("pause"),
        QStyle.SP_MediaPlay: fxicons.get_icon("play_arrow"),
        QStyle.SP_MediaSeekBackward: fxicons.get_icon("fast_rewind"),
        QStyle.SP_MediaSeekForward: fxicons.get_icon("fast_forward"),
        QStyle.SP_MediaSkipBackward: fxicons.get_icon("skip_previous"),
        QStyle.SP_MediaSkipForward: fxicons.get_icon("skip_next"),
        QStyle.SP_MediaStop: fxicons.get_icon("stop"),
        QStyle.SP_MediaVolume: fxicons.get_icon("volume_up"),
        QStyle.SP_MediaVolumeMuted: fxicons.get_icon("volume_off"),
        QStyle.SP_MessageBoxCritical: fxicons.get_icon("error", color=colors_dict["feedback"]["error"]["light"]),
        QStyle.SP_MessageBoxInformation: fxicons.get_icon("info", color=colors_dict["feedback"]["info"]["light"]),
        QStyle.SP_MessageBoxQuestion: fxicons.get_icon("help", color=colors_dict["feedback"]["success"]["light"]),
        QStyle.SP_MessageBoxWarning: fxicons.get_icon("warning", color=colors_dict["feedback"]["warning"]["light"]),
        QStyle.SP_RestoreDefaultsButton: fxicons.get_icon("restore"),
        QStyle.SP_TitleBarCloseButton: fxicons.get_icon("close"),
        QStyle.SP_TitleBarContextHelpButton: fxicons.get_icon("help"),
        QStyle.SP_TitleBarMaxButton: fxicons.get_icon("maximize"),
        QStyle.SP_TitleBarMenuButton: fxicons.get_icon("menu"),
        QStyle.SP_TitleBarMinButton: fxicons.get_icon("minimize"),
        QStyle.SP_TitleBarNormalButton: fxicons.get_icon("restore"),
        QStyle.SP_TitleBarShadeButton: fxicons.get_icon("arrow_drop_down"),
        QStyle.SP_TitleBarUnshadeButton: fxicons.get_icon("arrow_drop_up"),
        QStyle.SP_ToolBarHorizontalExtensionButton: fxicons.get_icon("arrow_right"),
        QStyle.SP_ToolBarVerticalExtensionButton: fxicons.get_icon("arrow_downward"),
        QStyle.SP_TrashIcon: fxicons.get_icon("delete"),
        QStyle.SP_VistaShield: fxicons.get_icon("security"),
    }
    # fmt: on
    return _standard_icon_map


class FXProxyStyle(QProxyStyle):
    """A custom style class that extends QProxyStyle to provide custom icons."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icon_color = "#b4b4b4"  # Default color

    def standardIcon(
        self,
        standardIcon: QStyle.StandardPixmap,
        option: Optional[QStyleOption] = None,
        widget: Optional[QWidget] = None,
    ) -> QIcon:
        """Returns an icon for the given standardIcon.

        Args:
            standardIcon (QStyle.StandardPixmap): The standard pixmap for
                which an icon should be returned.
            option (QStyleOption, optional): An option that can be used to
                fine-tune the look of the icon. Defaults to `None`.
            widget (QWidget, optional): The widget for which the icon is being
                requested. Defaults to `None`.

        Returns:
            QIcon: The icon for the standardIcon. If no custom icon is found,
                the default icon is returned.
        """

        icon = _get_standard_icon_map().get(standardIcon)
        if icon is not None:
            return icon
        return super().standardIcon(standardIcon, option, widget)

    def set_icon_color(self, color: str):
        """Sets the color of the icons.

        Args:
            color (str): The color to set the icons to.
        """

        self.icon_color = color
        self.update()


def get_current_palette(widget: QWidget) -> None:
    """Prints the current palette of the given Qt object.

    This function retrieves the current palette of the given Qt object and
    prints each color role in each state group in the format
    `QPalette.State, QPalette.Role, QColor(r, g, b)`.

    Args:
        widget: The Qt widget whose palette is to be retrieved.
    """

    palette = widget.palette()
    role_names = {
        QPalette.Window: "Window",
        QPalette.WindowText: "WindowText",
        QPalette.Base: "Base",
        QPalette.AlternateBase: "AlternateBase",
        QPalette.ToolTipBase: "ToolTipBase",
        QPalette.ToolTipText: "ToolTipText",
        QPalette.Text: "Text",
        QPalette.Button: "Button",
        QPalette.ButtonText: "ButtonText",
        QPalette.BrightText: "BrightText",
        QPalette.Link: "Link",
        QPalette.Highlight: "Highlight",
        QPalette.HighlightedText: "HighlightedText",
        QPalette.Light: "Light",
        QPalette.Midlight: "Midlight",
        QPalette.Dark: "Dark",
        QPalette.Mid: "Mid",
        QPalette.Shadow: "Shadow",
        QPalette.LinkVisited: "LinkVisited",
        QPalette.NoRole: "NoRole",
    }

    group_names = {
        QPalette.Active: "Active",
        QPalette.Inactive: "Inactive",
        QPalette.Disabled: "Disabled",
    }

    for role, role_name in role_names.items():
        for group, group_name in group_names.items():
            color = palette.color(group, role)
            print(
                f"QPalette.{group_name}, QPalette.{role_name}, QColor({color.red()}, {color.green()}, {color.blue()})"
            )


def set_dark_palette(widget: QWidget) -> QPalette:
    """Set the object palette to a dark theme.

    Args:
        widget: The QWidget (QApplication, QWindow, etc.) to set
            the palette on.

    Returns:
        QPalette: The custom palette.
    """

    # fmt: off
    palette = QPalette()
    palette.setColor(QPalette.Active, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Inactive, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Active, QPalette.WindowText, QColor(212, 212, 212))
    palette.setColor(QPalette.Inactive, QPalette.WindowText, QColor(212, 212, 212))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(128, 128, 128))
    palette.setColor(QPalette.Active, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Inactive, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Active, QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.Inactive, QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.Disabled, QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.Active, QPalette.ToolTipBase, QColor(37, 37, 37))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipBase, QColor(37, 37, 37))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipBase, QColor(37, 37, 37))
    palette.setColor(QPalette.Active, QPalette.ToolTipText, QColor(240, 240, 240))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipText, QColor(240, 240, 240))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipText, QColor(240, 240, 240))
    palette.setColor(QPalette.Active, QPalette.Text, QColor(212, 212, 212))
    palette.setColor(QPalette.Inactive, QPalette.Text, QColor(212, 212, 212))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
    palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Inactive, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Active, QPalette.ButtonText, QColor(212, 212, 212))
    palette.setColor(QPalette.Inactive, QPalette.ButtonText, QColor(212, 212, 212))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))
    palette.setColor(QPalette.Active, QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Link, QColor(86, 156, 214))
    palette.setColor(QPalette.Inactive, QPalette.Link, QColor(86, 156, 214))
    palette.setColor(QPalette.Disabled, QPalette.Link, QColor(86, 156, 214))
    palette.setColor(QPalette.Active, QPalette.Highlight, QColor(0, 122, 204))
    palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(63, 63, 63))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(0, 122, 204))
    palette.setColor(QPalette.Active, QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor(212, 212, 212))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(128, 128, 128))
    palette.setColor(QPalette.Active, QPalette.Light, QColor(80, 80, 80))
    palette.setColor(QPalette.Inactive, QPalette.Light, QColor(80, 80, 80))
    palette.setColor(QPalette.Disabled, QPalette.Light, QColor(80, 80, 80))
    palette.setColor(QPalette.Active, QPalette.Midlight, QColor(70, 70, 70))
    palette.setColor(QPalette.Inactive, QPalette.Midlight, QColor(70, 70, 70))
    palette.setColor(QPalette.Disabled, QPalette.Midlight, QColor(70, 70, 70))
    palette.setColor(QPalette.Active, QPalette.Dark, QColor(35, 35, 35))
    palette.setColor(QPalette.Inactive, QPalette.Dark, QColor(35, 35, 35))
    palette.setColor(QPalette.Disabled, QPalette.Dark, QColor(35, 35, 35))
    palette.setColor(QPalette.Active, QPalette.Mid, QColor(50, 50, 50))
    palette.setColor(QPalette.Inactive, QPalette.Mid, QColor(50, 50, 50))
    palette.setColor(QPalette.Disabled, QPalette.Mid, QColor(50, 50, 50))
    palette.setColor(QPalette.Active, QPalette.Shadow, QColor(20, 20, 20))
    palette.setColor(QPalette.Inactive, QPalette.Shadow, QColor(20, 20, 20))
    palette.setColor(QPalette.Disabled, QPalette.Shadow, QColor(0, 0, 0))
    palette.setColor(QPalette.Active, QPalette.LinkVisited, QColor(180, 130, 200))
    palette.setColor(QPalette.Inactive, QPalette.LinkVisited, QColor(180, 130, 200))
    palette.setColor(QPalette.Disabled, QPalette.LinkVisited, QColor(180, 130, 200))
    palette.setColor(QPalette.Active, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.NoRole, QColor(0, 0, 0))
    # fmt: on

    widget.setPalette(palette)
    return palette


def set_light_palette(widget: QWidget) -> QPalette:
    """Set the object palette to a light theme.

    Args:
        widget: The QWidget (QApplication, QWindow, etc.) to set the palette on.

    Returns:
        QPalette: The custom palette.
    """

    # fmt: off
    palette = QPalette()
    palette.setColor(QPalette.Active, QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.Inactive, QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.Disabled, QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.Active, QPalette.WindowText, QColor(30, 30, 30))
    palette.setColor(QPalette.Inactive, QPalette.WindowText, QColor(30, 30, 30))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(150, 150, 150))
    palette.setColor(QPalette.Active, QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor(245, 245, 245))
    palette.setColor(QPalette.Active, QPalette.AlternateBase, QColor(248, 248, 248))
    palette.setColor(QPalette.Inactive, QPalette.AlternateBase, QColor(248, 248, 248))
    palette.setColor(QPalette.Disabled, QPalette.AlternateBase, QColor(248, 248, 248))
    palette.setColor(QPalette.Active, QPalette.ToolTipBase, QColor(255, 255, 225))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipBase, QColor(255, 255, 225))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipBase, QColor(255, 255, 225))
    palette.setColor(QPalette.Active, QPalette.ToolTipText, QColor(30, 30, 30))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipText, QColor(30, 30, 30))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipText, QColor(30, 30, 30))
    palette.setColor(QPalette.Active, QPalette.Text, QColor(30, 30, 30))
    palette.setColor(QPalette.Inactive, QPalette.Text, QColor(30, 30, 30))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
    palette.setColor(QPalette.Active, QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.Inactive, QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.Disabled, QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.Active, QPalette.ButtonText, QColor(30, 30, 30))
    palette.setColor(QPalette.Inactive, QPalette.ButtonText, QColor(30, 30, 30))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
    palette.setColor(QPalette.Active, QPalette.BrightText, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.BrightText, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.BrightText, QColor(0, 0, 0))
    palette.setColor(QPalette.Active, QPalette.Link, QColor(0, 102, 204))
    palette.setColor(QPalette.Inactive, QPalette.Link, QColor(0, 102, 204))
    palette.setColor(QPalette.Disabled, QPalette.Link, QColor(0, 102, 204))
    palette.setColor(QPalette.Active, QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(220, 220, 220))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.Active, QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor(30, 30, 30))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Midlight, QColor(230, 230, 230))
    palette.setColor(QPalette.Inactive, QPalette.Midlight, QColor(230, 230, 230))
    palette.setColor(QPalette.Disabled, QPalette.Midlight, QColor(245, 245, 245))
    palette.setColor(QPalette.Active, QPalette.Dark, QColor(180, 180, 180))
    palette.setColor(QPalette.Inactive, QPalette.Dark, QColor(180, 180, 180))
    palette.setColor(QPalette.Disabled, QPalette.Dark, QColor(180, 180, 180))
    palette.setColor(QPalette.Active, QPalette.Mid, QColor(200, 200, 200))
    palette.setColor(QPalette.Inactive, QPalette.Mid, QColor(200, 200, 200))
    palette.setColor(QPalette.Disabled, QPalette.Mid, QColor(200, 200, 200))
    palette.setColor(QPalette.Active, QPalette.Shadow, QColor(150, 150, 150))
    palette.setColor(QPalette.Inactive, QPalette.Shadow, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.Shadow, QColor(100, 100, 100))
    palette.setColor(QPalette.Active, QPalette.LinkVisited, QColor(128, 78, 160))
    palette.setColor(QPalette.Inactive, QPalette.LinkVisited, QColor(128, 78, 160))
    palette.setColor(QPalette.Disabled, QPalette.LinkVisited, QColor(128, 78, 160))
    palette.setColor(QPalette.Active, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.NoRole, QColor(0, 0, 0))
    # fmt: on

    widget.setPalette(palette)
    return palette


def set_style(widget: QWidget, style: str = None) -> FXProxyStyle:
    """Set the style.

    Args:
        widget (QWidget): The QWidget subclass to set the style to.
        style (str, optional): The style to set. Defaults to `None`.

    Returns:
        FXProxyStyle: The custom style.

    Note:
        You can retrieve the styles available on your system with
            `QStyleFactory.keys()`.
        Only those string values are accepted in the `style` argument.
    """

    if style is not None:
        style = QStyleFactory.create(style)

    custom_style = FXProxyStyle(style)
    widget.setStyle(custom_style)
    return custom_style


def get_theme(widget: QWidget) -> str:
    """Get the theme of the widget.

    Args:
        widget: The QWidget subclass to get the theme from.

    Returns:
        The theme of the widget. Can be either "dark", "light", or
            "unknown".
    """

    palette = widget.palette()
    if palette.color(QPalette.Window) == QColor(53, 53, 53):
        return "dark"
    elif palette.color(QPalette.Window) == QColor(240, 240, 240):
        return "light"
    return "unknown"


def set_theme(widget: QWidget, theme: str) -> None:
    """Set the theme of the widget.

    Args:
        widget (QWidget): The QWidget subclass to set the theme to.
        theme (str): The theme to set. Can be either "dark" or "light".
    """

    if theme == "dark":
        set_dark_palette(widget)
    elif theme == "light":
        set_light_palette(widget)


def invalidate_standard_icon_map() -> None:
    """Invalidate the cached standard icon map.

    This should be called when changing themes so icons are regenerated
    with the new color scheme on next access.
    """

    global _standard_icon_map
    _standard_icon_map = None


def toggle_theme(
    widget: QWidget,
    color_a: str = _COLOR_A_DEFAULT,
    color_b: str = _COLOR_B_DEFAULT,
) -> str:
    """Toggle the theme of the widget between light and dark.

    This function handles all necessary state updates including:
    - Switching the stylesheet
    - Updating icon colors
    - Invalidating icon caches
    - Applying the appropriate palette

    Args:
        widget: The QWidget subclass to toggle the theme on.
        color_a: The primary color to use. Defaults to `_COLOR_A_DEFAULT`.
        color_b: The secondary color to use. Defaults to `_COLOR_B_DEFAULT`.

    Returns:
        str: The new theme that was applied ("dark" or "light").

    Examples:
        Toggle theme on a window (standalone or inside a DCC)
        >>> new_theme = fxstyle.toggle_theme(window)
        >>> print(f"Switched to {new_theme} theme")

        Toggle theme with custom colors
        >>> fxstyle.toggle_theme(window, color_a="#FF5722", color_b="#E64A19")
    """

    global _theme

    # Determine new theme
    new_theme = "light" if _theme == "dark" else "dark"

    # Update icon colors for the new theme
    # Dark theme: light gray icons, Light theme: dark gray icons
    icon_color = "#B4B4B4" if new_theme == "dark" else "#424242"
    fxicons.set_icon_defaults(color=icon_color)

    # Clear icon caches so they regenerate with new colors
    fxicons.clear_icon_cache()

    # Invalidate the standard icon map
    invalidate_standard_icon_map()

    # Apply the new stylesheet
    widget.setStyleSheet(
        load_stylesheet(
            color_a=color_a,
            color_b=color_b,
            theme=new_theme,
        )
    )

    # Apply palette (works even without access to QApplication)
    if new_theme == "dark":
        set_dark_palette(widget)
    else:
        set_light_palette(widget)

    return new_theme


def _remove_comments(text: str) -> str:
    """Remove single-line and multi-line comments from the input text.

    Args:
        text (str): The input text containing comments.

    Returns:
        str: The input text with comments removed.
    """

    # Regular expression to remove single-line and multi-line comments
    pattern = r"(\"(?:\\\"|.)*?\"|\'.*?\'|//.*?$|/\*.*?\*/)"
    return re.sub(
        pattern,
        lambda m: "" if m.group(0).startswith("/") else m.group(0),
        text,
        flags=re.DOTALL | re.MULTILINE,
    )


def load_colors_from_jsonc(jsonc_file: str = COLOR_FILE) -> dict:
    """Load colors from a JSONC (JSON with comments) file.

    Args:
        jsonc_file (str): The path to the JSONC file. Defaults to `COLOR_FILE`.

    Returns:
        dict: A dictionary containing color definitions.
    """

    global _colors
    if _colors is not None:
        return _colors

    with open(jsonc_file, "r") as f:
        jsonc_content = f.read()
        json_content = _remove_comments(jsonc_content)
        _colors = json.loads(json_content)
        return _colors


def replace_colors(
    stylesheet: str,
    colors_dict: dict = load_colors_from_jsonc(COLOR_FILE),
    prefix: str = "",
) -> str:
    """Replace color placeholders in a stylesheet with actual color values.

    This function searches for placeholders in the format `@{prefix}{key}`
    and replaces them with the corresponding color values from the dictionary.

    Args:
        stylesheet: The stylesheet string containing color placeholders.
        colors_dict: Dictionary containing color definitions. Only top-level
            non-dict values are used. Defaults to colors from COLOR_FILE.
        prefix: Prefix for placeholder names. Defaults to empty string.

    Returns:
        The stylesheet with all matching placeholders replaced.

    Examples:
        >>> colors = {"primary": "#FF5722", "secondary": "#E64A19"}
        >>> qss = "color: @primary; background: @secondary;"
        >>> result = replace_colors(qss, colors)
        >>> print(result)
        'color: #FF5722; background: #E64A19;'
    """

    placeholders = {
        f"@{prefix}{key}": value
        for key, value in colors_dict.items()
        if not isinstance(value, dict)
    }
    for placeholder, color in placeholders.items():
        stylesheet = stylesheet.replace(placeholder, color)
    return stylesheet


def load_stylesheet(
    style_file: str = STYLE_FILE,
    color_a: str = _COLOR_A_DEFAULT,
    color_b: str = _COLOR_B_DEFAULT,
    extra: Optional[str] = None,
    theme: str = "dark",
) -> str:
    """Load the stylesheet and replace some part of the given QSS file to
    make them work in a DCC.

    Args:
        style_file: The path to the QSS file. Defaults to `STYLE_FILE`.
        color_a: The primary color to use. Defaults to `#649eff`.
        color_b: The secondary color to use. Defaults to `#4188ff`.
        extra: Extra stylesheet content to append. Defaults to `None`.
        theme: The theme to use, either 'dark' or 'light'. Defaults to 'dark'.

    Returns:
        str: The stylesheet with the right elements replaced.
    """

    if not os.path.exists(style_file):
        return "None"

    with open(style_file, "r") as in_file:
        stylesheet = in_file.read()

    # Ensure font compatibility on multipe platforms
    if sys.platform == "win32":
        default_font = "Segoe UI"
    else:
        default_font = QFontDatabase.systemFont(
            QFontDatabase.GeneralFont
        ).family()
    font_stylesheet = f"""* {{
        font-family: "{default_font}";
    }}
    """

    # Determine which icon folder to use based on theme
    icon_folder = "stylesheet_dark" if theme == "dark" else "stylesheet_light"

    replace = {
        "@ColorA": color_a,
        "@ColorB": color_b,
        "~icons": str(_parent_directory / "icons" / icon_folder).replace(
            os.sep, "/"
        ),
    }

    global _theme
    if theme == "dark":
        _theme = "dark"
        replace.update(
            {
                "black": "white",
                "#181818": "silver",
                "@SliderHandle": "#BBBBBB",
                "@GreyH": "#201F1F",
                "@GreyP": "#2A2929",
                "@GreyA": "#3A3939",
                "@GreyB": "#2D2C2C",
                "@GreyC": "#302F2F",
                "@GreyF": "#404040",
                "@GreyQ": "#605F5F",
                "@GreyO": "#403F3F",
                "@GreyK": "#4A4949",
                "@GreyJ": "#444444",
                "@GreyI": "#6C6C6C",
                "@GreyN": "#727272",
                "@GreyD": "#777777",
                "@GreyG": "#787876",
                "@GreyM": "#A8A8A8",
                "@GreyL": "#B1B1B1",
                "@GreyE": "#BBBBBB",
            }
        )
    elif theme == "light":
        _theme = "light"
        replace.update(
            {
                "white": "#1E1E1E",  # Text becomes dark
                "silver": "#2D2D2D",  # Secondary text dark
                "@SliderHandle": "#FFFFFF",  # White slider handle
                "@GreyH": "#FFFFFF",  # Lightest background (inputs, lists)
                "@GreyP": "#F5F5F5",  # Very light (scrollbar bg)
                "@GreyA": "#E0E0E0",  # Light border
                "@GreyB": "#FAFAFA",  # Alternate row bg
                "@GreyC": "#F0F0F0",  # Main widget background
                "@GreyF": "#BDBDBD",  # Disabled bg
                "@GreyQ": "#9E9E9E",  # Scrollbar handle
                "@GreyO": "#EEEEEE",  # Subtle bg
                "@GreyK": "#BDBDBD",  # Border color
                "@GreyJ": "#CACACA",  # Subtle border
                "@GreyI": "#757575",  # Medium gray
                "@GreyN": "#616161",  # Darker gray
                "@GreyD": "#757575",  # Disabled text
                "@GreyG": "#424242",  # Dark accent
                "@GreyM": "#9E9E9E",  # Medium text
                "@GreyL": "#616161",  # Secondary text
                "@GreyE": "#212121",  # Primary text (dark on light)
            }
        )

    for key, value in replace.items():
        stylesheet = stylesheet.replace(key, value)

    stylesheet = (
        font_stylesheet + stylesheet + extra
        if extra
        else font_stylesheet + stylesheet
    )

    stylesheet = stylesheet + extra if extra else stylesheet

    return stylesheet
