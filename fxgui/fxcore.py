"""
Wrapper around the `QtCore` module for `fxgui`.

This module provides core functionality and custom classes to enhance the use
of `QtCore` within the `fxgui` framework.

Classes:
    FXSortFilterProxyModel: A filter model using fuzzy matching based on
        SequenceMatcher similarity ratios.

Examples:
    Using FXSortFilterProxyModel with a search bar:

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
from typing import Optional

# Third-party
from qtpy.QtCore import (
    QSortFilterProxyModel,
    Qt,
    QModelIndex,
    Slot,
)
from qtpy.QtGui import (
    QBrush,
    QColor,
)
from qtpy.QtWidgets import (
    QWidget,
)


# Public API
__all__ = [
    "FXSortFilterProxyModel",
]


class FXSortFilterProxyModel(QSortFilterProxyModel):
    """A filter model that uses `SequenceMatcher` to filter items based on
    a similarity ratio. The similarity ratio is a value between 0 and 1,
    where 1 indicates a perfect match.

    Examples:
        Filter a list of items using the `FXSortFilterProxyModel`
        >>> items = ["apple", "banana", "cherry", "date"]
        >>> search_bar = QLineEdit()
        >>> view = QListView()
        >>> model = QStringListModel()
        >>> model.setStringList(items)
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
        """Initialize the FXSortFilterProxyModel.

        Args:
            ratio: The ratio threshold for filtering.
            color_match: Whether to enable color matching.
            parent: The parent widget.
        """
        super().__init__(parent)
        self._filter_text = ""
        self._ratio = ratio
        self._color_match = color_match
        self._show_all = False
        # Per-instance matcher (a class-level one is shared mutable state
        # across every proxy). SequenceMatcher caches analysis of seq2, so
        # the filter text lives in seq2 and each row's text goes in seq1;
        # quick_ratio() is symmetric, so the value is unchanged.
        self._matcher = SequenceMatcher()
        self.sort(0, Qt.AscendingOrder)

    @Slot(str)
    def set_filter_text(self, text: str) -> None:
        """Set the filter text.

        Args:
            text: The filter text.
        """

        self._filter_text = text.lower()
        self._matcher.set_seq2(self._filter_text)
        self.invalidate()

    @Slot(float)
    def set_ratio(self, ratio: float) -> None:
        """Set the ratio threshold for filtering.

        Args:
            ratio: The ratio threshold.
        """

        self._ratio = ratio
        self.invalidate()

    @Slot(bool)
    def set_show_all(self, show_all: bool) -> None:
        """Set whether to show all items regardless of the filter.

        Args:
            show_all: Whether to show all items.
        """

        self._show_all = show_all
        self.invalidate()

    @Slot(bool)
    def set_color_match(self, color_match: bool) -> None:
        """Set whether to enable color matching.

        Args:
            color_match: Whether to enable color matching.
        """

        self._color_match = color_match
        self.invalidate()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        """Determine whether a row should be accepted by the filter.

        Args:
            source_row: The source row index.
            source_parent: The source parent index.

        Returns:
            bool: `True` if the row is accepted, `False` otherwise.
        """
        # Early exits for common cases
        if self._show_all or not self._filter_text or self._ratio <= 0.0:
            return True

        text = (
            self.sourceModel().index(source_row, 0, source_parent).data() or ""
        ).lower()
        if not text:
            return False

        # Substring match takes priority (handles short search strings well)
        if self._filter_text in text:
            return True

        # Fall back to fuzzy matching for typos and partial matches
        self._matcher.set_seq1(text)
        return self._matcher.quick_ratio() >= self._ratio

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Compare two indices to determine their order.

        Args:
            left: The left index.
            right: The right index.

        Returns:
            `True` if the left index is less than the right index,
            `False` otherwise.
        """
        if not self._filter_text or self._show_all:
            return left.row() < right.row()

        left_text = left.data().lower() if left.data() else ""
        right_text = right.data().lower() if right.data() else ""

        # Filter text stays cached in seq2; only seq1 changes per row
        self._matcher.set_seq1(left_text)
        left_ratio = self._matcher.quick_ratio()
        self._matcher.set_seq1(right_text)
        right_ratio = self._matcher.quick_ratio()

        return left_ratio > right_ratio

    def data(
        self, index: QModelIndex, role: int = Qt.DisplayRole
    ) -> Optional[QBrush]:
        """Get the data for a given role and index.

        Args:
            index: The model index.
            role: The role for which data is requested.

        Returns:
            The data for the given role and index.
        """
        if (
            role == Qt.ForegroundRole
            and self._filter_text
            and self._ratio > 0.0
            and self._color_match
        ):
            # Get text from source model to avoid recursion
            source_index = self.mapToSource(index)
            text = (
                self.sourceModel().data(source_index, Qt.DisplayRole) or ""
            ).lower()

            self._matcher.set_seq1(text)
            ratio = self._matcher.quick_ratio()

            # Poor matches fade toward the theme's disabled text color,
            # strong matches toward the accent. A red/green gradient is
            # invisible to red-green colorblind users and reads as
            # "error/success" rather than match quality.
            return QBrush(self._match_color(ratio))

        return super().data(index, role)

    @staticmethod
    def _match_color(ratio: float) -> QColor:
        """Interpolate between theme disabled-text and accent colors.

        Args:
            ratio: Match quality between 0.0 (poor) and 1.0 (perfect).

        Returns:
            The interpolated color.
        """
        # Imported here to avoid a circular import at module load
        from fxgui import fxstyle

        colors = fxstyle.get_theme_colors()
        poor = QColor(colors.get("text_disabled", "#777777"))
        good = QColor(colors.get("accent_primary", "#2196F3"))
        ratio = max(0.0, min(1.0, ratio))
        return QColor(
            int(poor.red() + (good.red() - poor.red()) * ratio),
            int(poor.green() + (good.green() - poor.green()) * ratio),
            int(poor.blue() + (good.blue() - poor.blue()) * ratio),
        )
