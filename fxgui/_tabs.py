"""Segmented tab bars and tab counts, behind `fxstyle.mark_as_segmented`
and `fxstyle.set_tab_count`.

The looks are in ``qss/style.qss``, next to the tab rules; this module
paints what a stylesheet cannot: the track, and the chip that slides to
the picked tab.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
import re
from typing import Optional, Union

# Third-party
from qtpy.QtCore import (
    QEvent, QObject, QRect, QRectF, QSize, Qt, QVariantAnimation)
from qtpy.QtGui import QColor, QPainter, QPen
from qtpy.QtWidgets import (
    QApplication, QLabel, QStyle, QStyleOptionTab, QTabBar, QTabWidget, QWidget)

# Internal
from fxgui import fxstyle, fxutils

# The dynamic property a segmented bar carries, matched in style.qss.
SEGMENTED_PROPERTY = "fxSegmented"
# A count badge's object name, matched in style.qss.
COUNT_NAME = "fxTabCount"

# The track's padding round the chips, in px: the tabs' margins in
# style.qss, which put the chips this far inside the track.
_TRACK_PAD = 4
# How much of the shadow token's alpha the chip's 1 px drop takes: the
# web look's `0 1px 2px` at 5 %.
_CHIP_SHADOW = 0.25


def tab_bar(tabs: Union[QTabBar, QTabWidget]) -> QTabBar:
    """Return the bar of `tabs`, a tab bar or a tab widget."""
    return tabs.tabBar() if isinstance(tabs, QTabWidget) else tabs


class _Segmented(QObject):
    """Paint a segmented bar's track and its picked tab's chip.

    Painted under the tabs, which the stylesheet leaves unfilled. The
    chip rides `fxstyle.ease_spring` to a newly picked tab over
    `fxstyle.MOTION_SPRING`; caught mid-way, it turns from where it is.
    Under reduced motion it jumps.
    """

    def __init__(self, bar: QTabBar):
        super().__init__(bar)
        self._bar = bar
        # The chip as last painted, where a slide starts from.
        self._shown: Optional[QRectF] = None
        self._start: Optional[QRectF] = None
        self._slide = QVariantAnimation(self)
        self._slide.setStartValue(0.0)
        self._slide.setEndValue(1.0)
        self._slide.setDuration(fxstyle.MOTION_SPRING)
        self._slide.setEasingCurve(fxstyle.ease_spring())
        self._slide.valueChanged.connect(self._repaint)
        bar.currentChanged.connect(self._picked)
        bar.installEventFilter(self)

    def _repaint(self, _value=None) -> None:
        self._bar.update()

    def _picked(self, _index: int) -> None:
        bar = self._bar
        if (
            not bar.property(SEGMENTED_PROPERTY)
            or not fxstyle.motion()
            or not bar.isVisible()
            or self._shown is None
        ):
            self._slide.stop()
            self._start = None
            bar.update()
            return
        self._start = QRectF(self._shown)
        self._slide.stop()
        self._slide.start()

    def chip(self, index: int) -> QRectF:
        """Return where tab `index`'s chip rests: inside the track's pad."""
        bar = self._bar
        rect = QRectF(bar.tabRect(index))
        last = bar.count() - 1
        return rect.adjusted(
            _TRACK_PAD if index == 0 else 0,
            _TRACK_PAD,
            -_TRACK_PAD if index == last else 0,
            -_TRACK_PAD,
        )

    def _chip_now(self) -> Optional[QRectF]:
        bar = self._bar
        index = bar.currentIndex()
        if index < 0:
            return None
        rest = self.chip(index)
        if self._start is None or self._slide.state() != QVariantAnimation.Running:
            return rest
        step = float(self._slide.currentValue())
        start = self._start
        return QRectF(
            start.x() + (rest.x() - start.x()) * step,
            start.y() + (rest.y() - start.y()) * step,
            start.width() + (rest.width() - start.width()) * step,
            start.height() + (rest.height() - start.height()) * step,
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Paint the track and chip before the bar draws its tabs."""
        if (
            event.type() == QEvent.Paint
            and watched is self._bar
            and watched.property(SEGMENTED_PROPERTY)
            and watched.count()
        ):
            self._paint()
        return False

    def _paint(self) -> None:
        bar = self._bar
        theme = fxstyle.colors()
        track = QRectF(bar.tabRect(0)).united(
            QRectF(bar.tabRect(bar.count() - 1)))
        painter = QPainter(bar)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.state_pressed))
        radius = fxstyle.CARD_RADIUS
        painter.drawRoundedRect(track, radius, radius)
        chip = self._chip_now()
        self._shown = chip
        if chip is not None:
            radius = fxstyle.BUTTON_RADIUS
            shadow = QColor(theme.shadow)
            shadow.setAlphaF(shadow.alphaF() * _CHIP_SHADOW)
            painter.setBrush(shadow)
            painter.drawRoundedRect(chip.translated(0, 1), radius, radius)
            # The ring's 1 px centred on a half pixel, inside the chip.
            painter.setPen(QPen(QColor(theme.border), 1))
            painter.setBrush(QColor(theme.surface))
            painter.drawRoundedRect(
                chip.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)
        painter.end()


def mark_as_segmented(
    tabs: Union[QTabBar, QTabWidget], is_segmented: bool = True
) -> None:
    """Implement `fxstyle.mark_as_segmented`."""
    bar = tab_bar(tabs)
    bar.setProperty(SEGMENTED_PROPERTY, bool(is_segmented))
    if bar.findChild(_Segmented, "", Qt.FindDirectChildrenOnly) is None:
        _Segmented(bar)
    fxutils.repolish(bar)
    bar.update()


def _count_side(bar: QTabBar) -> QTabBar.ButtonPosition:
    """Return the side a count stands on: after the label, unless a close
    button takes that side."""
    close = QTabBar.ButtonPosition(
        bar.style().styleHint(QStyle.SH_TabBar_CloseButtonPosition, None, bar))
    if bar.tabsClosable() and close == QTabBar.RightSide:
        # shortcut: a closable bar's count stands before the label; a
        # count after it needs the close button drawn by hand.
        return QTabBar.LeftSide
    return QTabBar.RightSide


class _Count(QLabel):
    """A tab's count badge: a child of the bar, set where its room says."""

    def __init__(self, room: "_CountRoom"):
        super().__init__(room.parentWidget())
        self.room = room
        self.setObjectName(COUNT_NAME)
        self.setAlignment(Qt.AlignCenter)
        # A click on the badge picks its tab.
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def event(self, event: QEvent) -> bool:
        """Have the room fit a style or font change."""
        handled = super().event(event)
        if event.type() in (QEvent.StyleChange, QEvent.FontChange):
            self.room.fit()
        return handled


class _CountRoom(QWidget):
    """The room Qt lays out for a count, as a tab button; it draws nothing.

    Qt sets a tab's button off the tab's edge, not its padding, by a gap
    that differs between Qt versions, and centres the label in what is
    left: the badge would stand 7 to 16 px off the label. So the badge is
    a child of its own, placed 4 px after the label rect the style gives
    the tab, which ends where the room starts less Qt's 4 px.
    """

    def __init__(self, bar: QTabBar):
        super().__init__(bar)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.badge = _Count(self)
        self.destroyed.connect(self.badge.deleteLater)

    def event(self, event: QEvent) -> bool:
        """Move the badge whenever Qt moves, sizes, shows or hides the room."""
        handled = super().event(event)
        if event.type() in (
            QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.Hide
        ):
            self.place()
        return handled

    def fit(self) -> None:
        """Take the badge's size; have the bar lay its tabs out again."""
        badge = self.badge
        badge.ensurePolished()
        hint = badge.sizeHint()
        badge.resize(hint)
        if self.size() != hint:
            self.resize(hint)
            QApplication.sendEvent(self.parentWidget(), QEvent(QEvent.StyleChange))
        self.place()

    def place(self) -> None:
        """Set the badge 4 px after its tab's label, or where Qt set the room."""
        bar = self.parentWidget()
        badge = self.badge
        badge.setVisible(not self.isHidden())
        index = next(
            (i for i in range(bar.count())
             if bar.tabButton(i, QTabBar.RightSide) is self), -1)
        x = self.x()
        if index >= 0:
            x = _label_rect(bar, index, self.size()).right() + 1 + _COUNT_GAP
        badge.move(x, self.y())
        badge.raise_()


# Between a tab's label and its count, in px.
_COUNT_GAP = 4


def _label_rect(bar: QTabBar, index: int, room: QSize) -> QRect:
    """Return the rect the bar's style gives tab `index`'s label."""
    probe = QStyleOptionTab()
    probe.initFrom(bar)
    probe.rect = bar.tabRect(index)
    probe.text = bar.tabText(index)
    probe.icon = bar.tabIcon(index)
    probe.iconSize = bar.iconSize()
    probe.shape = bar.shape()
    probe.rightButtonSize = room
    left = bar.tabButton(index, QTabBar.LeftSide)
    if left is not None:
        probe.leftButtonSize = left.size()
    last = bar.count() - 1
    where = QStyleOptionTab.TabPosition
    probe.position = (
        where.OnlyOneTab if last == 0
        else where.Beginning if index == 0
        else where.End if index == last
        else where.Middle)
    if index == bar.currentIndex():
        probe.state |= QStyle.State_Selected
    # shortcut: the label rect is the label's own width only at the tab's
    # hint width; an expanding bar's wider tabs centre it, short of here.
    return bar.style().subElementRect(QStyle.SE_TabBarTabText, probe, bar)


def _count_room(bar: QTabBar, index: int):
    """Return the side and room of tab `index`'s count, or (None, None)."""
    for side in (QTabBar.RightSide, QTabBar.LeftSide):
        button = bar.tabButton(index, side)
        if isinstance(button, _CountRoom):
            return side, button
    return None, None


def set_tab_count(
    tabs: Union[QTabBar, QTabWidget], index: int, count: Optional[int]
) -> None:
    """Implement `fxstyle.set_tab_count`."""
    bar = tab_bar(tabs)
    if not 0 <= index < bar.count():
        raise IndexError(f"No tab {index}: the bar has {bar.count()}.")
    side, room = _count_room(bar, index)
    if count is None:
        if room is not None:
            bar.setTabButton(index, side, None)
            room.deleteLater()
        bar.setAccessibleTabName(index, "")
        return
    if room is None:
        room = _CountRoom(bar)
        bar.setTabButton(index, _count_side(bar), room)
    room.badge.setText(str(count))
    # Read as "Label, N": the text without its mnemonic's "&", then the count.
    label = re.sub(r"&(.)", r"\1", bar.tabText(index))
    bar.setAccessibleTabName(index, f"{label}, {count}")
    room.fit()
