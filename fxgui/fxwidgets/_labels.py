"""Custom label widgets."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QSize, Qt
from qtpy.QtGui import QFontMetrics, QIcon, QPainter, QPixmap
from qtpy.QtWidgets import QFormLayout, QLabel, QStyle, QToolTip, QWidget


class FXElidedLabel(QLabel):
    """A QLabel that cuts its text with an ellipsis when it does not fit.

    On one line the text is cut where `mode` says. With `wordWrap()` on
    and a maximum height set, it is cut from the right at the last line
    that fits; `mode` has no meaning across wrapped lines.

    Args:
        text: The label's text.
        parent: Parent widget.
        mode: Where one line is cut. `Qt.ElideMiddle` keeps apart strings
            that share a tail, such as paths under one root.

    Examples:
        >>> label = FXElidedLabel("a very long identity", mode=Qt.ElideMiddle)
    """

    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        mode: Qt.TextElideMode = Qt.ElideRight,
    ):
        super().__init__(text, parent)
        self._full_text = text
        self._mode = mode

    def minimumSizeHint(self) -> QSize:
        """Return no width and one line's height, so the label can shrink."""
        # QLabel's own minimum width is its whole text: it would never elide.
        return QSize(0, super().minimumSizeHint().height())

    def mode(self) -> Qt.TextElideMode:
        """Return where one line is cut when it does not fit."""
        return self._mode

    def set_mode(self, mode: Qt.TextElideMode) -> None:
        """Cut one line where `mode` says from now on."""
        self._mode = mode
        self._elide_text()

    def setText(self, text: str) -> None:
        """Set the text and store the full text for elision."""
        self._full_text = text
        super().setText(text)
        self._elide_text()

    def text(self) -> str:
        """Return the whole text that was set, not the shortened one."""
        return self._full_text

    def elided_text(self) -> str:
        """Return the text as painted, shortened to fit the label."""
        return super().text()

    def event(self, event: QEvent) -> bool:
        """Show the whole text as the tip of a cut label with no tip set."""
        if (
            event.type() == QEvent.ToolTip
            and not self.toolTip()
            and super().text() != self._full_text
        ):
            QToolTip.showText(event.globalPos(), self._full_text, self)
            return True
        return super().event(event)

    def sizeHint(self) -> QSize:
        """Ask for the room the whole text needs, on one line."""
        hint = super().sizeHint()
        if self.wordWrap():
            return hint
        metrics = QFontMetrics(self.font())
        extra = metrics.horizontalAdvance(self._full_text) - (
            metrics.horizontalAdvance(super().text())
        )
        return QSize(hint.width() + max(0, extra), hint.height())

    def resizeEvent(self, event) -> None:
        """Re-elide text when the label is resized."""
        super().resizeEvent(event)
        self._elide_text()

    def changeEvent(self, event: QEvent) -> None:
        """Re-elide text in a new font."""
        super().changeEvent(event)
        if event.type() == QEvent.FontChange:
            self._elide_text()

    def _elide_text(self) -> None:
        """Elide the text to fit within the label's width."""
        if not self._full_text:
            return

        metrics = QFontMetrics(self.font())
        available_width = self.width() - 2  # Small margin

        if self.wordWrap():
            # 16777215 is QWIDGETSIZE_MAX: no maximum, so nothing to cut to.
            if self.maximumHeight() >= 16777215:
                super().setText(self._full_text)
                return
            line_height = max(1, metrics.lineSpacing())
            max_lines = max(1, self.maximumHeight() // line_height)

            # Simple approach: truncate text if it would exceed max lines
            words = self._full_text.split()
            current_text = ""
            line_count = 1
            current_line_width = 0

            for word in words:
                word_width = metrics.horizontalAdvance(word + " ")
                if current_line_width + word_width > available_width:
                    line_count += 1
                    current_line_width = word_width
                    if line_count > max_lines:
                        current_text = current_text.rstrip() + "..."
                        break
                else:
                    current_line_width += word_width
                current_text += word + " "
            else:
                current_text = self._full_text

            super().setText(current_text.rstrip())
        else:
            # Single line elision
            elided = metrics.elidedText(
                self._full_text, self._mode, available_width
            )
            super().setText(elided)


class FXIconLabel(QLabel):
    """A label that draws a QIcon when painted, so it takes theme inks then.

    A QLabel pixmap is baked once; an fxicons icon here follows every
    theme switch with no signal. Disabled draws the icon's Disabled mode.

    Examples:
        >>> label = FXIconLabel(size=18)
        >>> fxicons.set_icon(label, "info", color="feedback_info_foreground")
    """

    def __init__(
        self,
        icon: Optional[QIcon] = None,
        parent: Optional[QWidget] = None,
        size: int = 16,
    ):
        super().__init__(parent)
        self._icon = QIcon() if icon is None else QIcon(icon)
        self._icon_size = QSize(size, size)
        self.setAlignment(Qt.AlignCenter)

    def icon(self) -> QIcon:
        """Return the icon drawn."""
        return QIcon(self._icon)

    def setIcon(self, icon: Optional[QIcon]) -> None:
        """Draw `icon`, or nothing for `None` or a null icon."""
        self._icon = QIcon() if icon is None else QIcon(icon)
        self.updateGeometry()
        self.update()

    def pixmap(self) -> QPixmap:
        """Return the icon as drawn now, or the plain pixmap without one."""
        if self._icon.isNull():
            return super().pixmap()
        mode = QIcon.Normal if self.isEnabled() else QIcon.Disabled
        return self._icon.pixmap(self._icon_size, mode)

    def iconSize(self) -> QSize:
        """Return the size the icon is drawn at."""
        return QSize(self._icon_size)

    def setIconSize(self, size: QSize) -> None:
        """Draw the icon at `size`."""
        self._icon_size = QSize(size)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        """Return the icon size plus the margins."""
        margins = self.contentsMargins()
        return self._icon_size.grownBy(margins)

    def minimumSizeHint(self) -> QSize:
        """Return the size hint: the icon is not drawn smaller."""
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        """Draw the icon in the mode the enabled state asks for."""
        if self._icon.isNull():
            return
        mode = QIcon.Normal if self.isEnabled() else QIcon.Disabled
        rect = QStyle.alignedRect(
            self.layoutDirection(), self.alignment(), self._icon_size,
            self.contentsRect(),
        )
        painter = QPainter(self)
        self._icon.paint(painter, rect, Qt.AlignCenter, mode)
        painter.end()


def fix_wrapped_heights(widget: QWidget) -> None:
    """Give every word-wrapped label under `widget` the height its width needs.

    Qt loses a label's height-for-width a few layouts deep and clips its
    last lines. Call after the labels have their width, and again from the
    holder's `resizeEvent`.
    """
    for label in widget.findChildren(QLabel):
        if label.wordWrap():
            label.setFixedHeight(label.heightForWidth(label.width()))


def align_labels(*forms: QFormLayout) -> None:
    """Give the labels of every form in `forms` one right-aligned column.

    Qt shares no label column across form layouts.
    """
    labels = []
    for form in forms:
        for row in range(form.rowCount()):
            item = form.itemAt(row, QFormLayout.LabelRole)
            if item is not None and isinstance(item.widget(), QLabel):
                labels.append(item.widget())
    if not labels:
        return
    widest = max(label.sizeHint().width() for label in labels)
    for label in labels:
        label.setFixedWidth(widest)
        # `setLabelAlignment` places the label, not its text.
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
