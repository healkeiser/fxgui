# :material-download: Installation

## From PyPI

The package is available on [PyPI](https://pypi.org/project/fxgui):

``` shell
pip install fxgui
```

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