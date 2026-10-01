"""Singleton metaclass for Qt widgets."""

# Third-party
from qtpy.QtCore import QObject

# Internal
from fxgui import _compat


class FXSingleton(type(QObject)):
    """Metaclass for Qt classes that are singletons.

    A call returns the live instance, shown and raised, or builds one when
    there is none or Qt has deleted it. Each subclass gets its own. A call
    that finds a live instance ignores its arguments, so a menu entry can
    call `MyWindow(parent=host)` every time; `reset_instance` first to
    build with new ones.

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
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        instance = cls._instance
        if instance is None or not _compat.is_valid(instance):
            cls._instance = super().__call__(*args, **kwargs)
        elif hasattr(instance, "show"):
            instance.show()
            instance.raise_()
            instance.activateWindow()
        return cls._instance

    def reset_instance(cls):
        """Forget the instance, so the next call builds a new one."""
        cls._instance = None
