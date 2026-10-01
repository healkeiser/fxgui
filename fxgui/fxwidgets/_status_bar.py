"""Custom status bar widget, and the status items it holds."""

# Built-in
import logging
from datetime import datetime
from typing import List, Optional, Tuple

# Third-party
from qtpy.QtCore import QEvent, QRectF, QSize, Qt, QTimer, Slot
from qtpy.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
)
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStatusBar,
    QToolButton,
    QWidget,
)

# Internal
from fxgui import fxicons, fxstyle, fxutils
from fxgui.fxwidgets._labels import FXIconLabel
from fxgui.fxwidgets._severity import INFO, SEVERITIES, log, severity
from fxgui.fxwidgets._tips import apply_tip

# The painted lines replace the base sheet's top border.
fxstyle.register_widget_style(
    """
    FXStatusBar {
        border: none;
    }
    """
)

# A message's tint, by the `severity` property `showMessage` sets. The
# second selector outranks the frame's own fill of a bar on the frame.
fxstyle.register_widget_style(
    " ".join(
        f'FXStatusBar[severity="{key}"], '
        f'QMainWindow[fxFrame="true"] > FXStatusBar[severity="{key}"] '
        f"{{ background: @feedback_{key}_background; }} "
        f'FXStatusBar[severity="{key}"] QLabel '
        f"{{ color: @feedback_{key}_ink; }}"
        for key in sorted({kind.feedback for kind in SEVERITIES.values()})
    )
)

# Accent line height, then the border line under it.
STATUS_LINE_HEIGHT = 3

# The side of a status item's icon, the size of the bar's message icon.
ICON_SIZE = 14

# Between an item's icon and its word.
_ICON_GAP = 4

# Least contrast of a toned icon on the bar: WCAG's floor for graphics.
_ICON_CONTRAST = 3.0

# Between the window's left edge and the first item or message.
_LEFT_MARGIN = 6

# The busy line: a run a third of the bar wide, crossing it in about a
# second and a half at 30 frames a second.
_BUSY_SPAN = 1 / 3
_BUSY_FRAME_MS = 33
_BUSY_FRAMES = 45


class FXStatusItem(QToolButton):
    """An icon and a word on a status bar, flat, lit when it is clickable.

    Painted against the bar as the bar is painted at that moment, a
    message's tint included, so its ink always reads. Hidden while it has
    no text.

    Args:
        text: The word shown. Defaults to `""`.
        icon: An fxicons icon name. Defaults to `None`.
        parent: Parent widget. Defaults to `None`.
        clickable: Whether a click does something; otherwise plain text
            that takes no mouse. Defaults to `True`.

    Examples:
        >>> item = FXStatusItem("3", "warning")
        >>> window.statusBar().add_item(item)
        >>> item.clicked.connect(show_log)
    """

    radius = fxstyle.BUTTON_RADIUS

    def __init__(
        self,
        text: str = "",
        icon: Optional[str] = None,
        parent: Optional[QWidget] = None,
        clickable: bool = True,
    ):
        super().__init__(parent)
        self.icon_name = icon or ""
        self.muted = False
        self.clickable = clickable
        self._tone = ""
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.set_clickable(clickable)
        self.setText(text)

    def setText(self, text: str) -> None:
        """Show `text`; an item with none hides."""
        super().setText(text)
        self._sync_visible()
        self.updateGeometry()

    def show_state(
        self, text: str, icon: str, muted: bool = False, tone: str = ""
    ) -> None:
        """Show `text` beside `icon`, muted or in a feedback `tone`.

        Args:
            text: The word shown.
            icon: An fxicons icon name.
            muted: Whether the word takes the muted ink.
            tone: A feedback level ("error", "warning", ...) for the icon,
                or `""` for the word's ink.
        """
        self.icon_name, self.muted, self._tone = icon, muted, tone
        self.setText(text)
        self.update()

    def set_clickable(self, clickable: bool) -> None:
        """Make a click do something, or make the item plain text."""
        self.clickable = clickable
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not clickable)
        self.update()

    def set_tip(self, title: str, body: str = "", keys: str = "") -> None:
        """Say what the item is and what its click does."""
        apply_tip(self, title, body, keys)
        # Qt would write a status tip over the bar's own items.
        self.setStatusTip("")

    def ground(self) -> str:
        """Return the colour the item is drawn on now."""
        bar = self._bar()
        if bar is not None:
            return bar.ground()
        return self.palette().color(self.backgroundRole()).name()

    def ink(self) -> str:
        """Return the word's colour on the ground the item is drawn on now."""
        return self._ink(self.ground())

    def _bar(self) -> Optional["FXStatusBar"]:
        widget = self.parentWidget()
        while widget is not None and not isinstance(widget, FXStatusBar):
            widget = widget.parentWidget()
        return widget

    def _ink(self, ground: str) -> str:
        theme = fxstyle.colors()
        word = theme.text_muted if self.muted else theme.text
        return fxstyle.readable_ink(ground, word)

    def _icon_ink(self, ground: str, ink: str) -> str:
        bar = self._bar()
        # On a tint the feedback colour is the ground's own hue.
        if self.muted or not self._tone or (bar is not None and bar.tint()):
            return ink
        tone = getattr(fxstyle.colors(), f"feedback_{self._tone}_foreground")
        return fxstyle.readable_ink(ground, tone, _ICON_CONTRAST)

    def sizeHint(self) -> QSize:
        """Return the icon, the word and the side padding."""
        metrics = self.fontMetrics()
        width = 2 * self.radius + metrics.horizontalAdvance(self.text())
        if self.icon_name:
            width += self.iconSize().width() + _ICON_GAP
        height = max(self.iconSize().height(), metrics.height()) + 4
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        """Return `sizeHint`: an item is never squeezed."""
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        """Paint the hover fill, the icon and the word against the bar."""
        ground = self.ground()
        lit = self.clickable and self.isEnabled() and self.underMouse()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if lit:
            ground = fxstyle.colors().state_hover
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
            painter.fillPath(path, QColor(ground))
        ink = self._ink(ground)
        x = self.radius
        if self.icon_name:
            size = self.iconSize()
            top = (self.height() - size.height()) // 2
            icon = fxicons.get_icon(
                self.icon_name, color=self._icon_ink(ground, ink))
            icon.paint(painter, x, top, size.width(), size.height())
            x += size.width() + _ICON_GAP
        painter.setPen(QColor(ink))
        painter.drawText(
            self.rect().adjusted(x, 0, 0, 0),
            int(Qt.AlignLeft | Qt.AlignVCenter),
            self.text(),
        )
        painter.end()

    def _sync_visible(self) -> None:
        # Shown without a parent, an item would open as its own window; a
        # parent's layout shows one with text as it takes it in.
        if self.parentWidget() is not None or not self.text():
            self.setVisible(bool(self.text()))


class FXStatusBar(QStatusBar):
    """Customized QStatusBar class.

    The accent line and the border under it are painted along the top,
    except on the frame (`fxstyle.mark_as_frame`) or after
    `hide_status_line`. `add_item` puts `FXStatusItem`s on the left,
    before the message, which never hides them, or on the right, before
    the company. `set_busy(True)` runs a line along the same top band,
    framed or not, so waiting moves no layout.

    Args:
        parent: Parent widget. Defaults to `None`.
        project: The project item's text. Defaults to `None`, hidden.
        version: The version item's text. Defaults to `None`, hidden.
        company: The company item's text. Defaults to `None`, hidden.

    Attributes:
        icon_label (QLabel): The icon label.
        message_label (QLabel): The message label.
        project_label (FXStatusItem): The project, plain until
            `set_clickable(True)`.
        version_label (FXStatusItem): The version, likewise.
        company_label (FXStatusItem): The company, likewise.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        project: Optional[str] = None,
        version: Optional[str] = None,
        company: Optional[str] = None,
    ):

        super().__init__(parent)

        # Line state; `None` colours read the theme when painted.
        self._line_wanted = True
        self._line_colors: Optional[Tuple[str, str]] = None
        # The shown message's feedback key.
        self._severity: Optional[str] = None
        self._message = ""
        self._busy = False
        self._busy_frame = 0
        self._busy_timer = QTimer(self)
        self._busy_timer.setInterval(_BUSY_FRAME_MS)
        self._busy_timer.timeout.connect(self._step_busy)

        self.icon_label = FXIconLabel(size=ICON_SIZE)
        self.message_label = QLabel()
        self.message_label.setTextFormat(Qt.RichText)
        # A long message is cut at the bar's end, never widens the window.
        self.message_label.setMinimumWidth(1)

        # Permanent, so no message hides the items; the message follows.
        self._left = QWidget()
        self._left.setObjectName("fxStatusItems")
        self._left_row = QHBoxLayout(self._left)
        self._left_row.setContentsMargins(_LEFT_MARGIN, 0, 0, 0)
        self._left_row.setSpacing(0)
        for widget in (self.icon_label, self.message_label):
            self._left_row.addWidget(widget)
            widget.setVisible(False)  # Hide if no message is shown
        self._left_row.addStretch(1)
        self.addPermanentWidget(self._left, 1)

        self.project_label = FXStatusItem(project or "", clickable=False)
        self.version_label = FXStatusItem(version or "", clickable=False)
        self.company_label = FXStatusItem(company or "", clickable=False)
        for item in (self.project_label, self.version_label, self.company_label):
            self.addPermanentWidget(item)

        self.messageChanged.connect(self._on_status_message_changed)

    def add_item(self, item: FXStatusItem, side: str = "left") -> None:
        """Put `item` on the bar, after the items already on that side.

        Args:
            item: The item to add.
            side: "left", before the message, or "right", before the
                company.

        Raises:
            ValueError: `side` is neither "left" nor "right".
        """
        if side == "left":
            self._left_row.insertWidget(
                self._left_row.indexOf(self.icon_label), item)
        elif side == "right":
            # Taken off and put back last, the company stays at the end.
            self.removeWidget(self.company_label)
            self.addPermanentWidget(item)
            self.addPermanentWidget(self.company_label)
            self.company_label._sync_visible()
        else:
            raise ValueError(f"side is 'left' or 'right', not {side!r}")

    def items(self) -> List[FXStatusItem]:
        """Return every status item on the bar, shown or not."""
        return self.findChildren(FXStatusItem)

    def tint(self) -> Optional[str]:
        """Return the colour a message tints the bar now, or `None`."""
        if self._severity:
            return QColor(getattr(
                fxstyle.colors(), f"feedback_{self._severity}_background"
            )).name()
        return None

    def ground(self) -> str:
        """Return the colour the bar is painted now: a tint, or its own."""
        # The sheet's fill, tint and frame included, as the palette holds it.
        return self.palette().color(self.backgroundRole()).name()

    def show_tip(self, tip: str) -> None:
        """Write a hover tip where messages go, after the items.

        `FXMainWindow` routes Qt's status tips here; an empty tip gives a
        message still standing back.
        """
        label = self.message_label
        if tip:
            label.setText(tip)
            label.show()
            self.icon_label.hide()
        elif self.currentMessage():
            label.setText(self._message)
            label.show()
            self.icon_label.show()
        else:
            label.clear()
            label.hide()

    def showMessage(
        self,
        message: str,
        severity_type: int = INFO,
        duration: float = 2.5,
        time: bool = True,
        logger: Optional[logging.Logger] = None,
        set_color: bool = True,
    ):
        """Display a message in the status bar with a specified severity.

        Args:
            message (str): The message to be displayed.
            severity_type (int, optional): The severity level of the message.
                Should be one of `CRITICAL`, `ERROR`, `WARNING`, `SUCCESS`,
                `INFO`, or `DEBUG`. Defaults to `INFO`.
            duration (float, optional): The duration in seconds for which
                the message should be displayed. Defaults to` 2.5`.
            time (bool, optional): Whether to display the current time before
                the message. Defaults to `True`.
            logger (Logger, optional): A logger object to log the message.
                Defaults to `None`.
            set_color (bool): Whether to tint the bar in the severity's
                colors until the message goes. Defaults to `True`.

        Examples:
            To display a critical error message with a red background
            >>> self.showMessage(
            ...     "Critical error occurred!",
            ...     severity_type=fxwidgets.CRITICAL,
            ...     duration=5,
            ...     logger=my_logger,
            ... )

        Note:
            Overrides the base class method.
        """

        # Qt's own message only drives `messageChanged` and the timeout.
        super().showMessage(" ", timeout=int(duration * 1000))

        self.icon_label.setVisible(True)
        self.message_label.setVisible(True)

        kind = severity(severity_type)
        severity_prefix = kind.title
        severity_icon = fxicons.get_icon(
            kind.icon, color=f"feedback_{kind.feedback}_foreground")

        # Use inline style for bold as QSS can interfere with <b> tag rendering
        message_prefix = (
            f"<b>{severity_prefix}</b>: {datetime.now():%H:%M} - "
            if time
            else f"<b>{severity_prefix}</b>: "
        )
        self.icon_label.setIcon(severity_icon)
        self._message = f"{message_prefix} {message}"
        self.message_label.setText(self._message)

        if set_color:
            self._set_tint(kind.feedback)

        log(logger, severity_type, message)

    def clearMessage(self):
        """Clear the message and its tint.

        Note:
            Overrides the base class method.
        """
        super().clearMessage()
        self._clear()

    def _clear(self) -> None:
        """Hide the message labels and drop the tint.

        Warning:
            This method is intended for internal use only.
        """
        self.icon_label.setIcon(None)
        self.icon_label.setVisible(False)
        self.message_label.clear()
        self.message_label.setVisible(False)
        self._message = ""
        self._set_tint(None)

    def _set_tint(self, key: Optional[str]) -> None:
        """Tint the bar for feedback `key`, or untint it for `None`.

        The tint is a registered rule on the `severity` property, so a
        switch recolours it.
        """
        self._severity = key
        self.setProperty("severity", key)
        # A descendant rule is matched again only when the label is.
        for widget in [self, *self.findChildren(QLabel)]:
            fxutils.repolish(widget)
        self._repaint_items()

    def _repaint_items(self) -> None:
        """Repaint the bar and its items against the ground of the moment."""
        self.update()
        for item in self.items():
            item.update()

    @Slot(str)
    def _on_status_message_changed(self, message: str) -> None:
        """Clear the labels and tint when Qt's timeout empties the message."""
        if not message:
            self._clear()

    def set_status_line_colors(self, color_a: str, color_b: str) -> None:
        """Paint the accent line as a gradient from `color_a` to `color_b`."""
        self._line_colors = (color_a, color_b)
        self.update()

    def hide_status_line(self) -> None:
        """Hide the accent line and the border under it."""
        self._line_wanted = False
        self.update()

    def show_status_line(self) -> None:
        """Show the accent line and border, unless the bar is on the frame."""
        self._line_wanted = True
        self.update()

    def set_busy(self, busy: bool) -> None:
        """Run the busy line along the top edge, or stop it."""
        self._busy = bool(busy)
        self._busy_frame = 0
        self._run_busy_timer()
        self.update(0, 0, self.width(), STATUS_LINE_HEIGHT)

    def is_busy(self) -> bool:
        """Return whether the busy line runs."""
        return self._busy

    def _run_busy_timer(self) -> None:
        if self._busy and self.isVisible():
            self._busy_timer.start()
        else:
            self._busy_timer.stop()

    def _step_busy(self) -> None:
        self._busy_frame = (self._busy_frame + 1) % _BUSY_FRAMES
        self.update(0, 0, self.width(), STATUS_LINE_HEIGHT)

    def showEvent(self, event) -> None:
        """Run the busy line again, if it ran when the bar hid."""
        super().showEvent(event)
        self._run_busy_timer()

    def hideEvent(self, event) -> None:
        """Stop the busy line's timer while nobody can see it."""
        super().hideEvent(event)
        self._run_busy_timer()

    def paintEvent(self, event) -> None:
        """Paint the bar, then its accent line or busy line along the top."""
        super().paintEvent(event)
        if self._busy:
            self._paint_busy()
            return
        # On the frame the bar joins the chrome, so it draws no line on top.
        if not self._line_wanted or self.property(fxstyle.FRAME_PROPERTY):
            return
        theme = fxstyle.colors()
        start, end = self._line_colors or (
            theme.accent_primary,
            theme.accent_secondary,
        )
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(start))
        gradient.setColorAt(1, QColor(end))
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), STATUS_LINE_HEIGHT, gradient)
        painter.fillRect(
            0,
            STATUS_LINE_HEIGHT,
            self.width(),
            1,
            QColor(
                getattr(theme, f"feedback_{self._severity}_foreground")
                if self._severity
                else theme.border
            ),
        )
        painter.end()

    def _paint_busy(self) -> None:
        """Paint a flat accent run across the bar's top band, as a chunk."""
        span = int(self.width() * _BUSY_SPAN)
        # From fully off the left edge to fully off the right one.
        left = -span + (self.width() + span) * self._busy_frame // _BUSY_FRAMES
        painter = QPainter(self)
        painter.fillRect(
            0, 0, self.width(), STATUS_LINE_HEIGHT, QColor(self.ground()))
        painter.fillRect(
            left, 0, span, STATUS_LINE_HEIGHT,
            QColor(fxstyle.colors().accent_primary))
        painter.end()

    def event(self, event: QEvent) -> bool:
        """Repaint when `fxstyle.mark_as_frame` marks or unmarks the bar."""
        if (
            event.type() == QEvent.DynamicPropertyChange
            and bytes(event.propertyName()) == fxstyle.FRAME_PROPERTY.encode()
        ):
            self._repaint_items()
        return super().event(event)
