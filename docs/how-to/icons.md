# :material-image: Icons

## Use `fxicons`

[fxicons](../technical/fxgui/fxicons.md) is a module that provides a way to use library icons in your applications. It comes with 5 libraries by default: "material", "fontawesome", "simple", "dcc", and "beacon". You can add your own libraries by using the `add_library` function.

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
from qtpy.QtWidgets import QPushButton
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

# Ask for an icon of that library by name
button = QPushButton()
button.setIcon(fxicons.get_icon("crowd", library="houdini"))
```

The `defaults` you pass are that library's size, colour, style and
extension: a `get_icon` call that leaves one out takes it from there.

### Name the library, the size and the colour per call

Without `library`, `get_icon` looks in "material". Every other default can
be overridden on the call itself:

```python
from fxgui import fxicons

icon = fxicons.get_icon("houdini", library="dcc")
small_red = fxicons.get_icon("home", width=32, height=32, color="red")
```

### A Name the Library Does Not Carry

`get_icon` raises `FileNotFoundError` for a name no library has. When the
name comes from your own data rather than from your own code, that is an
ordinary answer rather than an exceptional one, so name a `fallback`
instead of wrapping the call:

```python
from fxgui import fxicons

tool = "my_inhouse_tool"  # a name read from your tracker

# A DCC the "dcc" library carries a brand mark for gets it; anything
# else gets the general-purpose icon rather than no icon at all.
icon = fxicons.get_icon(tool, library="dcc", fallback="apps")
```

A fallback **name** is looked up in the *default* library, not in the one
you asked for. That is deliberate: the library that just failed to carry
the name is the least likely place for the stand-in, and the
general-purpose set is where it lives. Size and colour carry over, so a
row that falls back does not change shape.

Pass a `QIcon` instead of a name to be answered with it as it is, and
`QIcon()` to ask for a blank rather than a picture of something else:

```python
from qtpy.QtGui import QIcon
from fxgui import fxicons

icon = fxicons.get_icon("my_inhouse_tool", library="dcc", fallback=QIcon())
```

A fallback that is not in the default library either still raises, since
a second silent stand-in would hide a mistake in your code rather than
in your data.

### Badge an icon

`badged` returns a copy of an icon with a filled dot at its lower right,
for work in flight, such as a tray icon while a job runs. The dot is a
theme token or a colour:

```python
from fxgui import fxicons

busy = fxicons.badged(fxicons.get_icon("cloud"), color="accent_primary")
```

## Icons Follow the Theme When Drawn

An fxgui icon is not a picture baked once. It names its colours, and it
looks them up each time Qt draws it, so a theme switch reaches every icon
with no code of yours.

```python
from qtpy.QtWidgets import QPushButton
from fxgui import fxicons

button = QPushButton("Save")
fxicons.set_icon(button, "save")
```

`set_icon(widget, name)` works on anything with `setIcon()`: buttons,
actions, `FXIconLabel`. It is `widget.setIcon(get_icon(name))`.

### Name the colour by token

`color` is the icon's colour in its resting state. Give it a theme token
name (any key of `fxstyle.colors()`, such as `"text_muted"` or
`"feedback_error_foreground"`) and it follows the theme. Give it a colour
(`"#ff0000"`, `"red"`) and it keeps that colour in every theme.

```python
from fxgui import fxicons, fxwidgets

indicator = fxwidgets.FXIconLabel()

# Follows the theme: the error colour of whichever theme is on.
fxicons.set_icon(indicator, "error", color="feedback_error_foreground")

# Stays red in every theme.
fxicons.set_icon(indicator, "error", color="#ff0000")
```

### The other states

Qt draws an icon in one of four modes. `inks` names the colour of the
three that are not the resting one, each a token or a colour:

| Mode | When Qt uses it | Default ink |
|------|-----------------|-------------|
| `color` (Normal) | At rest | The library's default, `"icon"` for material, fontawesome and simple |
| `"active"` | A hovered tool button or toolbar button, a focused push button, a menu's highlighted row | The resting ink; `"icon_on_accent_primary"` on a menu's highlighted row, which is the accent |
| `"selected"` | A selected item-view row | `"icon_on_accent_primary"` |
| `"disabled"` | A disabled widget | `"text_disabled"` |

```python
from fxgui import fxicons

icon = fxicons.get_icon(
    "send",
    color="icon_on_accent_primary",
    inks={"active": "icon_on_accent_secondary"},
)
```

Any other key in `inks` raises `ValueError`. Name an `"active"` ink only
for a button that hovers on a coloured fill, as the send button above
does: a hovered button sits on the grey hover fill, so by default its
icon keeps the resting ink.

A full-colour library (`dcc`, or one added with `recolor=False`) keeps its
own pixels in every mode, whatever colour you ask for.

Where icons share one ink, as the rows of a command palette do, ask for a
DCC's one-colour mark: its name plus `_mark`, such as `houdini_mark`. It is
drawn in the theme's icon ink, like a material icon. Marks exist for
Houdini, Maya, Nuke, Blender, Cinema 4D, DaVinci Resolve, Unreal Engine,
After Effects, Photoshop and Substance Painter.

```python
icon = fxicons.get_icon("houdini_mark", library="dcc")
```

An `FXCommand` names one as `dcc:houdini_mark`.

### An icon in a label

A `QLabel` pixmap is baked once. `FXIconLabel` holds a `QIcon` instead
and draws it when painted, so it follows the theme too. A disabled label
draws the icon's Disabled mode.

```python
from fxgui import fxicons, fxwidgets

label = fxwidgets.FXIconLabel(size=18)
fxicons.set_icon(label, "info", color="feedback_info_foreground")
```

### `get_pixmap` is a snapshot

`fxicons.get_pixmap()` returns a pixmap drawn now. A token colour is read
once, at the call. Use it for something you redraw yourself; use
`get_icon` or `set_icon` for anything that should follow the theme.

### Using `set_icon` with Actions

For menu and toolbar actions, use the `icon_name` parameter in `fxutils.create_action()`:

```python
from fxgui import fxutils, fxwidgets

window = fxwidgets.FXMainWindow(title="Editor")
save_action = fxutils.create_action(
    window,
    "Save",
    trigger=lambda: print("saved"),
    icon_name="save",
)
```

## QtAwesome (Optional)

[QtAwesome](https://qtawesome.readthedocs.io/en/latest/index.html) is not bundled with fxgui; install it separately for features such as animated icons. First, install it:

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
application.exec()
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
application.exec()
```

!!! warning
    The `QtAwesome` package doesn't work properly within Houdini, so you should use the `fxicons` module instead.
