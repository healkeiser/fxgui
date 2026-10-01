"""Round avatar: a person's photo, or their initials on a coloured disc."""

# Built-in
import re
import zlib
from typing import Optional

# Third-party
from qtpy.QtCore import QRectF, QSize, Qt
from qtpy.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from qtpy.QtWidgets import QSizePolicy, QWidget

# Internal
from fxgui import fxicons, fxstyle


# Deep enough that white initials read at 4.5:1 on every one.
AVATAR_COLORS = (
    "#c2185b",
    "#bf360c",
    "#9e6a00",
    "#2e7d32",
    "#00796b",
    "#0277bd",
    "#3949ab",
    "#6a3fb5",
    "#8e24aa",
    "#546e7a",
)


def _initials(name: str) -> str:
    words = [word for word in re.split(r"[\s._-]+", name) if word]
    return "".join(word[0] for word in words[:2]).upper()


class FXAvatar(QWidget):
    """A circle showing a person's photo, or their initials on a disc.

    The disc colour comes from the name, so one person keeps one colour in
    every thread and across runs.

    Args:
        name: The person's name; its first two words give the initials.
        parent: Parent widget.
        size: The circle's diameter, in logical pixels.
        pixmap: A photo, cropped to the circle. Replaces the initials.

    Examples:
        >>> avatar = FXAvatar("Anne Martin", size=32)
        >>> avatar.set_pixmap(QPixmap("anne.png"))
    """

    def __init__(
        self,
        name: str = "",
        parent: Optional[QWidget] = None,
        *,
        size: int = 26,
        pixmap: Optional[QPixmap] = None,
    ):
        super().__init__(parent)
        self._name = ""
        self._size = size
        self._pixmap: Optional[QPixmap] = None
        self._face: Optional[QPixmap] = None
        self._face_key: tuple = ()
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(size, size)
        self.set_name(name)
        self.set_pixmap(pixmap)

    def name(self) -> str:
        """Return the person's name."""
        return self._name

    def initials(self) -> str:
        """Return the initials drawn on the disc, empty for no name."""
        return _initials(self._name)

    def color(self) -> QColor:
        """Return the disc colour the name picks."""
        # crc32, not hash(): hash() is salted per process.
        index = zlib.crc32(self._name.encode("utf-8")) % len(AVATAR_COLORS)
        return QColor(AVATAR_COLORS[index])

    def set_name(self, name: str) -> None:
        """Show `name`'s initials and colour, and use it as the tooltip."""
        self._name = name or ""
        self.setToolTip(self._name)
        self.update()

    def set_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        """Show `pixmap` cropped round, or the initials again for `None`."""
        self._pixmap = pixmap if pixmap and not pixmap.isNull() else None
        self.update()

    def set_size(self, size: int) -> None:
        """Resize the circle to `size` logical pixels across."""
        self._size = size
        self.setFixedSize(size, size)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        """Return the circle's size."""
        return QSize(self._size, self._size)

    def minimumSizeHint(self) -> QSize:
        """Return the circle's size."""
        return self.sizeHint()

    def _cropped_face(self, ratio: float) -> QPixmap:
        """Return the photo centre-cropped square, `size` across at `ratio`."""
        side = round(self._size * ratio)
        key = (self._pixmap.cacheKey(), side, ratio)
        # The key holds the photo, side and ratio, so any change misses.
        if self._face_key != key:
            source = self._pixmap
            edge = min(source.width(), source.height())
            square = source.copy(
                (source.width() - edge) // 2,
                (source.height() - edge) // 2,
                edge,
                edge,
            )
            face = square.scaled(
                side, side, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            face.setDevicePixelRatio(ratio)
            self._face, self._face_key = face, key
        return self._face

    def paintEvent(self, event) -> None:
        """Paint the photo or the initials disc."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        whole = QRectF(0, 0, self._size, self._size)
        if self._pixmap is not None:
            face = self._cropped_face(self.devicePixelRatioF())
            clip = QPainterPath()
            clip.addEllipse(whole)
            painter.setClipPath(clip)
            painter.drawPixmap(whole, face, QRectF(face.rect()))
            # Inset half its width, or the ring is cut at the edge.
            painter.setClipping(False)
            painter.setPen(QPen(QColor(255, 255, 255, 127), 1.0))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(whole.adjusted(0.5, 0.5, -0.5, -0.5))
            return

        disc = self.color()
        ink = fxstyle.get_contrast_text_color(disc.name())
        painter.setPen(Qt.NoPen)
        painter.setBrush(disc)
        painter.drawEllipse(whole)
        initials = self.initials()
        if not initials:
            side = round(self._size * 0.6)
            glyph = fxicons.get_pixmap(
                "person", side, side, color=ink,
                dpr=self.devicePixelRatioF())
            offset = (self._size - side) / 2
            painter.drawPixmap(QRectF(offset, offset, side, side), glyph,
                               QRectF(glyph.rect()))
            return
        font = QFont(self.font())
        font.setPixelSize(max(1, self._size * 2 // 5))
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(ink))
        painter.drawText(whole, Qt.AlignCenter, initials)
