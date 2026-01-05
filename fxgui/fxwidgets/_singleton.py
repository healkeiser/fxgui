"""Singleton metaclass for Qt widgets."""

# Third-party
from qtpy.QtCore import QObject
from qtpy.QtWidgets import QWidget


class FXSingleton(type(QObject)):
    """Metaclass for Qt classes that are singletons.

    This metaclass ensures that only one instance of each class can exist.
    If an instance already exists, it returns the existing instance instead
    of creating a new one. Each subclass gets its own singleton instance.

    Examples:
        >>> from fxgui import fxwidgets
        >>>
        >>> class MySingletonWindow(fxwidgets.FXMainWindow, metaclass=fxwidgets.FXSingleton):
        ...     pass
        >>>
        >>> window1 = MySingletonWindow()
        >>> window2 = MySingletonWindow()
        >>> assert window1 is window2  # Same instance
    """

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls._instance: QWidget = None
        cls._initialized: bool = False

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
            cls._initialized = True
        else:
            # If instance already exists, just show it (if it's a window)
            if hasattr(cls._instance, "show"):
                cls._instance.show()
                cls._instance.raise_()
                cls._instance.activateWindow()
        return cls._instance

    def reset_instance(cls):
        """Reset the singleton instance. Useful for testing or cleanup."""
        cls._instance = None
        cls._initialized = False
