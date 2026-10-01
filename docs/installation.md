# :material-download: Installation

## From PyPI

The package is available on [PyPI](https://pypi.org/project/fxgui):

``` shell
pip install fxgui
```

## Qt Binding

A Qt 6 binding is required and not installed with fxgui: PySide6 6.5 or
newer, or PyQt6. A DCC such as Houdini ships its own PySide6; outside one,
install it yourself:

``` shell
pip install fxgui "PySide6>=6.5"
```

Qt 5 (PySide2, PyQt5) and PySide6 older than 6.5 are not supported:
`import fxgui` raises an `ImportError` that names the binding or the
version it found.

## From Source

Clone the repository with submodules:

``` shell
git clone --recurse-submodules https://github.com/healkeiser/fxgui
cd fxgui
pip install -e .
```

Or using the requirements file:

``` shell
pip install -r requirements.txt
```

## Optional Dependencies

### Docking

`fxdocking.FXDockArea` docks panes with Qt Advanced Docking System
(QtAds). Its Python package, `PySide6-QtAds`, is built against one exact
PySide6: each release names the PySide6 it needs, and pip replaces the
one you have to match it. So install it with your own PySide6 version
named beside it. Find your version first:

``` shell
pip show PySide6-Essentials
```

Then name it, here 6.8.2:

``` shell
pip install PySide6-QtAds "PySide6-Essentials==6.8.2"
```

pip picks the QtAds release made for that PySide6 and leaves your
PySide6 alone. If it answers `ResolutionImpossible`, no QtAds release was
made for your PySide6 (6.5.3, Houdini 21's, has none): docking is not
available there.

Inside a DCC, PySide6 comes with the application, not from pip, so
`pip show` finds nothing. Do not pip install QtAds into a DCC's Python:
its PySide6 would load beside the host's and break it.

Only `fxgui.fxdocking` imports QtAds; the rest of fxgui works without it.

### Documentation

To build this site with [Zensical](https://zensical.org):

``` shell
pip install -e ".[zensical]"
zensical serve    # Preview at http://127.0.0.1:8000
zensical build    # Write the site to site/
```

## DCC Integration

!!! question
    In order to have access to the module inside your application, make sure to add `fxgui` to the `$PYTHONPATH` of the DCCs. For Houdini, you can find the `houdini_package.json` example file.