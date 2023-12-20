#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Scripts related to the QGraphicsDropShadowEffect."""

# Third-party
from PySide2 import QtWidgets
from PySide2.QtWidgets import QGraphicsDropShadowEffect

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


def add_shadows(
    parent: QtWidgets.QWidget,
    shadow_object: QtWidgets.QWidget,
    color: str = "#000000",
    blur: float = 10,
    offset: float = 0,
) -> QGraphicsDropShadowEffect:
    """Apply shadows to a widget.

    Args:
        parent (QWidget, optional): Parent object.
        shadow_object (QWidget): Object to receive shadows.
        color (str, optional): Color of the shadows. Defaults to `#000000`.
        blur (float, optional): Blur level of the shadows. Defaults to `10`.
        offset (float, optional): Offset of the shadow from the
            `shadow_object`. Defaults to `0`.

    Returns:
        QGraphicsDropShadowEffect: The shadow object.

    Examples:
        >>> # Apply shadows to `self.top_toolbar` widget
        >>> add_shadows(self, self.top_toolbar, "#212121")
    """

    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(blur)
    shadow.setOffset(offset)
    shadow.setColor(color)
    shadow_object.setGraphicsEffect(shadow)
    return shadow
