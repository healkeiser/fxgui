"""Building a widget shows no window of its own, not even for a moment."""

# Third-party
import pytest
from qtpy.QtCore import QEvent, QObject
from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout

# Internal
from fxgui import fxwidgets


class _Shows(QObject):
    def __init__(self):
        super().__init__()
        self.windows = []

    def eventFilter(self, watched, event):
        if (
            event.type() == QEvent.Show
            and watched.isWidgetType()
            and watched.isWindow()
        ):
            self.windows.append(type(watched).__name__)
        return False


def _accordion():
    accordion = fxwidgets.FXAccordion()
    accordion.add_section("a", QLabel("a"), icon="settings")
    return accordion


def _collapsible():
    section = fxwidgets.FXCollapsibleWidget(title="t", icon="settings")
    layout = QVBoxLayout()
    layout.addWidget(QLabel("x"))
    section.set_content_layout(layout)
    return section


BUILDERS = {
    "breadcrumb": lambda: fxwidgets.FXBreadcrumb(show_navigation=True),
    "tags": lambda: fxwidgets.FXTagInput(),
    "path": lambda: fxwidgets.FXFilePathWidget(mode="folder"),
    "code": lambda: fxwidgets.FXCodeBlock("x = 1"),
    "accordion": _accordion,
    "collapsible": _collapsible,
    "drop": lambda: fxwidgets.FXDropZone(extensions={".exr"}),
    "log": lambda: fxwidgets.FXOutputLogWidget(),
    "timeline": lambda: fxwidgets.FXTimelineSlider(
        show_loop_controls=True, show_keyframe_controls=True),
    "timeline_below": lambda: fxwidgets.FXTimelineSlider(
        controls_position="below"),
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_building_shows_no_window(qtbot, qapp, name):
    shows = _Shows()
    QApplication.instance().installEventFilter(shows)
    try:
        widget = BUILDERS[name]()
        qtbot.addWidget(widget)
        qapp.processEvents()
    finally:
        QApplication.instance().removeEventFilter(shows)

    assert shows.windows == []


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_a_dropped_widget_is_freed_without_the_cycle_collector(
    qtbot, qapp, name
):
    """A child holding its parent is a cycle: the collector then deletes a
    shown top-level widget at some later moment, mid-event, and crashes."""
    import gc
    import weakref

    gc.disable()
    try:
        widget = BUILDERS[name]()
        if name == "breadcrumb":
            widget.set_path(["a", "b"])
        widget.show()
        qtbot.waitExposed(widget)
        widget.close()
        ref = weakref.ref(widget)
        del widget
        assert ref() is None
    finally:
        gc.enable()
