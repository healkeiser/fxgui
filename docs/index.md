# :material-home:{.scale-in-center} Home

<div id="top"></div>
<div align="center">
  <a href="https://github.com/healkeiser/fxgui">
    <img src="images/fxgui_logo_background_dark.svg" alt="fxgui" width="128" >
  </a>
  <p align="center">
    <br/>
  </p>
</div>

## What is fxgui

Custom Python classes and utilities tailored for Qt built UI, in VFX-oriented DCC applications.

## Features

- **Multi-DCC Support**: Works seamlessly in Houdini, Maya, Nuke, and standalone Python
- **Theme System**: Dark/light themes with automatic persistence and easy customization
- **Icon Libraries**: Built-in Material Icons, Font Awesome, Simple Icons, and DCC-specific icons
- **Theme-Aware Icons**: Icons automatically update colors when switching themes
- **Custom Widgets**: Pre-styled widgets including main windows, splash screens, collapsible panels, and more
- **Configuration Management**: Persistent settings via QSettings with INI format

## Quick Start

```python
from fxgui import fxwidgets

# Create an application with automatic theming
app = fxwidgets.FXApplication()

# Create a themed main window
window = fxwidgets.FXMainWindow(title="My App")
window.show()

app.exec_()
```

## Modules Overview

| Module | Description |
|--------|-------------|
| [fxconfig](fxconfig.md) | Configuration and settings management |
| [fxcore](fxcore.md) | Core functionality (fuzzy filtering proxy model) |
| [fxdcc](fxdcc.md) | DCC-specific utilities (Houdini, Maya, Nuke) |
| [fxicons](fxicons.md) | Icon management with multiple libraries |
| [fxstyle](fxstyle.md) | Theming, stylesheets, and color management |
| [fxutils](fxutils.md) | General utility functions |
| [fxwidgets](fxwidgets.md) | Custom Qt widgets |

!!! note
    This documentation is updated regularly to reflect the most recent changes.<br>
    If you spot any issue or have a feature request, don't hesitate to send me an [email](mailto:valentin.onze@gmail.com).
