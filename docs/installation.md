# :material-download:{.scale-in-center} Installation

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

### MkDocs Documentation

For building documentation with MkDocs:

``` shell
pip install -e ".[mkdocs]"
# or
pip install -r requirements.mkdocs.txt
```

### Zensical Documentation

For building documentation with Zensical:

``` shell
pip install -e ".[zensical]"
# or
pip install -r requirements.zensical.txt
```

!!! note
    Zensical is still in early development and does not yet support all MkDocs plugins.

## DCC Integration

!!! question
    In order to have access to the module inside your application, make sure to add `fxgui` to the `$PYTHONPATH` of the DCCs. For Houdini, you can find the `houdini_package.json` example file.