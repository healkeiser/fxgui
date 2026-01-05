# :material-theme-light-dark:{.scale-in-center} Theming

fxgui uses a YAML configuration file to define all theme colors. YAML supports **anchors and aliases** for theme inheritance, allowing you to create new themes that extend existing ones and override only specific colors.

## Understanding the Theme Structure

The default `style.yaml` file contains several sections:

```yaml
# Feedback colors for status messages
feedback:
  debug:
    foreground: "#26C6DA"
    background: "#006064"
  info:
    foreground: "#7661f6"
    background: "#372d75"
  success:
    foreground: "#8ac549"
    background: "#466425"
  warning:
    foreground: "#ffbb33"
    background: "#7b5918"
  error:
    foreground: "#ff4444"
    background: "#7b2323"

# DCC branding colors
dcc:
  houdini: "#ff6600"
  maya: "#38a6cc"
  nuke: "#fcb434"

# Theme definitions with inheritance
themes:
  dark: &dark  # Define anchor for inheritance
    accent_primary: "#2196F3"
    # ... all colors ...

  dracula:
    <<: *dark  # Inherit from dark theme
    accent_primary: "#bd93f9"  # Override specific colors
```

## Theme Color Roles - Complete Reference

Each theme defines semantic color roles. All names are designed to clearly indicate their purpose:

### Accent Colors

| Role | Purpose |
|------|---------|
| `accent_primary` | Primary interactive color - hover borders, selections, progress/slider gradient end, menu selections |
| `accent_secondary` | Secondary interactive color - gradient starts, item hover backgrounds, menu pressed states |

### Surface Colors (Backgrounds)

| Role | Purpose |
|------|---------|
| `surface` | Main widget/window backgrounds, buttons, selected tabs, toolbar |
| `surface_alt` | Alternate surface - odd rows in lists/tables, secondary panels |
| `surface_sunken` | Recessed/inset areas - input fields, lists, menus, status bar, slider tracks |
| `tooltip` | Tooltip popup backgrounds |

### Border Colors

| Role | Purpose |
|------|---------|
| `border` | Standard borders - inputs, containers, menus, separators |
| `border_light` | Subtle borders - tooltips, button borders, tab borders |
| `border_strong` | Emphasized borders - frames, separator lines |

### Text Colors

| Role | Purpose |
|------|---------|
| `text` | Primary text for all widgets |
| `text_muted` | De-emphasized text - inactive tabs, placeholders, secondary labels |
| `text_disabled` | Disabled widget text |
| `text_on_accent_primary` | *(Optional)* Text on `accent_primary` backgrounds (e.g., selected items). Auto-computed if omitted |
| `text_on_accent_secondary` | *(Optional)* Text on `accent_secondary` backgrounds (e.g., hovered items). Auto-computed if omitted |

### Interactive State Colors

| Role | Purpose |
|------|---------|
| `state_hover` | Hover state backgrounds - buttons, dock widgets |
| `state_pressed` | Pressed/checked/active backgrounds - buttons, tabs, tool buttons |

### Scrollbar Colors

| Role | Purpose |
|------|---------|
| `scrollbar_track` | Track/gutter background, also used for menubar/statusbar borders |
| `scrollbar_thumb` | Draggable thumb, also used for checked header backgrounds |
| `scrollbar_thumb_hover` | Thumb hover state |

### Layout Colors

| Role | Purpose |
|------|---------|
| `grid` | Table gridlines, header section borders |
| `separator` | Separator/splitter hover backgrounds |

### Slider Colors

| Role | Purpose |
|------|---------|
| `slider_thumb` | Slider handle/knob color |
| `slider_thumb_hover` | Slider handle hover and pressed states |

### Icon Color

| Role | Purpose |
|------|---------|
| `icon` | Tint color for monochrome icons via `fxicons.get_icon()` and standard Qt icons |

## Feedback Colors Reference

Used by `FXNotificationBanner`, `FXLogWidget`, and other status/feedback widgets:

| Level | Property | Usage |
|-------|----------|-------|
| `debug` | `foreground` | Text/icon color for debug messages |
| `debug` | `background` | Background color for debug notifications |
| `info` | `foreground` | Text/icon color for info messages |
| `info` | `background` | Background color for info notifications |
| `success` | `foreground` | Text/icon color for success messages |
| `success` | `background` | Background color for success notifications |
| `warning` | `foreground` | Text/icon color for warning messages |
| `warning` | `background` | Background color for warning notifications |
| `error` | `foreground` | Text/icon color for error messages |
| `error` | `background` | Background color for error notifications |

## DCC Colors Reference

Used by DCC-specific widgets and branding elements:

| Key | Software | Default Color |
|-----|----------|---------------|
| `houdini` | SideFX Houdini | `#ff6600` (orange) |
| `maya` | Autodesk Maya | `#38a6cc` (teal/cyan) |
| `nuke` | Foundry Nuke | `#fcb434` (yellow/gold) |
| `megascans` | Quixel Megascans | `#8ecd4f` (green) |
| `bridge` | Quixel Bridge | `#1aa9f3` (blue) |

## Creating Your Custom Theme

1. **Copy the default file** as a starting point:

```python
from pathlib import Path
from fxgui import fxconstants

# The default style.yaml location
default_file = fxconstants.STYLES_FILE
print(f"Default file: {default_file}")

# Copy it to your preferred location
import shutil
custom_file = Path.home() / ".fxgui" / "my_theme.yaml"
custom_file.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(default_file, custom_file)
```

2. **Add your theme** using YAML inheritance:

```yaml
themes:
  # Base dark theme with anchor
  dark: &dark
    accent_primary: "#2196F3"
    surface: "#302f2f"
    # ... existing dark colors ...

  # Your custom theme inheriting from dark
  monokai:
    <<: *dark  # Inherit ALL colors from dark theme

    # Override only the colors you want to change
    accent_primary: "#A6E22E"
    accent_secondary: "#66D9EF"

    surface: "#272822"
    surface_alt: "#1e1f1c"
    surface_sunken: "#1a1a17"
    tooltip: "#3e3d32"

    border: "#49483e"
    border_light: "#75715e"
    border_strong: "#49483e"

    text: "#f8f8f2"
    text_muted: "#a59f85"
    text_disabled: "#75715e"

    state_hover: "#3e3d32"
    state_pressed: "#49483e"

    scrollbar_track: "#1e1f1c"
    scrollbar_thumb: "#49483e"
    scrollbar_thumb_hover: "#75715e"

    grid: "#49483e"
    separator: "#75715e"

    slider_thumb: "#f8f8f2"
    slider_thumb_hover: "#ffffff"

    icon: "#f8f8f2"
```

!!! tip "YAML Inheritance"
    Use `&anchor_name` to define a base theme, then `<<: *anchor_name` to inherit from it.
    Any colors you specify after the inheritance line will override the inherited values.

## Using Your Custom Theme

```python
from fxgui import fxstyle, fxwidgets

# Set your custom color file BEFORE creating any widgets
fxstyle.set_color_file("/path/to/my_theme.yaml")

# Check available themes (includes your custom ones)
print(fxstyle.get_available_themes())  # ['dark', 'light', 'monokai']

# Create your application
app = fxwidgets.FXApplication()
window = fxwidgets.FXMainWindow(title="Custom Theme Demo")
window.show()

# Apply your custom theme
fxstyle.apply_theme(window, "monokai")

app.exec_()
```

## Switching Themes at Runtime

You can switch between any themes defined in your YAML file:

```python
from fxgui import fxstyle

# Toggle between themes
current = fxstyle.get_theme()
if current == "dark":
    fxstyle.apply_theme(window, "monokai")
else:
    fxstyle.apply_theme(window, "dark")
```

!!! tip
    Theme selection is automatically persisted via `fxconfig`. When the user restarts the application, their last selected theme is restored.

!!! note
    Built-in themes include: `dark`, `light`, `dracula`, and `one_dark_pro`.

---

## Making Custom Widgets Theme-Aware

When you create your own widgets, you'll want them to automatically update when the user switches themes. fxgui provides `FXThemeAware`, a mixin that handles this for you.

### Basic Usage

```python
from qtpy.QtWidgets import QWidget, QLabel, QVBoxLayout
from fxgui import fxstyle


class MyCustomWidget(fxstyle.FXThemeAware, QWidget):
    """A simple theme-aware widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.label = QLabel("Hello, World!")
        layout.addWidget(self.label)

    def _apply_theme_styles(self):
        """Called automatically when theme changes."""
        colors = fxstyle.get_theme_colors()

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
            }}
            QLabel {{
                color: {colors['text']};
            }}
        """)
```

That's it! Your widget will now:

- Apply styles when first created
- Automatically update when `fxstyle.apply_theme()` is called
- React to Qt palette changes

### Key Points

| Rule | Description |
|------|-------------|
| Inherit first | Always list `FXThemeAware` **before** the Qt class: `class MyWidget(fxstyle.FXThemeAware, QWidget)` |
| Override `_apply_theme_styles()` | This method is called automatically - just define your styling logic here |
| Fetch colors dynamically | Always call `fxstyle.get_theme_colors()` inside `_apply_theme_styles()`, never cache colors in `__init__` |

### Using Accent Colors

For interactive elements like buttons or links, use accent colors:

```python
def _apply_theme_styles(self):
    colors = fxstyle.get_theme_colors()
    accents = fxstyle.get_accent_colors()

    self.button.setStyleSheet(f"""
        QPushButton {{
            background-color: {accents['primary']};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {accents['secondary']};
        }}
    """)
```

### Custom-Painted Widgets

For widgets that use `paintEvent()` instead of stylesheets, fetch colors in the paint method:

```python
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QPainter, QColor
from fxgui import fxstyle


class MyPaintedWidget(fxstyle.FXThemeAware, QWidget):
    """A custom-painted theme-aware widget."""

    def paintEvent(self, event):
        painter = QPainter(self)

        # Fetch colors dynamically each paint
        colors = fxstyle.get_theme_colors()
        accents = fxstyle.get_accent_colors()

        # Use the colors
        painter.fillRect(self.rect(), QColor(colors['surface']))
        painter.setPen(QColor(accents['primary']))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
```

The `FXThemeAware` mixin automatically calls `update()` on theme change, triggering a repaint.

### Available Color Keys

Use `fxstyle.get_theme_colors()` for these:

```python
colors = fxstyle.get_theme_colors()

# Surface colors
colors['surface']        # Main window/dialog background
colors['surface_alt']    # Alternate/secondary panels
colors['surface_sunken'] # Input fields, code blocks
colors['tooltip']        # Tooltip background

# Border colors
colors['border']         # Primary borders
colors['border_light']   # Subtle separators, dividers
colors['border_strong']  # Emphasized borders, focus rings

# Text colors
colors['text']           # Primary text
colors['text_muted']     # Secondary/hint text
colors['text_disabled']  # Disabled elements

# Interactive states
colors['state_hover']    # Hover state background
colors['state_pressed']  # Pressed/checked background

# Component-specific
colors['scrollbar_track']       # Scrollbar track
colors['scrollbar_thumb']       # Scrollbar handle
colors['scrollbar_thumb_hover'] # Scrollbar handle on hover
colors['slider_thumb']          # Slider handle
colors['slider_thumb_hover']    # Slider handle on hover
colors['grid']                  # Table/tree gridlines
colors['separator']             # Menu/toolbar separators
colors['icon']                  # Icon tint color
```

Use `fxstyle.get_accent_colors()` for these:

```python
accents = fxstyle.get_accent_colors()
accents['primary']       # Primary accent (buttons, links)
accents['secondary']     # Secondary accent (hover states)
```

### Complete Example

```python
from qtpy.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from fxgui import fxstyle, fxwidgets


class FXInfoCard(fxstyle.FXThemeAware, QWidget):
    """A themed info card with title and action button."""

    def __init__(self, title="Info", parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_label = QLabel(title)
        self.action_btn = QPushButton("Learn More")

        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.action_btn)

    def _apply_theme_styles(self):
        colors = fxstyle.get_theme_colors()
        accents = fxstyle.get_accent_colors()

        # Card container
        self.setStyleSheet(f"""
            FXInfoCard {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
        """)

        # Title
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                font-size: 16px;
                font-weight: bold;
            }}
        """)

        # Button
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accents['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {accents['secondary']};
            }}
        """)


# Usage
if __name__ == "__main__":
    app = fxwidgets.FXApplication()

    card = FXInfoCard("Welcome to fxgui")
    card.resize(300, 200)
    card.show()

    # Theme changes automatically update the card
    fxstyle.apply_theme(card, "dark")

    app.exec_()
```
