"""Tree widget items with natural sorting."""

# Built-in
import re

# Third-party
from qtpy.QtWidgets import QTreeWidgetItem


# Pre-compiled regex for natural sorting (module-level for reuse)
_NATURAL_SORT_PATTERN = re.compile(r"([0-9]+)")


class FXSortedTreeWidgetItem(QTreeWidgetItem):
    """Custom `QTreeWidgetItem` that provides natural sorting for strings
    containing numbers. This is useful for sorting items like version numbers
    or other strings where numeric parts should be ordered numerically.

    For example, this class will sort the following strings in the correct
    human-friendly order:

    - "something1"
    - "something9"
    - "something17"
    - "something25"

    Instead of the default sorting order:

    - "something1"
    - "something17"
    - "something25"
    - "something9"
    """

    def __lt__(self, other: "FXSortedTreeWidgetItem") -> bool:
        """Override the less-than operator to provide a custom sorting logic.

        Args:
            other: Another instance of `FXSortedTreeWidgetItem` to compare with.

        Returns:
            `True` if the current item is less than the other item according to
            the natural sort order, `False` otherwise.
        """
        # Get the index of the column currently being used for sorting
        column = self.treeWidget().sortColumn()

        # Compare the items using the custom natural sort key
        return self._generate_natural_sort_key(
            self.text(column)
        ) < self._generate_natural_sort_key(other.text(column))

    @staticmethod
    def _generate_natural_sort_key(s: str) -> list:
        """Generate a sort key for natural sorting of strings containing
        numbers in a human-friendly way.

        Args:
            s: The string to sort.

        Returns:
            A list of elements where numeric parts are converted to integers
            and other parts are converted to lowercase strings.
        """
        # Use pre-compiled regex for better performance
        return [
            int(text) if text.isdigit() else text.lower()
            for text in _NATURAL_SORT_PATTERN.split(s)
        ]


def example() -> None:
    import sys
    from qtpy.QtWidgets import QVBoxLayout, QWidget, QTreeWidget
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXSortedTreeWidgetItem Demo")

    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Value"])
    tree.setSortingEnabled(True)

    # Add items with numbers that need natural sorting
    items = [
        "Version 1",
        "Version 9",
        "Version 10",
        "Version 2",
        "Version 20",
        "Version 11",
    ]

    for item_text in items:
        item = FXSortedTreeWidgetItem([item_text, "Some value"])
        tree.addTopLevelItem(item)

    layout.addWidget(tree)

    window.resize(400, 300)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
