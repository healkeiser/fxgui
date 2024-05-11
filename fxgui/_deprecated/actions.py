"""Scripts related to the QAction."""

# Built-in
from typing import Union, Callable

# Thirs-party
from qtpy.QtGui import QIcon, QKeySequence
from qtpy.QtWidgets import QAction, QWidget

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


def create_action(
    parent: QWidget,
    name: str,
    icon: str,
    trigger: Callable,
    enable: bool = True,
    visible: bool = True,
    shortcut: str = None,
) -> Union[QAction, None]:
    """Creates a QACtion.

    Args:
        parent (QWidget): Parent object.
        name (str): Name to display.
        icon (str): Icon path.
        trigger (Callable): Function to trigger when clicked.
        enable (bool, optional): Enable/disable. Defaults to `True`.
        visible (bool, optional): Show/hide. Defaults to `True`.
        shortcut (str, optional): If not `None`, key sequence (hotkeys) to use.
            Defaults to `None`.

    Returns:
        Union[QAction, None]:
    """

    action = QAction(name, parent or None)
    action.setIcon(QIcon(icon))
    action.triggered.connect(trigger)
    action.setEnabled(enable)
    action.setVisible(visible)
    if shortcut is not None:
        action.setShortcut(QKeySequence(shortcut))

    return action
