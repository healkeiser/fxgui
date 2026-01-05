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

## Running Widget Examples

Every widget in the `fxwidgets` module includes a standalone example that demonstrates its usage. Set the `DEVELOPER_MODE` environment variable to `1` to enable examples:

```bash
# Set the environment variable first
set DEVELOPER_MODE=1  # Windows
export DEVELOPER_MODE=1  # Linux/macOS

# Run any widget file directly
python -m fxgui.fxwidgets._breadcrumb
python -m fxgui.fxwidgets._accordion
python -m fxgui.fxwidgets._collapsible
python -m fxgui.fxwidgets._range_slider
# ... and more
```

!!! tip "Explore Widgets Interactively"
    This is a great way to explore the available widgets and see how they behave before integrating them into your application.

## Available Widgets

The [fxwidgets](../technical/widgets/index.md) module provides many pre-styled widgets:

| Widget | Description |
|--------|-------------|
| `FXAccordion` | Accordion container with expandable sections |
| `FXApplication` | Application with automatic theming and style |
| `FXBreadcrumb` | Clickable breadcrumb trail for hierarchical navigation |
| `FXCollapsibleWidget` | Expandable/collapsible container |
| `FXColorLabelDelegate` | Delegate for color label rendering in views |
| `FXElidedLabel` | Label with automatic text elision |
| `FXFilePathWidget` | File/folder path input with browse button |
| `FXFloatingDialog` | Styled floating dialog |
| `FXIconLineEdit` | Line edit with icon support |
| `FXLoadingSpinner` | Animated loading spinner |
| `FXLoadingOverlay` | Loading overlay for widgets |
| `FXMainWindow` | Main window with toolbar, status bar, and theme toggle |
| `FXNotificationBanner` | Notification banner for messages |
| `FXOutputLogWidget` | Log display with level filtering |
| `FXPasswordLineEdit` | Password input with visibility toggle |
| `FXProgressCard` | Progress indicator card |
| `FXRangeSlider` | Dual-handle range slider |
| `FXRatingWidget` | Star rating input widget |
| `FXResizedScrollArea` | Smooth-scrolling scroll area |
| `FXSearchBar` | Search input with filtering |
| `FXSplashScreen` | Customizable splash screen |
| `FXStatusBar` | Themed status bar |
| `FXSystemTray` | System tray icon with menu |
| `FXTagInput` | Tag/chip input widget |
| `FXThumbnailDelegate` | Delegate for thumbnail rendering in views |
| `FXTimelineSlider` | Timeline slider for media/animation |
| `FXToggleSwitch` | iOS-style toggle switch |
| `FXTooltip` | Custom styled tooltips |
| `FXWidget` | Base widget with optional UI file loading |

!!! tip
    All widgets automatically inherit the current theme and update when the theme changes.
