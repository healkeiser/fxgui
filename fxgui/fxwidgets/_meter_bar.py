"""A quiet meter: one fill, or several shares side by side."""

# Built-in
from typing import Iterable, List, NamedTuple, Optional, Union

# Third-party
from qtpy.QtCore import QRectF, QSize
from qtpy.QtGui import QColor, QPainter, QPainterPath
from qtpy.QtWidgets import QSizePolicy, QWidget

# Internal
from fxgui import fxstyle

# The bar's thickness: 6 px, 4 px compact (in a tooltip or a dense cell).
_HEIGHT = 6
_COMPACT_HEIGHT = 4
# A faint share is work under way, not done.
_FAINT = 0.4


class FXMeterShare(NamedTuple):
    """One share of a meter.

    Attributes:
        value: How much it is worth.
        color: A theme token name (such as "feedback_success_foreground")
            or any colour QColor reads. Defaults to the accent.
        faint: Draw it at 40 %: work under way rather than done.
    """

    value: float
    color: str = "accent_primary"
    faint: bool = False


class FXMeterBar(QWidget):
    """A meter as the web look's: a quiet track, rounded ends, and one fill
    or several coloured shares side by side (a status split).

    The track is the text at 8 % over the pane (`@meter_track`); colours
    are read when it paints, so a theme switch needs no call.

    Args:
        shares: The shares, in the order they fill the bar: numbers (the
            accent) or `FXMeterShare`.
        maximum: What a full bar is worth; the shares' sum when 0. A bar
            past it stops full.
        compact: 4 px instead of 6 px, for a tooltip or a dense cell.
        parent: Parent widget.

    Examples:
        >>> bar = FXMeterBar([FXMeterShare(5, "feedback_success_foreground"),
        ...                   FXMeterShare(3, "feedback_warning_foreground")],
        ...                  maximum=63)
    """

    def __init__(
        self,
        shares: Iterable[Union[float, FXMeterShare]] = (),
        maximum: float = 0,
        compact: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._shares: List[FXMeterShare] = []
        self._maximum = maximum
        self._height = _COMPACT_HEIGHT if compact else _HEIGHT
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(self._height)
        self.set_shares(shares, maximum)

    def set_shares(
        self,
        shares: Iterable[Union[float, FXMeterShare]],
        maximum: Optional[float] = None,
    ) -> None:
        """Show `shares`; `maximum` as in the constructor, kept if None."""
        self._shares = [
            share if isinstance(share, FXMeterShare) else FXMeterShare(share)
            for share in shares
        ]
        if maximum is not None:
            self._maximum = maximum
        total = sum(max(share.value, 0) for share in self._shares)
        whole = self._maximum or total
        self.setAccessibleName("Meter")
        self.setAccessibleDescription(
            f"{total:g} of {whole:g}" if whole else "Empty")
        self.update()

    def shares(self) -> List[FXMeterShare]:
        """Return the shares shown."""
        return list(self._shares)

    def fractions(self) -> List[float]:
        """Return each share's part of the bar's width, 0 to 1."""
        total = sum(max(share.value, 0) for share in self._shares)
        whole = self._maximum or total
        if whole <= 0:
            return [0.0 for _ in self._shares]
        left, parts = 1.0, []
        for share in self._shares:
            part = min(max(share.value, 0) / whole, left)
            parts.append(part)
            left -= part
        return parts

    def sizeHint(self) -> QSize:
        return QSize(120, self._height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        radius = rect.height() / 2
        track = QPainterPath()
        track.addRoundedRect(rect, radius, radius)
        painter.setClipPath(track)
        tokens = fxstyle._token_map(fxstyle.get_theme())
        painter.fillRect(rect, QColor(tokens["@meter_track"]))
        theme = fxstyle.colors()
        x = rect.left()
        fractions = self.fractions()
        for share, fraction in zip(self._shares, fractions):
            width = rect.width() * fraction
            if width <= 0:
                continue
            color = QColor(getattr(theme, share.color, None) or share.color)
            if share.faint:
                color.setAlphaF(color.alphaF() * _FAINT)
            part = QRectF(x, rect.top(), width, rect.height())
            if len(self._shares) == 1:
                # One fill rounds its own end, as the track does.
                path = QPainterPath()
                path.addRoundedRect(part, radius, radius)
                painter.fillPath(path, color)
            else:
                painter.fillRect(part, color)
            x += width
        painter.end()

