#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VFXSplashscreen module."""

# Built-in
import os
import time

# Third-party
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Internal
import style
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
        title (str, optional): Title text to be displayed. Defaults to
            "Untitled".
        information (str, optional): Information text to be displayed.
            Defaults to a placeholder text.
        show_progress_bar (bool, optional): Whether to display a progress bar.
            Defaults to False.
        project (str, optional): Project name. Defaults to "N/A".
        version (str, optional): Version information. Defaults to "v0.0.0".
        fade_in (bool, optional): Whether to apply a fade-in effect on the
            splash screen. Defaults to False.

    Example:
        >>> app = QApplication(sys.argv)
        >>> splash = VFXSplashScreen(
        ...     image_path="path_to_your_image.png",
        ...     title="My Awesome App",
        ...     information="Loading...",
        ...     show_progress_bar=True,
        ...     project="Cool Project",
        ...     version="v1.2.3",
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
        image_path=None,
        title=None,
        information=None,
        show_progress_bar=False,
        project=None,
        version=None,
        fade_in=False,
    ):
        # Load the image using image_path and redirect as the original pixmap
        # argument from QSplashScreen
        if image_path is not None and os.path.isfile(image_path):
            image = self._resize_image(image_path)
        else:
            image = os.path.join(
                os.path.dirname(__file__), "images", "snap.png"
            )

        super().__init__(image)

        # Stylesheet
        self.setStyleSheet(style.load_stylesheet(light_theme=False))

        # Attributes
        self.pixmap = image
        self.title = title
        self.information = information
        self.show_progress_bar = show_progress_bar
        self.project = project
        self.version = version
        self.fade_in = fade_in

        # Functions
        self._grey_overlay()

    def progress(self, value, max_range=100):
        for value in range(max_range):
            time.sleep(0.25)
            self.progress_bar.setValue(value)

    def showMessage(self, message):
        self.info_label.setText(message.capitalize())

    # - Hidden methods

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
            "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis "
            "praesentium voluptatum deleniti atque corrupti quos dolores et quas "
            "molestias excepturi sint occaecati cupiditate non provident, similique "
            "sunt in culpa qui officia deserunt mollitia animi, id est laborum et "
            "dolorum fuga. Et harum quidem rerum facilis est et expedita distinctio. "
            "Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil "
            "impedit quo minus id quod maxime placeat facere possimus, omnis voluptas "
            "assumenda est, omnis dolor repellendus. Temporibus autem quibusdam et aut "
            "officiis debitis aut rerum necessitatibus saepe eveniet ut et voluptates "
            "repudiandae sint et molestiae non recusandae. Itaque earum rerum hic "
            "tenetur a sapiente delectus, ut aut reiciendis voluptatibus maiores alias "
            "consequatur aut perferendis doloribus asperiores repellat."
        )

        # Main QFrame
        frame = QFrame(self)
        frame.setGeometry(0, 0, self.pixmap.width() // 2, self.pixmap.height())
        # Eauivqlent to #1a1a1a with opacity
        stylesheet = "background-color: @tableBackground;"
        stylesheet = style.replace_colors(stylesheet)
        frame.setStyleSheet(stylesheet)
        shadows.add_shadows(self, frame)

        # Create a vertical layout for the QFrame
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(50, 50, 50, 50)

        # Title QLabel with a slightly bigger font and bold
        self.title_label = QLabel(
            self.title
            if self.title != None and len(self.title) >= 1
            else "Untitled"
        )
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(
            "font-size: 14pt;"
        )  # Mandatory because of style.qss
        layout.addWidget(self.title_label)

        # Spacer
        spacer_a = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer_a)

        # Information
        self.info_label = QLabel(
            self.information
            if self.information != None and len(self.information) >= 1
            else lorem_ipsum
        )
        self.info_label.setAlignment(Qt.AlignJustify)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Spacer
        spacer_b = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer_b)

        # Progress Bar
        if self.show_progress_bar:
            self.progress_bar = QProgressBar()
            layout.addWidget(self.progress_bar)

        # Spacer
        spacer_c = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer_c)

        # Copyright QLabel
        self.copyright_label = QLabel(
            f"{self.project if self.project != None and len(self.project)>=1 else 'N/A'} | {self.version if self.version != None and len(self.version)>=1 else 'v0.0.0'} | \u00A9 Company Ltd."
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
