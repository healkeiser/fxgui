"""A loading placeholder: the shape of a list or a pane, greyed."""

# Built-in
import math
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QObject, QRect, QRectF, QSize, Qt, QVariantAnimation
from qtpy.QtGui import QColor, QLinearGradient, QPainter
from qtpy.QtWidgets import QAbstractScrollArea, QWidget

# Internal
from fxgui import _compat, fxstyle
from fxgui.fxutils import later

# The layouts a skeleton draws.
_KINDS = ("rows", "cards", "lines")
# How far the blocks' grey and the sweep's light stand from the ground: the
# text at 5 % over it, as the web kit's elevated fill.
_GREY = 0.05
_LIGHT_ALPHA = 0.05
# One light sweeping across every 1.6 s.
_SWEEP_MS = 1600
# A row's side inset, the gap between its blocks, its thumbnail slot.
_ROW_INSET = 16
_GAP = 12
_THUMBNAIL = (44, 24)
# A card: its padding, height and the width a column needs.
_CARD_PAD = 16
_CARD_HEIGHT = 120
_CARD_COLUMN = 640
# A line of text: a bar and the pitch between bars.
_LINE_BAR = 12
_LINE_PITCH = 20


def _width(seed: int, low: float, high: float) -> float:
    """Return a width between `low` and `high`, the same for every paint."""
    return round(low + ((seed * 37) % 17) / 16 * (high - low))


def _fade(index: int) -> float:
    """Return a block's opacity: fading toward the bottom, not a wall."""
    return max(0.25, 1 - index * 0.06)


class FXSkeleton(QWidget):
    """Grey blocks in the shape of what is loading, a light sweeping across.

    Shown while a list or a pane waits for its data, instead of an empty
    page or a spinner. `kind` picks the shape: ``"rows"`` (a list row's
    height, a thumbnail slot and text bars), ``"cards"`` (a grid of cards)
    or ``"lines"`` (a paragraph). The light sweeps across every 1.6 s while
    the skeleton shows; under reduced motion it stays still. Screen readers
    hear "Loading".

    Args:
        parent: Parent widget.
        kind: ``"rows"``, ``"cards"`` or ``"lines"``.
        count: How many rows, cards or lines. None fills the height.
        thumbnail: Whether a row has a thumbnail slot.

    Raises:
        ValueError: If `kind` is not one of the three.

    Examples:
        >>> skeleton = FXSkeleton(kind="cards", count=6)
        >>> FXSkeleton.cover(tree)  # While the rows load.
        >>> FXSkeleton.uncover(tree)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        kind: str = "rows",
        count: Optional[int] = None,
        thumbnail: bool = True,
    ):
        super().__init__(parent)
        if kind not in _KINDS:
            raise ValueError(f"kind must be one of {_KINDS}, not {kind!r}")
        self._kind = kind
        self._count = count
        self._thumbnail = thumbnail
        # Set by cover(): the skeleton fills the ground of what it covers.
        self._covering = False
        self._sweep = 0.0
        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(_SWEEP_MS)
        self._animation.setEasingCurve(fxstyle.ease_out())
        self._animation.setLoopCount(-1)
        self._animation.valueChanged.connect(self._swept)
        self.setAccessibleName("Loading")
        self.setFocusPolicy(Qt.NoFocus)

    @property
    def kind(self) -> str:
        """The layout drawn: ``"rows"``, ``"cards"`` or ``"lines"``."""
        return self._kind

    @classmethod
    def cover(
        cls,
        view: QWidget,
        kind: str = "rows",
        count: Optional[int] = None,
        thumbnail: bool = True,
    ) -> "FXSkeleton":
        """Cover `view` with a skeleton until `uncover`; return the skeleton.

        A scroll area (a list, a tree, a table) is covered inside its frame,
        so its header stays. The skeleton follows the view's resizes. A view
        already covered keeps its skeleton.

        Args:
            view: The widget waiting for its data.
            kind: ``"rows"``, ``"cards"`` or ``"lines"``.
            count: How many rows, cards or lines. None fills the height.
            thumbnail: Whether a row has a thumbnail slot.

        Returns:
            The skeleton over `view`.
        """
        target = _target(view)
        found = _covering(target)
        if found is not None:
            return found
        skeleton = cls(target, kind, count, thumbnail)
        skeleton._covering = True
        # A view's viewport is made by Qt, which keeps it past Python.
        _compat.hold(skeleton)
        target.installEventFilter(skeleton)
        skeleton.setGeometry(target.rect())
        skeleton.show()
        skeleton.raise_()
        return skeleton

    @staticmethod
    def uncover(view: QWidget) -> None:
        """Remove the skeleton `cover` put over `view`, if any."""
        skeleton = _covering(_target(view))
        if skeleton is not None:
            # Not found again before Qt deletes it: cover() makes a new one.
            skeleton._covering = False
            skeleton.hide()
            skeleton.deleteLater()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Cover the view again when it resizes, or gains a child."""
        if watched is self.parent():
            if event.type() == QEvent.Resize:
                self.setGeometry(watched.rect())
            elif event.type() == QEvent.ChildAdded and self._covering:
                # A child made later (an index widget) stacks over the cover.
                later(0, self, self._rise)
        return super().eventFilter(watched, event)

    def _rise(self) -> None:
        """Go over the view's children, under its loading line."""
        from fxgui.fxwidgets._top_progress import FXTopProgress

        parent = self.parentWidget()
        if not self._covering or parent is None:
            return
        self.raise_()
        for line in parent.findChildren(
            FXTopProgress, "", Qt.FindDirectChildrenOnly
        ):
            if line.isVisible():
                line.raise_()

    def showEvent(self, event) -> None:
        """Start the sweep, unless motion is reduced."""
        super().showEvent(event)
        if fxstyle.motion():
            self._animation.start()

    def hideEvent(self, event) -> None:
        """Stop the sweep while nobody sees it."""
        self._animation.stop()
        self._sweep = 0.0
        super().hideEvent(event)

    def _swept(self, value) -> None:
        self._sweep = float(value)
        self.update()

    def _ground(self) -> QColor:
        """Return the colour the skeleton is drawn on: what it covers, or
        the page."""
        if self._covering:
            # The colour the person sees there: a plain widget's palette is
            # see-through where the sheet paints its pane, card or dialog.
            return fxstyle._ground(self.parentWidget())
        return QColor(fxstyle.colors().surface)

    def paintEvent(self, event) -> None:
        """Paint the blocks, then the sweeping light over them."""
        colors = fxstyle.colors()
        ground = self._ground()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._covering:
            painter.fillRect(self.rect(), ground)
        # The blocks stand where the covered content stood: inside its
        # contents margins (a pane's gap), the whole rect over a viewport.
        box = self._box()
        self._extent = box.size()
        painter.save()
        painter.translate(box.topLeft())
        grey = QColor(fxstyle.mix_oklab(ground, colors.text_strong, _GREY))
        painter.setPen(Qt.NoPen)
        painter.setBrush(grey)
        if self._kind == "rows":
            self._paint_rows(painter)
        elif self._kind == "cards":
            self._paint_cards(painter, QColor(colors.border))
        else:
            self._paint_lines(painter)
        painter.restore()
        painter.setOpacity(1.0)
        if self._animation.state() == QVariantAnimation.Running:
            self._paint_light(painter, QColor(colors.text_strong))
        painter.end()

    # The blocks' layout size, set by each paint; the widget's own before.
    _extent = QSize()

    def _box(self) -> QRect:
        """Return the rect the blocks are laid out in."""
        owner = self.parentWidget() if self._covering else None
        if owner is None:
            return self.rect()
        margins = owner.contentsMargins()
        return self.rect().adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom())

    def _how_many(self, pitch: float) -> int:
        if self._count is not None:
            return self._count
        height = self._extent.height() if self._extent.isValid() else self.height()
        return max(1, math.ceil(height / pitch))

    def _paint_rows(self, painter: QPainter) -> None:
        height = fxstyle.row_height()
        right = self._extent.width() - _ROW_INSET
        for index in range(1, self._how_many(height) + 1):
            painter.setOpacity(_fade(index))
            middle = (index - 1) * height + height / 2
            x = _ROW_INSET
            if self._thumbnail:
                width, tall = _THUMBNAIL
                painter.drawRoundedRect(
                    QRectF(x, middle - tall / 2, width, tall), 4, 4)
                x += width + _GAP
            bars = [_width(index, 70, 140)]
            bars += [_width(index + column, 40, 110) for column in range(1, 5)]
            for width in bars:
                # Whole bars only: a sliver at the edge reads as a glitch.
                if x + width > right:
                    break
                painter.drawRoundedRect(QRectF(x, middle - 6, width, 12), 6, 6)
                x += width + _GAP

    def _paint_cards(self, painter: QPainter, edge: QColor) -> None:
        columns = max(1, min(3, self._extent.width() // _CARD_COLUMN + 1))
        width = (self._extent.width() - _CARD_PAD * 2 - _GAP * (columns - 1)) / columns
        rows = max(1, math.ceil(
            (self._extent.height() - _CARD_PAD) / (_CARD_HEIGHT + _GAP)))
        count = self._count if self._count is not None else rows * columns
        grey = painter.brush()
        for index in range(1, count + 1):
            painter.setOpacity(_fade(index))
            row, column = divmod(index - 1, columns)
            card = QRectF(
                _CARD_PAD + column * (width + _GAP),
                _CARD_PAD + row * (_CARD_HEIGHT + _GAP),
                width,
                _CARD_HEIGHT,
            )
            painter.setPen(edge)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(grey)
            inner = card.adjusted(_CARD_PAD, _CARD_PAD, -_CARD_PAD, -_CARD_PAD)
            x, y = inner.left(), inner.top()
            painter.drawRoundedRect(QRectF(x, y, 24, 24), 4, 4)
            title = (inner.width() - 32) * _width(index, 30, 50) / 100
            painter.drawRoundedRect(QRectF(x + 32, y + 5, title, 14), 6, 6)
            y += 24 + _GAP
            painter.drawRoundedRect(QRectF(x, y, inner.width(), 8), 4, 4)
            y += 8 + _GAP
            third = (inner.width() - 32) / 3
            for slot in range(3):
                painter.drawRoundedRect(
                    QRectF(x + slot * (third + 16), y, third, 32), 6, 6)

    def _paint_lines(self, painter: QPainter) -> None:
        for index in range(1, self._how_many(_LINE_PITCH) + 1):
            painter.setOpacity(_fade(index))
            width = self._extent.width() * _width(index, 60, 100) / 100
            top = (index - 1) * _LINE_PITCH + (_LINE_PITCH - _LINE_BAR) / 2
            painter.drawRoundedRect(QRectF(0, top, width, _LINE_BAR), 6, 6)

    def _paint_light(self, painter: QPainter, light: QColor) -> None:
        # One band the skeleton's width, from off its left to off its right.
        width = self.width()
        left = -width + self._sweep * 2 * width
        gradient = QLinearGradient(left, 0, left + width, 0)
        clear = QColor(light)
        clear.setAlphaF(0.0)
        light.setAlphaF(_LIGHT_ALPHA)
        gradient.setColorAt(0.0, clear)
        gradient.setColorAt(0.5, light)
        gradient.setColorAt(1.0, clear)
        painter.fillRect(self.rect(), gradient)


def _target(view: QWidget) -> QWidget:
    """Return what a skeleton covers: a scroll area's viewport, or `view`."""
    if isinstance(view, QAbstractScrollArea):
        return view.viewport()
    return view


def _covering(target: QWidget) -> Optional[FXSkeleton]:
    """Return the skeleton `cover` put over `target`, if any."""
    for child in target.children():
        if isinstance(child, FXSkeleton) and child._covering:
            return child
    return None
