"""A summary row pinned under an item view's rows, lined up with its columns."""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from typing import Dict, Optional, Sequence

# Third-party
from qtpy.QtCore import QEvent, QMetaObject, QObject, Qt, Slot
from qtpy.QtGui import QColor, QPainter, QPaintEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableView,
    QTreeView,
    QWidget,
)

# Internal
from fxgui import fxstyle, fxutils
from fxgui._compat import is_valid
from fxgui.fxwidgets._labels import FXElidedLabel

# Text a step below the body, muted unless the consumer marks it strong.
fxstyle.register_widget_style(
    """
    FXSummaryRow QLabel {
        color: @text_muted;
        font-size: @font_size_small;
        background: transparent;
    }
    FXSummaryRow QLabel[strong="true"] {
        color: @text;
    }
    """
)


class FXSummaryRow(QWidget):
    """One row pinned at the bottom of a tree or table view: its totals.

    The row is not a model row: it sits in the view's bottom margin, so it
    stays put while the rows scroll, and is never selected or reached by
    the keyboard. Each cell lines up with its column through resizes,
    hidden and moved sections and horizontal scrolling. The consumer
    computes the totals and hands each cell its text.

    The row is as tall as a row at the `fxstyle.row_size` in force, on a
    band of the view's surface under a rule in the border colour. A cell
    takes its column's header alignment unless given its own.

    Args:
        view: The `QTreeView` or `QTableView` (or a subclass, such as
            `FXKeyboardTree`) to pin the row under. The row is its child.

    Raises:
        TypeError: If `view` has no horizontal header to line up with.

    Examples:
        >>> summary = FXSummaryRow(tree)
        >>> summary.set_texts(["9 shots", "5/63 tasks done", "300"])
        >>> summary.set_text(3, "0.1 d", Qt.AlignRight, strong=True)
    """

    def __init__(self, view: QAbstractItemView):
        if isinstance(view, QTreeView):
            header = view.header()
        elif isinstance(view, QTableView):
            header = view.horizontalHeader()
        else:
            raise TypeError(
                f"FXSummaryRow needs a QTreeView or a QTableView, "
                f"not {type(view).__name__}"
            )
        super().__init__(view)
        self._view = view
        self._header: QHeaderView = header
        self._texts: Dict[int, str] = {}
        self._alignments: Dict[int, Qt.AlignmentFlag] = {}
        self._strong: Dict[int, bool] = {}
        self._labels: Dict[int, FXElidedLabel] = {}

        self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName("Summary")
        self.setAccessibleDescription(
            "Totals of the rows shown, one per column; not a data row"
        )

        for signal in (
            header.sectionResized,
            header.sectionMoved,
            header.sectionCountChanged,
            header.geometriesChanged,
        ):
            signal.connect(self._header_changed)
        view.horizontalScrollBar().valueChanged.connect(self._lay_out)
        # The view resets its viewport margins on every geometry update:
        # each one resizes the viewport, where the bottom margin goes back.
        view.viewport().installEventFilter(self)
        fxstyle.theme_changed.connect(self._fit)
        # Just above the viewport: the frame's round corners, which the
        # theme draws over the view's children, stay above the row.
        self.lower()
        view.viewport().lower()
        # A child made after its parent shows stays hidden until shown.
        self.show()

    ###### Public API

    def view(self) -> QAbstractItemView:
        """Return the view the row is pinned under."""
        return self._view

    def set_text(
        self,
        column: int,
        text: str,
        alignment: Optional[Qt.AlignmentFlag] = None,
        strong: bool = False,
    ) -> None:
        """Show `text` in a column's cell.

        Args:
            column: The column's logical index, as the model numbers it.
            text: The cell's text. Long text is cut with an ellipsis and
                shown whole in the cell's tooltip.
            alignment: The text's horizontal alignment. None takes the
                header's (the model's `headerData` `TextAlignmentRole`),
                else the left.
            strong: Draw the text in the body colour instead of muted.
        """
        self._texts[column] = text
        self._strong[column] = strong
        if alignment is None:
            self._alignments.pop(column, None)
        else:
            self._alignments[column] = alignment
        self._lay_out()

    def set_texts(self, texts: Sequence[str]) -> None:
        """Replace every cell's text, the first for column 0, and so on.

        Alignments and strong marks set before are dropped.
        """
        self.clear()
        for column, text in enumerate(texts):
            self._texts[column] = text
        self._lay_out()

    def text(self, column: int) -> str:
        """Return a column's text, empty when none was set."""
        return self._texts.get(column, "")

    def clear(self) -> None:
        """Empty every cell."""
        self._texts.clear()
        self._alignments.clear()
        self._strong.clear()
        for label in self._labels.values():
            label.hide()  # Gone now, not at the next event loop turn.
            label.deleteLater()
        self._labels.clear()

    def cell(self, column: int) -> Optional[FXElidedLabel]:
        """Return the label drawing a column's cell, None if it has no text."""
        return self._labels.get(column)

    def setVisible(self, visible: bool) -> None:
        """Show or hide the row, giving its room back to the rows."""
        super().setVisible(visible)
        self._fit()

    ###### Qt overrides

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Keep the bottom margin and the row under the viewport."""
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            self._fit()
        return False

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the band and its top rule, in the theme in force."""
        theme = fxstyle.colors()
        painter = QPainter(self)
        painter.fillRect(
            self.rect(), QColor(fxstyle.depth_shade(theme.surface, 1)))
        painter.fillRect(0, 0, self.width(), 1, QColor(theme.border))

    ###### Private

    @Slot()
    def _fit(self) -> None:
        """Reserve the row's height under the viewport and sit in it."""
        if not self._alive():
            return
        view = self._view
        height = 0 if self.isHidden() else fxstyle.row_height()
        margins = view.viewportMargins()
        if margins.bottom() != height:
            # Protected in C++; PySide reaches it on a view made in Python.
            view.setViewportMargins(
                margins.left(), margins.top(), margins.right(), height)
        viewport = view.viewport().geometry()
        self.setGeometry(
            viewport.x(), viewport.bottom() + 1, viewport.width(), height)
        self._lay_out()

    @Slot()
    def _header_changed(self) -> None:
        """Lay the cells out now, and again once the header has settled."""
        self._lay_out()
        # A stretched last section signals its new size before it stores it.
        QMetaObject.invokeMethod(self, "_lay_out", Qt.QueuedConnection)

    @Slot()
    def _lay_out(self) -> None:
        """Put each cell over its column, as the header places it now."""
        if not self._alive():
            return
        header = self._header
        lead = int(fxstyle.colors().cell_lead.rstrip("px"))
        for column in list(self._labels):
            if column not in self._texts:
                self._labels.pop(column).deleteLater()
        for column, text in self._texts.items():
            label = self._labels.get(column)
            if label is None:
                label = FXElidedLabel(parent=self)
                label.setFocusPolicy(Qt.NoFocus)
                self._labels[column] = label
            if label.text() != text:
                label.setText(text)
                label.setAccessibleName(text)
            label.setAlignment(self._alignment(column))
            strong = self._strong.get(column, False)
            if label.property("strong") != strong:
                label.setProperty("strong", strong)
                fxutils.repolish(label)
            if column >= header.count() or header.isSectionHidden(column):
                label.hide()
                continue
            left = header.sectionViewportPosition(column)
            width = header.sectionSize(column)
            label.setGeometry(
                left + lead, 1, max(0, width - 2 * lead), self.height() - 1)
            label.show()

    def _alive(self) -> bool:
        """Return whether the view and its header are not being torn down."""
        # The header and viewport still signal while the view is destroyed.
        return is_valid(self._view) and is_valid(self._header)

    def _alignment(self, column: int) -> Qt.AlignmentFlag:
        """Return a cell's alignment: its own, else its header's, else left."""
        alignment = self._alignments.get(column)
        if alignment is None:
            # The header's model is the view's, and the header outlives it.
            model = self._header.model()
            alignment = (
                model.headerData(column, Qt.Horizontal, Qt.TextAlignmentRole)
                if model is not None
                else None
            )
        if alignment is None:
            alignment = Qt.AlignLeft
        elif isinstance(alignment, int):
            alignment = Qt.AlignmentFlag(alignment)
        return (alignment & Qt.AlignHorizontal_Mask) | Qt.AlignVCenter
