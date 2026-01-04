# :material-widgets:{.scale-in-center} Widgets

## Subclass the `FXMainWindow`

You can subclass any widgets in the `fxwidgets` module. Here's a practical example with `FXMainWindow`:

``` python
# Third-party
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton

# Internal
from fxgui import fxwidgets, fxicons


class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.add_layout()
        self.add_buttons()

    def add_layout(self):
        """Adds a vertical layout to the main layout of the widget."""

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

    def add_buttons(self):
        """Adds buttons to the main layout of the widget."""

        # Use fxicons for theme-aware icons
        home_button = QPushButton("Home")
        fxicons.set_icon(home_button, "home")

        settings_button = QPushButton("Settings")
        fxicons.set_icon(settings_button, "settings")

        self.main_layout.addWidget(home_button)
        self.main_layout.addWidget(settings_button)
        self.main_layout.addStretch()


class MyWindow(fxwidgets.FXMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.toolbar.hide()
        self.setCentralWidget(MyWidget(parent=self))
        self.adjustSize()


application = fxwidgets.FXApplication()
window = MyWindow()
window.setWindowTitle("Subclassed FXMainWindow")
window.show()
application.exec_()
```

## Available Widgets

The [fxwidgets](fxwidgets.md) module provides many pre-styled widgets:

| Widget | Description |
|--------|-------------|
| `FXApplication` | Application with automatic theming and style |
| `FXMainWindow` | Main window with toolbar, status bar, and theme toggle |
| `FXWidget` | Base widget with optional UI file loading |
| `FXSplashScreen` | Customizable splash screen |
| `FXCollapsibleWidget` | Expandable/collapsible container |
| `FXDialog` | Styled dialog base class |
| `FXMessageBox` | Themed message boxes |
| `FXPasswordLineEdit` | Password input with visibility toggle |
| `FXOutputLogWidget` | Log display with level filtering |
| `FXScrollArea` | Smooth-scrolling scroll area |
| `FXSystemTrayIcon` | System tray icon with menu |

!!! tip
    All widgets automatically inherit the current theme and update when the theme changes.
