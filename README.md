<div align="center">

  ![Logo](https://raw.githubusercontent.com/healkeiser/fxgui/main/fxgui/images/fxgui_logo_background_dark.svg#gh-light-mode-only)
  ![Logo](https://raw.githubusercontent.com/healkeiser/fxgui/main/fxgui/images/fxgui_logo_background_light.svg#gh-dark-mode-only)

  <h3 align="center">fxgui</h3>

  <p align="center">
    Custom Python classes and utilities tailored for Qt built UI, in VFX-oriented DCC applications.
    <br/><br/>
    <a href="https://healkeiser.github.io/fxgui"><strong>Documentation</strong></a>
  </p>

  ##

  <p align="center">
    <!-- Maintenance status -->
    <img src="https://img.shields.io/badge/maintenance-actively--developed-brightgreen.svg?&label=Maintenance"> &nbsp;&nbsp;
    <!-- <img src="https://img.shields.io/badge/maintenance-deprecated-red.svg?&label=Maintenance">&nbsp;&nbsp; -->
    <!-- License -->
    <img src="https://img.shields.io/github/license/healkeiser/fxgui?&label=License"/> &nbsp;&nbsp;
    <!-- GitHub build workflow -->
    <img src="https://img.shields.io/github/actions/workflow/status/healkeiser/fxgui/release.yml?&label=Build&logo=github-actions&logoColor=white" alt="Build"> &nbsp;&nbsp;
    <!-- PyPI version-->
    <a href="https://pypi.org/project/fxgui"><img src="https://img.shields.io/pypi/v/fxgui?&logo=pypi&logoColor=white&label=Version" alt="PyPI Version"/></a> &nbsp;&nbsp;
    <!-- PyPI downloads -->
    <a href="https://pepy.tech/projects/fxgui"><img src="https://static.pepy.tech/badge/fxgui" alt="PyPI Downloads"></a> &nbsp;&nbsp;
    <!-- Last Commit -->
    <img src="https://img.shields.io/github/last-commit/healkeiser/fxgui?logo=github&label=Last%20Commit" alt="Last Commit"> &nbsp;&nbsp;
    <!-- Commit Activity -->
    <a href="https://github.com/healkeiser/fxgui/pulse" alt="Activity"><img src="https://img.shields.io/github/commit-activity/m/healkeiser/fxgui?&logo=github&label=Commit%20Activity"></a> &nbsp;&nbsp;
    <!-- GitHub stars -->
    <img src="https://img.shields.io/github/stars/healkeiser/fxgui" alt="GitHub Stars"/> &nbsp;&nbsp;
  </p>

</div>



<!-- TABLE OF CONTENTS -->
## Table of Contents

- [Table of Contents](#table-of-contents)
- [About](#about)
- [Installation](#installation)
- [Example](#example)
- [Documentation](#documentation)
- [Screenshots](#screenshots)
- [Contact](#contact)



<!-- ABOUT -->
## About

Custom Python classes and utilities tailored for Qt built UI, in VFX-oriented DCC applications.



<!-- INSTALLATION -->
## Installation

### From PyPI

The package is available on [PyPI](https://pypi.org/project/fxgui):

``` shell
pip install fxgui
```

### From Source

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

### Optional Dependencies

For building documentation with MkDocs:

``` shell
pip install -e ".[mkdocs]"
# or
pip install -r requirements.mkdocs.txt
```

For building documentation with Zensical:

``` shell
pip install -e ".[zensical]"
# or
pip install -r requirements.zensical.txt
```

> [!NOTE]
> Zensical is still in early development and does not yet support all MkDocs plugins.

> [!IMPORTANT]
> In order to have access to the module inside your application, make sure to add `fxgui` to the `$PYTHONPATH` of the DCCs. For Houdini, you can find the [`houdini_package.json` example file](./houdini_package.json).



<!-- EXAMPLE -->
## Example

After installing fxgui, you can run the demo:

``` shell
python examples.py
```

Or:

``` python
from fxgui import examples

examples.main()
```

### Widget Examples

Each widget in the `fxwidgets` module includes a standalone example that can be run directly. Set the `DEVELOPER_MODE` environment variable to `1` to enable examples:

``` shell
# Set the environment variable first
set DEVELOPER_MODE=1  # Windows
export DEVELOPER_MODE=1  # Linux/macOS

# Run any widget file directly to see its example
python -m fxgui.fxwidgets._breadcrumb
python -m fxgui.fxwidgets._accordion
python -m fxgui.fxwidgets._collapsible
# ... and more
```



<!-- DOCUMENTATION -->
## Documentation

Please read the full documentation [here](https://healkeiser.github.io/fxgui/).



<!-- CONTACT -->
## Contact

Project Link: [fxgui](https://github.com/healkeiser/fxgui)

<p align='center'>
  <!-- GitHub profile -->
  <a href="https://github.com/healkeiser">
    <img src="https://img.shields.io/badge/healkeiser-181717?logo=github&style=social" alt="GitHub"/></a>&nbsp;&nbsp;
  <!-- LinkedIn -->
  <a href="https://www.linkedin.com/in/valentin-beaumont">
    <img src="https://img.shields.io/badge/Valentin%20Beaumont-0A66C2?logo=linkedin&style=social" alt="LinkedIn"/></a>&nbsp;&nbsp;
  <!-- Behance -->
  <a href="https://www.behance.net/el1ven">
    <img src="https://img.shields.io/badge/el1ven-1769FF?logo=behance&style=social" alt="Behance"/></a>&nbsp;&nbsp;
  <!-- X -->
  <a href="https://twitter.com/valentinbeaumon">
    <img src="https://img.shields.io/badge/@valentinbeaumon-1DA1F2?logo=x&style=social" alt="Twitter"/></a>&nbsp;&nbsp;
  <!-- Instagram -->
  <a href="https://www.instagram.com/val.beaumontart">
    <img src="https://img.shields.io/badge/@val.beaumontart-E4405F?logo=instagram&style=social" alt="Instagram"/></a>&nbsp;&nbsp;
  <!-- Gumroad -->
  <a href="https://healkeiser.gumroad.com/subscribe">
    <img src="https://img.shields.io/badge/healkeiser-36a9ae?logo=gumroad&style=social" alt="Gumroad"/></a>&nbsp;&nbsp;
  <!-- Gmail -->
  <a href="mailto:valentin.onze@gmail.com">
    <img src="https://img.shields.io/badge/valentin.onze@gmail.com-D14836?logo=gmail&style=social" alt="Email"/></a>&nbsp;&nbsp;
  <!-- Buy me a coffee -->
  <a href="https://www.buymeacoffee.com/healkeiser">
    <img src="https://img.shields.io/badge/Buy Me A Coffee-FFDD00?&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me A Coffee"/></a>&nbsp;&nbsp;
</p>
