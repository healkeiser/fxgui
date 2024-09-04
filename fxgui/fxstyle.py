"""UI stylesheet, HEX colors and others.

Examples:
    >>> import style
    >>> colors = style.load_colors_from_jsonc()
    >>> houdini_orange = colors["houdini"]["main"]
    #3cc0fd
"""

# Built-in
import os
import re
import json
import platform
from pathlib import Path
from typing import Optional

# Third-party
from qtpy.QtCore import QObject
from qtpy.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleOption,
    QWidget,
    QStyleFactory,
)
from qtpy.QtGui import QIcon, QPalette, QColor

# Internal
from fxgui import fxicons


# Constants
_parent_directory = Path(__file__).parent
STYLE_FILE = _parent_directory / "qss" / "style.qss"
COLOR_FILE = _parent_directory / "style.jsonc"

# Lighter
_COLOR_A_DEFAULT = "#912d9af4"  # "#282727"  # "#605f5f"  # "rgba(89, 126, 151, 200)"  # "#597e97"

# Darker
_COLOR_B_DEFAULT = (
    "#8c2275b8"  # "#302f2f"  # "rgba(61, 87, 104, 200)"  # "#3d5768"
)

# Globals
_colors = None


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

        colors_dict = load_colors_from_jsonc()

        # fmt: off
        STANDARD_ICON_MAP = {
            QStyle.SP_ArrowBack: ("arrow_back", self.icon_color),
            QStyle.SP_ArrowDown: ("arrow_downward", self.icon_color),
            QStyle.SP_ArrowForward: ("arrow_forward", self.icon_color),
            QStyle.SP_ArrowLeft: ("arrow_back", self.icon_color),
            QStyle.SP_ArrowRight: ("arrow_forward", self.icon_color),
            QStyle.SP_ArrowUp: ("arrow_upward", self.icon_color),
            QStyle.SP_BrowserReload: ("refresh", self.icon_color),
            QStyle.SP_BrowserStop: ("block", self.icon_color),
            QStyle.SP_CommandLink: ("arrow_forward", self.icon_color),
            QStyle.SP_ComputerIcon: ("computer", self.icon_color),
            QStyle.SP_CustomBase: ("tune", self.icon_color),
            QStyle.SP_DesktopIcon: ("desktop_windows", self.icon_color),
            QStyle.SP_DialogAbortButton: ("cancel", self.icon_color),
            QStyle.SP_DialogApplyButton: ("done", self.icon_color),
            QStyle.SP_DialogCancelButton: ("cancel", self.icon_color),
            QStyle.SP_DialogCloseButton: ("close", self.icon_color),
            QStyle.SP_DialogDiscardButton: ("delete", self.icon_color),
            QStyle.SP_DialogHelpButton: ("help", self.icon_color),
            QStyle.SP_DialogIgnoreButton: ("notifications_paused", self.icon_color),
            QStyle.SP_DialogNoButton: ("cancel", self.icon_color),
            QStyle.SP_DialogNoToAllButton: ("do_not_disturb", self.icon_color),
            QStyle.SP_DialogOkButton: ("done", self.icon_color),
            QStyle.SP_DialogOpenButton: ("open_in_new", self.icon_color),
            QStyle.SP_DialogResetButton: ("cleaning_services", self.icon_color),
            QStyle.SP_DialogRetryButton: ("restart_alt", self.icon_color),
            QStyle.SP_DialogSaveAllButton: ("save", self.icon_color),
            QStyle.SP_DialogSaveButton: ("save", self.icon_color),
            QStyle.SP_DialogYesButton: ("done", self.icon_color),
            QStyle.SP_DialogYesToAllButton: ("done", self.icon_color),
            QStyle.SP_DirClosedIcon: ("folder", self.icon_color),
            QStyle.SP_DirHomeIcon: ("home", self.icon_color),
            QStyle.SP_DirIcon: ("folder_open", self.icon_color),
            QStyle.SP_DirLinkIcon: ("drive_file_move", self.icon_color),
            QStyle.SP_DirLinkOpenIcon: ("folder_open", self.icon_color),
            QStyle.SP_DockWidgetCloseButton: ("cancel", self.icon_color),
            QStyle.SP_DirOpenIcon: ("folder_open", self.icon_color),
            QStyle.SP_DriveCDIcon: ("album", self.icon_color),
            QStyle.SP_DriveDVDIcon: ("album", self.icon_color),
            QStyle.SP_DriveFDIcon: ("usb", self.icon_color),
            QStyle.SP_DriveHDIcon: ("dns", self.icon_color),
            QStyle.SP_DriveNetIcon: ("cloud", self.icon_color),
            QStyle.SP_FileDialogBack: ("arrow_back", self.icon_color),
            QStyle.SP_FileDialogContentsView: ("find_in_page", self.icon_color),
            QStyle.SP_FileDialogDetailedView: ("description", self.icon_color),
            QStyle.SP_FileDialogEnd: ("note", self.icon_color),
            QStyle.SP_FileDialogInfoView: ("info", self.icon_color),
            QStyle.SP_FileDialogListView: ("grid_view", self.icon_color),
            QStyle.SP_FileDialogNewFolder: ("create_new_folder", self.icon_color),
            QStyle.SP_FileDialogStart: ("insert_drive_file", self.icon_color),
            QStyle.SP_FileDialogToParent: ("upload_file", self.icon_color),
            QStyle.SP_FileIcon: ("description", self.icon_color),
            QStyle.SP_FileLinkIcon: ("file_present", self.icon_color),
            QStyle.SP_LineEditClearButton: ("close", self.icon_color),
            QStyle.SP_MediaPause: ("pause", self.icon_color),
            QStyle.SP_MediaPlay: ("play_arrow", self.icon_color),
            QStyle.SP_MediaSeekBackward: ("fast_rewind", self.icon_color),
            QStyle.SP_MediaSeekForward: ("fast_forward", self.icon_color),
            QStyle.SP_MediaSkipBackward: ("skip_previous", self.icon_color),
            QStyle.SP_MediaSkipForward: ("skip_next", self.icon_color),
            QStyle.SP_MediaStop: ("stop", self.icon_color),
            QStyle.SP_MediaVolume: ("volume_up", self.icon_color),
            QStyle.SP_MediaVolumeMuted: ("volume_off", self.icon_color),
            #
            QStyle.SP_MessageBoxCritical: ("error", colors_dict["feedback"]["error"]["light"]),
            QStyle.SP_MessageBoxInformation: ("info", colors_dict["feedback"]["info"]["light"]),
            QStyle.SP_MessageBoxQuestion: ("help", colors_dict["feedback"]["success"]["light"]),
            QStyle.SP_MessageBoxWarning: ("warning", colors_dict["feedback"]["warning"]["light"]),
            #
            QStyle.SP_RestoreDefaultsButton: ("restore", self.icon_color),
            QStyle.SP_TitleBarCloseButton: ("close", self.icon_color),
            QStyle.SP_TitleBarContextHelpButton: ("question_mark", self.icon_color),
            QStyle.SP_TitleBarMaxButton: ("maximize", self.icon_color),
            QStyle.SP_TitleBarMenuButton: ("menu", self.icon_color),
            QStyle.SP_TitleBarMinButton: ("minimize", self.icon_color),
            QStyle.SP_TitleBarNormalButton: ("close_fullscreen", self.icon_color),
            QStyle.SP_TitleBarShadeButton: ("expand_more", self.icon_color),
            QStyle.SP_TitleBarUnshadeButton: ("expand_less", self.icon_color),
            QStyle.SP_ToolBarHorizontalExtensionButton: ("keyboard_arrow_right", self.icon_color),
            QStyle.SP_ToolBarVerticalExtensionButton: ("keyboard_arrow_down", self.icon_color),
            QStyle.SP_TrashIcon: ("delete", self.icon_color),
            QStyle.SP_VistaShield: ("security", self.icon_color),
        }
        # fmt: on

        icon_name, color = STANDARD_ICON_MAP.get(standardIcon, (None, None))
        if icon_name is not None:
            return fxicons.get_pixmap(icon_name, color=color)
        else:
            return super().standardIcon(standardIcon, option, widget)

    def set_icon_color(self, color: str):
        """Sets the color of the icons.

        Args:
            color (str): The color to set the icons to.
        """

        self.icon_color = color
        self.update()


def get_current_palette(object: QObject) -> None:
    """Prints the current palette of the given Qt object.

    This function retrieves the current palette of the given Qt object and prints
    each color role in each state group in the format `QPalette.State, QPalette.Role, QColor(r, g, b)`.

    Args:
        object (QObject): The Qt object whose palette is to be retrieved.
    """

    palette = object.palette()
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


def _set_dark_palette(object: QObject) -> QPalette:
    """Set the object palette to a dark theme.

    Args:
        application (QObject): The QObject (QApplication, QWindow, etc.) to set
            the palette on.

    Returns:
        QPalette: The custom palette.
    """

    palette = QPalette()
    palette.setColor(QPalette.Active, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Inactive, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(
        QPalette.Active, QPalette.WindowText, QColor(255, 255, 255)
    )
    palette.setColor(
        QPalette.Inactive, QPalette.WindowText, QColor(255, 255, 255)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.WindowText, QColor(169, 169, 169)
    )
    palette.setColor(QPalette.Active, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Inactive, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(
        QPalette.Active, QPalette.AlternateBase, QColor(53, 53, 53)
    )
    palette.setColor(
        QPalette.Inactive, QPalette.AlternateBase, QColor(53, 53, 53)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.AlternateBase, QColor(53, 53, 53)
    )
    palette.setColor(QPalette.Active, QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(
        QPalette.Inactive, QPalette.ToolTipBase, QColor(25, 25, 25)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.ToolTipBase, QColor(25, 25, 25)
    )
    palette.setColor(
        QPalette.Active, QPalette.ToolTipText, QColor(255, 255, 255)
    )
    palette.setColor(
        QPalette.Inactive, QPalette.ToolTipText, QColor(255, 255, 255)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.ToolTipText, QColor(255, 255, 255)
    )
    palette.setColor(QPalette.Active, QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(169, 169, 169))
    palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Inactive, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(
        QPalette.Active, QPalette.ButtonText, QColor(255, 255, 255)
    )
    palette.setColor(
        QPalette.Inactive, QPalette.ButtonText, QColor(255, 255, 255)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.ButtonText, QColor(169, 169, 169)
    )
    palette.setColor(QPalette.Active, QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Active, QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Inactive, QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Disabled, QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Active, QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(
        QPalette.Inactive, QPalette.Highlight, QColor(42, 130, 218)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.Highlight, QColor(42, 130, 218)
    )
    palette.setColor(
        QPalette.Active, QPalette.HighlightedText, QColor(35, 35, 35)
    )
    palette.setColor(
        QPalette.Inactive, QPalette.HighlightedText, QColor(35, 35, 35)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.HighlightedText, QColor(35, 35, 35)
    )
    palette.setColor(QPalette.Active, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Midlight, QColor(227, 227, 227))
    palette.setColor(
        QPalette.Inactive, QPalette.Midlight, QColor(227, 227, 227)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.Midlight, QColor(247, 247, 247)
    )
    palette.setColor(QPalette.Active, QPalette.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.Inactive, QPalette.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.Disabled, QPalette.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.Active, QPalette.Mid, QColor(160, 160, 160))
    palette.setColor(QPalette.Inactive, QPalette.Mid, QColor(160, 160, 160))
    palette.setColor(QPalette.Disabled, QPalette.Mid, QColor(160, 160, 160))
    palette.setColor(QPalette.Active, QPalette.Shadow, QColor(105, 105, 105))
    palette.setColor(QPalette.Inactive, QPalette.Shadow, QColor(105, 105, 105))
    palette.setColor(QPalette.Disabled, QPalette.Shadow, QColor(0, 0, 0))
    palette.setColor(
        QPalette.Active, QPalette.LinkVisited, QColor(255, 0, 255)
    )
    palette.setColor(
        QPalette.Inactive, QPalette.LinkVisited, QColor(255, 0, 255)
    )
    palette.setColor(
        QPalette.Disabled, QPalette.LinkVisited, QColor(255, 0, 255)
    )
    palette.setColor(QPalette.Active, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.NoRole, QColor(0, 0, 0))
    object.setPalette(palette)
    return palette


def set_dark_palette(object: QObject) -> QPalette:
    """Set the object palette to a dark theme.

    Args:
        object (QObject): The QObject (QApplication, QWindow, etc.) to set the
            palette on.

    Returns:
        QPalette: The custom palette.
    """

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, "white")
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, "white")
    palette.setColor(QPalette.Text, "white")
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, "white")
    palette.setColor(QPalette.BrightText, "red")
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
    palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, "darkGray")
    palette.setColor(QPalette.Disabled, QPalette.WindowText, "darkGray")
    palette.setColor(QPalette.Disabled, QPalette.Text, "darkGray")
    palette.setColor(QPalette.Disabled, QPalette.Light, QColor(53, 53, 53))
    object.setPalette(palette)
    return palette


def set_light_palette(object: QObject) -> QPalette:
    """Set the object palette to a light theme.

    Args:
        object (QObject): The QObject (QApplication, QWindow, etc.) to set the palette on.

    Returns:
        QPalette: The custom palette.
    """

    # fmt: off
    palette = QPalette()
    palette.setColor(QPalette.Active, QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.Inactive, QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.Disabled, QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.Active, QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(120, 120, 120))
    palette.setColor(QPalette.Active, QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor(240, 240, 240))
    palette.setColor(QPalette.Active, QPalette.AlternateBase, QColor(233, 231, 227))
    palette.setColor(QPalette.Inactive, QPalette.AlternateBase, QColor(233, 231, 227))
    palette.setColor(QPalette.Disabled, QPalette.AlternateBase, QColor(247, 247, 247))
    palette.setColor(QPalette.Active, QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.Active, QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Active, QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 120, 120))
    palette.setColor(QPalette.Active, QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.Inactive, QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.Disabled, QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.Active, QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 120, 120))
    palette.setColor(QPalette.Active, QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Link, QColor(0, 0, 255))
    palette.setColor(QPalette.Inactive, QPalette.Link, QColor(0, 0, 255))
    palette.setColor(QPalette.Disabled, QPalette.Link, QColor(0, 0, 255))
    palette.setColor(QPalette.Active, QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(240, 240, 240))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.Active, QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Midlight, QColor(227, 227, 227))
    palette.setColor(QPalette.Inactive, QPalette.Midlight, QColor(227, 227, 227))
    palette.setColor(QPalette.Disabled, QPalette.Midlight, QColor(247, 247, 247))
    palette.setColor(QPalette.Active, QPalette.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.Inactive, QPalette.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.Disabled, QPalette.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.Active, QPalette.Mid, QColor(160, 160, 160))
    palette.setColor(QPalette.Inactive, QPalette.Mid, QColor(160, 160, 160))
    palette.setColor(QPalette.Disabled, QPalette.Mid, QColor(160, 160, 160))
    palette.setColor(QPalette.Active, QPalette.Shadow, QColor(105, 105, 105))
    palette.setColor(QPalette.Inactive, QPalette.Shadow, QColor(105, 105, 105))
    palette.setColor(QPalette.Disabled, QPalette.Shadow, QColor(0, 0, 0))
    palette.setColor(QPalette.Active, QPalette.LinkVisited, QColor(255, 0, 255))
    palette.setColor(QPalette.Inactive, QPalette.LinkVisited, QColor(255, 0, 255))
    palette.setColor(QPalette.Disabled, QPalette.LinkVisited, QColor(255, 0, 255))
    palette.setColor(QPalette.Active, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.NoRole, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.NoRole, QColor(0, 0, 0))
    # fmt: on

    object.setPalette(palette)
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
    prefix="",
) -> str:
    """_summary_

    Args:
        stylesheet (str): The stylesheet to replace the colors in.
        colors_dict (dict, optional): The dict to use to search for colors to be
            replaced. Defaults to `load_colors_from_jsonc(COLOR_FILE)`.
        prefix (str, optional): The identifier prefix for colors to be replaced.
            Defaults to `""`.

    Returns:
        str: The stylesheet with replaced colors.
    """

    placeholders = {
        f"@{prefix}{key}": value
        for key, value in colors_dict.items()
        if not isinstance(value, dict)
    }
    for placeholder, color in placeholders.items():
        stylesheet = stylesheet.replace(placeholder, color)
    return stylesheet


def _load_stylesheet(
    style_file: str = STYLE_FILE, color_file: str = COLOR_FILE
) -> Optional[str]:
    """Load and process the stylesheet.

    This function loads a stylesheet from a QSS file and applies color
    replacements based on the definitions in `style.jsonc` file. It also
    replaces certain placeholders with their corresponding values.

    Args:
        style_file (str, optional): The path to the QSS file. Defaults to `HOUDINI_STYLE_FILE`.
        color_file (str, optional): The path to the JSONC file containing color definitions. Defaults to `COLOR_FILE`.

    Returns:
        Optional[str]: The processed stylesheet content, or `None` if the file(s) don't exist.
    """

    if not os.path.exists(style_file):
        return None

    if not os.path.exists(color_file):
        return None

    with open(style_file, "r") as in_file:
        stylesheet = in_file.read()

    colors_dict = load_colors_from_jsonc(color_file)

    # Perform color replacements
    stylesheet = replace_colors(stylesheet, colors_dict)

    # Replace icons path
    stylesheet = stylesheet.replace(
        "qss:", os.path.dirname(__file__).replace("\\", "/") + "/"
    )

    return stylesheet


def _load_stylesheet(style_file: str = STYLE_FILE):
    """Load the stylesheet and replace some part of the given QSS file to
    make them work in Houdini.

    Args:
        style_file (str, optional): The path to the QSS file.
            Defaults to `STYLE_FILE`.

    Returns:
        str: The stylesheet with the right elements replaced.
    """

    if not os.path.exists(style_file):
        return "None"

    with open(style_file, "r") as in_file:
        stylesheet = in_file.read()

    stylesheet_path = os.path.dirname(style_file)
    stylesheet_path = stylesheet_path.replace("\\", "/") + "/"

    replace = {
        "@icons": str(Path(__file__).parent / "icons" / "stylesheet").replace(
            "\\", "/"
        )
    }

    for key, value in replace.items():
        stylesheet = stylesheet.replace(key, value)

    return stylesheet


def _load_stylesheet(style_file: str = STYLE_FILE):
    """Load the stylesheet and replace some part of the `.qss` file to
    make them work in Houdini.

    Returns:
        str:
            The stylesheet with the right elements replaced.
    """

    if not os.path.exists(style_file):
        return "None"

    with open(style_file, "r") as in_file:
        stylesheet = in_file.read()

    def replace_colors(stylesheet, colors_dict, prefix=""):
        for key, value in colors_dict.items():
            if isinstance(value, dict):
                # Recursively replace nested dictionaries
                stylesheet = replace_colors(
                    stylesheet,
                    value,
                    f"{prefix.replace(' ', '_')}{key.replace(' ', '_')}_",
                )
            else:
                # Replace color placeholders with their corresponding values
                placeholder = f"@{prefix}{key}"
                stylesheet = stylesheet.replace(placeholder, value)

    # Colors
    # stylesheet = replace_colors(stylesheet, COLORS)

    # Icons
    stylesheet = stylesheet.replace(
        "~icons",
        str(_parent_directory / "icons" / "stylesheet").replace("\\", "/"),
    )

    return stylesheet


def load_stylesheet(
    style_file: str = STYLE_FILE,
    color_a: str = _COLOR_A_DEFAULT,
    color_b: str = _COLOR_B_DEFAULT,
    extra: Optional[str] = None,
) -> str:
    """Load the stylesheet and replace some part of the given QSS file to
    make them work in a DCC.

    Args:
        style_file (str, optional): The path to the QSS file.
            Defaults to `STYLE_FILE`.
        color_a (str, optional): The primary color to use.
            Defaults to `#649eff`.
        color_b (str, optional): The secondary color to use.
            Defaults to `#4188ff`.
        extra (str, optional): Extra stylesheet content to append.
            Defaults to `None`.

    Returns:
        str: The stylesheet with the right elements replaced.
    """

    if not os.path.exists(style_file):
        return "None"

    with open(style_file, "r") as in_file:
        stylesheet = in_file.read()

    # Ensure font compatibility on multipe platforms
    if platform.system() == "Windows":
        font_stylesheet = """* {
            font-family: "Segoe UI";
        }
        """
    elif platform.system() == "Linux":
        font_stylesheet = """* {
            font-family: "Open Sans";
        }
        """
    elif platform.system() == "Darwin":
        font_stylesheet = """* {
            font-family: "SF Pro";
        }
        """

    replace = {
        "@ColorA": color_a,
        "@ColorB": color_b,
        #
        "@GreyH": "#201F1F",
        "@GreyA": "#3A3939",
        "@GreyB": "#2D2C2C",
        "@GreyC": "#302F2F",
        "@GreyF": "#404040",
        "@GreyO": "#403F3F",
        "@GreyK": "#4A4949",
        "@GreyJ": "#444",
        "@GreyI": "#6c6c6c",
        "@GreyN": "#727272",
        "@GreyD": "#777777",
        "@GreyG": "#787876",
        "@GreyM": "#a8a8a8",
        "@GreyL": "#b1b1b1",
        "@GreyE": "#bbb",
        "@White": "#FFFFFF",
        #
        "@Grey90": "#201F1F",
        "@Grey85": "#2B2B2B",
        "@Grey82": "#2D2C2C",
        "@Grey81": "#302F2F",
        "@Grey77": "#3A3939",
        "@Grey75": "#403F3F",
        "@Grey75Alt": "#404040",
        "@Grey73": "#444",
        "@Grey71": "#4A4949",
        "@Grey58": "#6c6c6c",
        "@Grey55": "#727272",
        "@Grey53": "#777777",
        "@Grey53Alt": "#787876",
        "@Grey34": "#a8a8a8",
        "@Grey30": "#b1b1b1",
        "@Grey27": "#bbb",
        #
        "~icons": str(_parent_directory / "icons" / "stylesheet").replace(
            os.sep, "/"
        ),
    }

    for key, value in replace.items():
        stylesheet = stylesheet.replace(key, value)

    stylesheet = (
        font_stylesheet + stylesheet + extra
        if extra
        else font_stylesheet + stylesheet
    )

    return stylesheet
