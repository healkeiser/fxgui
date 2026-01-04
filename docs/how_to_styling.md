# :material-palette:{.scale-in-center} Styling

## Style an Existing Application

In the case where you already have made some custom applications, and don't want to be bothered by subclassing the widgets inside the [fxwidgets](fxwidgets.md) module but still want all applications to look and feel the same, you can call the `fxstyle.load_stylesheet()` function and apply the returned stylesheet to your current application/widget.

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
    You can pass extra arguments to the [load_stylesheet()](fxstyle.md) function.

## Apply the Custom Google Material Icons

You can find a `QProxyStyle` subclass in [fxstyle](fxstyle.md), called `FXProxyStyle`. When used on a `QApplication` instance, it allows you to switch the defaults icons provided by `Qt` for Google Material icons.

``` python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
application.setStyle(fxstyle.FXProxyStyle())
```

!!! tip
    The `FXApplication` class found inside [fxwidgets](fxwidgets.md) already applies this custom style.


![Sreenshot](images/screenshot_built_in_icons.png)

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
    By default, the `FXApplication` found inside [fxwidgets](fxwidgets.md) already applies this custom style.

!!! warning
    Applying the `FXProxyStyle` is only allowed on a `QApplication` instance! So if you're instantiating a `FXMainWindow` inside a parent DCC, **do not** set the style on it.
