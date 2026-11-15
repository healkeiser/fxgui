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

    # The sender waits for this loop's answer, so it is another process.
    with qtbot.waitSignal(first.woken, timeout=15000):
        sender = _send(_name("second"), "")

    assert sender.wait(15) == 0


def test_a_released_name_can_be_claimed_again(qtbot):
    first = FXSingleInstance(_name("again"))
    assert first.claim()
    first.deleteLater()
    qtbot.wait(50)

    assert FXSingleInstance(_name("again")).claim()


def test_try_claim_takes_a_free_name_and_never_wakes_the_holder(qtbot):
    first = FXSingleInstance(_name("try"))
    assert first.try_claim()
    woken = []
    first.woken.connect(lambda: woken.append(True))

    assert not FXSingleInstance(_name("try")).try_claim()
    qtbot.wait(200)

    assert woken == []


def test_try_claim_takes_a_name_once_its_holder_is_gone(qtbot):
    first = FXSingleInstance(_name("try-again"))
    assert first.claim()
    first.deleteLater()
    qtbot.wait(50)

    assert FXSingleInstance(_name("try-again")).try_claim()


def test_the_holder_claiming_again_keeps_the_name_at_once(qtbot):
    import time

    first = FXSingleInstance(_name("twice"))
    assert first.claim()

    start = time.monotonic()
    assert first.claim("again")
    assert first.try_claim()
    assert time.monotonic() - start < 1


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


# Claims with a short reach, and prints what came of it.
_CLAIM = "\n".join(
    (
        "import sys",
        "from qtpy.QtCore import QCoreApplication",
        "from fxgui.fxwidgets import FXSingleInstance, _single_instance",
        "_single_instance._REACH_SECONDS = float(sys.argv[3])",
        "app = QCoreApplication([])",
        "try:",
        "    held = FXSingleInstance(sys.argv[1]).claim(sys.argv[2])",
        "    print('claimed' if held else 'handed', flush=True)",
        "except RuntimeError as error:",
        "    print('error', error, flush=True)",
    )
)


def _claim(name, message, reach=1.0):
    """Start another process that claims `name`; read what it prints."""
    return subprocess.Popen(
        [sys.executable, "-c", _CLAIM, name, message, str(reach)],
        stdout=subprocess.PIPE,
        text=True,
    )


def _hold_lock(name):
    """Hold `name`'s lock as a copy would, without listening."""
    lock = FXSingleInstance(name)._lock_file()
    assert lock.tryLock(0)
    return lock


def _finish(qtbot, process):
    """Run the event loop until `process` exits; return its output."""
    qtbot.waitUntil(lambda: process.poll() is not None, timeout=20000)
    return process.stdout.read().strip()


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


# Claims the moment a go file appears. Its first knock finds nobody: it
# says so in a probed file, then knocks again once a listening file appears.
_RACE = "\n".join(
    (
        "import os, sys, time",
        "from qtpy.QtCore import QCoreApplication",
        "from qtpy import QtNetwork",
        "from fxgui.fxwidgets import FXSingleInstance",
        "app = QCoreApplication([])",
        "name, go, probed, listening = sys.argv[1:5]",
        "def wait_for(path):",
        "    deadline = time.monotonic() + 15",
        "    while not os.path.exists(path) and time.monotonic() < deadline:",
        "        time.sleep(0.002)",
        "instance = FXSingleInstance(name)",
        "knock = instance._hand_over",
        "def first_knock(payload, deadline):",
        "    instance._hand_over = knock",
        "    reached = knock(payload, deadline)",
        "    open(probed, 'w').close()",
        "    wait_for(listening)",
        "    return reached",
        "instance._hand_over = first_knock",
        "print('ready', flush=True)",
        "wait_for(go)",
        "sys.exit(instance.claim('late'))",
    )
)


def test_a_start_racing_one_not_yet_listening_hands_over(
    qtbot, tmp_path, monkeypatch
):
    import time

    from qtpy.QtCore import QTimer
    from qtpy.QtNetwork import QLocalServer

    go, probed, listening = (tmp_path / n for n in ("go", "probed", "listening"))
    racer = subprocess.Popen(
        [sys.executable, "-c", _RACE, _name("race"), str(go), str(probed),
         str(listening)],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert racer.stdout.readline().strip() == "ready"
    real_listen = QLocalServer.listen

    def slow_listen(server, name):
        # The other start probes while this one has yet to listen.
        go.write_text("")
        deadline = time.monotonic() + 15
        while not probed.exists() and time.monotonic() < deadline:
            time.sleep(0.002)
        return real_listen(server, name)

    monkeypatch.setattr(QLocalServer, "listen", slow_listen)
    first = FXSingleInstance(_name("race"))
    said = []
    first.messaged.connect(said.append)
    first.woken.connect(lambda: said.append("woken"))
    assert first.claim()
    assert probed.exists(), "the racing start never found nobody listening"
    # Knock again once this loop runs: a sender gone before it is accepted
    # loses its message.
    QTimer.singleShot(0, lambda: listening.write_text(""))

    qtbot.waitUntil(lambda: bool(said), timeout=10000)
    assert said == ["late"]
    assert racer.wait(15) == 0, "the racing start also took the name"


def test_a_framed_message_is_acknowledged_once_read(qtbot):
    from qtpy.QtNetwork import QLocalSocket

    first = FXSingleInstance(_name("ack"))
    assert first.claim()
    sender = QLocalSocket()
    with qtbot.waitSignal(first.messaged, timeout=5000) as caught:
        sender.connectToServer(_name("ack") + "-ack")
        assert sender.waitForConnected(5000)
        sender.write((4).to_bytes(4, "big") + b"link")

    assert caught.args == ["link"]
    qtbot.waitUntil(lambda: sender.bytesAvailable() > 0)
    assert bytes(sender.read(1)) == b"\x06"


def test_a_holder_that_never_answers_is_not_taken_for_reached(qtbot):
    from qtpy.QtNetwork import QLocalServer

    name = _name("hung")
    lock = _hold_lock(name)
    hung = QLocalServer()
    assert hung.listen(name + "-ack")  # takes connections, never reads
    try:
        out = _finish(qtbot, _claim(name, "link", reach=1.0))
    finally:
        hung.close()
        lock.unlock()

    assert out.startswith("error") and "does not answer" in out


# Holds the name, says so, then keeps its loop busy before running it.
_BUSY = "\n".join(
    (
        "import sys, time",
        "from qtpy.QtCore import QCoreApplication, QTimer",
        "from fxgui.fxwidgets import FXSingleInstance",
        "app = QCoreApplication([])",
        "instance = FXSingleInstance(sys.argv[1])",
        "assert instance.claim()",
        "def show(text):",
        "    print(text, flush=True)",
        "    app.quit()",
        "instance.messaged.connect(show)",
        "QTimer.singleShot(5000, app.quit)",
        "print('holding', flush=True)",
        "time.sleep(1.5)",
        "app.exec()",
    )
)


def test_a_holder_busy_when_the_message_comes_still_gets_it():
    name = _name("busy")
    holder = subprocess.Popen(
        [sys.executable, "-c", _BUSY, name], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "holding"
        # The holder's loop is busy now: no claim here may count it reached
        # until that loop has read the message.
        assert not FXSingleInstance(name).claim("link")
        assert holder.communicate(timeout=15)[0].strip() == "link"
    finally:
        holder.kill()


def test_a_new_start_still_reaches_an_old_holder(qtbot):
    from qtpy.QtNetwork import QLocalServer

    name = _name("old-holder")
    lock = _hold_lock(name)
    old = QLocalServer()
    assert old.listen(name)  # an older fxgui: the bare name only
    received = bytearray()

    def take():
        connection = old.nextPendingConnection()
        connection.readyRead.connect(
            lambda: received.extend(bytes(connection.readAll())))

    old.newConnection.connect(take)
    try:
        out = _finish(qtbot, _claim(name, "link", reach=5.0))
        qtbot.waitUntil(lambda: bytes(received) == b"link")
    finally:
        old.close()
        lock.unlock()

    assert out == "handed"


def test_an_old_start_still_reaches_a_new_holder(qtbot):
    from qtpy.QtNetwork import QLocalSocket

    first = FXSingleInstance(_name("old-start"))
    assert first.claim()
    sender = QLocalSocket()
    with qtbot.waitSignal(first.messaged, timeout=5000) as caught:
        sender.connectToServer(_name("old-start"))
        assert sender.waitForConnected(5000)
        sender.write(b"link")
        sender.disconnectFromServer()

    assert caught.args == ["link"]


def test_a_holder_on_its_way_out_hands_the_name_on(qtbot):
    from qtpy.QtNetwork import QLocalServer

    name = _name("leaving")
    lock = _hold_lock(name)
    leaving = QLocalServer()
    assert leaving.listen(name + "-ack")
    knocks = []

    def refuse():
        connection = leaving.nextPendingConnection()
        knocks.append(True)
        connection.abort()  # quitting: hangs up without an answer

    leaving.newConnection.connect(refuse)
    starter = _claim(name, "link", reach=10.0)
    try:
        qtbot.waitUntil(lambda: bool(knocks), timeout=15000)
    finally:
        leaving.close()
        lock.unlock()

    assert _finish(qtbot, starter) == "claimed"


def test_an_oversized_frame_gets_no_answer_and_no_signal(qtbot):
    from fxgui.fxwidgets._single_instance import MAX_MESSAGE_BYTES
    from qtpy.QtNetwork import QLocalSocket

    first = FXSingleInstance(_name("big-frame"))
    assert first.claim()
    said = []
    first.messaged.connect(said.append)
    first.woken.connect(lambda: said.append("woken"))
    sender = QLocalSocket()
    sender.connectToServer(_name("big-frame") + "-ack")
    assert sender.waitForConnected(5000)

    sender.write((MAX_MESSAGE_BYTES + 1).to_bytes(4, "big"))
    qtbot.waitUntil(
        lambda: sender.state() == QLocalSocket.LocalSocketState.UnconnectedState)

    assert said == []
    assert sender.bytesAvailable() == 0
