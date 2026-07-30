"""Paint-path tests for FXTooltip.

Regression: the arrow polygon was built with ``QPolygonF.append(QPoint(...))``.
PySide and PyQt5 silently convert QPoint to QPointF there, PyQt6 raises
TypeError, so every tooltip paint crashed under PyQt6. Nothing caught it
because the widget had no tests and a tooltip only paints once shown.
"""

# Third-party
import pytest
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import FXTooltip, FXTooltipPosition


@pytest.mark.parametrize(
    "position",
    [
        FXTooltipPosition.TOP,
        FXTooltipPosition.BOTTOM,
        FXTooltipPosition.LEFT,
        FXTooltipPosition.RIGHT,
    ],
)
def test_tooltip_paints_arrow_for_every_position(qtbot, position):
    """Painting must not raise for any arrow direction, on any binding."""
    anchor = QWidget()
    anchor.resize(200, 100)

    # FXTooltip is a frameless top-level that keeps a reference to its
    # anchor and runs its own timers. Registering it with qtbot lets the
    # anchor outlive it non-deterministically, which crashes the Qt event
    # loop during teardown, so tear it down explicitly here instead.
    tooltip = FXTooltip(
        parent=anchor, title="Probe", description="probe tooltip"
    )
    try:
        tooltip._arrow_position = position
        tooltip._arrow_offset = 20
        tooltip.resize(160, 60)

        # grab() drives a real paintEvent synchronously.
        image = tooltip.grab().toImage()

        assert not image.isNull()
        assert image.width() > 0 and image.height() > 0
    finally:
        tooltip.hide()
        tooltip.setParent(None)
        tooltip.deleteLater()
        anchor.deleteLater()


def test_tooltip_arrow_polygon_accepts_float_points(qtbot):
    """Pin the exact API pairing that broke: QPolygonF takes QPointF."""
    from qtpy.QtCore import QPointF
    from qtpy.QtGui import QPolygonF

    polygon = QPolygonF()
    polygon.append(QPointF(1.0, 2.0))

    assert polygon.count() == 1
