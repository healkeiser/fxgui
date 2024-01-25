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
from PySide2.QtWidgets import QProxyStyle, QStyle, QStyleOption, QWidget, QApplication, QStyleFactory
from PySide2.QtGui import QIcon, QPalette, QColor

# Internal
try:
    from pyside2_vfx_template import icons
except ModuleNotFoundError:
    import icons

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

        colors_dict = load_colors_from_jsonc()

        STANDARD_ICON_MAP = {
            QStyle.SP_ArrowBack: ("arrow_back", "white"),
            QStyle.SP_ArrowDown: ("arrow_downward", "white"),
            QStyle.SP_ArrowForward: ("arrow_forward", "white"),
            QStyle.SP_ArrowLeft: ("arrow_back", "white"),
            QStyle.SP_ArrowRight: ("arrow_forward", "white"),
            QStyle.SP_ArrowUp: ("arrow_upward", "white"),
            QStyle.SP_BrowserReload: ("refresh", "white"),
            QStyle.SP_BrowserStop: ("block", "white"),
            QStyle.SP_CommandLink: ("arrow_forward", "white"),
            QStyle.SP_ComputerIcon: ("computer", "white"),
            QStyle.SP_CustomBase: ("tune", "white"),
            QStyle.SP_DesktopIcon: ("desktop_windows", "white"),
            QStyle.SP_DialogAbortButton: ("cancel", "white"),
            QStyle.SP_DialogApplyButton: ("done", "white"),
            QStyle.SP_DialogCancelButton: ("cancel", "white"),
            QStyle.SP_DialogCloseButton: ("close", "white"),
            QStyle.SP_DialogDiscardButton: ("delete", "white"),
            QStyle.SP_DialogHelpButton: ("help", "white"),
            QStyle.SP_DialogIgnoreButton: ("notifications_paused", "white"),
            QStyle.SP_DialogNoButton: ("cancel", "white"),
            QStyle.SP_DialogNoToAllButton: ("do_not_disturb", "white"),
            QStyle.SP_DialogOkButton: ("done", "white"),
            QStyle.SP_DialogOpenButton: ("open_in_new", "white"),
            QStyle.SP_DialogResetButton: ("cleaning_services", "white"),
            QStyle.SP_DialogRetryButton: ("restart_alt", "white"),
            QStyle.SP_DialogSaveAllButton: ("save", "white"),
            QStyle.SP_DialogSaveButton: ("save", "white"),
            QStyle.SP_DialogYesButton: ("done", "white"),
            QStyle.SP_DialogYesToAllButton: ("done", "white"),
            QStyle.SP_DirClosedIcon: ("folder", "white"),
            QStyle.SP_DirHomeIcon: ("home", "white"),
            QStyle.SP_DirIcon: ("folder_open", "white"),
            QStyle.SP_DirLinkIcon: ("drive_file_move", "white"),
            QStyle.SP_DirLinkOpenIcon: ("folder_open", "white"),
            QStyle.SP_DockWidgetCloseButton: ("cancel", "white"),
            QStyle.SP_DirOpenIcon: ("folder_open", "white"),
            QStyle.SP_DriveCDIcon: ("album", "white"),
            QStyle.SP_DriveDVDIcon: ("album", "white"),
            QStyle.SP_DriveFDIcon: ("usb", "white"),
            QStyle.SP_DriveHDIcon: ("dns", "white"),
            QStyle.SP_DriveNetIcon: ("cloud", "white"),
            QStyle.SP_FileDialogBack: ("arrow_back", "white"),
            QStyle.SP_FileDialogContentsView: ("find_in_page", "white"),
            QStyle.SP_FileDialogDetailedView: ("description", "white"),
            QStyle.SP_FileDialogEnd: ("note", "white"),
            QStyle.SP_FileDialogInfoView: ("info", "white"),
            QStyle.SP_FileDialogListView: ("grid_view", "white"),
            QStyle.SP_FileDialogNewFolder: ("create_new_folder", "white"),
            QStyle.SP_FileDialogStart: ("insert_drive_file", "white"),
            QStyle.SP_FileDialogToParent: ("upload_file", "white"),
            QStyle.SP_FileIcon: ("description", "white"),
            QStyle.SP_FileLinkIcon: ("file_present", "white"),
            QStyle.SP_LineEditClearButton: ("close", "white"),
            QStyle.SP_MediaPause: ("pause", "white"),
            QStyle.SP_MediaPlay: ("play_arrow", "white"),
            QStyle.SP_MediaSeekBackward: ("fast_rewind", "white"),
            QStyle.SP_MediaSeekForward: ("fast_forward", "white"),
            QStyle.SP_MediaSkipBackward: ("skip_previous", "white"),
            QStyle.SP_MediaSkipForward: ("skip_next", "white"),
            QStyle.SP_MediaStop: ("stop", "white"),
            QStyle.SP_MediaVolume: ("volume_up", "white"),
            QStyle.SP_MediaVolumeMuted: ("volume_off", "white"),
            #
            QStyle.SP_MessageBoxCritical: ("error", colors_dict["feedback"]["error"]["light"]),
            QStyle.SP_MessageBoxInformation: ("info", colors_dict["feedback"]["info"]["light"]),
            QStyle.SP_MessageBoxQuestion: ("help", colors_dict["feedback"]["success"]["light"]),
            QStyle.SP_MessageBoxWarning: ("warning", colors_dict["feedback"]["warning"]["light"]),
            #
            QStyle.SP_RestoreDefaultsButton: ("restore", "white"),
            QStyle.SP_TitleBarCloseButton: ("close", "white"),
            QStyle.SP_TitleBarContextHelpButton: ("question_mark", "white"),
            QStyle.SP_TitleBarMaxButton: ("maximize", "white"),
            QStyle.SP_TitleBarMenuButton: ("menu", "white"),
            QStyle.SP_TitleBarMinButton: ("minimize", "white"),
            QStyle.SP_TitleBarNormalButton: ("close_fullscreen", "white"),
            QStyle.SP_TitleBarShadeButton: ("expand_more", "white"),
            QStyle.SP_TitleBarUnshadeButton: ("expand_less", "white"),
            QStyle.SP_ToolBarHorizontalExtensionButton: ("keyboard_arrow_right", "white"),
            QStyle.SP_ToolBarVerticalExtensionButton: ("keyboard_arrow_down", "white"),
            QStyle.SP_TrashIcon: ("delete", "white"),
            QStyle.SP_VistaShield: ("security", "white"),
        }

        icon_name, color = STANDARD_ICON_MAP.get(standardIcon, (None, None))
        if icon_name is not None:
            return icons.get_icon(icon_name, color=color)
        else:
            return super().standardIcon(standardIcon, option, widget)


def set_application_palette(application: QApplication) -> QPalette:
    """Set the application palette to a dark theme.

    Args:
        application (QApplication): The application to set the palette to.

    Returns:
        QPalette: The custom palette.
    """

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, QColor("white"))
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ToolTipText, QColor("white"))
    dark_palette.setColor(QPalette.Text, QColor("white"))
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, QColor("white"))
    dark_palette.setColor(QPalette.BrightText, QColor("red"))
    # Controls the highlight color
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    # dark_palette.setColor(QPalette.Link, QColor("#35caff"))
    # dark_palette.setColor(QPalette.Highlight, QColor("#35caff"))
    #
    dark_palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("darkGray"))
    dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("darkGray"))
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor("darkGray"))
    dark_palette.setColor(QPalette.Disabled, QPalette.Light, QColor(53, 53, 53))
    application.setPalette(dark_palette)

    return dark_palette


def set_application_style(application: QApplication) -> VFXProxyStyle:
    """Set the "Fusion" style in a dark theme.

    Args:
        application (QApplication, optional): The application to set the style to.

    Returns:
        VFXProxyStyle: The custom style.
    """

    fusion_style = QStyleFactory.create("Fusion")
    custom_style = VFXProxyStyle(fusion_style)
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
