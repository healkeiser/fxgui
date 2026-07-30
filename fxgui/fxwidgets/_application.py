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
        applied to the host application in that case; style individual
        widgets with ``fxstyle.load_stylesheet()`` instead.
    """

    _instance = None  # Private class attribute to hold the singleton instance

    def __new__(cls, *args, **kwargs):
        existing = QApplication.instance()
        if existing is not None and not isinstance(existing, cls):
            # A foreign QApplication is already running (DCC host or another
            # framework). Returning a non-`cls` instance from __new__ skips
            # __init__, so the host application is left untouched.
            return existing

        if cls._instance is None:

            # Create the instance if it doesn't exist
            cls._instance = super(FXApplication, cls).__new__(cls)

            # Initialize the instance once
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
        if not self.__initialized:
            if not args:
                # PyQt's QApplication requires argv positionally; PySide
                # defaults it. An empty list matches PySide's no-argument
                # behavior.
                args = ([],)
            super().__init__(*args, **kwargs)

            fxstyle.set_style(self, "Fusion")

            # Register as themed root: the saved theme's stylesheet is
            # applied now and re-applied automatically on apply_theme().
            fxstyle.register_themed_root(self)

            # The registry owns the stylesheet now, but subclasses may
            # override `_on_theme_changed`, so the hook still has to fire.
            fxstyle.theme_changed.connect(self._on_theme_changed)

            # Mark the instance as initialized
            self.__initialized = True

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

    @classmethod
    def instance(cls, *args, **kwargs):
        """Return the existing instance or create a new one if it doesn't
        exist.
        """

        # This ensures that `__new__` and `__init__` are called if the instance
        # doesn't exist
        return cls(*args, **kwargs)


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
