"""One running copy per name; a second start is refused and wakes the first."""

# Built-in
import os

# Third-party
import pytest

# Internal
from fxgui.fxwidgets import FXSingleInstance


def _name(tag):
    """A lock name no other test or session shares."""
    return f"fxgui-test-{tag}-{os.getpid()}"


def test_the_first_claim_holds_the_name(qtbot):
    instance = FXSingleInstance(_name("first"))

    assert instance.claim()


def test_a_second_claim_is_refused_and_wakes_the_first(qtbot):
    first = FXSingleInstance(_name("second"))
    assert first.claim()

    with qtbot.waitSignal(first.woken):
        assert not FXSingleInstance(_name("second")).claim()


def test_a_released_name_can_be_claimed_again(qtbot):
    first = FXSingleInstance(_name("again"))
    assert first.claim()
    first.deleteLater()
    qtbot.wait(50)

    assert FXSingleInstance(_name("again")).claim()


def test_a_name_that_cannot_be_listened_on_raises(qtbot, monkeypatch):
    from qtpy.QtNetwork import QLocalServer

    monkeypatch.setattr(QLocalServer, "listen", lambda self, name: False)

    with pytest.raises(RuntimeError, match="cannot listen"):
        FXSingleInstance(_name("refused")).claim()
