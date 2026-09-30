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

## Frame a Window Around Its Panes

`FXMainWindow(framed=True)` draws the window as one frame around its panes, the way a code editor does: the menu bar, the toolbars, the status bar and the window behind the central widget all paint the theme's `frame` color, with no lines between them.

```python
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QListWidget, QSplitter, QTextEdit, QVBoxLayout, QWidget
from fxgui import fxstyle, fxwidgets

application = fxwidgets.FXApplication()
window = fxwidgets.FXMainWindow(title="My App", framed=True)
window.set_banner_text("My App")
window.set_banner_icon("widgets")

body = QWidget()
fxstyle.mark_as_frame(body)
layout = QVBoxLayout(body)
layout.setContentsMargins(6, 0, 6, 6)

splitter = QSplitter(Qt.Horizontal)
splitter.setHandleWidth(6)
fxstyle.mark_as_frame(splitter)
splitter.addWidget(QListWidget())
splitter.addWidget(QTextEdit())
layout.addWidget(splitter)

window.setCentralWidget(body)
window.show()
application.exec_()
```

What changes in a framed window:

| Part | Plain window | Framed window |
|------|--------------|---------------|
| Banner | A 50 px band under the toolbar | Gone; its icon and text sit at the right end of the menu bar, centred on the menu titles, with no fill of their own |
| `set_banner_text()`, `set_banner_icon()` | Change the banner | Change the menu bar corner; the icon defaults to 16 px |
| `hide_banner()`, `show_banner()` | Hide or show the banner | Hide or show the menu bar corner |
| Menu bar, toolbars, status bar | `surface_sunken` / `surface`, with a line under each | `frame`, no lines |
| Status bar accent line | Shown, with a 1 px line under it | Shown, with no line under it |
| A status bar set later with `setStatusBar()` | As given | Painted in `frame` too |
| `window.title_corner` | `None` | The widget in the menu bar corner holding `banner_icon` and `banner_label` |

The window does not paint your central widget: mark it, and any band of your own inside it, with `fxstyle.mark_as_frame()`. A widget left unmarked keeps its usual fill, which is what a pane should do.

### What `mark_as_frame()` does

| Widget marked | Result |
|---------------|--------|
| Any widget | Paints the `frame` color |
| A `QLabel`, `QCheckBox`, `QRadioButton` or disabled `QToolButton` placed directly in it | No fill of its own, so it sits on the frame |
| A `QSplitter` | Its handles are gaps in the `frame` color with a short centred mark of five dots in the `splitter_mark` color; the handle keeps exactly the width `setHandleWidth()` gives it |

Call `fxstyle.mark_as_frame(widget, False)` to remove the mark. Only direct children lose their fill: a label inside a pane inside a marked band keeps the pane's color.

!!! note
    The mark is painted, not loaded from an image: it follows theme switches, stays the same size on screen at 100 %, 150 % and 200 % scaling (each dot is two logical pixels, rounded to whole screen pixels), and reaches handles the splitter creates after it was marked. Set the handle width before or after marking; either order works.

For the 1 px edge of a pane sitting on the frame, use the `@pane_border` token (or `get_theme_colors()["pane_border"]`) rather than `@border`: in some themes `border` is nearly the frame's own color.

## Flat Icon Buttons

An icon-only `QPushButton` given the `fxRole="flat"` property has no box: it shows a fill on hover and a darker one when pressed, an accent border when it has keyboard focus, and nothing when disabled.

```python
from qtpy.QtWidgets import QPushButton
from fxgui import fxicons

back = QPushButton()
back.setProperty("fxRole", "flat")
fxicons.set_icon(back, "arrow_back")
```

Set the property before the button is shown, or call `fxutils.repolish(button)` after changing it.
