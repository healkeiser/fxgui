"""FXApplication - Custom QApplication."""

from qtpy.QtWidgets import QApplication

from fxgui import fxstyle


class FXApplication(QApplication):
    """Customized QApplication class."""

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
            self.setStyleSheet(fxstyle.load_stylesheet())

            # Mark the instance as initialized
            self.__initialized = True

    @classmethod
    def instance(cls, *args, **kwargs):
        """Return the existing instance or create a new one if it doesn't
        exist.
        """

        # This ensures that `__new__` and `__init__` are called if the instance
        # doesn't exist
        return cls(*args, **kwargs)
