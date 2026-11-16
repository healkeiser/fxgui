"""A carded view's footer: a row of actions inside its card, under its rows."""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Third-party
from qtpy.QtCore import QEvent, QObject, QRect, Qt, Slot
from qtpy.QtWidgets import QAbstractScrollArea, QFrame, QLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui._compat import is_valid
from fxgui.fxwidgets._summary_row import FOOTER_PROPERTY, FXSummaryRow

# The card's own surface, a rule on top. By its name: a view's own rules
# for the frames inside it outrank a class alone.
fxstyle.register_widget_style(
    """
    QFrame#fxViewFooter {
        background-color: @surface_sunken;
        border: none;
        border-top: 1px solid @border;
        border-radius: 0px;
    }
    """
)


class FXViewFooter(QFrame):
    """A row of actions at the foot of a tree's or table's card.

    It sits in the view's bottom margin, under the rows and any
    `FXSummaryRow`, so the card's edge and round corners frame it with
    them, as the web look's table footers. The scroll bars scroll the rows
    and the summary, so they end above it: the horizontal one runs right
    under the summary, the vertical one beside the rows and summary, and
    the footer spans the card under both. Hidden, it gives its room back.

    Args:
        view: The tree or table view, a `QAbstractScrollArea`.
        actions: The layout of its buttons; the footer takes it and sets
            its margins, so the buttons' ends line up with the cells' text.

    Examples:
        >>> actions = QHBoxLayout()
        >>> actions.addWidget(add_button)
        >>> actions.addWidget(remove_button)
        >>> actions.addStretch()
        >>> footer = FXViewFooter(table, actions)
    """

    def __init__(self, view: QAbstractScrollArea, actions: QLayout):
        super().__init__(view)
        self.setObjectName("fxViewFooter")
        self._view = view
        lead = int(fxstyle.colors().cell_lead.rstrip("px"))
        gap = fxstyle.PANE_GAP
        actions.setContentsMargins(lead, gap, lead, gap)
        self.setLayout(actions)
        # The view resets its viewport margins on every geometry update,
        # and puts its scroll bars back wherever it lays itself out.
        view.viewport().installEventFilter(self)
        # Held for the footer's life: PySide 6.5 marks a scroll bar's own
        # wrapper deleted once a passing wrapper of its container is freed.
        self._boxes = (
            view.horizontalScrollBar().parentWidget(),
            view.verticalScrollBar().parentWidget(),
        )
        for box in self._boxes:
            box.installEventFilter(self)
        fxstyle.theme_changed.connect(self._fit)
        # Under the frame's round corners, which the theme draws on top.
        self.lower()
        view.viewport().lower()
        self.show()

    def event(self, event: QEvent) -> bool:
        """Refit when the actions ask for another height, or it shows."""
        handled = super().event(event)
        if event.type() in (QEvent.LayoutRequest, QEvent.Show, QEvent.Hide):
            self._fit()
        return handled

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Keep the bottom margin, the scroll bars and the footer in place."""
        if event.type() in (
            QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Hide
        ):
            self._fit()
        return False

    @Slot()
    def _fit(self) -> None:
        """Reserve the footer's height under any summary row and sit in it."""
        view = self._view
        if not is_valid(view):
            return
        height = 0 if self.isHidden() else self.sizeHint().height()
        view.setProperty(FOOTER_PROPERTY, height)
        summary = view.findChild(FXSummaryRow, "", Qt.FindDirectChildrenOnly)
        above = 0 if summary is None or summary.isHidden() else (
            summary.height())
        margins = view.viewportMargins()
        if margins.bottom() != above + height:
            view.setViewportMargins(
                margins.left(), margins.top(), margins.right(), above + height)
        if not height:
            return
        viewport = view.viewport().geometry()
        under = viewport.bottom() + 1 + above
        # Rows, summary, then the horizontal bar; the footer last, at the
        # card's foot across its whole width.
        horizontal, vertical = self._boxes
        if horizontal is not view and horizontal.isVisible():
            _place(horizontal, horizontal.x(), under,
                   horizontal.width(), horizontal.height())
            under += horizontal.height()
        if vertical is not view and vertical.isVisible():
            _place(vertical, vertical.x(), vertical.y(), vertical.width(),
                   viewport.bottom() + 1 + above - vertical.y())
        frame = view.frameWidth()
        _place(self, frame, under, view.width() - 2 * frame, height)


def _place(widget: QWidget, x: int, y: int, width: int, height: int) -> None:
    """Set `widget`'s geometry when it differs: each set re-enters `_fit`."""
    if widget.geometry() != QRect(x, y, width, height):
        widget.setGeometry(x, y, width, height)
