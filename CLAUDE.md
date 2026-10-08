# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fxgui is a Python library providing custom Qt-based widgets and utilities for VFX Digital Content Creation (DCC) applications. It runs on Qt 6 only, through QtPy: PySide6 6.5 or newer (Houdini 21 ships 6.5.3) or PyQt6.

## Development Commands

### Setup
```bash
git clone https://github.com/healkeiser/fxgui
pip install -e .
```

### Gallery
```bash
python -m fxgui.examples    # Every public widget, a page per kind
```
`fxgui/examples.py` is the only example. A new public widget gets a section
there, titled with its class name; `tests/test_gallery.py` fails otherwise.

### Documentation
```bash
pip install -e ".[zensical]"
zensical serve    # Local preview at http://127.0.0.1:8000
zensical build    # Build static docs into site/
```
`zensical.toml` is the config; zensical's own theme, no custom CSS. The
api-autonav plugin writes one API page per public module under
`technical/fxgui/`. `strict = true`: a broken link fails the build.

## Architecture

### Core Modules

- **fxstyle.py** - Themes from `style.yaml`. A themed root wears the theme's stylesheet, palette (`palette()`) and font (`font()`); `apply_theme(name)` re-applies all three and emits `theme_changed`. `colors()` is the cached colour namespace
- **fxconfig.py** - QSettings-based persistent configuration (INI format)
- **fxcore.py** - `FXSortFilterProxyModel` with fuzzy matching
- **fxicons.py** - Multi-library icons whose colours are theme token names, resolved by a `QIconEngine` each time the icon is drawn
- **fxutils.py** - UI utilities (load_ui, create_action, shadows, repolish)

### Theming Contract (pull model)

Nothing is notified to restyle; everything reads the theme when Qt draws:

- **Looks in QSS** - built-in rules live in `qss/style.qss`; a widget module registers its own with `fxstyle.register_widget_style(qss)` at import, `@tokens` for colours, the class name or an objectName as selector. State goes through a dynamic property plus `fxutils.repolish(widget)`.
- **Base sheet carries shape and state only** - no rule sets a fill or a font on every widget. Default fills come from the palette and the default size and family from the root font, so `setFont`, item `BackgroundRole` and labels on cards behave. A root inside a host application adds `_HOST_RULES`, since Qt gives widgets made later in such a window the host's palette and font.
- **Painting** - read `fxstyle.colors()` inside `paintEvent`; never cache colours.
- **Icons** - `fxicons.get_icon`/`set_icon` take token names (`color="text_muted"`, `inks={"active": ...}`); `FXIconLabel` draws an icon in a label. No widget re-bakes an icon on a theme switch.
- **`theme_changed`** - only for real side effects (re-highlighting, a cached render). Connect a bound method of the widget; Qt drops it with the widget.
- No widget calls `setStyleSheet(load_stylesheet())` on itself; windows register as themed roots.

```python
fxstyle.register_widget_style("MyCard { background: @surface; }")

class MyCard(QFrame):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QColor(fxstyle.colors().accent_primary))
```

### Widget Structure

The `fxwidgets/` directory contains 30+ custom widgets. Each module:
- Private module name (e.g., `_accordion.py`)
- No `example()` or `__main__` block: the gallery shows it
- Signals/slots with `@Slot` decorator

## Conventions

### Code Style
- Google-style docstrings with Args/Returns sections
- Comprehensive type annotations
- Public API exported via `__all__`
- Module metadata: `__author__`, `__email__`

### Git Commit Messages
Use conventional commit format with type prefix:
```
[FEAT] Add new widget
[FIX] Fix theme not updating
[CHORE] Update dependencies
[DOC] Improve docstrings
[STYLE] Format code
[BUILD] Update release workflow
```

### Branches
- `main` - stable releases
- `dev` - active development

## Release Pipeline

GitHub Actions automates:
1. Changelog generation via auto-changelog
2. GitHub Release creation
3. PyPI publishing
4. Documentation deployment to GitHub Pages

Versioning uses setuptools_scm (derived from git tags).
