"""One running copy of an application per name, and a way to wake it."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QObject, Signal


# Long enough for a named pipe on a loaded machine, unfelt on first start.
_PROBE_MS = 300


class FXSingleInstance(QObject):
    """A lock on a local socket name; a second start wakes the first.

    Put the user in `name` so two accounts on one machine each get their
    own copy. QtNetwork is imported on `claim`, so a host without it can
    still import fxgui.

    Args:
        name: The socket name to hold, such as `f"my-app-{getuser()}"`.
        parent: Parent object.

    Signals:
        woken: Another start asked for this copy; show the window.

    Raises:
        RuntimeError: From `claim`, when no copy runs but the name cannot
            be listened on.

    Examples:
        >>> instance = FXSingleInstance(f"my-app-{getpass.getuser()}")
        >>> if not instance.claim():
        ...     sys.exit(0)  # the running copy has been woken
        >>> instance.woken.connect(window.show)
    """

    woken = Signal()

    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._name = name
        self._server = None

    def claim(self) -> bool:
        """Take the name, or wake the copy that holds it and return False."""
        from qtpy.QtNetwork import QLocalServer, QLocalSocket

        probe = QLocalSocket()
        probe.connectToServer(self._name)
        if probe.waitForConnected(_PROBE_MS):
            probe.disconnectFromServer()
            return False
        # A crash leaves the socket file on some platforms; on Windows a no-op.
        QLocalServer.removeServer(self._name)
        server = QLocalServer(self)
        if not server.listen(self._name):
            # Not "another copy runs": that copy would have answered.
            raise RuntimeError(
                f"cannot listen on {self._name!r}: {server.errorString()}")
        server.newConnection.connect(self._on_connection)
        self._server = server
        return True

    def _on_connection(self) -> None:
        """Let the connection go, nothing is read, and say we were woken."""
        connection = self._server.nextPendingConnection()
        if connection is not None:
            connection.disconnected.connect(connection.deleteLater)
        self.woken.emit()
