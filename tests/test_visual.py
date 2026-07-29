"""Visual validation: focus indicators must actually change the pixels.

Each test grabs the widget before and after focus and asserts the rendering
differs (a focus ring that paints nothing is not a focus ring). Set the
``FXGUI_SCREENSHOT_DIR`` environment variable to also dump the grabbed
frames as PNGs for human inspection.
"""

# Built-in
import os

# Internal
from fxgui.fxwidgets import FXRangeSlider, FXRatingWidget, FXToggleSwitch


def _save(image, name: str) -> None:
    directory = os.environ.get("FXGUI_SCREENSHOT_DIR")
    if directory:
        os.makedirs(directory, exist_ok=True)
        image.save(os.path.join(directory, name))


def _grab(widget):
    widget.repaint()
    return widget.grab().toImage()


def _focused_vs_unfocused(qtbot, widget, name: str):
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.activateWindow()

    widget.clearFocus()
    unfocused = _grab(widget)
    _save(unfocused, f"{name}_unfocused.png")

    widget.setFocus()
    qtbot.waitUntil(widget.hasFocus, timeout=2000)
    focused = _grab(widget)
    _save(focused, f"{name}_focused.png")

    return unfocused, focused


def test_toggle_switch_focus_ring_changes_pixels(qtbot):
    unfocused, focused = _focused_vs_unfocused(
        qtbot, FXToggleSwitch(), "toggle_switch"
    )
    assert focused != unfocused


def test_rating_widget_focus_ring_changes_pixels(qtbot):
    rating = FXRatingWidget(max_rating=5)
    rating.set_rating(3)
    unfocused, focused = _focused_vs_unfocused(qtbot, rating, "rating_widget")
    assert focused != unfocused


def test_range_slider_focus_ring_changes_pixels(qtbot):
    slider = FXRangeSlider(minimum=0, maximum=100, low=25, high=75)
    unfocused, focused = _focused_vs_unfocused(qtbot, slider, "range_slider")
    assert focused != unfocused


def test_dark_theme_text_hierarchy_screenshot(qtbot):
    """Render text vs text_muted side by side in the dark theme so the
    restored hierarchy can be inspected visually."""
    from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

    from fxgui import fxstyle

    colors = fxstyle.get_colors()["themes"]["dark"]
    panel = QWidget()
    panel.setStyleSheet(f"background: {colors['surface']};")
    layout = QVBoxLayout(panel)
    for role in ("text", "text_muted", "text_disabled"):
        label = QLabel(f"{role}: the quick brown fox 0123456789")
        label.setStyleSheet(
            f"color: {colors[role]}; background: {colors['surface']};"
            "font-size: 14px;"
        )
        layout.addWidget(label)

    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)
    _save(_grab(panel), "dark_text_hierarchy.png")
