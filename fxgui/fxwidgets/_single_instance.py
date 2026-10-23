"""One running copy of an application per name, and a way to wake it."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QObject, Signal, Slot


# Long enough for a named pipe on a loaded machine, unfelt on first start.
_PROBE_MS = 300

# A message is a wake-up note, not a transfer: anything longer is dropped.
MAX_MESSAGE_BYTES = 64 * 1024


class FXSingleInstance(QObject):
    """A lock on a local socket name; a second start wakes the first.

    Put the user in `name` so two accounts on one machine each get their
    own copy. QtNetwork is imported on `claim`, so a host without it can
    still import fxgui. Only the same user's processes can connect, but
    any of them can: treat a message as untrusted input.

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
            be listened on.

    Examples:
        >>> instance = FXSingleInstance(f"my-app-{getpass.getuser()}")
        >>> if not instance.claim(" ".join(sys.argv[1:])):
        ...     sys.exit(0)  # the running copy has been handed the text
        >>> instance.woken.connect(window.show)
        >>> instance.messaged.connect(window.open_arguments)
    """

    woken = Signal()
    messaged = Signal(str)

    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._name = name
        self._server = None

    def claim(self, message: str = "") -> bool:
        """Take the name, or hand `message` to the copy holding it.

        Args:
            message: Text for the running copy's `messaged`; empty wakes
                it through `woken` instead. UTF-8, at most
                `MAX_MESSAGE_BYTES`.

        Returns:
            True when this process now holds the name, False when another
            copy holds it and was handed `message`.

        Raises:
            ValueError: If `message` is longer than `MAX_MESSAGE_BYTES`.
        """
        from qtpy.QtNetwork import QLocalServer, QLocalSocket

        payload = message.encode("utf-8")
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError(
                f"a message holds at most {MAX_MESSAGE_BYTES} bytes, "
                f"got {len(payload)}")
        probe = QLocalSocket()
        probe.connectToServer(self._name)
        if probe.waitForConnected(_PROBE_MS):
            if payload:
                probe.write(payload)
                probe.waitForBytesWritten(_PROBE_MS)
            probe.disconnectFromServer()
            # Unwritten bytes keep it closing; leaving now would lose them.
            if probe.state() != QLocalSocket.LocalSocketState.UnconnectedState:
                probe.waitForDisconnected(_PROBE_MS)
            return False
        # A crash leaves the socket file on some platforms; on Windows a no-op.
        QLocalServer.removeServer(self._name)
        server = QLocalServer(self)
        # Another account on the machine cannot hand this copy a message.
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not server.listen(self._name):
            # Not "another copy runs": that copy would have answered.
            raise RuntimeError(
                f"cannot listen on {self._name!r}: {server.errorString()}")
        server.newConnection.connect(self._on_connection)
        self._server = server
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
            if not received or len(received) > MAX_MESSAGE_BYTES:
                self.woken.emit()
                return
            self.messaged.emit(bytes(received).decode("utf-8", "replace"))

        connection.readyRead.connect(read)
        connection.disconnected.connect(finished)
        # A start that hung up before this ran never fires `disconnected`.
        if connection.state() == QLocalSocket.LocalSocketState.UnconnectedState:
            finished()
