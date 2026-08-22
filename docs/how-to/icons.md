# :material-image:{.scale-in-center} Icons

## Use `fxicons`

[fxicons](../technical/fxicons.md) is a module that provides a way to use library icons in your applications. It comes with 5 libraries by default: "material", "fontawesome", "simple", "dcc", and "beacon". You can add your own libraries by using the `add_library` function.

### Basic Usage

```python
from qtpy.QtWidgets import QPushButton
from fxgui import fxicons

button = QPushButton()
button.setIcon(fxicons.get_icon("home"))
```

### Add a Custom Library

```python
from pathlib import Path
from fxgui import fxicons

# Add the houdini library
fxicons.add_library(
    library="houdini",
    pattern="{root}/{library}/{style}/{icon_name}.{extension}",
    defaults={
        "extension": "svg",
        "style": "CROWDS",
        "color": None,
        "width": 48,
        "height": 48,
    },
    root=str(Path.home() / "Pictures" / "Icons"),
)

# Set the houdini library as the default
fxicons.set_default_icon_library(library="houdini")

# Override the defaults for the houdini library
fxicons.set_icon_defaults(apply_to="houdini", color="red")

# Apply the icon to a button
button = QPushButton()
button.setIcon(fxicons.get_icon("crowd"))
```

### Specify Library Per Icon

If you don't set a new default library, the `fxicons` module will use the "material" library as default. You can also specify the library when calling the `get_icon` function:

```python
from fxgui import fxicons

icon = fxicons.get_icon("crowd", library="houdini")
```

### Global Icon Defaults

If no argument `apply_to` is given to `set_icon_defaults`, it will apply to all libraries.

```python
from fxgui import fxicons

# Set all icons to be red and 32x32
fxicons.set_icon_defaults(color="red", width=32, height=32)
```

Arguments set on the `get_icon` function will override the defaults set by `set_icon_defaults`:

```python
from fxgui import fxicons

# Set all icons to be red and 32x32
fxicons.set_icon_defaults(color="red", width=32, height=32)

# Get a blue icon
icon = fxicons.get_icon("home", color="blue")
```

### A Name the Library Does Not Carry

`get_icon` raises `FileNotFoundError` for a name no library has. When the
name comes from your own data rather than from your own code, that is an
ordinary answer rather than an exceptional one, so name a `fallback`
instead of wrapping the call:

```python
from fxgui import fxicons

# A DCC the "dcc" library carries a brand mark for gets it; anything
# else gets the general-purpose icon rather than no icon at all.
icon = fxicons.get_icon(whatever_the_tracker_said, library="dcc", fallback="apps")
```

A fallback **name** is looked up in the *default* library, not in the one
you asked for. That is deliberate: the library that just failed to carry
the name is the least likely place for the stand-in, and the
general-purpose set is where it lives. Size and colour carry over, so a
row that falls back does not change shape.

Pass a `QIcon` instead of a name to be answered with it as it is, and
`QIcon()` to ask for a blank rather than a picture of something else:

```python
icon = fxicons.get_icon(name, library="dcc", fallback=QIcon())
```

A fallback that is not in the default library either still raises, since
a second silent stand-in would hide a mistake in your code rather than
in your data.

### Superpose Icons

You can superpose as many icons as you want, from background to foreground:

```python
from fxgui import fxicons

icon_a = fxicons.get_icon("home")
icon_b = fxicons.get_icon("add")
icon_c = fxicons.get_icon("settings", color="red")
icon = fxicons.superpose_icons(icon_a, icon_b, icon_c)
```

## Theme-Aware Icons with `set_icon`

Icons automatically update their colors when toggling between light and dark themes. Use `fxicons.set_icon()` to register any widget for automatic icon refresh:

```python
from qtpy.QtWidgets import QPushButton, QToolButton
from fxgui import fxicons

# Create a button with a theme-aware icon
button = QPushButton("Save")
fxicons.set_icon(button, "save")

# Works with any widget that has setIcon()
tool_btn = QToolButton()
fxicons.set_icon(tool_btn, "settings")
```

When the theme changes, all widgets registered via `set_icon()` automatically have their icons refreshed to match the new theme colors.

### Using `set_icon` with Actions

For menu and toolbar actions, use the `icon_name` parameter in `fxutils.create_action()`:

```python
from fxgui import fxutils

# The action is automatically registered for icon refresh
save_action = fxutils.create_action(
    parent,
    "Save",
    trigger=save_function,
    icon_name="save",
)
```

!!! tip
    This approach is used internally by widgets like `FXCollapsibleWidget`, `FXOutputLogWidget`, and `FXPasswordLineEdit`, so their icons update automatically on theme change.

## QtAwesome (Optional)

[QtAwesome](https://qtawesome.readthedocs.io/en/latest/index.html) is no longer bundled with fxgui, but you can install it separately if you want its features like animated icons. First, install it:

```bash
pip install qtawesome
```

Then you can use it like this:

```python
import qtawesome as qta
from qtpy.QtWidgets import QPushButton
from fxgui import fxwidgets


application = fxwidgets.FXApplication()
window = fxwidgets.FXMainWindow(title="QtAwesome Example")
button = QPushButton("Network")
button.setIcon(qta.icon("mdi.access-point-network"))
window.setCentralWidget(button)
window.show()
application.exec_()
```

And the very cool features from this package, such as animated icons:

```python
import qtawesome as qta
from qtpy.QtWidgets import QPushButton
from fxgui import fxwidgets


application = fxwidgets.FXApplication()
window = fxwidgets.FXMainWindow(title="Animated Icon")
button = QPushButton("Loading...")
animation = qta.Spin(button)
spin_icon = qta.icon("fa5s.spinner", color="red", animation=animation)
button.setIcon(spin_icon)
window.setCentralWidget(button)
window.show()
application.exec_()
```

!!! warning
    The `QtAwesome` package doesn't work properly within Houdini, so you should use the `fxicons` module instead.
