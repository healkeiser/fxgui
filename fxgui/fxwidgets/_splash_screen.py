"""Custom splash screen widget."""

# Built-in
import os
from typing import Optional

# Third-party
from qtpy.QtCore import Qt, QRect, QTimer, Slot
from qtpy.QtGui import (
    QBitmap,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QSpacerItem,
    QSplashScreen,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxconstants, fxstyle, fxutils
from fxgui.fxwidgets._labels import FXElidedLabel


class _FXBorderWidget(QWidget):
    """Internal widget to draw the border on top of all other content."""

    def __init__(
        self,
        parent: QWidget,
        border_width: int,
        border_color: str,
        corner_radius: int,
    ):
        super().__init__(parent)
        self.border_width = border_width
        self.border_color = border_color
        self.corner_radius = corner_radius
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event) -> None:
        if self.border_width <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(self.border_color))
        pen.setWidthF(self.border_width)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        rect = self.rect()
        half_pen = self.border_width / 2.0
        border_rect = rect.adjusted(half_pen, half_pen, -half_pen, -half_pen)

        if self.corner_radius > 0:
            adjusted_radius = max(0, self.corner_radius - half_pen)
            painter.drawRoundedRect(
                border_rect, adjusted_radius, adjusted_radius
            )
        else:
            painter.drawRect(border_rect)

        painter.end()


class FXSplashScreen(fxstyle.FXThemeAware, QSplashScreen):
    """Customized QSplashScreen class."""

    ICON_HEIGHT = 32
    IDEAL_WIDTH = 800
    IDEAL_HEIGHT = 450

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
        fade_in: bool = False,
        set_stylesheet: bool = True,
        overlay_opacity: float = 1.0,
        corner_radius: int = 0,
        border_width: int = 0,
        border_color: str = "#4a4949",
    ):
        image = self._load_image(image_path)
        super().__init__(image)

        # Attributes
        self.pixmap: QPixmap = image
        self._default_icon = str(fxconstants.FAVICON_LIGHT)
        self.icon: QIcon = QIcon(icon) if icon else QIcon(self._default_icon)
        self.title: str = title or "Untitled"
        self.information: str = information or self._default_information()
        self.show_progress_bar: bool = show_progress_bar
        self.project: str = project or "Project"
        self.version: str = version or "0.0.0"
        self.company: str = company or "Company"
        self.fade_in: bool = fade_in
        self.overlay_opacity: float = overlay_opacity
        self.corner_radius: int = corner_radius
        self.border_width: int = border_width
        self.border_color: str = border_color  # Will use theme default if None

        # Enable transparency for smooth anti-aliased corners
        # Both flags are required for truly transparent rounded corners
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Methods
        self._grey_overlay()
        self._create_border_overlay()

        # Styling - load_stylesheet() automatically uses the saved theme
        if set_stylesheet:
            self.setStyleSheet(fxstyle.load_stylesheet())

        # Apply overlay opacity after stylesheet to ensure it's not overridden
        self._apply_overlay_opacity()

    def _on_theme_changed(self, _theme_name: str = None) -> None:
        """Handle theme changes."""
        # Update overlay background color
        if hasattr(self, "overlay_frame"):
            self._apply_overlay_opacity()

        # Update border color if using theme default (no explicit color set)
        if self.border_color is None:
            if hasattr(self, "_border_widget"):
                self._border_widget.border_color = self.theme.border_light
                self._border_widget.update()

    # Private methods
    def _load_image(self, image_path: Optional[str]) -> QPixmap:
        if image_path is None:
            image_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "images", "snap.png"
            )
        elif not os.path.isfile(image_path):
            raise ValueError(f"Invalid image path: {image_path}")
        return self._resize_image(image_path)

    def _default_information(self) -> str:
        return (
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

    def _resize_image(self, image_path: str) -> QPixmap:
        pixmap = QPixmap(image_path)
        width = pixmap.width()
        height = pixmap.height()

        aspect = width / float(height)
        ideal_aspect = self.IDEAL_WIDTH / float(self.IDEAL_HEIGHT)

        if aspect > ideal_aspect:
            new_width = int(ideal_aspect * height)
            offset = (width - new_width) / 2
            crop_rect = QRect(offset, 0, new_width, height)
        else:
            new_height = int(width / ideal_aspect)
            offset = (height - new_height) / 2
            crop_rect = QRect(0, int(offset), width, new_height)

        cropped_pixmap = pixmap.copy(crop_rect)
        resized_pixmap = cropped_pixmap.scaled(
            self.IDEAL_WIDTH,
            self.IDEAL_HEIGHT,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        return resized_pixmap

    def _grey_overlay(self) -> None:
        self.overlay_frame = QFrame(self)
        self._update_overlay_geometry()
        fxutils.add_shadows(self, self.overlay_frame)

        # Apply background opacity via stylesheet
        self._apply_overlay_opacity()

        layout = QVBoxLayout(self.overlay_frame)
        layout.setContentsMargins(50, 50, 50, 50)

        self.icon_label = QLabel()
        pixmap = QPixmap(self.icon.pixmap(self.ICON_HEIGHT))
        self.icon_label.setPixmap(pixmap)

        self.title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("font-size: 18pt;")

        title_icon_layout = QHBoxLayout()
        title_icon_layout.addWidget(self.icon_label)
        title_icon_layout.addWidget(self.title_label)
        title_icon_layout.setSpacing(10)
        title_icon_layout.addStretch()
        layout.addLayout(title_icon_layout)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self.info_label = FXElidedLabel(self.information)
        self.info_label.setAlignment(Qt.AlignJustify)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 10pt;")
        # Limit height to allow proper text elision
        self.info_label.setMaximumHeight(120)
        layout.addWidget(self.info_label)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignLeft)
        self.message_label.setStyleSheet("font-size: 10pt;")
        layout.addWidget(self.message_label)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        if self.show_progress_bar:
            self.progress_bar = QProgressBar()
            layout.addWidget(self.progress_bar)

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Copyright QLabel
        self.copyright_label = QLabel(
            f"{self.project} | {self.version} | {self.company}"
        )
        self.copyright_label.setStyleSheet(
            "font-size: 8pt; qproperty-alignment: AlignBottom;"
        )

        layout.addWidget(self.copyright_label)

    def _update_overlay_geometry(self) -> None:
        """Update overlay frame geometry accounting for border."""

        # Inset the overlay by the full border width so it doesn't cover the border
        inset = self.border_width
        x = inset
        y = inset
        width = (self.pixmap.width() // 2) - inset
        height = self.pixmap.height() - (2 * inset)
        self.overlay_frame.setGeometry(x, y, width, height)

    def _create_border_overlay(self) -> None:
        """Create a transparent overlay widget that draws the border on top."""

        # Use theme color if no explicit border color was provided
        border_color = self.border_color or self.theme.border_light
        self._border_widget = _FXBorderWidget(
            self,
            self.border_width,
            border_color,
            self.corner_radius,
        )
        self._border_widget.setGeometry(self.rect())
        self._border_widget.raise_()  # Ensure it's on top

    def _update_border_overlay(self) -> None:
        """Update the border overlay with current settings."""

        if hasattr(self, "_border_widget"):
            # Use theme color if no explicit border color was provided
            border_color = self.border_color or self.theme.border_light
            self._border_widget.border_width = self.border_width
            self._border_widget.border_color = border_color
            self._border_widget.corner_radius = self.corner_radius
            self._border_widget.setGeometry(self.rect())
            self._border_widget.update()

    def _update_copyright_label(self) -> None:
        project = self.project or "Project"
        version = self.version or "0.0.0"
        company = self.company or "\u00a9 Company"
        self.copyright_label.setText(f"{project} | {version} | {company}")

    def _fade_in(self) -> None:
        opaqueness = 0.0
        step = 0.001
        self.setWindowOpacity(opaqueness)
        self.show()

        @Slot()
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

    # Public methods
    def set_progress(self, value: int, max_range: int = 100):
        """Set the progress value for the splash screen.

        Args:
            value: The progress value.
            max_range: The maximum progress value. Defaults to `100`.
        """

        self.progress_bar.setRange(0, max_range)
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def set_pixmap(self, image_path: str) -> None:
        """Set the pixmap for the splash screen.

        Args:
            image_path: The path to the image file.
        """

        self.pixmap = self._resize_image(image_path)
        self.setPixmap(self.pixmap)

    def set_icon(self, icon_path: str) -> None:
        """Set the icon for the splash screen.

        Args:
            icon_path: The path to the icon file.
        """

        self.icon = QIcon(icon_path)
        pixmap = QPixmap(icon_path).scaledToHeight(
            self.ICON_HEIGHT, Qt.SmoothTransformation
        )
        self.icon_label.setPixmap(pixmap)

    def set_title(self, title: str) -> None:
        """Set the title for the splash screen.

        Args:
            title: The title string.
        """

        self.title = title
        self.title_label.setText(title)

    def set_information_text(self, information: str) -> None:
        """Set the information text for the splash screen.

        Args:
            information: The information text.
        """

        self.information = information
        self.info_label.setText(information)

    def toggle_progress_bar_visibility(self, show: bool) -> None:
        """Toggle the visibility of the progress bar.

        Args:
            show: Whether to show the progress bar.
        """

        self.show_progress_bar = show
        self.progress_bar.setVisible(show)

    def set_project_label(self, project: str) -> None:
        """Set the project name for the splash screen.

        Args:
            project: The project name.
        """

        self.project = project
        self._update_copyright_label()

    def set_version_label(self, version: str) -> None:
        """Set the version information for the splash screen.

        Args:
            version: The version string.
        """

        self.version = version
        self._update_copyright_label()

    def set_company_label(self, company: str) -> None:
        """Set the company name for the splash screen.

        Args:
            company: The company name.
        """

        self.company = company
        self._update_copyright_label()

    def toggle_fade_in(self, fade_in: bool) -> None:
        """Toggle the fade-in effect for the splash screen.

        Args:
            fade_in: Whether to fade in the splash screen.
        """

        self.fade_in = fade_in

    def set_overlay_opacity(self, opacity: float) -> None:
        """Set the opacity of the grey overlay background.

        Args:
            opacity: The opacity value between 0.0 (transparent) and 1.0 (opaque).
        """

        self.overlay_opacity = max(0.0, min(1.0, opacity))
        self._apply_overlay_opacity()

    def _apply_overlay_opacity(self) -> None:
        """Apply the overlay opacity to the frame's background color.

        Uses theme-aware surface color for the overlay background.
        """

        alpha = int(self.overlay_opacity * 255)

        # Get theme-aware surface color
        surface_color = QColor(self.theme.surface)

        # Set the frame background with opacity, and ensure all child QLabel
        # widgets have transparent backgrounds so they don't show through
        self.overlay_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba({surface_color.red()}, {surface_color.green()}, {surface_color.blue()}, {alpha});
            }}
            QFrame > QLabel {{
                background-color: transparent;
            }}
            """
        )

    def set_corner_radius(self, radius: int) -> None:
        """Set the corner radius for rounded corners.

        Args:
            radius: The corner radius in pixels. Use 0 for sharp corners.
        """

        self.corner_radius = max(0, radius)
        if self.corner_radius > 0:
            self._apply_rounded_mask()
        else:
            self.clearMask()
        self._update_border_overlay()
        self.update()

    def set_border(self, width: int, color: str = "#555555") -> None:
        """Set the border around the splash screen.

        Args:
            width: The border width in pixels. Use 0 for no border.
            color: The border color as a hex string.
        """

        self.border_width = max(0, width)
        self.border_color = color
        self._update_overlay_geometry()
        self._update_border_overlay()
        self.update()

    # Events
    def paintEvent(self, event) -> None:
        """Override to draw the pixmap with rounded corners."""

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Create rounded rectangle path
        path = QPainterPath()
        rect = self.rect()

        if self.corner_radius > 0:
            path.addRoundedRect(
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                self.corner_radius,
                self.corner_radius,
            )
        else:
            path.addRect(rect.x(), rect.y(), rect.width(), rect.height())

        # Clip to rounded rectangle and draw pixmap
        painter.setClipPath(path)
        painter.drawPixmap(rect, self.pixmap)
        painter.end()

    def mousePressEvent(self, _):
        pass

    def showEvent(self, event):
        super().showEvent(event)

        # Apply rounded mask for true window transparency
        if self.corner_radius > 0:
            self._apply_rounded_mask()

        if self.fade_in:
            self._fade_in()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reapply mask when resized
        if self.corner_radius > 0:
            self._apply_rounded_mask()

    def _apply_rounded_mask(self) -> None:
        """Apply a rounded rectangle mask for true window transparency."""

        # Create a bitmap mask with anti-aliased rounded corners
        bitmap = QBitmap(self.size())
        bitmap.fill(Qt.color0)  # Start fully transparent

        painter = QPainter(bitmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(Qt.color1)  # Opaque brush
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            self.rect(),
            self.corner_radius,
            self.corner_radius,
        )
        painter.end()

        self.setMask(bitmap)


def example() -> None:
    import sys
    import time
    from fxgui.fxwidgets import FXApplication

    app = FXApplication(sys.argv)

    splash = FXSplashScreen(
        title="FXSplashScreen",
        information="Loading resources and preparing the application...",
        show_progress_bar=True,
        project="Demo Project",
        version="1.0.0",
        company="Demo Company",
        corner_radius=12,
        border_width=1,
        fade_in=True,
    )
    splash.show()

    # Simulate loading progress
    for i in range(101):
        splash.set_progress(i)
        app.processEvents()
        time.sleep(0.02)

    splash.close()
    sys.exit(0)


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
