"""The gallery shows every public widget, in every theme, without a warning."""

# Built-in
import importlib
import inspect
import pkgutil

# Third-party
import pytest
from qtpy.QtCore import QtMsgType
from qtpy.QtWidgets import QGroupBox, QTabWidget

# Internal
from fxgui import examples, fxstyle, fxwidgets

# Not widgets: an app, process plumbing, theme plumbing, data and an enum.
_NOT_SHOWN = {
    "FXApplication",
    "FXCommand",
    "FXSingleInstance",
    "FXSingleton",
    "FXThemeColors",
    "FXThemeManager",
    "FXTooltipManager",
    "FXTooltipPosition",
}


# The offscreen platform's own: no fonts in a PySide6 wheel, no size hints.
_PLATFORM_NOISE = (
    "QFontDatabase: Cannot find font directory",
    "This plugin does not support",
)


def _titles(window) -> str:
    tabs = window.centralWidget()
    found = [tabs.tabText(i) for i in range(tabs.count())]
    found += [box.title() for box in window.findChildren(QGroupBox)]
    return " / ".join(found)


def _shown(window) -> set:
    return set(_titles(window).replace("/", " ").split())


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
def test_the_gallery_builds_and_paints_in_every_theme(qapp, qtlog, theme):
    fxstyle.apply_theme(theme)
    window = examples.build()
    window.show()
    tabs = window.findChild(QTabWidget)
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        qapp.processEvents()
        window.grab()
    window.close()
    window.deleteLater()
    qapp.processEvents()
    warnings = [
        record.message
        for record in qtlog.records
        if record.type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg)
        and not record.message.startswith(_PLATFORM_NOISE)
    ]
    assert warnings == []


def test_the_gallery_shows_every_public_widget(qapp):
    window = examples.build()
    shown = _shown(window)
    classes = [
        name
        for name in fxwidgets.__all__
        if inspect.isclass(getattr(fxwidgets, name))
        and name not in _NOT_SHOWN
    ]
    assert [name for name in classes if name not in shown] == []
    assert "FXDockArea" in shown
    window.deleteLater()


def test_no_widget_module_carries_an_example_of_its_own():
    carrying = []
    for info in pkgutil.iter_modules(fxwidgets.__path__):
        module = importlib.import_module(f"fxgui.fxwidgets.{info.name}")
        source = inspect.getsource(module)
        if hasattr(module, "example") or "__main__" in source:
            carrying.append(info.name)
    assert carrying == []
