#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""_summary_"""

# Third-party
from PySide2.QtWidgets import QGraphicsDropShadowEffect

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


def add_shadows(parent, shadow_object, color="#1a1a1a", blur=10, offset=0):
    """Apply shadows on chosen object.

    Args:
        parent (Qt.QWidget): Parent object.
        shadow_object (Qt.QWidget): Object to receive shadows.
        color (str, optional): Color of the shadows. Defaults to "#000000".
        blur (float, optional): Blur level of the shadows. Defaults to 10.
        offset (float, optional): Offset of the shadow from the
            `shadow_object`. Defaults to 0.

    Examples:
        >>> import shadows
        >>> shadows.add_shadows(self, self.top_toolbar, "#212121")
    """

    if parent is not None:
        shadow = QGraphicsDropShadowEffect(parent)
    else:
        shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(offset)
    shadow.setColor(color)
    shadow_object.setGraphicsEffect(shadow)
