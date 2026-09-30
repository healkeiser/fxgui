"""FXSingleton hands back one live instance, never a deleted one."""

# Third-party
import pytest
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import FXSingleton


def test_one_instance_while_it_lives(qtbot):
    class Probe(QWidget, metaclass=FXSingleton):
        pass

    first = Probe()
    qtbot.addWidget(first)

    assert Probe() is first


def test_a_deleted_instance_is_replaced(qtbot):
    shiboken = pytest.importorskip("shiboken6")

    class Probe(QWidget, metaclass=FXSingleton):
        pass

    first = Probe()
    shiboken.delete(first)
    second = Probe()
    qtbot.addWidget(second)

    assert shiboken.isValid(second)
    assert second is not first


def test_reset_instance_forgets_it(qtbot):
    class Probe(QWidget, metaclass=FXSingleton):
        pass

    first = Probe()
    qtbot.addWidget(first)
    Probe.reset_instance()
    second = Probe()
    qtbot.addWidget(second)

    assert second is not first
    assert not hasattr(Probe, "_initialized")
