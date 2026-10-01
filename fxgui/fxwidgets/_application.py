"""Custom QApplication."""

# Third-party
from qtpy.QtWidgets import QApplication

# Internal
from fxgui import fxstyle


class FXApplication(QApplication):
    """Customized QApplication class.

    On initialization, the application loads the previously saved theme
    from persistent storage. If no theme was saved, defaults to "dark".

    Note:
        Qt allows a single QApplication per process. When one already exists
        and is not an FXApplication (e.g. inside Houdini, Maya, or Nuke),
        calling ``FXApplication()`` returns the host's application instance
        untouched instead of raising ``RuntimeError``. fxgui styling is NOT
        applied to the host application in that case; fxgui's windows,
        dialogs, tray menu and splash register themselves as themed roots.
    """

    def __new__(cls, *args, **kwargs):
        existing = QApplication.instance()
        if existing is not None:
            # A foreign application skips __init__, so the host is untouched.
            return existing
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        if not getattr(self, "_fx_initialized", False):
            if not args:
                # PyQt's QApplication requires argv positionally; PySide
                # defaults it.
                args = ([],)
            super().__init__(*args, **kwargs)
            self._fx_initialized = True

            fxstyle.set_style(self, "Fusion")

            # The saved theme's sheet now, and again on every apply_theme().
            fxstyle.register_themed_root(self)
