# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fxgui is a Python library providing custom Qt-based widgets and utilities for VFX Digital Content Creation (DCC) applications. It uses QtPy for compatibility across PySide2/PySide6/PyQt5/PyQt6.

## Development Commands

### Setup
```bash
git clone --recurse-submodules https://github.com/healkeiser/fxgui
pip install -e .
```

### Running Examples
```bash
python -m fxgui.examples                    # Full showcase application
DEVELOPER_MODE=1 python -m fxgui.fxwidgets._accordion  # Individual widget example
```

### Documentation
```bash
pip install -r requirements.mkdocs.txt
mkdocs serve    # Local preview at http://127.0.0.1:8000
mkdocs build    # Build static docs
```

## Architecture

### Core Modules

- **fxstyle.py** - Theming engine with `FXThemeManager` singleton and `FXThemeAware` mixin. Uses YAML-based theme definitions (`style.yaml`) with semantic color roles
- **fxconfig.py** - QSettings-based persistent configuration (INI format)
- **fxcore.py** - `FXSortFilterProxyModel` with fuzzy matching
- **fxdcc.py** - DCC integration (Houdini, Maya, Nuke) with auto-detection
- **fxicons.py** - Multi-library icon management (beacon, fontawesome, dcc-specific) with LRU caching and theme-aware updates
- **fxutils.py** - UI utilities (load_ui, create_action, shadows, tooltips)

### Widget Patterns

The `fxwidgets/` directory contains 30+ custom widgets. Key patterns:

**Theme Awareness** - Inherit from `FXThemeAware` mixin for automatic theme updates:
```python
class MyWidget(FXThemeAware, QWidget):
    def _on_theme_changed(self, _theme_name: str = None):
        colors = fxstyle.get_theme_colors()
        self.setStyleSheet(f"background: {colors['surface']};")
```

**Icon Usage** - Use `set_icon()` for theme-aware icons:
```python
from fxgui.fxicons import set_icon, get_icon
set_icon(button, "check")  # Auto-updates on theme change
```

**Widget Structure** - Each widget module follows this pattern:
- Private module name (e.g., `_accordion.py`)
- Standalone `example()` function for testing (runs with `DEVELOPER_MODE=1`)
- Signals/slots with `@Slot` decorator
- Methods: `_initialize()`, `_connect_signals()` for setup

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
