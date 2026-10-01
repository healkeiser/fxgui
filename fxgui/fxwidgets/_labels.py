"""Custom label widgets."""

# Built-in
import warnings
from typing import Optional

# Third-party
from qtpy.QtCore import QEvent, QSize, Qt
from qtpy.QtGui import QFontMetrics, QIcon, QPainter, QPixmap
from qtpy.QtWidgets import QFormLayout, QLabel, QStyle, QToolTip, QWidget


class FXElidedLabel(QLabel):
    """A QLabel that elides text with '...' when it doesn't fit.

    This label automatically truncates text and adds an ellipsis when the
    text is too long to fit within the available space.

    Args:
        text: The label's text. Defaults to `""`.
        parent: Parent widget. Defaults to `None`.
        mode: Where the text is cut when it does not fit. Defaults to
            `Qt.ElideRight`. `Qt.ElideMiddle` is what tells apart
            strings that share a tail -- paths under a common root, or
            email-shaped identities at one domain, where two long values
            cut from the right come out looking identical.

            Governs the SINGLE-LINE case only. With `wordWrap()` on, the
            text is cut at the last line that fits and an ellipsis is
            appended there, whatever the mode -- because
            `QFontMetrics.elidedText` elides one line, and there is no
            one obvious meaning for "elide the middle" of a wrapped
            block (which line loses its middle?). Enabling word wrap on
            a label whose mode is not `ElideRight` warns, rather than
            quietly doing something else than it was asked.

    Examples:
        >>> from qtpy.QtCore import Qt
        >>> from fxgui import fxwidgets
        >>> label = fxwidgets.FXElidedLabel(
        ...     "a very long identity", mode=Qt.ElideMiddle
        ... )
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
        self._warned_about_mode = False

    def minimumSizeHint(self) -> QSize:
        """No width at all, and the height one line of this font needs.

        `QLabel`'s own minimum width IS the width of its whole text --
        measured, 696px for a 58-character string -- and a minimum is
        not a preference: a label that will not go below its own text
        width does not elide when the room runs out, it takes the room
        from whatever shares its row and, failing that, from the window.
        Measured: a 47-character string in a row with a button, in a
        window told to be 200px wide, forced the window to 680px and
        pushed the button from x=90 to x=570.

        Which makes an eliding label with `QLabel`'s minimum a widget
        that cannot do the one thing it exists for. This yields the
        width instead, which is what eliding means, and keeps the height
        so a row is still a row.

        Returns:
            QSize: Zero width, at `QLabel`'s own minimum height.
        """
        return QSize(0, super().minimumSizeHint().height())

    @property
    def mode(self) -> Qt.TextElideMode:
        """Where the text is cut when it does not fit."""
        return self._mode

    @mode.setter
    def mode(self, mode: Qt.TextElideMode) -> None:
        self._mode = mode
        self._warn_if_mode_is_moot()
        self._elide_text()

    def setWordWrap(self, wrap: bool) -> None:
        """Wrap the text, and say so if that makes `mode` moot.

        Args:
            wrap: Whether the label wraps rather than eliding on one
                line.
        """
        super().setWordWrap(wrap)
        self._warn_if_mode_is_moot()

    def _warn_if_mode_is_moot(self) -> None:
        """Warn once per label when word wrap has overruled `mode`.

        The combination is not an error -- the label still elides, from
        the right, at the last line that fits. It is worth a word because
        the alternative is a caller who asked for `ElideMiddle` getting
        `ElideRight` with nothing anywhere saying so.
        """
        if self._warned_about_mode:
            return
        if not self.wordWrap() or self._mode == Qt.ElideRight:
            return
        self._warned_about_mode = True
        warnings.warn(
            "FXElidedLabel: `mode` governs single-line elision only, and "
            "wordWrap() is on, so this label truncates from the right at "
            "the last line that fits. Turn word wrap off to elide at "
            f"{self._mode!r}.",
            RuntimeWarning,
            stacklevel=3,
        )

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

    def _elide_text(self) -> None:
        """Elide the text to fit within the label's width."""
        if not self._full_text:
            return

        metrics = QFontMetrics(self.font())
        available_width = self.width() - 2  # Small margin

        if self.wordWrap():
            # For word-wrapped labels, limit by line count. `_mode` does
            # not reach here: see the class docstring's `mode` entry.
            available_height = (
                self.maximumHeight()
                if self.maximumHeight() < 16777215
                else self.height()
            )
            line_height = metrics.lineSpacing()
            max_lines = (
                max(1, available_height // line_height)
                if line_height > 0
                else 5
            )

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


def example() -> None:
    import sys

    from qtpy.QtWidgets import (
        QGroupBox,
        QVBoxLayout,
        QWidget,
    )

    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app: FXApplication = FXApplication(sys.argv)

    # Main window
    window = FXMainWindow()
    window.setWindowTitle("Labels Example")
    window.resize(400, 200)
    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)

    # Elided label examples
    elided_group = QGroupBox("Elided Labels")
    elided_layout = QVBoxLayout(elided_group)

    # Short text (won't be elided)
    short_label = FXElidedLabel("1. Short text that fits")
    elided_layout.addWidget(short_label)

    # Long text (will be elided)
    long_text = (
        "2. This is a very long text that will be automatically truncated "
        "with an ellipsis when it doesn't fit within the available width "
        "of the label widget."
    )
    long_label = FXElidedLabel(long_text)
    long_label.setFixedWidth(250)
    elided_layout.addWidget(long_label)

    # Word-wrapped elided label
    wrapped_text = (
        "3. This is a very long text that will be automatically truncated "
        "with an ellipsis when it doesn't fit within the available width "
        "of the label widget."
    )
    wrapped_label = FXElidedLabel(wrapped_text)
    wrapped_label.setWordWrap(True)
    wrapped_label.setFixedWidth(200)
    wrapped_label.setMaximumHeight(50)
    elided_layout.addWidget(wrapped_label)

    layout.addWidget(elided_group)
    layout.addStretch()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
