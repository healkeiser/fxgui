"""UI stylesheet, HEX colors and others.

Examples:
    >>> import style
    >>> colors = style.load_colors_from_jsonc()
    >>> houdini_orange = colors["houdini"]["main"]
    #3cc0fd
"""

# Built-in
import re
import json
from pathlib import Path
from typing import Optional

# Third-party
from qtpy.QtCore import QObject
from qtpy.QtWidgets import QProxyStyle, QStyle, QStyleOption, QWidget, QApplication, QStyleFactory
from qtpy.QtGui import QIcon, QPalette, QColor

# Internal
try:
    import style, icons
except ModuleNotFoundError:
    from fxgui import style, icons

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


# Constants
STYLE_FILE = Path(__file__).parent / "qss" / "style.qss"
COLORS_FILE = Path(__file__).parent / "style.jsonc"

# Globals
_colors = None


class VFXProxyStyle(QProxyStyle):
    """A custom style class that extends QProxyStyle to provide custom icons."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icon_color = "red"  # Default color

    def standardIcon(
        self,
        standardIcon: QStyle.StandardPixmap,
        option: Optional[QStyleOption] = None,
        widget: Optional[QWidget] = None,
    ) -> QIcon:
        """Returns an icon for the given standardIcon.

        Args:
            standardIcon (QStyle.StandardPixmap): The standard pixmap for which an icon should be returned.
            option (QStyleOption, optional): An option that can be used to fine-tune the look of the icon.
                Defaults to `None`.
            widget (QWidget, optional): The widget for which the icon is being requested. Defaults to `None`.

        Returns:
            QIcon: The icon for the standardIcon. If no custom icon is found, the default icon is returned.
        """

        colors_dict = style.load_colors_from_jsonc()

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

        icon_name, color = STANDARD_ICON_MAP.get(standardIcon, (None, None))
        if icon_name is not None:
            return icons.get_pixmap(icon_name, color=color)
        else:
            return super().standardIcon(standardIcon, option, widget)

    def set_icon_color(self, color: str):
        """Sets the color of the icons.

        Args:
            color (str): The color to set the icons to.
        """
        self.icon_color = color


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


def set_dark_palette(object: QObject) -> QPalette:
    """Set the object palette to a dark theme.

    Args:
        application (QObject): The QObject (QApplication, QWindow, etc.) to set the palette on.

    Returns:
        QPalette: The custom palette.
    """

    palette = QPalette()
    palette.setColor(QPalette.Active, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Inactive, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.Active, QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(169, 169, 169))
    palette.setColor(QPalette.Active, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Inactive, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.Active, QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.Inactive, QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.Active, QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.Active, QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Active, QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(169, 169, 169))
    palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Inactive, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Disabled, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Active, QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.Inactive, QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(169, 169, 169))
    palette.setColor(QPalette.Active, QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Inactive, QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Active, QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Inactive, QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Disabled, QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Active, QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.Active, QPalette.HighlightedText, QColor(35, 35, 35))
    palette.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor(35, 35, 35))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(35, 35, 35))
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
    object.setPalette(palette)
    return palette


def set_light_palette(object: QObject) -> QPalette:
    """Set the object palette to a light theme.

    Args:
        application (QObject): The QObject (QApplication, QWindow, etc.) to set the palette on.

    Returns:
        QPalette: The custom palette.
    """

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
    object.setPalette(palette)
    return palette


def set_style(application: QApplication, style: Optional[str] = "Fusion") -> VFXProxyStyle:
    """Set the "Fusion" style in a dark theme.

    Args:
        application (QApplication, optional): The application to set the style to.
        style (str, optional): The style to set. Defaults to "Fusion".

    Returns:
        VFXProxyStyle: The custom style.
    """

    style = QStyleFactory.create("Fusion")
    custom_style = VFXProxyStyle(style)
    application.setStyle(custom_style)

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


def load_colors_from_jsonc(jsonc_file: str = COLORS_FILE) -> dict:
    """Load colors from a JSONC (JSON with comments) file.

    Args:
        jsonc_file (str): The path to the JSONC file. Defaults to `COLORS_FILE`.

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
    colors_dict: dict = load_colors_from_jsonc(COLORS_FILE),
    prefix="",
) -> str:
    """_summary_

    Args:
        stylesheet (str): The stylesheet to replace the colors in.
        colors_dict (dict, optional): The dict to use to search for colors to be
            replaced. Defaults to `load_colors_from_jsonc(COLORS_FILE)`.
        prefix (str, optional): The identifier prefix for colors to be replaced.
            Defaults to `""`.

    Returns:
        str: The stylesheet with replaced colors.
    """

    placeholders = {f"@{prefix}{key}": value for key, value in colors_dict.items() if not isinstance(value, dict)}
    for placeholder, color in placeholders.items():
        stylesheet = stylesheet.replace(placeholder, color)
    return stylesheet
