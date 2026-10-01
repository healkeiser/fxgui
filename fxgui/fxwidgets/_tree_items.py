"""Tree widget items that sort by a key, else naturally by text."""

# Built-in
import re

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QTreeWidgetItem


_NATURAL_SORT_PATTERN = re.compile(r"([0-9]+)")


class FXSortedTreeWidgetItem(QTreeWidgetItem):
    """A row that sorts by its `SORT_ROLE` key, else naturally by its text.

    Natural order puts "v9" before "v10". A key lives on its own role since
    Qt stores display and edit data together. Never `super().__lt__()`: it
    re-enters this override through Shiboken and recurses until segfault.
    """

    #: The per-column sort key, any type its column's keys compare with.
    #: Clear of `FXThumbnailDelegate`'s roles, below its `FIRST_FREE_ROLE`.
    SORT_ROLE = Qt.UserRole + 16

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        """Compare by the sort column's key, else by its natural text."""
        tree = self.treeWidget()
        column = tree.sortColumn() if tree is not None else 0
        mine = self.data(column, self.SORT_ROLE)
        theirs = other.data(column, self.SORT_ROLE)
        if mine is not None and theirs is not None:
            try:
                return bool(mine < theirs)
            except TypeError:
                pass
        return self._natural_key(self.text(column)) < self._natural_key(
            other.text(column)
        )

    @staticmethod
    def _natural_key(text: str) -> list:
        return [
            int(part) if part.isdigit() else part.lower()
            for part in _NATURAL_SORT_PATTERN.split(text)
        ]
