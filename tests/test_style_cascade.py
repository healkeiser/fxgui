"""Spike/guard tests: the Qt mechanics the pull-model theming relies on.

1. An ancestor setStyleSheet delivers QEvent.StyleChange to descendants.
2. A custom-painted descendant repaints after an ancestor restyle.
3. A QSS class selector matches a Python subclass name, and a plain
   QWidget subclass paints a QSS background when WA_StyledBackground
   is set.
4. Repolishing a deep tree is fast enough for switch-time use.
"""

import time

from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget


class _PaintTracker(QWidget):
    """Custom-painted child that counts paints and StyleChange events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paint_count = 0
        self.style_change_count = 0
        self.setMinimumSize(40, 40)

    def paintEvent(self, event):
        self.paint_count += 1
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ff0000"))
        painter.end()

    def changeEvent(self, event):
        if event.type() == QEvent.StyleChange:
            self.style_change_count += 1
        super().changeEvent(event)


class _StyledBox(QWidget):
    """Plain QWidget subclass targeted by a QSS class selector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Required for QSS backgrounds from an ANCESTOR sheet: a plain
        # QWidget subclass ignores them otherwise. setStyleSheet directly
        # on a widget enables this implicitly, ancestor sheets do not.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumSize(40, 40)


def _build_tree(depth_widget_cls):
    """Root > container > tracked child, so the cascade crosses a level."""
    root = QWidget()
    layout = QVBoxLayout(root)
    container = QWidget(root)
    layout.addWidget(container)
    inner = QVBoxLayout(container)
    child = depth_widget_cls(container)
    inner.addWidget(child)
    return root, child


def test_ancestor_restyle_delivers_stylechange(qtbot):
    root, child = _build_tree(_PaintTracker)
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)

    child.style_change_count = 0
    root.setStyleSheet("QWidget { background-color: #0000ff; }")
    qtbot.wait(50)

    assert child.style_change_count >= 1


def test_ancestor_restyle_repaints_custom_painted_child(qtbot):
    root, child = _build_tree(_PaintTracker)
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)
    qtbot.wait(50)

    before = child.paint_count
    root.setStyleSheet("QWidget { background-color: #00ff00; }")

    qtbot.waitUntil(lambda: child.paint_count > before, timeout=2000)


def test_qss_class_selector_matches_python_subclass(qtbot):
    root, child = _build_tree(_StyledBox)
    qtbot.addWidget(root)
    root.setStyleSheet("_StyledBox { background-color: #ff00ff; }")
    root.show()
    qtbot.waitExposed(root)

    image = child.grab().toImage()
    assert image.pixelColor(child.rect().center()) == QColor("#ff00ff")


def test_qss_class_selector_matches_qt_subclass(qtbot):
    """Same check for a QLabel subclass (no WA_StyledBackground needed)."""

    class _FancyLabel(QLabel):
        pass

    root = QWidget()
    layout = QVBoxLayout(root)
    label = _FancyLabel("x")
    label.setMinimumSize(40, 40)
    layout.addWidget(label)
    qtbot.addWidget(root)
    root.setStyleSheet("_FancyLabel { background-color: #00ffff; }")
    root.show()
    qtbot.waitExposed(root)

    image = label.grab().toImage()
    assert image.pixelColor(label.rect().center()) == QColor("#00ffff")


def test_repolish_cost_on_deep_tree(qtbot):
    """Measure switch-time repolish on ~300 widgets. Generous bound: the
    point is a recorded number, not a race."""
    root = QWidget()
    layout = QVBoxLayout(root)
    parent = root
    for _ in range(10):  # 10 levels deep
        box = QWidget(parent)
        (parent.layout() or QVBoxLayout(parent)).addWidget(box)
        QVBoxLayout(box)
        for _ in range(30):  # 30 labels per level
            box.layout().addWidget(QLabel("x", box))
        parent = box
    qtbot.addWidget(root)
    root.show()
    qtbot.waitExposed(root)

    start = time.perf_counter()
    root.setStyleSheet("QLabel { color: #123456; }")
    qtbot.wait(10)
    elapsed = time.perf_counter() - start

    print(f"\nrepolish of ~300-widget tree took {elapsed * 1000:.1f} ms")
    assert elapsed < 2.0
