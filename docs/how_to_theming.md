# :material-theme-light-dark:{.scale-in-center} Theming

fxgui uses a JSONC (JSON with comments) file to define all theme colors. You can create your own custom themes by creating a new JSONC file with your color definitions.

## Understanding the Theme Structure

The default `style.jsonc` file contains several sections:

```jsonc
{
    // Feedback colors for status messages
    "feedback": {
        "debug": { "foreground": "#26C6DA", "background": "#006064" },
        "info": { "foreground": "#7661f6", "background": "#372d75" },
        "success": { "foreground": "#8ac549", "background": "#466425" },
        "warning": { "foreground": "#ffbb33", "background": "#7b5918" },
        "error": { "foreground": "#ff4444", "background": "#7b2323" }
    },
    // DCC branding colors
    "dcc": {
        "houdini": "#ff6600",
        "maya": "#38a6cc",
        "nuke": "#fcb434"
    },
    // Theme definitions
    "themes": {
        "dark": { /* ... */ },
        "light": { /* ... */ },
        "my_custom_theme": { /* ... */ }
    }
}
```

## Theme Color Roles

Each theme must define these color roles:

| Role | Description |
|------|-------------|
| `accent_primary` | Primary accent color (buttons, links, selections) |
| `accent_secondary` | Secondary accent (hover states, gradients) |
| `surface` | Main widget background |
| `surface_alt` | Alternate backgrounds (odd rows, secondary surfaces) |
| `input` | Input fields, list backgrounds |
| `tooltip` | Tooltip background |
| `border` | Primary border color |
| `border_subtle` | Subtle/light borders |
| `border_frame` | Frame borders |
| `text` | Primary text color |
| `text_secondary` | Secondary/muted text |
| `text_disabled` | Disabled text |
| `hover` | Hover state background |
| `pressed` | Pressed/checked state background |
| `selected` | Selected item background |
| `disabled` | Disabled widget background |
| `scrollbar_bg` | Scrollbar track |
| `scrollbar_handle` | Scrollbar handle |
| `scrollbar_hover` | Scrollbar handle on hover |
| `separator` | Separator lines |
| `slider_handle` | Slider handle color |
| `slider_hover` | Slider handle on hover |
| `icon` | Icon tint color |

## Creating Your Custom Theme

1. **Copy the default file** as a starting point:

```python
from pathlib import Path
from fxgui import fxconstants

# The default style.jsonc location
default_file = fxconstants.STYLES_FILE
print(f"Default file: {default_file}")

# Copy it to your preferred location
import shutil
custom_file = Path.home() / ".fxgui" / "my_theme.jsonc"
custom_file.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(default_file, custom_file)
```

2. **Add your theme** to the `themes` section:

```jsonc
{
    "themes": {
        "dark": { /* ... existing ... */ },
        "light": { /* ... existing ... */ },
        "monokai": {
            "accent_primary": "#A6E22E",
            "accent_secondary": "#66D9EF",
            "surface": "#272822",
            "surface_alt": "#1e1f1c",
            "input": "#1a1a17",
            "tooltip": "#3e3d32",
            "border": "#49483e",
            "border_subtle": "#75715e",
            "border_frame": "#49483e",
            "text": "#f8f8f2",
            "text_secondary": "#a59f85",
            "text_disabled": "#75715e",
            "hover": "#3e3d32",
            "pressed": "#49483e",
            "selected": "#49483e",
            "disabled": "#3e3d32",
            "scrollbar_bg": "#1e1f1c",
            "scrollbar_handle": "#49483e",
            "scrollbar_hover": "#75715e",
            "separator": "#75715e",
            "slider_handle": "#f8f8f2",
            "slider_hover": "#ffffff",
            "icon": "#f8f8f2"
        }
    }
}
```

## Using Your Custom Theme

```python
from fxgui import fxstyle, fxwidgets

# Set your custom color file BEFORE creating any widgets
fxstyle.set_color_file("/path/to/my_theme.jsonc")

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

You can switch between any themes defined in your JSONC file:

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
