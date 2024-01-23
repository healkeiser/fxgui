# Third-party
from PySide2 import *
from PySide2 import QtWidgets
from PySide2.QtGui import QPalette, QColor


###### CODE ####################################################################


class VFXApplication(QtWidgets.QApplication):
    def __init__(self):
        super().__init__()

        self._set_application_style()

    def _set_application_style(self):
        """Set the "Fusion" style in a dark theme."""

        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColor("white"))
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, QColor("white"))
        dark_palette.setColor(QPalette.Text, QColor("white"))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor("white"))
        dark_palette.setColor(QPalette.BrightText, QColor("red"))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("darkGray"))
        dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("darkGray"))
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor("darkGray"))
        dark_palette.setColor(QPalette.Disabled, QPalette.Light, QColor(53, 53, 53))
        self.setPalette(dark_palette)
        self.setStyle("Fusion")
