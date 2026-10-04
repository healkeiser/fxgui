"""A sort-filter proxy that matches loosely and ranks by relevance.

Examples:
    >>> from fxgui.fxcore import FXSortFilterProxyModel
    >>> proxy = FXSortFilterProxyModel(ratio=0.6)
    >>> proxy.setSourceModel(my_model)
    >>> search_bar.textChanged.connect(proxy.set_filter_text)
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from difflib import SequenceMatcher
from typing import Any, Dict, Optional

# Third-party
from qtpy.QtCore import QModelIndex, QSortFilterProxyModel, Qt, Slot
from qtpy.QtGui import QBrush, QColor
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import fxstyle


# Public API
__all__ = [
    "FXSortFilterProxyModel",
]


def _text(index: QModelIndex) -> str:
    """Return an index's display data as lower-case text, whatever its type."""
    value = index.data(Qt.DisplayRole)
    return "" if value is None else str(value).lower()


def _score(matcher: SequenceMatcher, text: str) -> float:
    """Return how well `text` matches the matcher's filter, 0.0 to 1.0.

    A substring hit is a perfect match, so short filters rank what contains
    them first. Anything else scores its `quick_ratio`.
    """
    if matcher.b in text:
        return 1.0
    matcher.set_seq1(text)
    return matcher.quick_ratio()


class FXSortFilterProxyModel(QSortFilterProxyModel):
    """A proxy that keeps rows scoring at least `ratio` and ranks them.

    One score (see `score`) filters, sorts and colours the rows. With
    recursive filtering on, a parent stays while one of its children
    matches.

    Examples:
        >>> model = QStringListModel(["apple", "banana", "cherry"])
        >>> proxy = FXSortFilterProxyModel()
        >>> proxy.setSourceModel(model)
        >>> view.setModel(proxy)
        >>> search_bar.textChanged.connect(proxy.set_filter_text)

    Notes:
        Base code from [Alex Telford](https://www.linkedin.com/in/mrminimaleffort):
        [LinkedIn post](https://www.linkedin.com/posts/mrminimaleffort_td-python-qt-activity-7270383661680603136-nvzb?utm_source=share&utm_medium=member_desktop)
    """

    def __init__(
        self,
        ratio: float = 0.5,
        color_match: bool = True,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the proxy.

        Args:
            ratio: The lowest score a row may have and stay.
            color_match: Whether a row's text is coloured by its score.
            parent: The parent object.
        """
        super().__init__(parent)
        self._ratio = ratio
        self._color_match = color_match
        # The filter text lives in seq2, which SequenceMatcher analyses once.
        self._matcher = SequenceMatcher(b="")
        self._scores: Dict[str, float] = {}
        self.sort(0, Qt.AscendingOrder)

    @Slot(str)
    def set_filter_text(self, text: str) -> None:
        """Filter and rank the rows by `text`."""
        self._matcher.set_seq2(text.lower())
        self._scores.clear()
        self.invalidate()

    def ratio(self) -> float:
        """Return the lowest score a row may have and stay."""
        return self._ratio

    @Slot(float)
    def set_ratio(self, ratio: float) -> None:
        """Set the lowest score a row may have and stay."""
        self._ratio = ratio
        self.invalidate()

    def score(self, text: str) -> float:
        """Return how well `text` matches the filter, cached per filter."""
        text = text.lower()
        found = self._scores.get(text)
        if found is None:
            found = self._scores[text] = _score(self._matcher, text)
        return found

    def _active(self) -> bool:
        return bool(self._matcher.b) and self._ratio > 0.0

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        """Keep a row whose score reaches the ratio."""
        if not self._active():
            return True
        text = _text(self.sourceModel().index(source_row, 0, source_parent))
        return bool(text) and self.score(text) >= self._ratio

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Rank the higher score first; ties keep the source order."""
        if self._active():
            left_score = self.score(_text(left))
            right_score = self.score(_text(right))
            if left_score != right_score:
                return left_score > right_score
        return left.row() < right.row()

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Colour a row's text by its score while a filter is set."""
        if role == Qt.ForegroundRole and self._color_match and self._active():
            score = self.score(_text(self.mapToSource(index)))
            return QBrush(self._match_color(score))
        return super().data(index, role)

    @staticmethod
    def _match_color(ratio: float) -> QColor:
        """Blend from `text_disabled` (poor) to `accent_primary` (perfect).

        Not red to green, which red-green colourblind users cannot read
        and which says error and success rather than match quality.
        """
        theme = fxstyle.colors()
        return QColor(fxstyle.mix(
            theme.text_disabled, theme.accent_primary,
            max(0.0, min(1.0, ratio))))
