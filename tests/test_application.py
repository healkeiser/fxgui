"""Tests for `fxgui.fxwidgets.FXApplication` inside a host application.

Regression: constructing FXApplication while another QApplication exists
(the situation inside Houdini/Maya/Nuke) raised RuntimeError, making the
library unusable in the DCCs it targets.
"""

# Third-party
from qtpy.QtWidgets import QApplication

# Internal
from fxgui.fxwidgets import FXApplication


def test_fxapplication_returns_host_application(qapp):
    """With a foreign QApplication running (pytest-qt's), FXApplication()
    must return it untouched instead of raising RuntimeError."""
    host_stylesheet = qapp.styleSheet()

    app = FXApplication()

    assert app is qapp
    # The host application must not be re-styled
    assert qapp.styleSheet() == host_stylesheet


def test_fxapplication_instance_classmethod(qapp):
    assert FXApplication.instance() is QApplication.instance()
