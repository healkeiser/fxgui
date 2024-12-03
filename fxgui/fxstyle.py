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
_COLOR_A_DEFAULT = "#007ACC"  # Lighter Blue
_COLOR_B_DEFAULT = "#005A9E"  # Darker Blue

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

        # ? Keeping this commented out for reference
        # fmt: off
        # STANDARD_ICON_MAP = {
        #     QStyle.SP_ArrowBack: qta.icon("mdi.arrow-left"),
        #     QStyle.SP_ArrowDown: qta.icon("mdi.arrow-down"),
        #     QStyle.SP_ArrowForward: qta.icon("mdi.arrow-right"),
        #     QStyle.SP_ArrowLeft: qta.icon("mdi.arrow-left"),
        #     QStyle.SP_ArrowRight: qta.icon("mdi.arrow-right"),
        #     QStyle.SP_ArrowUp: qta.icon("mdi.arrow-up"),
        #     QStyle.SP_BrowserReload: qta.icon("mdi.refresh"),
        #     QStyle.SP_BrowserStop: qta.icon("mdi.block-helper"),
        #     QStyle.SP_CommandLink: qta.icon("mdi.arrow-right"),
        #     QStyle.SP_ComputerIcon: qta.icon("mdi.desktop-classic"),
        #     QStyle.SP_CustomBase: qta.icon("mdi.tune"),
        #     QStyle.SP_DesktopIcon: qta.icon("mdi.desktop-mac"),
        #     QStyle.SP_DialogAbortButton: qta.icon("mdi.cancel"),
        #     QStyle.SP_DialogApplyButton: qta.icon("mdi.check"),
        #     QStyle.SP_DialogCancelButton: qta.icon("mdi.cancel"),
        #     QStyle.SP_DialogCloseButton: qta.icon("mdi.close"),
        #     QStyle.SP_DialogDiscardButton: qta.icon("mdi.delete"),
        #     QStyle.SP_DialogHelpButton: qta.icon("mdi.help-circle"),
        #     QStyle.SP_DialogIgnoreButton: qta.icon("mdi.bell-off"),
        #     QStyle.SP_DialogNoButton: qta.icon("mdi.cancel"),
        #     QStyle.SP_DialogNoToAllButton: qta.icon("mdi.do-not-disturb"),
        #     QStyle.SP_DialogOkButton: qta.icon("mdi.check"),
        #     QStyle.SP_DialogOpenButton: qta.icon("mdi.open-in-new"),
        #     QStyle.SP_DialogResetButton: qta.icon("mdi.broom"),
        #     QStyle.SP_DialogRetryButton: qta.icon("mdi.restart"),
        #     QStyle.SP_DialogSaveAllButton: qta.icon("mdi.content-save-all"),
        #     QStyle.SP_DialogSaveButton: qta.icon("mdi.content-save"),
        #     QStyle.SP_DialogYesButton: qta.icon("mdi.check"),
        #     QStyle.SP_DialogYesToAllButton: qta.icon("mdi.check-all"),
        #     QStyle.SP_DirClosedIcon: qta.icon("mdi.folder"),
        #     QStyle.SP_DirHomeIcon: qta.icon("mdi.home"),
        #     QStyle.SP_DirIcon: qta.icon("mdi.folder-open"),
        #     QStyle.SP_DirLinkIcon: qta.icon("mdi.link-variant"),
        #     QStyle.SP_DirLinkOpenIcon: qta.icon("mdi.folder-open"),
        #     QStyle.SP_DockWidgetCloseButton: qta.icon("mdi.close"),
        #     QStyle.SP_DirOpenIcon: qta.icon("mdi.folder-open"),
        #     QStyle.SP_DriveCDIcon: qta.icon("mdi.disc"),
        #     QStyle.SP_DriveDVDIcon: qta.icon("mdi.disc"),
        #     QStyle.SP_DriveFDIcon: qta.icon("mdi.usb"),
        #     QStyle.SP_DriveHDIcon: qta.icon("mdi.harddisk"),
        #     QStyle.SP_DriveNetIcon: qta.icon("mdi.cloud"),
        #     QStyle.SP_FileDialogBack: qta.icon("mdi.arrow-left"),
        #     QStyle.SP_FileDialogContentsView: qta.icon("mdi.file-find"),
        #     QStyle.SP_FileDialogDetailedView: qta.icon("mdi.file-document"),
        #     QStyle.SP_FileDialogEnd: qta.icon("mdi.file-check"),
        #     QStyle.SP_FileDialogInfoView: qta.icon("mdi.information"),
        #     QStyle.SP_FileDialogListView: qta.icon("mdi.view-list"),
        #     QStyle.SP_FileDialogNewFolder: qta.icon("mdi.folder-plus"),
        #     QStyle.SP_FileDialogStart: qta.icon("mdi.file"),
        #     QStyle.SP_FileDialogToParent: qta.icon("mdi.file-upload"),
        #     QStyle.SP_FileIcon: qta.icon("mdi.file"),
        #     QStyle.SP_FileLinkIcon: qta.icon("mdi.link"),
        #     QStyle.SP_LineEditClearButton: qta.icon("mdi.close"),
        #     QStyle.SP_MediaPause: qta.icon("mdi.pause"),
        #     QStyle.SP_MediaPlay: qta.icon("mdi.play"),
        #     QStyle.SP_MediaSeekBackward: qta.icon("mdi.rewind"),
        #     QStyle.SP_MediaSeekForward: qta.icon("mdi.fast-forward"),
        #     QStyle.SP_MediaSkipBackward: qta.icon("mdi.skip-previous"),
        #     QStyle.SP_MediaSkipForward: qta.icon("mdi.skip-next"),
        #     QStyle.SP_MediaStop: qta.icon("mdi.stop"),
        #     QStyle.SP_MediaVolume: qta.icon("mdi.volume-high"),
        #     QStyle.SP_MediaVolumeMuted: qta.icon("mdi.volume-off"),
        #     QStyle.SP_MessageBoxCritical: qta.icon("mdi.alert-circle", color=colors_dict["feedback"]["error"]["light"]),
        #     QStyle.SP_MessageBoxInformation: qta.icon("mdi.information", color=colors_dict["feedback"]["info"]["light"]),
        #     QStyle.SP_MessageBoxQuestion: qta.icon("mdi.help-circle", color=colors_dict["feedback"]["success"]["light"]),
        #     QStyle.SP_MessageBoxWarning: qta.icon("mdi.alert", color=colors_dict["feedback"]["warning"]["light"]),
        #     QStyle.SP_RestoreDefaultsButton: qta.icon("mdi.restore"),
        #     QStyle.SP_TitleBarCloseButton: qta.icon("mdi.close"),
        #     QStyle.SP_TitleBarContextHelpButton: qta.icon("mdi.help-circle"),
        #     QStyle.SP_TitleBarMaxButton: qta.icon("mdi.window-maximize"),
        #     QStyle.SP_TitleBarMenuButton: qta.icon("mdi.menu"),
        #     QStyle.SP_TitleBarMinButton: qta.icon("mdi.window-minimize"),
        #     QStyle.SP_TitleBarNormalButton: qta.icon("mdi.window-restore"),
        #     QStyle.SP_TitleBarShadeButton: qta.icon("mdi.arrow-collapse-down"),
        #     QStyle.SP_TitleBarUnshadeButton: qta.icon("mdi.arrow-collapse-up"),
        #     QStyle.SP_ToolBarHorizontalExtensionButton: qta.icon("mdi.arrow-right"),
        #     QStyle.SP_ToolBarVerticalExtensionButton: qta.icon("mdi.arrow-down"),
        #     QStyle.SP_TrashIcon: qta.icon("mdi.delete"),
        #     QStyle.SP_VistaShield: qta.icon("mdi.shield"),
        # }
        # fmt: on

        # fmt: off
        STANDARD_ICON_MAP = {
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

        icon = STANDARD_ICON_MAP.get(standardIcon)
        if icon is not None:
            return icon
        else:
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


def load_stylesheet(
    style_file: str = STYLE_FILE,
    color_a: str = _COLOR_A_DEFAULT,
    color_b: str = _COLOR_B_DEFAULT,
    extra: Optional[str] = None,
) -> str:
    """Load the stylesheet and replace some part of the given QSS file to
    make them work in a DCC.

    Args:
        style_file: The path to the QSS file. Defaults to `STYLE_FILE`.
        color_a: The primary color to use. Defaults to `#649eff`.
        color_b: The secondary color to use. Defaults to `#4188ff`.
        extra: Extra stylesheet content to append. Defaults to `None`.

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

    stylesheet = stylesheet + extra if extra else stylesheet

    return stylesheet
