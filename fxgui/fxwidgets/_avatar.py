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
        self._face = None
        self.update()

    def set_size(self, size: int) -> None:
        """Resize the circle to `size` logical pixels across."""
        self._size = size
        self._face = None
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
        """Return the photo scaled to cover the circle at `ratio`."""
        side = round(self._size * ratio)
        face = self._face
        if face is None or face.width() != side:
            face = self._pixmap.scaled(
                side,
                side,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            face.setDevicePixelRatio(ratio)
            self._face = face
        return face

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
            logical = face.deviceIndependentSize()
            painter.drawPixmap(
                QRectF(
                    (self._size - logical.width()) / 2,
                    (self._size - logical.height()) / 2,
                    logical.width(),
                    logical.height(),
                ),
                face,
                QRectF(face.rect()),
            )
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
            glyph = fxicons.get_pixmap("person", side, side, color=ink)
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


def example() -> None:
    import sys
    from qtpy.QtWidgets import QHBoxLayout
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXAvatar Demo")
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QHBoxLayout(widget)
    for name in ("Anne Martin", "Madonna", "Bob Stone", ""):
        layout.addWidget(FXAvatar(name, widget, size=40))
    layout.addStretch()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
