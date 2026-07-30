# :material-palette:{.scale-in-center} Styling

## Style an Existing Application

In the case where you already have made some custom applications, and don't want to be bothered by subclassing the widgets inside the [fxwidgets](../technical/fxwidgets/index.md) module but still want all applications to look and feel the same, you can call the `fxstyle.load_stylesheet()` function and apply the returned stylesheet to your current application/widget.

```python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
application.setStyleSheet(fxstyle.load_stylesheet())
```

```python
from qtpy.QtWidgets import QMainWindow
from fxgui import fxstyle

window = QMainWindow()
window.setStyleSheet(fxstyle.load_stylesheet())
```

!!! note
    You can set this stylesheet on a `QMainWindow`, `QWidget`, etc.

!!! note
    You can pass extra arguments to the [load_stylesheet()](../technical/fxstyle.md) function.

!!! warning
    `load_stylesheet()` returns a one-time snapshot. If the user switches themes afterward, nothing updates on its own, you'd have to call it again and re-apply it yourself. For a widget that should keep following theme switches, register it as a themed root instead (see below).

## Staying in Sync with Theme Switches

`fxstyle.register_themed_root()` applies the current theme's stylesheet to a widget, or the `QApplication` itself, immediately, and re-applies it automatically on every later `fxstyle.apply_theme()` call. Qt cascades the stylesheet to all descendants, so registering the top-level widget is enough, children don't need to register themselves.

```python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
fxstyle.register_themed_root(application)
fxstyle.apply_theme("dracula")
```

!!! note
    `fxwidgets.FXApplication` and `fxwidgets.FXMainWindow(set_stylesheet=True)` (the default) call `register_themed_root()` on themselves already, so you rarely need to call it directly unless you're styling a plain `QApplication` or `QWidget`.

!!! warning "DCC-embedded windows"
    If you're embedding a window inside a DCC host (Houdini, Maya, Nuke), register the window itself, never the host's `QApplication`. `FXMainWindow` already does this correctly at construction, so its stylesheet updates on theme switches without ever restyling the host application.

Use `load_stylesheet()` when you need a one-off stylesheet string, for example a manual snapshot handed to a DCC panel you don't want tracked as a themed root. Use `register_themed_root()` when the widget should keep following theme switches for the lifetime of the application. See [Theming](theming.md) for reading colors directly (`fxstyle.colors()`), reacting to switches (`theme_changed`), and registering your own widget styles (`register_widget_style()`).

## Apply the Custom Google Material Icons

You can find a `QProxyStyle` subclass in [fxstyle](../technical/fxstyle.md), called `FXProxyStyle`. When used on a `QApplication` instance, it allows you to switch the defaults icons provided by `Qt` for Google Material icons.

``` python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
application.setStyle(fxstyle.FXProxyStyle())
```

!!! tip
    The `FXApplication` class found inside [fxwidgets](../technical/fxwidgets/index.md) already applies this custom style.


You can now use the icons by doing:

```python
from qtpy.QtWidgets import QStyle
from fxgui import fxwidgets


application = fxwidgets.FXApplication()
window = fxwidgets.FXMainWindow(title="My App")
style = window.style()
# Use standard icons that are automatically themed
print(style.standardIcon(QStyle.SP_MessageBoxCritical))
window.show()
application.exec_()
```

!!! note
    By default, the `FXApplication` found inside [fxwidgets](../technical/fxwidgets/index.md) already applies this custom style.

!!! warning
    Applying the `FXProxyStyle` is only allowed on a `QApplication` instance! So if you're instantiating a `FXMainWindow` inside a parent DCC, **do not** set the style on it.
