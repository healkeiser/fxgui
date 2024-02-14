"""VFXSplashscreen module.

This module contains the VFXSplashScreen class, a customized QSplashScreen class.
The VFXSplashScreen class provides a splash screen for your application. It allows
for customization of the splash screen image, title, information text, and more.
It also provides options for displaying a progress bar and applying a fade-in effect.

Classes:
    VFXSplashScreen: A class for creating a customized splash screen.
"""

# Built-in
import os
import time
from typing import Optional

# Third-party
from qtpy.QtWidgets import *
from qtpy.QtUiTools import *
from qtpy.QtCore import *
from qtpy.QtGui import *

# Internal
try:
    from pyside2_vfx_template import shadows
except ModuleNotFoundError:
    import shadows

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

###### CODE ####################################################################


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
        company (str, optional): Company name. Defaults to `Company Ltd.`.
        theme (str, optional): Theme to be applied to the splash screen.
            Defaults to `dark`.
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
        company (str): Company name. Defaults to `Company Ltd.`.
        theme (str): Theme applied to the splash screen.
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
        theme: str = "dark",
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
        self.theme: str = theme
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
        shadows.add_shadows(self, frame)

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
        company = self.company if self.company and len(self.company) >= 1 else "Company Ltd."

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
