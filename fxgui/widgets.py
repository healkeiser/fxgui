"""Scripts related to the QtWidgets module."""

# Built-in
import os
import logging
from typing import Optional
from datetime import datetime
from webbrowser import open_new_tab
from urllib.parse import urlparse

# Third-party
from qtpy.QtWidgets import *
from qtpy.QtUiTools import *
from qtpy.QtCore import *
from qtpy.QtGui import *

# Internal
try:
    import style, utils, icons
except ModuleNotFoundError:
    from fxgui import style, utils, icons


###### CODE ####################################################################


# Constants
CRITICAL = 0
ERROR = 1
WARNING = 2
SUCCESS = 3
INFO = 4


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

        colors_dict = style.load_colors_from_jsonc()

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
            return icons.get_pixmap(icon_name, color=color)
        else:
            return super().standardIcon(standardIcon, option, widget)


class VFXApplication(QApplication):
    """Customized QApplication class."""

    def __init__(self):
        super().__init__()

        style.set_application_palette(self)
        style.set_application_style(self)


class VFXSplashScreen(QSplashScreen):
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
        project (str, optional): Project name. Defaults to `N/A`.
        version (str, optional): Version information. Defaults to `v0.0.0`.
        company (str, optional): Company name. Defaults to `Company`.
        accent_color (str, optional): Accent color to be applied to the splash
            screen. Defaults to `#039492`.
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
        project (str): Project name. Defaults to `N/A`.
        version (str): Version information. Defaults to `v0.0.0`.
        company (str): Company name. Defaults to `Company`.
        accent_color (str): Accent color applied to the splash screen.
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
        >>> splash = VFXSplashScreen(
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
        accent_color: str = "#039492",
        fade_in: bool = False,
    ):
        # Load the image using image_path and redirect as the original pixmap
        # argument from `QSplashScreen`
        if image_path is not None and os.path.isfile(image_path):
            image = self._resize_image(image_path)
        elif image_path is None:
            image = os.path.join(os.path.dirname(__file__), "images", "snap.png")
        else:
            raise ValueError(f"Invalid image path: {image_path}")

        super().__init__(image)

        # Attributes
        self.pixmap: QPixmap = image
        self._default_icon = os.path.join(os.path.dirname(__file__), "icons", "favicon.png")
        self.icon: QIcon = icon
        self.title: str = title
        self.information: str = information
        self.show_progress_bar: bool = show_progress_bar
        self.project: str = project
        self.version: str = version
        self.company: str = company
        self.accent_color: str = accent_color
        self.fade_in: bool = fade_in

        # Methods
        self._grey_overlay()

    def progress(self, value, max_range=100):
        for value in range(max_range):
            time.sleep(0.25)
            self.progress_bar.setValue(value)

    def showMessage(self, message):
        self.info_label.setText(message.capitalize())

    # - Private methods

    def _resize_image(self, image_path: str, ideal_width: int = 800, ideal_height: int = 450) -> QPixmap:
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
        frame.setStyleSheet("background-color: #232323;")
        utils.add_shadows(self, frame)

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
        spacer_a = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer_a)

        # Information
        self.info_label = QLabel(
            self.information if self.information is not None and len(self.information) >= 1 else lorem_ipsum
        )
        self.info_label.setAlignment(Qt.AlignJustify)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Spacer
        spacer_b = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer_b)

        # Progress Bar
        if self.show_progress_bar:
            self.progress_bar = QProgressBar()
            layout.addWidget(self.progress_bar)

        # Spacer
        spacer_c = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer_c)

        # Copyright QLabel
        project = self.project if self.project and len(self.project) >= 1 else "N/A"
        version = self.version if self.version and len(self.version) >= 1 else "v0.0.0"
        company = self.company if self.company and len(self.company) >= 1 else "Company"

        self.copyright_label = QLabel(f"{project} | {version} | \u00A9 {company}")
        self.copyright_label.setStyleSheet("font-size: 8pt; qproperty-alignment: AlignBottom;")
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


class VFXWindow(QMainWindow):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        size: Optional[int] = None,
        flags: Optional[Qt.WindowFlags] = None,
        documentation: Optional[str] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
        accent_color: str = "#039492",
        ui_file: Optional[str] = None,
    ):
        """Customized QMainWindow class.

        Args:
            parent (QWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
            icon (str, optional): Path to the window icon image. Defaults to `None`.
            title (str, optional): Title of the window. Defaults to `None`.
            size (Tuple[int, int], optional): Window size as width and height.
                Defaults to `None`.
            flags (Qt.WindowFlags, optional): Window flags. Defaults to `None`.
            documentation (str, optional): URL to the tool's documentation.
                Defaults to `None`.
            version (str, optional): Version label for the window.
                Defaults to `None`.
            company (str, optional): Company name for the window.
                Defaults to `Company`.
            accent_color (str, optional): Accent color to be applied to the splash
                screen. Defaults to `#039492`.
            ui_file (str, optional): Path to the UI file for loading.
                Defaults to `None`.

        Attributes:
            window_icon (QIcon): The icon of the window.
            window_title (str): The title of the window.
            window_size (QSize): The size of the window.
            window_flags (Qt.WindowFlags): The window flags.
            documentation (str): The documentation string.
            project (str): The project name.
            version (str): The version string.
            company (str): The company name.
            accent_color (str): The accent color.
            ui_file (str): The UI file path.

            CRITICAL (int): Constant for critical log level.
            ERROR (int): Constant for error log level.
            WARNING (int): Constant for warning log level.
            SUCCESS (int): Constant for success log level.
            INFO (int): Constant for info log level.

            about_action (QAction): Action for the "About" menu item.
            hide_action (QAction): Action for the "Hide" menu item.
            hide_others_action (QAction): Action for the "Hide Others" menu item.
            close_action (QAction): Action for the "Close" menu item.
            check_updates_action (QAction): Action for the "Check for Updates..."
                menu item.
            settings_action (QAction): Action for the "Settings" menu item.
            window_on_top_action (QAction): Action for the "Always On Top" menu
                item.
            minimize_window_action (QAction): Action for the "Minimize" menu item.
            maximize_window_action (QAction): Action for the "Maximize" menu item.
            open_documentation_action (QAction): Action for the "Documentation"
                menu item.
            previous_action (QAction): Action for the "Previous" toolbar item.
            next_action (QAction): Action for the "Next" toolbar item.
            refresh_action (QAction): Action for the "Refresh" toolbar item.
            home_action (QAction): Action for the "Home" toolbar item.

            menu_bar (QMenuBar): The menu bar of the window.
            icon_menu (QMenu): The icon menu of the menu bar.
            main_menu (QMenu): The main menu of the menu bar.
            about_menu (QAction): The "About" menu item in the main menu.
            check_updates_menu (QAction): The "Check for Updates..." menu item in
                the main menu.
            close_menu (QAction): The "Close" menu item in the main menu.
            hide_main_menu (QAction): The "Hide" menu item in the main menu.
            hide_others_menu (QAction): The "Hide Others" menu item in the main
                menu.
            edit_menu (QMenu): The edit menu of the menu bar.
            settings_menu (QAction): The "Settings" menu item in the edit menu.
            window_menu (QMenu): The window menu of the menu bar.
            minimize_menu (QAction): The "Minimize" menu item in the window menu.
            maximize_menu (QAction): The "Maximize" menu item in the window menu.
            on_top_menu (QAction): The "Always On Top" menu item in the window menu.
            help_menu (QMenu): The help menu of the menu bar.
            open_documentation_menu (QAction): The "Documentation" menu item in the
                help menu.

            toolbar (QToolBar): The toolbar of the window.
            previous_toolbar (QAction): The "Previous" toolbar item.
            next_toolbar (QAction): The "Next" toolbar item.
            refresh_toolbar (QAction): The "Refresh" toolbar item.
            home_toolbar (QAction): The "Home" toolbar item.
            about_dialog (QDialog): The "About" dialog.

            status_bar (QStatusBar): The status bar of the window.
            project_label (QLabel): The project label in the status bar.
            version_label (QLabel): The version label in the status bar.
            company_label (QLabel): The company label in the status bar.

        Examples:
            Outside a DCC
            >>> app = QApplication(sys.argv)
            >>> _window = VFXWindow(
            ...     icon="path/to/icon.png",
            ...     title="My Custom Window",
            ...     size=(800, 600),
            ...     documentation="https://my_tool_docs.com",
            ...     project="Awesome Project",
            ...     version="v1.0.0",
            ...     ui_file="path/to/ui_file.ui",
            ... )
            >>> _window.show()
            >>> _window.set_statusbar_message("Window initialized", window.INFO)
            >>> sys.exit(app.exec_())

            Inside a DCC (Houdini)
            >>> houdini_window = dcc.get_houdini_main_window()
            >>> houdini_style = dcc.get_houdini_stylesheet()
            >>> _window = window.VFXWindow(
            ...    parent=houdini_window,
            ...    ui_file="path/to/ui_file.ui",
            ...   )
            >>> _window.show()
            >>> _window.set_statusbar_message("Window initialized", window.INFO)

            Hide toolbar and menu bar
            >>> houdini_window = dcc.get_houdini_main_window()
            >>> houdini_style = dcc.get_houdini_stylesheet()
            >>> _window = window.VFXWindow(
            ...    parent=houdini_window,
            ...    ui_file="path/to/ui_file.ui",
            ...   )
            >>> _window.show()
            >>> _window.hide_toolbar()
            >>> _window.hide_menu_bar()
        """

        super().__init__(parent)

        # Attributes
        self._default_icon = os.path.join(os.path.dirname(__file__), "icons", "favicon.png")
        self.window_icon: QIcon = icon
        self.window_title: str = title
        self.window_size: QSize = size
        self.window_flags: Qt.WindowFlags = flags
        self.documentation: str = documentation
        self.project: str = project or "Project"
        self.version: str = version or "0.0.0"
        self.company: str = company or "Company"
        self.accent_color: str = accent_color
        self.ui_file: str = ui_file

        self.CRITICAL: int = CRITICAL
        self.ERROR: int = ERROR
        self.WARNING: int = WARNING
        self.SUCCESS: int = SUCCESS
        self.INFO: int = INFO

        # Methods
        self._create_actions()
        self._load_ui()
        self._set_window_icon()
        self._set_window_title()
        self._set_window_size()
        self._set_window_flags()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._check_documentation()
        self._add_shadows()

        # Custom stylesheet
        # self.setStyleSheet(style.load_stylesheet())

    # - Private methods

    def _load_ui(self) -> None:
        """Loads the UI from the specified UI file and sets it as the central
        widget of the main window.

        Warning:
            This method is intended for internal use only.
        """

        if self.ui_file is not None:
            self.ui = utils.load_ui(self, self.ui_file)

            # Add the loaded UI to the main window
            self.setCentralWidget(self.ui)

    def _set_window_icon(self) -> None:
        """Sets the window icon from the specified icon path.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_icon is not None and os.path.isfile(self.window_icon):
            self.setWindowIcon(QIcon(self.window_icon))
        else:
            self.setWindowIcon(QIcon(self._default_icon))

    def _set_window_title(self) -> None:
        """Sets the window title from the specified title.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_title is not None and len(self.window_title) >= 1:
            self.setWindowTitle(f"{self.window_title} *")
        else:
            self.setWindowTitle(f"Window *")

    def _set_window_size(self) -> None:
        """Sets the window size from the specified size.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_size is not None and len(self.window_size) >= 1:
            self.resize(QSize(*self.window_size))
        else:
            self.resize(QSize(500, 600))

    def _set_window_flags(self) -> None:
        """Sets the window flags from the specified flags.

        Warning:
            This method is intended for internal use only.
        """

        if self.window_flags is not None:
            self.setWindowFlags(self.windowFlags() | self.window_flags)

    def _create_actions(self) -> None:
        """Creates the actions for the window.

        Warning:
            This method is intended for internal use only.
        """

        # Main menu
        self.about_action = utils.create_action(
            self,
            "About",
            icons.get_pixmap("support", color="white"),
            self._show_about_dialog,
            enable=True,
            visible=True,
        )

        self.hide_action = utils.create_action(
            self,
            "Hide",
            icons.get_pixmap("hide_source", color="white"),
            self.hide,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+h",
        )

        self.hide_others_action = utils.create_action(
            self,
            "Hide Others",
            icons.get_pixmap("hide_source", color="white"),
            None,
            enable=False,
            visible=True,
        )

        self.close_action = utils.create_action(
            self,
            "Close",
            icons.get_pixmap("close", color="white"),
            self.close,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+q",
        )

        self.check_updates_action = utils.create_action(
            self,
            "Check for Updates...",
            icons.get_pixmap("update", color="white"),
            None,
            enable=False,
            visible=True,
        )

        # Edit menu
        self.settings_action = utils.create_action(
            self,
            "Settings",
            icons.get_pixmap("settings", color="white"),
            None,
            enable=False,
            visible=True,
            shortcut="Ctrl+Alt+s",
        )

        # Window menu
        self.window_on_top_action = utils.create_action(
            self,
            "Always On Top",
            icons.get_pixmap("hdr_strong", color="white"),
            self._window_on_top,
            enable=True,
            visible=True,
            shortcut="Ctrl+Shift+t",
        )

        self.minimize_window_action = utils.create_action(
            self,
            "Minimize",
            icons.get_pixmap("minimize", color="white"),
            self.showMinimized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+m",
        )

        self.maximize_window_action = utils.create_action(
            self,
            "Maximize",
            icons.get_pixmap("maximize", color="white"),
            self.showMaximized,
            enable=True,
            visible=True,
            shortcut="Ctrl+Alt+f",
        )

        # Help menu
        self.open_documentation_action = utils.create_action(
            self,
            "Documentation",
            icons.get_pixmap("contact_support", color="white"),
            lambda: open_new_tab(self.documentation),
            enable=True,
            visible=True,
        )

        # Toolbar
        self.home_action = utils.create_action(
            self,
            "Home",
            icons.get_pixmap("home", color="white"),
            None,
            enable=False,
            visible=True,
        )

        self.previous_action = utils.create_action(
            self,
            "Previous",
            icons.get_pixmap("arrow_back", color="white"),
            None,
            enable=False,
            visible=True,
        )

        self.next_action = utils.create_action(
            self,
            "Next",
            icons.get_pixmap("arrow_forward", color="white"),
            None,
            enable=False,
            visible=True,
        )

        self.refresh_action = utils.create_action(
            self,
            "Refresh",
            icons.get_pixmap("refresh", color="white"),
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
        self.check_updates_menu = self.main_menu.addAction(self.check_updates_action)
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)
        self.hide_main_menu = self.main_menu.addAction(self.hide_action)
        self.hide_others_menu = self.main_menu.addAction(self.hide_others_action)
        self.main_menu.addSeparator()
        self.close_menu = self.main_menu.addAction(self.close_action)

        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("&Edit")
        self.settings_menu = self.edit_menu.addAction(self.settings_action)

        # Window menu
        self.window_menu = self.menu_bar.addMenu("&Window")
        self.minimize_menu = self.window_menu.addAction(self.minimize_window_action)
        self.maximize_menu = self.window_menu.addAction(self.maximize_window_action)
        self.window_menu.addSeparator()
        self.on_top_menu = self.window_menu.addAction(self.window_on_top_action)
        self.window_menu.addSeparator()

        # Help menu
        self.help_menu = self.menu_bar.addMenu("&Help")
        self.open_documentation_menu = self.help_menu.addAction(self.open_documentation_action)

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

    def _create_status_bar(self) -> None:
        """Creates the status bar for the window.

        Warning:
            This method is intended for internal use only.
        """

        self.project_label = self._generate_label(self.project, "N/A")
        self.version_label = self._generate_label(self.version, "v0.0.0")
        self.company_label = self._generate_label(self.company, "\u00A9 Company")

        separator_str = "|"
        separator_left = QLabel(separator_str)
        separator_right = QLabel(separator_str)

        widgets = [
            self.project_label,
            separator_left,
            self.version_label,
            separator_right,
            self.company_label,
        ]

        for widget in widgets:
            self.statusBar().addPermanentWidget(widget)
        self.statusBar().setEnabled(True)
        self.statusBar().setVisible(True)

        self.statusBar().messageChanged.connect(self._on_status_message_changed)

    def _on_status_message_changed(self, args):
        """If there are no arguments, which means the message is being removed,
        then change the status bar background back to black.
        """

        if not args:
            self.statusBar().setStyleSheet(
                """
                QStatusBar {
                    border: 0px solid transparent;
                    background: #1b1b1b;
                    border-top: 1px solid black;
                }
            """
            )

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

        project_label = self._generate_label(self.project, "N/A")
        project_label.setAlignment(Qt.AlignCenter)
        version_label = self._generate_label(self.version, "v0.0.0")
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
                icons.get_pixmap("hdr_strong", color="white"),
                self.windowTitle().replace(" **", " *"),
            ),
            False: (
                "Regular Position",
                icons.get_pixmap("hdr_weak", color="white"),
                self.windowTitle().replace(" *", " **"),
            ),
        }
        stays_on_top = bool(flags & Qt.WindowStaysOnTopHint)
        text, icon, window_title = action_values[stays_on_top]
        flags ^= Qt.WindowStaysOnTopHint
        self.window_on_top_action.setText(text)
        if icon is not None:
            self.window_on_top_action.setIcon(icon)
        self.setWindowFlags(flags)
        self.setWindowTitle(window_title)
        self.show()

    def _move_window(self) -> None:
        """Moves the window to the selected area of the screen.

        Warning:
            This method is intended for internal use only.
        """

        frame_geo = self.frameGeometry()
        desktop_geometry = QDesktopWidget().availableGeometry()
        center_point = desktop_geometry.center()
        left_top_point = QPoint(desktop_geometry.left(), desktop_geometry.top())
        right_top_point = QPoint(desktop_geometry.right(), desktop_geometry.top())
        left_bottom_point = QPoint(desktop_geometry.left(), desktop_geometry.bottom())
        right_bottom_point = QPoint(desktop_geometry.right(), desktop_geometry.bottom())
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

    def _add_shadows(self) -> None:
        """Adds shadows to the window elements.

        Warning:
            This method is intended for internal use only.
        """

        utils.add_shadows(self, self.menu_bar)
        # utils.add_shadows(self, self.toolbar)
        utils.add_shadows(self, self.statusBar())

    def _get_current_time(self, display_seconds: bool = False, display_date: bool = False) -> str:
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

    # - Public methods

    def hide_toolbar(self) -> None:
        """Hide the toolbar."""

        self.toolbar.hide()

    def show_toolbar(self) -> None:
        """Show the toolbar."""

        self.toolbar.show()

    def hide_menu_bar(self) -> None:
        """Hide the menu bar."""

        self.menu_bar.hide()

    def show_menu_bar(self) -> None:
        """Show the menu bar."""

        self.menu_bar.show()

    def hide_statusbar(self) -> None:
        """Hide the status bar."""

        self.statusBar().hide()

    def show_statusbar(self) -> None:
        """Show the status bar."""

        self.statusBar().show()

    def set_statusbar_message(
        self,
        message: str,
        severity_type: int = 4,
        duration: float = 2.5,
        time: bool = True,
        logger: logging.Logger = None,
    ) -> None:
        """Display a message in the status bar with a specified severity.

        Args:
            message (str): The message to be displayed.
            severity_type (int, optional): The severity level of the message.
                Should be one of `CRITICAL`, `ERROR`, `WARNING`, `SUCCESS`,
                or `INFO`. Defaults to `INFO`.
            duration (float, optional): The duration in seconds for which
                the message should be displayed. Defaults to` 2.5`.
            time (bool, optional): Whether to display the current time before
                the message. Defaults to `True`.
            logger (Logger, optional): A logger object to log the message.
                Defaults to `None`.

        Examples:
            To display a critical error message with a red background
            >>> self.set_statusbar_message(
            ...     "Critical error occurred!",
            ...     severity_type=self.CRITICAL,
            ...     duration=5,
            ...     logger=my_logger,
            ... )

        Note:
            You can either use the window instance to retrieve the verbosity
            constants, or the window module.
        """

        # Create dictionnary for verbosity colors
        colors_dict = style.load_colors_from_jsonc()
        severity_mapping = {
            0: (
                "Critical",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxCritical),
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            1: (
                "Error",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxCritical),
                colors_dict["feedback"]["error"]["background"],
                colors_dict["feedback"]["error"]["dark"],
            ),
            2: (
                "Warning",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning),
                colors_dict["feedback"]["warning"]["background"],
                colors_dict["feedback"]["warning"]["dark"],
            ),
            3: (
                "Success",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxQuestion),
                colors_dict["feedback"]["success"]["background"],
                colors_dict["feedback"]["success"]["dark"],
            ),
            4: (
                "Info",
                QApplication.style().standardIcon(QStyle.SP_MessageBoxInformation),
                colors_dict["feedback"]["info"]["background"],
                colors_dict["feedback"]["info"]["dark"],
            ),
        }

        (
            severity_prefix,
            severity_icon,
            status_bar_color,
            status_bar_border_color,
        ) = severity_mapping[severity_type]

        # Message
        message_prefix = f"{severity_prefix}: {self._get_current_time()} - " if time else f"{severity_prefix}: "
        notification_message = f"{message_prefix} {message}"
        self.statusBar().showMessage(notification_message, duration * 1000)
        self.statusBar().setStyleSheet(
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
                logger.warning(message)
            elif severity_type == 2:
                logger.error(message)
            elif severity_type == 3 or severity_type == 4:
                logger.info(message)

    # - Events

    def closeEvent(self, event) -> None:
        self.setParent(None)


class VFXFloatingDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[QPixmap] = None,
        title: Optional[str] = None,
    ):
        """A floating dialog that appears at the cursor's position.
        It closes when any mouse button except the right one is pressed.

        Args:
            parent (QtWidget, optional): Parent widget. Defaults to `hou.qt.mainWindow()`.
            icon (QPixmap): The QPixmap icon.
            title (str): The dialog title.

        Attributes:
            dialog_icon (Qicon): _summary_.
            drop_position (tuple): _summary_.
            title_widget (QWidget): _summary_.
            title_label (QLabel): _summary_.
            title_layout (QLayout): _summary_.
            main_widget (Qwidget): _summary_.
            main_layout (QLayout): _summary_.
            layout (QLayout): _summary_.
            button_box (QDialogButtonBox): _summary_.
        """

        super().__init__(parent)

        # Attributes
        _icon = QPixmap(icons.get_icon_path("home"))
        _icon = icons.convert_pixmap_to_color(_icon, "white")
        self._default_icon = _icon
        self.dialog_icon: QIcon = icon
        self.dialog_title: str = title

        self.drop_position = QCursor.pos()
        self.dialog_position = (
            self.drop_position.x() - (self.width() / 2),
            self.drop_position.y() - (self.height() / 2),
        )

        # Methods
        self._setup_title()
        self._setup_main_widget()
        self._setup_buttons()
        self._setup_layout()
        self._handle_connections()
        self.set_dialog_icon(self.dialog_icon)
        self.set_dialog_title(self.dialog_title)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.resize(200, 40)
        self.setStyleSheet(
            """
            VFXFloatingDialog {
                border-top: 1px solid #949494;
                border-left: 1px solid #949494;
                border-bottom: 1px solid #262626;
                border-right: 1px solid #262626;
            }
        """
        )

    # - Private methods

    def _setup_title(self):
        """_summary_

        Warning:
            This method is intended for internal use only.
        """

        self._icon_label = QLabel(self)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title_widget = QWidget(self)
        self.title_widget.setStyleSheet("background-color: #2b2b2b;")

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

        if not icon:
            icon = self._default_icon

        self._icon_label.setPixmap(icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.dialog_icon = icon

    def set_dialog_title(self, title: str = None) -> None:
        """Sets the dialog's title.

        Args:
            title (str): The title of the dialog.
        """

        if title is not None and len(title) >= 1:
            self.title_label.setText(f"{title}")
        else:
            self.title_label.setText("Floating Dialog")

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
        super().close()
