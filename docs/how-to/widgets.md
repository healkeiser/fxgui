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

The [fxwidgets](../technical/fxwidgets/index.md) module provides many pre-styled widgets:

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
| `FXTooltip` | Widget-hosting tooltip, for what native tooltips cannot do |
| `FXWidget` | Base widget with optional UI file loading |

!!! tip
    All widgets automatically inherit the current theme and update when the theme changes.

## Tooltips

`apply_tip` is the everyday path. It formats a small HTML string and hands it to Qt's own `setToolTip`, plus a markup-free status tip for the window's status bar:

``` python
# Internal
from fxgui.fxwidgets import apply_tip

apply_tip(
    save_button,
    "Save",
    "Write the current scene to disk, overwriting the last version",
    "Ctrl+S",
)
```

The title renders in the theme's primary text, the body dimmed, and the shortcut sits right-aligned as a keycap. Colors are read from the active theme on every call, so tooltips follow a theme switch and a studio's custom theme with no extra wiring. Every string is HTML-escaped, so a path holding `&` or `<` reaches the user as text.

Two lower-level helpers are exported alongside it: `tip()` returns the HTML if you need to set it yourself, and `keycap()` renders one shortcut as a key (through `QKeySequence`, so a Mac shows the platform glyphs rather than the literal "Ctrl").

Reach for [`FXTooltip`](../technical/fxwidgets/index.md) instead when a native tooltip cannot do the job:

- hosting live widgets (icons, images, action buttons)
- staying up while the pointer is over the tooltip itself
- persistent or programmatic show/hide
- arrow-anchored placement relative to a specific widget

### Opting in to FXTooltipManager

`FXTooltipManager` installs an application-wide event filter that replaces *every* tooltip with an `FXTooltip`. It is opt-in:

``` python
window = fxwidgets.FXMainWindow(rich_tooltips=True)
```

!!! warning "Changed in 12.0.0"
    Constructing an `FXMainWindow` under an `FXApplication` used to install the manager automatically. It no longer does, so tooltips are Qt's own unless you pass `rich_tooltips=True`. If your application relied on the manager without asking for it, you lose the following until you opt in:

    - **Tooltips that survive the pointer.** The manager's tooltips are persistent and hide on a delay, so a user can move onto one to finish reading. Native tooltips vanish on the first mouse move.
    - **Automatic item-view tooltips.** With the manager, hovering a row in any item view builds a tooltip from `FXThumbnailDelegate` roles: a 200px thumbnail preview, `name (type)`, and the description. Native tooltips show `Qt.ToolTipRole` only, and nothing sets it for you.
    - **Configurable delays.** `FXTooltipManager.install(show_delay=..., hide_delay=...)` controls appearance timing application-wide. Native tooltips use the platform style's delay, which the application cannot override per widget.
    - **The arrow and anchored placement.** Manager tooltips are positioned against the widget or item rectangle with an arrow pointing at it. Native tooltips appear at the cursor.
    - **Icons and images inside a tooltip**, fade animations, and the drop shadow.
    - **`set_tooltip()` return value.** With the manager it returns `None` and stores rich fields as dynamic properties; without it, it falls back to creating a per-widget `FXTooltip` and returns that instance. The tooltip still renders; only the return value and the delay source change.

    Nothing was removed: `FXTooltip`, `FXTooltipManager` and `set_tooltip` behave exactly as before once `rich_tooltips=True`.
