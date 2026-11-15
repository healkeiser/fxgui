"""One running copy of an application per name, and a way to wake it."""

# Built-in
import hashlib
import os
import time
from typing import Optional

# Third-party
from qtpy.QtCore import QDir, QLockFile, QObject, QThread, Signal, Slot


# Long enough for a named pipe on a loaded machine, unfelt on first start.
_PROBE_MS = 300

# How long a start that lost the lock keeps knocking while the winner,
# started in the same instant, comes up to listen.
_REACH_SECONDS = 5.0
_RETRY_MS = 50

# A message is a wake-up note, not a transfer: anything longer is dropped.
MAX_MESSAGE_BYTES = 64 * 1024

# A copy of this fxgui also listens on the name plus this suffix, where a
# message is framed and acknowledged; an older copy listens on the bare name.
_ACK_SUFFIX = "-ack"
# A framed message: its length in this many big-endian bytes, then the text.
_HEADER = 4
# The byte a copy answers once it has read a framed message whole.
_ACK = b"\x06"


class FXSingleInstance(QObject):
    """A lock on a local socket name; a second start wakes the first.

    Put the user in `name` so two accounts on one machine each get their
    own copy. QtNetwork is imported on `claim`, so a host without it can
    still import fxgui. Only the same user's processes can connect, but
    any of them can: treat a message as untrusted input. Qt cannot tell
    who listens on a name: on a machine several people use at once,
    another account could listen on the name first (Windows pipe names
    are machine-wide) and be handed a start's message. This is meant for
    single-user workstations; put the user in the name.

    Args:
        name: The socket name to hold, such as `f"my-app-{getuser()}"`.
        parent: Parent object.

    Signals:
        woken: Another start asked for this copy with nothing to say;
            show the window.
        messaged: Another start handed this copy a text, such as the
            arguments it was started with.

    Raises:
        RuntimeError: From `claim`, when no copy runs but the name cannot
            be listened on, or the copy holding it does not acknowledge
            the message in time.

    Examples:
        >>> instance = FXSingleInstance(f"my-app-{getpass.getuser()}")
        >>> if not instance.claim(" ".join(sys.argv[1:])):
        ...     sys.exit(0)  # the running copy has been handed the text
        >>> instance.woken.connect(window.show)
        >>> instance.messaged.connect(window.open_arguments)
        >>> # A restart: while not instance.try_claim(): wait, then retry
    """

    woken = Signal()
    messaged = Signal(str)

    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._name = name
        self._server = None
        self._ack_server = None
        self._lock = None

    def claim(self, message: str = "") -> bool:
        """Take the name, or hand `message` to the copy holding it.

        Args:
            message: Text for the running copy's `messaged`; empty wakes
                it through `woken` instead. UTF-8, at most
                `MAX_MESSAGE_BYTES`.

        Returns:
            True when this process now holds the name, False when another
            copy holds it and acknowledged `message`, or is an older fxgui
            that was handed it unconfirmed.

        Raises:
            ValueError: If `message` is longer than `MAX_MESSAGE_BYTES`.
            RuntimeError: The name cannot be listened on, or the copy
                holding it does not acknowledge `message` within 5 s (it
                may still read it later).
        """
        payload = message.encode("utf-8")
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError(
                f"a message holds at most {MAX_MESSAGE_BYTES} bytes, "
                f"got {len(payload)}")
        # Already the holder: handing over would knock on itself.
        if self._lock is not None:
            return True
        lock = self._lock_file()
        deadline = time.monotonic() + _REACH_SECONDS
        # Tried each round: a holder on its way out lets go meanwhile.
        while not lock.tryLock(0):
            if self._hand_over(payload, deadline):
                return False
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"the copy holding {self._name!r} does not answer")
            QThread.msleep(_RETRY_MS)
        self._listen(lock)
        return True

    def try_claim(self) -> bool:
        """Take the name if no copy holds it; never contact the holder.

        For a start that must wait for a copy on its way out, such as a
        restart: call it until it returns True, pausing between calls.
        `claim` instead hands a message to a running copy.

        Returns:
            True when this process holds the name, now or already.

        Raises:
            RuntimeError: No copy holds the name, but it cannot be
                listened on.
        """
        if self._lock is not None:
            return True
        lock = self._lock_file()
        if not lock.tryLock(0):
            return False
        self._listen(lock)
        return True

    def _lock_file(self) -> QLockFile:
        """Return the lock file that picks one holder of the name."""
        # Windows lets two servers listen on one name, so two starts in the
        # same instant would both win the probe: a lock file picks one.
        digest = hashlib.sha256(self._name.encode("utf-8")).hexdigest()[:24]
        lock = QLockFile(os.path.join(QDir.tempPath(), f"fxgui-{digest}.lock"))
        # Stale only when its process is gone, however long a copy runs.
        lock.setStaleLockTime(0)
        return lock

    def _listen(self, lock: QLockFile) -> None:
        """Listen on the name, framed and bare, under the held `lock`.

        Raises:
            RuntimeError: Either name cannot be listened on.
        """
        from qtpy.QtNetwork import QLocalServer

        servers = []
        # The framed name first: a start that finds it never falls back to
        # the unconfirmed bare name.
        for name, slot in (
            (self._name + _ACK_SUFFIX, self._on_framed_connection),
            (self._name, self._on_connection),
        ):
            # A crash leaves the socket file on some platforms; on Windows a no-op.
            QLocalServer.removeServer(name)
            server = QLocalServer(self)
            # Another account on the machine cannot hand this copy a message.
            server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
            if not server.listen(name):
                error = server.errorString()
                for opened in servers:
                    opened.close()
                lock.unlock()
                raise RuntimeError(f"cannot listen on {name!r}: {error}")
            server.newConnection.connect(slot)
            servers.append(server)
        self._ack_server, self._server = servers
        self._lock = lock
        self.destroyed.connect(lock.unlock)

    def _hand_over(self, payload: bytes, deadline: float) -> bool:
        """Hand `payload` to the copy holding the name; True once it has it.

        A copy of this fxgui acknowledges a message once read; one that has
        not by `deadline` (hung, or quitting) has not got it. Only when the
        acknowledging name does not exist, an older fxgui, is the payload
        handed over unconfirmed, as that copy expects.
        """
        from qtpy.QtNetwork import QLocalSocket

        probe = QLocalSocket()
        probe.connectToServer(self._name + _ACK_SUFFIX)
        if probe.waitForConnected(_PROBE_MS):
            probe.write(len(payload).to_bytes(_HEADER, "big") + payload)
            wait_ms = max(int((deadline - time.monotonic()) * 1000), _PROBE_MS)
            # A Unix socket sends only once flushed; waiting to read does not.
            probe.waitForBytesWritten(wait_ms)
            # The holder answers and hangs up: on Unix the wait can end on the
            # hang-up with the answer already in, so read what came either way.
            if not probe.bytesAvailable():
                probe.waitForReadyRead(wait_ms)
            acked = bytes(probe.read(1)) == _ACK
            probe.abort()
            return acked
        missing = (
            QLocalSocket.LocalSocketError.ServerNotFoundError,
            # A Unix socket file a crashed copy left, with no one listening.
            QLocalSocket.LocalSocketError.ConnectionRefusedError,
        )
        if probe.error() not in missing:
            return False
        return self._hand_over_unconfirmed(payload)

    def _hand_over_unconfirmed(self, payload: bytes) -> bool:
        """Hand `payload` the old way, to a copy of an older fxgui: unconfirmed."""
        from qtpy.QtNetwork import QLocalSocket

        probe = QLocalSocket()
        probe.connectToServer(self._name)
        if not probe.waitForConnected(_PROBE_MS):
            return False
        if payload:
            probe.write(payload)
            probe.waitForBytesWritten(_PROBE_MS)
        probe.disconnectFromServer()
        # Unwritten bytes keep it closing; leaving now would lose them.
        if probe.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            probe.waitForDisconnected(_PROBE_MS)
        return True

    @Slot()
    def _on_connection(self) -> None:
        """Read what the new start sends until it hangs up, then answer."""
        from qtpy.QtNetwork import QLocalSocket

        connection = self._server.nextPendingConnection()
        if connection is None:
            return
        received = bytearray()

        def read() -> None:
            received.extend(bytes(connection.readAll()))
            if len(received) > MAX_MESSAGE_BYTES:
                connection.abort()

        def finished() -> None:
            # Its destructor emits `disconnected` again, into a dying object.
            connection.readyRead.disconnect(read)
            connection.disconnected.disconnect(finished)
            read()
            connection.deleteLater()
            # Oversized: not a sender of ours; wake rather than show it.
            self._deliver(
                b"" if len(received) > MAX_MESSAGE_BYTES else bytes(received))

        connection.readyRead.connect(read)
        connection.disconnected.connect(finished)
        # A start that hung up before this ran never fires `disconnected`.
        if connection.state() == QLocalSocket.LocalSocketState.UnconnectedState:
            finished()

    @Slot()
    def _on_framed_connection(self) -> None:
        """Read one framed message, acknowledge it, then hand it on."""
        from qtpy.QtNetwork import QLocalSocket

        connection = self._ack_server.nextPendingConnection()
        if connection is None:
            return
        received = bytearray()
        state = {"answered": False, "closed": False}

        def read() -> None:
            if state["answered"]:
                return
            received.extend(bytes(connection.readAll()))
            if len(received) < _HEADER:
                return
            size = int.from_bytes(received[:_HEADER], "big")
            if size > MAX_MESSAGE_BYTES or len(received) > _HEADER + size:
                # Not a sender of ours: no answer, no signal.
                state["answered"] = True
                connection.abort()
                return
            if len(received) < _HEADER + size:
                return
            state["answered"] = True
            # Answered before the slots run: a slot may open a dialog and
            # hold the sender past its deadline.
            connection.write(_ACK)
            connection.flush()
            connection.disconnectFromServer()
            self._deliver(bytes(received[_HEADER:]))

        def finished() -> None:
            if state["closed"]:
                return
            state["closed"] = True
            # Its destructor emits `disconnected` again, into a dying object.
            connection.readyRead.disconnect(read)
            connection.disconnected.disconnect(finished)
            connection.deleteLater()

        connection.readyRead.connect(read)
        connection.disconnected.connect(finished)
        # Bytes that came before this ran raise no `readyRead`.
        read()
        if connection.state() == QLocalSocket.LocalSocketState.UnconnectedState:
            finished()

    def _deliver(self, payload: bytes) -> None:
        """Say what a start handed over: `woken` for nothing, else `messaged`."""
        if not payload:
            self.woken.emit()
            return
        self.messaged.emit(payload.decode("utf-8", "replace"))
