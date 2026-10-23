"""One running copy per name; a second start is refused and wakes the first."""

# Built-in
import os
import subprocess
import sys

# Third-party
import pytest

# Internal
from fxgui.fxwidgets import FXSingleInstance


def _name(tag):
    """A lock name no other test or session shares."""
    return f"fxgui-test-{tag}-{os.getpid()}"


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


# A message is read while the sender waits, so the sender is another process.
_SEND = "\n".join(
    (
        "import sys",
        "from qtpy.QtCore import QCoreApplication",
        "from fxgui.fxwidgets import FXSingleInstance",
        "app = QCoreApplication([])",
        "sys.exit(FXSingleInstance(sys.argv[1]).claim(sys.argv[2]))",
    )
)


def _send(name, message):
    """Start another process that claims `name` carrying `message`."""
    return subprocess.Popen([sys.executable, "-c", _SEND, name, message])


def test_a_second_process_hands_its_message_to_the_first(qtbot):
    first = FXSingleInstance(_name("message"))
    assert first.claim()
    woken = []
    first.woken.connect(lambda: woken.append(True))

    with qtbot.waitSignal(first.messaged, timeout=15000) as caught:
        sender = _send(_name("message"), "lotchi://x?a=1&b=%20é")

    assert caught.args == ["lotchi://x?a=1&b=%20é"]
    assert woken == []
    assert sender.wait(15) == 0


def test_a_message_over_the_limit_is_refused_before_sending(qtbot):
    from fxgui.fxwidgets._single_instance import MAX_MESSAGE_BYTES

    with pytest.raises(ValueError, match="at most"):
        FXSingleInstance(_name("long")).claim("x" * (MAX_MESSAGE_BYTES + 1))


def test_a_message_over_the_limit_wakes_instead(qtbot):
    from fxgui.fxwidgets._single_instance import MAX_MESSAGE_BYTES
    from qtpy.QtNetwork import QLocalSocket

    first = FXSingleInstance(_name("flood"))
    assert first.claim()
    messaged = []
    first.messaged.connect(messaged.append)

    sender = QLocalSocket()
    with qtbot.waitSignal(first.woken, timeout=15000):
        sender.connectToServer(_name("flood"))
        assert sender.waitForConnected(5000)
        sender.write(b"x" * (MAX_MESSAGE_BYTES + 1))
        sender.disconnectFromServer()

    assert messaged == []
