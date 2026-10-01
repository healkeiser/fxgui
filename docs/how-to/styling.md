# :material-palette: Styling

## Style an Existing Application

To give an application you already have the fxgui look, make its
`QApplication` a themed root:

```python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
fxstyle.register_themed_root(application)
fxstyle.apply_theme("dracula")
```

That puts the theme's stylesheet, palette and font on the application,
and again on every later `fxstyle.apply_theme()`. `FXApplication` does
this on itself, so with it you call nothing.

Inside a host application (Houdini, Maya, Nuke), never register the
host's `QApplication`: register your own top-level window.

```python
from qtpy.QtWidgets import QMainWindow
from fxgui import fxstyle

window = QMainWindow()
fxstyle.register_themed_root(window)
```

`FXMainWindow`, `FXFloatingDialog`, `FXSplashScreen` and the
`FXSystemTray` menu do this on themselves, so the host is never
restyled. While the `QApplication` is a themed root, registering a widget
does nothing: the application's sheet already reaches it.

### A stylesheet by hand

`fxstyle.load_stylesheet()` returns the theme's stylesheet as text and
changes nothing. It is a snapshot: a later theme switch does not reach
it. A window styled with it also needs the palette and the font:

```python
window.setStyleSheet(fxstyle.load_stylesheet())
window.setPalette(fxstyle.palette())
window.setFont(fxstyle.font())
```

Prefer `register_themed_root()` whenever the window should follow theme
switches. See [Theming](theming.md) for what the stylesheet, the palette
and the font each carry, reading colours (`fxstyle.colors()`), and
registering your own widget styles (`register_widget_style()`).

## Apply the Custom Google Material Icons

You can find a `QProxyStyle` subclass in [fxstyle](../technical/fxgui/fxstyle.md), called `FXProxyStyle`. When used on a `QApplication` instance, it allows you to switch the defaults icons provided by `Qt` for Google Material icons.

``` python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
application.setStyle(fxstyle.FXProxyStyle())
```

!!! tip
    The `FXApplication` class found inside [fxwidgets](../technical/fxgui/fxwidgets/index.md) already applies this custom style.


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
    By default, the `FXApplication` found inside [fxwidgets](../technical/fxgui/fxwidgets/index.md) already applies this custom style.

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
| Menu bar, toolbars, status bar | `surface_sunken` / `surface`, with a line under each | `frame`, no lines |
| Status bar accent line | Shown, with a 1 px line under it | Shown, with no line under it |
| A status bar set later with `setStatusBar()` | As given | Painted in `frame` too |

In both, the window's icon and name sit at the right end of the menu bar,
in `window.title_corner` (`banner_icon` and `banner_label`), with no fill
of their own. `set_banner_text()` and `set_banner_icon()` change them; the
icon defaults to 16 px.

A framed window paints the frame behind your central widget, but the
central widget itself keeps the surface: mark it, and any band of your own
inside it, with `fxstyle.mark_as_frame()`. A child of the window left
unmarked keeps the surface, which is what a pane should do.

### What `mark_as_frame()` does

| Widget marked | Result |
|---------------|--------|
| Any widget | Paints the `frame` color |
| A disabled `QToolButton` placed directly in it | No fill and no border, so it sits on the frame |
| A `QSplitter` | Its handles are gaps in the `frame` color with a short centred mark of five dots in the `splitter_mark` color; the handle keeps exactly the width `setHandleWidth()` gives it |

Call `fxstyle.mark_as_frame(widget, False)` to remove the mark. A plain label has no fill anywhere, so it shows whatever is behind it: the frame in a marked band, the pane's colour in a pane.

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
