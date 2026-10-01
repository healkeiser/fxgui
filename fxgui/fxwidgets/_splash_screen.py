"""Custom splash screen widget."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QPropertyAnimation, QRect, QRectF, Qt
from qtpy.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSplashScreen,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxconstants, fxstyle, fxutils
from fxgui.fxwidgets._labels import FXElidedLabel

fxstyle.register_widget_style(
    """
    FXSplashScreen QLabel { background: transparent; }
    FXSplashScreen QLabel#fxSplashCopyright { color: @text_muted; }
    """
)


def _rounded(rect: QRect, radius: int) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), radius, radius)
    return path


class _FXOverlay(QFrame):
    """The panel over the image's left half, the surface at an opacity."""

    def __init__(self, parent: "FXSplashScreen", opacity: float):
        super().__init__(parent)
        self.opacity = opacity

    def paintEvent(self, event) -> None:
        color = QColor(fxstyle.colors().surface)
        color.setAlphaF(self.opacity)
        splash = self.parentWidget()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # Inside the splash's own rounded corners.
        painter.setClipPath(_rounded(
            splash.rect().translated(-self.pos()), splash.corner_radius))
        painter.fillRect(self.rect(), color)
        painter.end()


class _FXBorderWidget(QWidget):
    """Draws the border on top of all other content."""

    def __init__(
        self,
        parent: QWidget,
        border_width: int,
        border_color: Optional[str],
        corner_radius: int,
    ):
        super().__init__(parent)
        self.border_width = border_width
        self.border_color = border_color
        self.corner_radius = corner_radius
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def color(self) -> QColor:
        """Return the border color: the given one, else the theme's."""
        return QColor(self.border_color or fxstyle.colors().border_light)

    def paintEvent(self, event) -> None:
        if self.border_width <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(self.color())
        pen.setWidthF(self.border_width)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        half = self.border_width / 2.0
        rect = QRectF(self.rect()).adjusted(half, half, -half, -half)
        radius = max(0.0, self.corner_radius - half)
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()


class FXSplashScreen(QSplashScreen):
    """A splash screen: the image, a panel with the title, and a progress bar.

    `showMessage` writes in the panel. A click hides it, as Qt's own does.

    Args:
        image_path: The image, cropped to 16:9. Defaults to fxgui's.
        icon: A path to the icon beside the title. Defaults to fxgui's.
        title: The title. Defaults to "Untitled".
        information: The text under the title. Defaults to `""`.
        show_progress_bar: Whether the progress bar shows before
            `set_progress`. Defaults to `False`.
        project: The copyright line's project. Defaults to `None`.
        version: The copyright line's version. Defaults to `None`.
        company: The copyright line's company. Defaults to `None`.
        fade_in: Whether to fade in over a second when shown. Defaults to
            `False`.
        overlay_opacity: The panel's opacity, 0.0 to 1.0. Defaults to 1.0.
        corner_radius: The corner radius, in pixels. Defaults to 0.
        border_width: The border width, in pixels. Defaults to 0, none.
        border_color: The border color. Defaults to `None`, the theme's
            `border_light`.

    Raises:
        ValueError: `image_path` is not an image Qt can read.
    """

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
        overlay_opacity: float = 1.0,
        corner_radius: int = 0,
        border_width: int = 0,
        border_color: Optional[str] = None,
    ):
        super().__init__(self._load_image(image_path))
        self._fade_in = fade_in
        self.corner_radius = max(0, corner_radius)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen
        )
        # The corners outside the painted clip stay see-through.
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._build_panel(
            QIcon(icon or str(fxconstants.FAVICON_LIGHT)),
            title or "Untitled",
            information or "",
            show_progress_bar,
            " | ".join(part for part in (project, version, company) if part),
            max(0.0, min(1.0, overlay_opacity)),
            border_width,
        )
        self._border_widget = _FXBorderWidget(
            self, border_width, border_color, self.corner_radius)
        self._border_widget.setGeometry(self.rect())
        self.messageChanged.connect(self.message_label.setText)
        fxstyle.register_themed_root(self)

    def _load_image(self, image_path: Optional[str]) -> QPixmap:
        pixmap = QPixmap(str(image_path or fxconstants.IMAGES_ROOT / "splash.png"))
        if pixmap.isNull():
            raise ValueError(f"Invalid image path: {image_path}")
        ideal = self.IDEAL_WIDTH / self.IDEAL_HEIGHT
        width, height = pixmap.width(), pixmap.height()
        if width / height > ideal:
            cropped = int(ideal * height)
            crop = QRect((width - cropped) // 2, 0, cropped, height)
        else:
            cropped = int(width / ideal)
            crop = QRect(0, (height - cropped) // 2, width, cropped)
        return pixmap.copy(crop).scaled(
            self.IDEAL_WIDTH,
            self.IDEAL_HEIGHT,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    def _build_panel(
        self,
        icon: QIcon,
        title: str,
        information: str,
        show_progress_bar: bool,
        copyright_line: str,
        opacity: float,
        inset: int,
    ) -> None:
        image = self.pixmap()
        self.overlay_frame = _FXOverlay(self, opacity)
        # Inside the border, over the image's left half.
        self.overlay_frame.setGeometry(
            inset, inset, image.width() // 2 - inset, image.height() - 2 * inset)
        fxutils.add_shadow(self.overlay_frame)

        layout = QVBoxLayout(self.overlay_frame)
        layout.setContentsMargins(24, 24, 24, 24)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(self.ICON_HEIGHT))
        self.title_label = QLabel(title)
        fxstyle.mark_as_title(self.title_label, rank="card")
        heading = QHBoxLayout()
        heading.setSpacing(8)
        heading.addWidget(self.icon_label)
        heading.addWidget(self.title_label)
        heading.addStretch()
        layout.addLayout(heading)
        layout.addStretch()

        self.info_label = FXElidedLabel(information)
        self.info_label.setAlignment(Qt.AlignJustify)
        self.info_label.setWordWrap(True)
        # Room to elide, not to grow.
        self.info_label.setMaximumHeight(120)
        layout.addWidget(self.info_label)
        layout.addStretch()

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        layout.addStretch()

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.progress_bar.setVisible(show_progress_bar)
        layout.addStretch()

        self.copyright_label = QLabel(copyright_line)
        self.copyright_label.setObjectName("fxSplashCopyright")
        layout.addWidget(self.copyright_label)

    def set_progress(self, value: int, max_range: int = 100) -> None:
        """Show the progress bar at `value` out of `max_range`, drawn now."""
        self.progress_bar.setRange(0, max_range)
        self.progress_bar.setValue(value)
        self.progress_bar.show()
        self.repaint()

    def paintEvent(self, event) -> None:
        """Draw the image clipped to the rounded corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setClipPath(_rounded(self.rect(), self.corner_radius))
        painter.drawPixmap(self.rect(), self.pixmap())
        painter.end()

    def showEvent(self, event) -> None:
        """Fade in over a second, if asked to."""
        super().showEvent(event)
        if self._fade_in:
            self._fade = QPropertyAnimation(self, b"windowOpacity", self)
            self._fade.setDuration(1000)
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
