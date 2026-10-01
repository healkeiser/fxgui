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

Qt 5 (PySide2, PyQt5) is not supported: `import fxgui` raises an
`ImportError` that names the binding it found.

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

`fxdocking.FXDockArea` docks panes with Qt Advanced Docking System:

``` shell
pip install "fxgui[docking]"
```

Nothing else in fxgui imports it.

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