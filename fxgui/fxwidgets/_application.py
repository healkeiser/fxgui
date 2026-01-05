"""Custom QApplication."""

# Third-party
from qtpy.QtWidgets import QApplication

# Internal
from fxgui import fxstyle


class FXApplication(QApplication):
    """Customized QApplication class.

    On initialization, the application loads the previously saved theme
    from persistent storage. If no theme was saved, defaults to "dark".
    """

    _instance = None  # Private class attribute to hold the singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:

            # Create the instance if it doesn't exist
            cls._instance = super(FXApplication, cls).__new__(cls)

            # Initialize the instance once
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
        if not self.__initialized:
            super().__init__(*args, **kwargs)

            fxstyle.set_style(self, "Fusion")

            # Load stylesheet with saved theme from persistent storage
            # load_stylesheet() automatically uses the saved theme
            self.setStyleSheet(fxstyle.load_stylesheet())

            # Connect to theme changes to update application stylesheet
            fxstyle.theme_manager.theme_changed.connect(self._on_theme_changed)

            # Mark the instance as initialized
            self.__initialized = True

    def _on_theme_changed(self, theme_name: str) -> None:
        """Update application stylesheet when theme changes."""
        self.setStyleSheet(fxstyle.load_stylesheet())

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
