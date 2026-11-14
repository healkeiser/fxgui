"""What a pane shows in place of content it does not have yet.

`FXEmptyState` says what to do next: an icon, the action in bold, then what
it brings, muted, centred as one block. `FXScrollShadow` marks where a
scroll area cuts its content off, so the content reads as going on below.
"""

# Built-in
from typing import Optional, Tuple

# Third-party
from qtpy.QtCore import QEvent, QObject, Qt
from qtpy.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent
from qtpy.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

# Internal
from fxgui import fxicons, fxstyle
from fxgui.fxwidgets._labels import FXIconLabel

# The prompt's icon, in pixels.
_ICON_PIXELS = 40

# The cut shadow's height, in pixels.
_SHADOW_PIXELS = 10


class FXEmptyState(QWidget):
    """An icon, the action to take, and what doing it brings.

    The widgets stay public: `icon` (an `FXIconLabel`), `action` and
    `detail` (labels).

    Args:
        icon: The icon's name in the default icon library.
        action: What the user does next, e.g. "Pick a task".
        detail: What doing it brings; empty for no second line.
        parent: Parent widget.

    Examples:
        >>> empty = FXEmptyState("inbox", "Pick a task", "Its files show here")
        >>> empty.prompt()
        ('Pick a task', 'Its files show here')
    """

    def __init__(
        self,
        icon: str,
        action: str,
        detail: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.icon = FXIconLabel(size=_ICON_PIXELS)
        self.action = QLabel()
        font = self.action.font()
        font.setBold(True)
        self.action.setFont(font)
        fxstyle.ink(self.action, "text")
        self.detail = QLabel()
        fxstyle.ink(self.detail, "text_muted")
        stack = QVBoxLayout(self)
        stack.setSpacing(fxstyle.PANE_GAP)
        stack.setContentsMargins(*(fxstyle.PANE_GAP,) * 4)
        stack.addStretch(1)
        stack.addWidget(self.icon)
        for label in (self.action, self.detail):
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignCenter)
            stack.addWidget(label)
        stack.addStretch(1)
        self.set_prompt(icon, action, detail)

    def set_prompt(self, icon: str, action: str, detail: str = "") -> None:
        """Say something else: another icon, action and detail.

        Args:
            icon: The icon's name in the default icon library.
            action: What the user does next.
            detail: What doing it brings; empty hides the second line.
        """
        # A disabled pane still reads its ask.
        fxicons.set_icon(
            self.icon,
            icon,
            color="text_muted",
            inks={"disabled": "text_muted"},
        )
        self.action.setText(action)
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))

    def prompt(self) -> Tuple[str, str]:
        """Return the action and the detail shown."""
        return self.action.text(), self.detail.text()


class FXScrollShadow(QWidget):
    """A line and a shadow where a scroll area cuts its content off below.

    It hides once the area is scrolled to the end, or has nothing to
    scroll. The colours are the theme's ``shadow`` and ``border``, read
    each time it paints.

    Args:
        area: The scroll area; the shadow is its child.

    Examples:
        >>> shadow = FXScrollShadow(area)
    """

    def __init__(self, area: QScrollArea):
        super().__init__(area)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._area = area
        bar = area.verticalScrollBar()
        bar.rangeChanged.connect(self._refresh)
        bar.valueChanged.connect(self._refresh)
        # The area's own resize arrives before it lays out its viewport.
        area.viewport().installEventFilter(self)
        self._refresh()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Follow the viewport's resizes."""
        if event.type() == QEvent.Resize:
            self._refresh()
        return False

    def _refresh(self) -> None:
        view = self._area.viewport().geometry()
        self.setGeometry(
            view.left(),
            view.bottom() + 1 - _SHADOW_PIXELS,
            view.width(),
            _SHADOW_PIXELS,
        )
        bar = self._area.verticalScrollBar()
        self.setVisible(bar.value() < bar.maximum())

    def paintEvent(self, event: QPaintEvent) -> None:
        """Fade the theme's shadow down onto a border-coloured line."""
        colors = fxstyle.colors()
        shade = QColor(colors.shadow)
        # The theme's alpha suits a blurred halo; a flat fade needs twice it.
        shade.setAlpha(min(255, shade.alpha() * 2))
        clear = QColor(shade)
        clear.setAlpha(0)
        fade = QLinearGradient(0, 0, 0, self.height())
        fade.setColorAt(0, clear)
        fade.setColorAt(1, shade)
        painter = QPainter(self)
        painter.fillRect(self.rect(), fade)
        painter.fillRect(
            0, self.height() - 1, self.width(), 1, QColor(colors.border)
        )
        painter.end()
