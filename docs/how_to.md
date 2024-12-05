# :material-book:{.scale-in-center} How-to

## Style an Existing Application

In the case where you already have made some custom applications, and don't want to be bothered by subclassing the widgets inside the [fxwidgets](fxwidgets.md) module but still want all applications to look and feel the same, you can call the `fxstyle.load_stylesheet()` function and apply the returned stylesheet to your current application/widget.

```python
from fxgui import fxstyle

application = QApplication()
application.setStyleSheet(fxstyle.load_stylesheet())
```

```python
from fxgui import fxstyle

window = QMainWindow()
window.setStyleSheet(fxstyle.load_stylesheet())
```

!!! note
    You can set this stylesheet on a `QMainWindow`, `QWidget`, etc.

!!! note
    You can pass extra arguments to the [load_stylesheet()](fxstyle.md) function.

## Subclass the `FXMainWindow`

You can subclass any widgets in the `fxwidgets` module. Here's a practical example with `FXMainWindow`:

``` python
# Third-party
import qtawesome as qta
from qtpy.QtWidgets import *
from qtpy.QtUiTools import *
from qtpy.QtCore import *
from qtpy.QtGui import *

# Internal
from fxgui import fxwidgets, fxutils, fxdcc, fxstyle


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

        pulse_button = QPushButton("Pulse Button")
        pulse_animation = qta.Pulse(pulse_button)
        pulse_icon = qta.icon(
            "fa.spinner", color="#b4b4b4", animation=pulse_animation
        )
        pulse_button.setIcon(pulse_icon)

        spin_button = QPushButton("Spin Button")
        spin_animation = qta.Spin(spin_button)
        spin_icon = qta.icon(
            "fa5s.spinner", color="#b4b4b4", animation=spin_animation
        )
        spin_button.setIcon(spin_icon)

        self.main_layout.addWidget(pulse_button)
        self.main_layout.addWidget(spin_button)
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

## Apply the Custom Google Material Icons

You can find a `QProxyStyle` subclass in [fxstyle](fxstyle.md), called `FXProxyStyle`. When used on a `QApplication` instance, it allows you to switch the defaults icons provided by `Qt` for Google Material icons.

``` python
from fxgui import fxstyle

application = QApplication()
application.setStyle(fxstyle.FXProxyStyle())
```

!!! tip
    The `FXApplication` class found inside [fxwidgets](fxwidgets.md) already applies this custom style.


![Sreenshot](docs/images/screenshot_built_in_icons.png)

You can now use the icons by doing:

```python
from qtpy import QStyle
from fxgui import fxwidgets


application = fxwidgets.FXApplication()
window = fxwidgets.FXWindow(ui_file="path/to/ui/file.ui")
style = window.style()
window.ui.button_critical.setIcon(style.standardIcon(QStyle.SP_MessageBoxCritical))
window.show()
application.exec_()
```

!!! note
    By default, the `FXApplication` found inside [fxwidgets](fxwidgets.md) already applies this custom style.

!!! warning
    Applying the `FXProxyStyle` is only allowed on a `QApplication` instance! So if you're instantiating a `FXMainWindow` inside a parent DCC, **do not** set the style on it.

## Use `fxicons`

[fxicons](fxicons.md) is a module that provides a way to use library icons in your applications. It comes with 4 libraries by default: "material", "fontawesome", "dcc", and "beacon". You can add your own libraries by using the `add_library` function. You can use it like this:

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

If you don't set a new default library, the `fxicons` module will use the "material" library as default. You can also precise the library you want to use when calling the `get_icon` function:

```python
from fxgui import fxicons

icon = fxicons.get_icon("crowd", library="houdini")
```

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

You can also superpose as many icons as you want, from backround to foreground:

```python
from fxgui import fxicons

icon_a = fxicons.get_icon("home")
icon_b = fxicons.get_icon("add")
icon_c = fxicons.get_icon("settings", color="red")
icon = fxicons.superpose_icons(icon_a, icon_b, icon_c)
```

## QtAwesome

`fxgui` comes bundled with [QtAwesome](https://qtawesome.readthedocs.io/en/latest/index.html), so you can use something like:

```python
import qtawesome as qta
from fxgui import fxwidgets


application = fxwidgets.FXApplication()
window = fxwidgets.FXWindow(ui_file="path/to/ui/file.ui")
window.ui.button_critical.setIcon(qta.icon("mdi.access-point-network"))
window.show()
application.exec_()
```

And the very cool features from this package, such as animated icons:

```python
import qtawesome as qta
from fxgui import fxwidgets


application = fxwidgets.FXApplication()
window = fxwidgets.FXWindow(ui_file="path/to/ui/file.ui")
button_ctitical = window.ui.button_critical
animation = qta.Spin(button_ctitical)
spin_icon = qta.icon("fa5s.spinner", color="red", animation=animation)
button_ctitical.setIcon(spin_icon)
window.show()
application.exec_()
```

!!! warning
    The `QtAwesome` package doesn't work properly within Houdini, so you should use the `fxicons` module instead.