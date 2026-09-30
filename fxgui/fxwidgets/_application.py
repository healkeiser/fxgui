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

            # Register as themed root: the saved theme's stylesheet is
            # applied now and re-applied automatically on apply_theme().
            fxstyle.register_themed_root(self)

            # The registry owns the stylesheet now, but subclasses may
            # override `_on_theme_changed`, so the hook still has to fire.
            fxstyle.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str) -> None:
        """Hook invoked after a theme change, for subclasses to extend.

        Args:
            theme_name: The name of the theme that was just applied.

        Note:
            The application stylesheet is applied by the themed-root
            registry before this runs, so the base implementation does
            nothing. Override it to react to theme changes; anything you
            set here wins over the registry's sheet. New code can connect
            to ``fxstyle.theme_changed`` instead of subclassing.
        """


def example() -> None:
    import sys
    from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget
    from fxgui.fxwidgets import FXMainWindow

    app = FXApplication(sys.argv)
    window = FXMainWindow()
    window.setWindowTitle("FXApplication Demo")

    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    label = QLabel("This is a demo of FXApplication with styled theme.")
    layout.addWidget(label)

    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import os

    if os.getenv("DEVELOPER_MODE") == "1":
        example()
