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
from fxgui import fxstyle

# The default style.yaml location
default_file = fxstyle.DEFAULT_COLOR_FILE
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
print(fxstyle.get_available_themes())
# ['dark', 'light', 'dracula', 'one_dark_pro', 'github_dark', 'github_light',
#  'catppuccin_mocha', 'catppuccin_latte', 'nord', 'material_dark',
#  'solarized_light', 'monokai']

# Create your application
app = fxwidgets.FXApplication()
window = fxwidgets.FXMainWindow(title="Custom Theme Demo")
window.show()

# Apply your custom theme, everywhere
fxstyle.apply_theme("monokai")

app.exec_()
```

!!! note
    `FXMainWindow` registers itself as a themed root at construction (see "Registering Themed Roots" further down), so `apply_theme()` updates it, and any other registered root, without you having to touch the window directly.

## Switching Themes at Runtime

You can switch between any themes defined in your YAML file:

```python
from fxgui import fxstyle

# Toggle between themes
current = fxstyle.get_theme()
if current == "dark":
    fxstyle.apply_theme("monokai")
else:
    fxstyle.apply_theme("dark")
```

`apply_theme(name)` is the canonical form. It updates the persisted theme, rebuilds the stylesheet, re-applies it to every registered root, refreshes icon colors, and emits `theme_changed`.

!!! warning "Deprecated"
    The old two-argument form, `apply_theme(widget, theme)`, still works: it registers `widget` as a themed root, then proceeds, but it now emits a `DeprecationWarning`. Call `apply_theme(theme)` on its own and register widgets separately with `register_themed_root()` (see below).

!!! tip
    Theme selection is automatically persisted via `fxconfig`. When the user restarts the application, their last selected theme is restored.

!!! note
    Built-in themes: `dark`, `light`, `dracula`, `one_dark_pro`, `github_dark`, `github_light`, `catppuccin_mocha`, `catppuccin_latte`, `nord`, `material_dark`, and `solarized_light`.

## Reading Theme Colors

For custom drawing or one-off styling, read colors directly instead of hardcoding hex values.

```python
from fxgui import fxstyle

colors = fxstyle.colors()
print(colors.surface)        # Current theme's main background
print(colors.accent_primary) # Current theme's primary accent
```

`fxstyle.colors()` returns the current theme as an attribute-access namespace. It's cached per theme and only rebuilt on theme switches, so it's cheap enough to call inside `paintEvent`. `fxstyle.get_theme_colors()` (a plain dict) still works, and is what `colors()` is built from; prefer `colors()` in new code.

## Registering Themed Roots

`fxstyle.register_themed_root(root)` registers a widget, or the `QApplication` itself, to receive the theme stylesheet. The current theme is applied immediately, and the same root receives every later `apply_theme()` update. Qt cascades the stylesheet to descendants, so you register the top-level widget once, not each child.

```python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
fxstyle.register_themed_root(application)
```

`fxwidgets.FXApplication` and `fxwidgets.FXMainWindow(set_stylesheet=True)` (the default) already call this on themselves, so most applications never need to call it directly.

!!! note
    Every `apply_theme()` call re-applies the stylesheet to *all* live registered roots, not just the one that triggered the switch. If you have several open `FXMainWindow` instances, they all update together.

!!! warning "DCC-embedded windows"
    Inside a DCC host (Houdini, Maya, Nuke), register the embedded window itself, never the host's `QApplication`. `FXMainWindow` does this automatically at construction, so the host application's own styling is never touched.

## Reacting to Theme Changes

`fxstyle.theme_changed` is a module-level signal (the same instance as `fxstyle.theme_manager.theme_changed`), emitted after a theme switch with the new theme's name.

```python
from fxgui import fxstyle


def _on_theme_changed(theme_name: str):
    print(f"Theme switched to {theme_name}")
    # e.g. invalidate a cached pixmap, or re-run syntax highlighting


fxstyle.theme_changed.connect(_on_theme_changed)
```

Connect to it for side effects a theme switch should trigger beyond appearance (a cached pixmap to invalidate, a highlighter to re-run). For styling itself, prefer `theme_style`, `register_widget_style()`, or reading `fxstyle.colors()`, rather than restyling by hand from a `theme_changed` slot.

## Registering Your Own Widget Styles

`fxstyle.register_widget_style(qss)` registers a QSS fragment, written once at module import time, using your widget's class name as the selector. The fragment can use `@tokens` (`@surface`, `@border`, and so on) exactly like the built-in stylesheet.

```python
from fxgui import fxstyle

fxstyle.register_widget_style("""
    MyWidget {
        background: @surface;
        border: 1px solid @border;
        border-radius: 4px;
    }
""")
```

Registered fragments are appended after the base stylesheet and re-resolved on every theme switch. If themed roots already exist when you register, the rebuilt sheet is re-applied to them immediately, so it's safe to register from a module imported after the application has started.

`fxstyle.build_stylesheet(theme=None)` builds the full sheet (base QSS plus all registered fragments, with `@tokens` resolved), and is what `register_themed_root()` / `apply_theme()` use internally. `fxstyle.load_stylesheet()` remains available for manual or DCC styling, but it does **not** include registered fragments, use `build_stylesheet()` instead if you need your widget's registered styles in a stylesheet you're applying by hand.

## Repolishing After a Property Change

If your QSS uses a Qt dynamic property in an attribute selector, for example `MyBanner[level="error"] { ... }`, Qt won't re-evaluate that selector just because you called `setProperty()`. Call `fxutils.repolish()` afterward:

```python
from fxgui import fxutils

banner.setProperty("level", "error")
fxutils.repolish(banner)
```

## The Custom Widget Contract

For a new custom widget, you don't need `FXThemeAware` to be theme-aware. The building blocks above cover almost every case:

- Put your rules in QSS with `@tokens`, using your class name as the selector, via `register_widget_style()`.
- Or read `fxstyle.colors()` inside `paintEvent()` for custom-painted widgets.
- Only connect to `fxstyle.theme_changed` if a theme switch has side effects beyond appearance.

```python
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QPainter, QColor
from fxgui import fxstyle

fxstyle.register_widget_style("""
    MyStatusChip {
        border: 1px solid @border;
        border-radius: 10px;
    }
""")


class MyStatusChip(QWidget):
    """A theme-aware widget with no FXThemeAware dependency."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(fxstyle.colors().surface))
        painter.setPen(QColor(fxstyle.colors().text))
        painter.drawText(self.rect(), Qt.AlignCenter, "Ready")
```

This is the recommended approach for new custom widgets going forward. It doesn't replace `FXThemeAware`: the mixin documented below is still fully supported, and every built-in fxgui widget still uses it. Reach for the mixin when you want its `theme_style` / `self.theme` / `_on_theme_changed()` conveniences bundled together; reach for the contract above when a plain QSS fragment or a `paintEvent` read is all your widget needs.

---

## Making Custom Widgets Theme-Aware

fxgui also provides `FXThemeAware`, a mixin that makes a widget automatically update when the user switches themes. It predates the contract above, remains fully supported, and is what every built-in fxgui widget uses today.

### Basic Usage

There are three ways to make your widgets theme-aware with the mixin, from simplest to most flexible:

#### Option 1: Declarative QSS with `theme_style` (Simplest)

Declare a `theme_style` class attribute with QSS containing `@color` tokens:

```python
from qtpy.QtWidgets import QWidget, QLabel, QVBoxLayout
from fxgui import fxstyle


class MyCustomWidget(fxstyle.FXThemeAware, QWidget):
    """A simple theme-aware widget using declarative styling."""

    # Declare your styles with @token placeholders - they auto-update!
    theme_style = """
        MyCustomWidget {
            background-color: @surface;
            border: 1px solid @border;
            border-radius: 4px;
        }
        MyCustomWidget QLabel {
            color: @text;
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.label = QLabel("Hello, World!")
        layout.addWidget(self.label)
```

That's it! The `@surface`, `@border`, and `@text` tokens are automatically replaced with the current theme colors, and the stylesheet is reapplied whenever the theme changes.

#### Option 2: Using `self.theme` in `paintEvent()` (For Custom Painting)

For widgets that use custom painting, access colors via the `self.theme` property:

```python
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QPainter, QColor
from fxgui import fxstyle


class MyPaintedWidget(fxstyle.FXThemeAware, QWidget):
    """A custom-painted theme-aware widget."""

    def paintEvent(self, event):
        painter = QPainter(self)

        # Access colors via self.theme - always returns current theme colors
        painter.fillRect(self.rect(), QColor(self.theme.surface))
        painter.setPen(QColor(self.theme.accent_primary))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        # Draw text with theme color
        painter.setPen(QColor(self.theme.text))
        painter.drawText(self.rect(), "Hello!")
```

The `FXThemeAware` mixin automatically calls `update()` on theme change, triggering a repaint with the new colors.

#### Option 3: Override `_on_theme_changed()` (For Complex Logic)

For widgets that need custom logic when the theme changes:

```python
from qtpy.QtWidgets import QWidget, QLabel, QVBoxLayout
from fxgui import fxstyle


class MyCustomWidget(fxstyle.FXThemeAware, QWidget):
    """A theme-aware widget with custom update logic."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.label = QLabel("Hello, World!")
        self.status_indicator = QWidget()
        layout.addWidget(self.label)
        layout.addWidget(self.status_indicator)

    def _on_theme_changed(self):
        """Called automatically when theme changes."""
        # Access colors via self.theme property
        self.setStyleSheet(f"""
            MyCustomWidget {{
                background-color: {self.theme.surface};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
            }}
        """)

        self.label.setStyleSheet(f"color: {self.theme.text};")

        # Custom logic - update a non-theme-aware child
        self.status_indicator.setStyleSheet(
            f"background: {self.theme.accent_primary};"
        )
```

!!! note
    You don't need to call `self.update()` - it's called automatically after `_on_theme_changed()` returns.

### Key Points

| Rule | Description |
|------|-------------|
| Inherit first | Always list `FXThemeAware` **before** the Qt class: `class MyWidget(fxstyle.FXThemeAware, QWidget)` |
| Use `self.theme` | Access colors via `self.theme.surface`, `self.theme.text`, etc. |
| Prefer `theme_style` | For simple QSS, use the declarative `theme_style` class attribute |
| Override `_on_theme_changed()` | For complex logic that runs when the theme changes |

### Using Accent Colors

For interactive elements like buttons or links, use accent colors:

```python
class MyButton(fxstyle.FXThemeAware, QWidget):
    theme_style = """
        QPushButton {
            background-color: @accent_primary;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: @accent_secondary;
        }
    """
```

Or programmatically:

```python
def _on_theme_changed(self):
    self.button.setStyleSheet(f"""
        QPushButton {{
            background-color: {self.theme.accent_primary};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {self.theme.accent_secondary};
        }}
    """)
```

### Available Color Tokens

These tokens can be used in `theme_style` (with `@` prefix) or accessed via `self.theme`:

```python
# Via self.theme property (recommended)
self.theme.surface          # Main window/dialog background
self.theme.surface_alt      # Alternate/secondary panels
self.theme.surface_sunken   # Input fields, code blocks
self.theme.tooltip          # Tooltip background

self.theme.border           # Primary borders
self.theme.border_light     # Subtle separators, dividers
self.theme.border_strong    # Emphasized borders, focus rings

self.theme.text             # Primary text
self.theme.text_muted       # Secondary/hint text
self.theme.text_disabled    # Disabled elements

self.theme.state_hover      # Hover state background
self.theme.state_pressed    # Pressed/checked background

self.theme.accent_primary   # Primary accent (buttons, links)
self.theme.accent_secondary # Secondary accent (hover states)

self.theme.scrollbar_track        # Scrollbar track
self.theme.scrollbar_thumb        # Scrollbar handle
self.theme.scrollbar_thumb_hover  # Scrollbar handle on hover
self.theme.slider_thumb           # Slider handle
self.theme.slider_thumb_hover     # Slider handle on hover
self.theme.grid                   # Table/tree gridlines
self.theme.separator              # Menu/toolbar separators
self.theme.icon                   # Icon tint color
```

In `theme_style`, use these as `@surface`, `@text`, `@accent_primary`, etc.

### Complete Example

```python
from qtpy.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from fxgui import fxstyle, fxwidgets


class FXInfoCard(fxstyle.FXThemeAware, QWidget):
    """A themed info card with title and action button."""

    # Declarative styling with @tokens
    theme_style = """
        FXInfoCard {
            background-color: @surface;
            border: 1px solid @border;
            border-radius: 8px;
        }
    """

    def __init__(self, title="Info", parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_label = QLabel(title)
        self.action_btn = QPushButton("Learn More")

        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.action_btn)

    def _on_theme_changed(self):
        # For child widgets that need programmatic styling
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.text};
                font-size: 16px;
                font-weight: bold;
            }}
        """)

        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_primary};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_secondary};
            }}
        """)


# Usage
if __name__ == "__main__":
    app = fxwidgets.FXApplication()

    card = FXInfoCard("Welcome to fxgui")
    card.resize(300, 200)
    card.show()

    # Theme changes automatically update the card
    fxstyle.apply_theme("dark")

    app.exec_()
```

---

## Legacy API (Deprecated)

!!! warning "Deprecated"
    The following API still works but is deprecated. Please migrate to the new API described above.

The old way of creating theme-aware widgets used `_apply_theme_styles()` and `fxstyle.get_theme_colors()`:

```python
from qtpy.QtWidgets import QWidget, QLabel, QVBoxLayout
from fxgui import fxstyle


class MyCustomWidget(fxstyle.FXThemeAware, QWidget):
    """Legacy theme-aware widget (deprecated)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.label = QLabel("Hello, World!")
        layout.addWidget(self.label)

    def _apply_theme_styles(self):
        """Deprecated: Use _on_theme_changed() or theme_style instead."""
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

### Migration Guide

| Old API | New API |
|---------|---------|
| `_apply_theme_styles()` | `_on_theme_changed()` or `theme_style` class attribute |
| `fxstyle.get_theme_colors()['surface']` | `self.theme.surface` |
| `fxstyle.get_accent_colors()['primary']` | `self.theme.accent_primary` |

### Why Migrate?

- **Simpler**: `theme_style` attribute requires no method override
- **Cleaner**: `self.theme.surface` is more readable than `colors['surface']`
- **Automatic repaints**: `self.update()` is called automatically after `_on_theme_changed()`
- **Less boilerplate**: No need to fetch colors dictionary in every method
