"""A hovered tool button sits on the neutral hover fill, its icon readable."""

import pytest
from qtpy.QtCore import QPoint, QRect, QSize
from qtpy.QtWidgets import QToolButton, QVBoxLayout, QWidget

from fxgui import fxicons, fxstyle

from _helpers import hover, near


def _most(image) -> list[str]:
    counts: dict[str, int] = {}
    for x in range(image.width()):
        for y in range(image.height()):
            name = image.pixelColor(x, y).name().lower()
            counts[name] = counts.get(name, 0) + 1
    return sorted(counts, key=lambda n: -counts[n])


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_a_hovered_tool_button_shows_its_icon_on_the_hover_fill(
    qtbot, qapp, theme
):
    """Hover is a fill, never the accent, and the icon stands out on it."""
    fxstyle.apply_theme(theme)
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    button = QToolButton(window)
    button.setAutoRaise(True)
    button.setIconSize(QSize(24, 24))
    fxicons.set_icon(button, "close")
    QVBoxLayout(window).addWidget(button)
    window.show()
    qtbot.waitExposed(window)

    hover(qtbot, button)
    area = QRect(button.mapTo(window, QPoint(0, 0)), button.size())
    seen = _most(window.grab(area).toImage())

    colours = dict(vars(fxstyle.colors()))
    assert near(seen[0], colours["state_hover"], 2), seen[:3]
    # The icon stands out from the fill it sits on, however it blends.
    assert any(not near(c, colours["state_hover"], 80)
               for c in seen[1:6]), seen[:6]
