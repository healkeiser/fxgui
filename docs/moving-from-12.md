# :material-swap-horizontal: Moving from 12.x

13.0.0 keeps one public name per job. A 12.x name that did the same job
as another is gone, so code written for 12.x can stop with an
`AttributeError`, an `ImportError` or a `TypeError` on its first run.

Find the name the error gives you in the tables below, and write what
the right-hand column says. "Gone" means 13.0.0 has nothing in its
place; the column says what to do instead.

## Before you start

| 12.x | 13.0.0 |
|------|--------|
| Qt 5 (PySide2, PyQt5) | Qt 6 only: PySide6 6.5 or newer, or PyQt6. `import fxgui` raises `ImportError` naming the binding or version it found |
| `pip install "fxgui[docking]"` | No `docking` extra. Install `PySide6-QtAds` beside your own PySide6, as [Installation](installation.md#docking) shows |
| `exec_()` | `exec()` |

### A property is now a method

Many values that were properties are now methods with a `set_` partner.
Reading one without `()` gives you a bound method instead of the value,
so nothing fails at once: the value just looks wrong.

```python
from fxgui import fxwidgets

crumb = fxwidgets.FXBreadcrumb()
crumb.set_path(["pilot", "sq010"])  # 12.x: crumb.path = [...]
print(crumb.path())                 # 12.x: crumb.path
```

| Class | Read with `()` | Set with |
|-------|----------------|----------|
| `FXAccordion` | `exclusive()` | `set_exclusive(b)` |
| `FXBreadcrumb` | `path()`, `home_path()` | `set_path(p)`, `set_home_path(p)` |
| `FXCollapsibleWidget` | `title()`, `is_expanded()`, `animation_duration()`, `max_content_height()` | `set_title(t)`, `set_animation_duration(ms)`, `set_max_content_height(px)` |
| `FXDropZone` | `title()`, `description()`, `accept_mode()`, `extensions()`, `multiple()`, `has_files()`, `selected_files()`, `file_tree()` | `set_title`, `set_description`, `set_accept_mode`, `set_extensions`, `set_multiple` |
| `FXElidedLabel` | `mode()` | `set_mode(m)` |
| `FXFilePathWidget` | `path()` | `set_path(p)` |
| `FXRangeSlider` | `low()`, `high()` | `set_low(v)`, `set_high(v)` |
| `FXRatingWidget` | `rating()` | `set_rating(v)` |
| `FXTagChip` | `text()` | |
| `FXTagInput` | `tags()` | |
| `FXTimelineSlider` | `current_frame()`, `fps()`, `frame_range()`, `view_range()`, `is_view_zoomed()`, `loop_playback()` | `set_frame(f)`, `set_fps`, `set_range`, `set_view_range`, `set_loop_playback` |

## fxconfig

| 12.x | 13.0.0 |
|------|--------|
| `get_settings()` | `fxconfig.get_value(key, default)` and `fxconfig.set_value(key, value)`. For a `QSettings` of your own: `QSettings(QSettings.IniFormat, QSettings.UserScope, name, "settings")` |
| `get_config_dir()`, `SETTINGS_FILE` | Gone. The file is that `QSettings`'s `fileName()`, and its folder is `Path(...fileName()).parent` |
| `get_application_name()` | Gone. Keep the name you gave `set_application_name` |

## fxconstants

| 12.x | 13.0.0 |
|------|--------|
| `FAVICON_DARK` | Gone. `FAVICON_LIGHT` stays |

## fxcore

| 12.x | 13.0.0 |
|------|--------|
| `FXSortFilterProxyModel.set_color_match(b)` | `FXSortFilterProxyModel(color_match=b)` |
| `FXSortFilterProxyModel.set_show_all(b)` | Gone |

## fxdcc

The whole module is gone. Ask the host application yourself:

| 12.x | 13.0.0 |
|------|--------|
| `get_houdini_main_window()` | `hou.qt.mainWindow()` |
| `get_houdini_stylesheet()` | `hou.qt.styleSheet()` |
| `get_maya_main_window()` | `wrapInstance(int(maya.OpenMayaUI.MQtUtil.mainWindow()), QWidget)` |
| `get_nuke_main_window()` | The top-level widget whose `metaObject().className()` is `"Foundry::UI::DockMainWindow"` |
| `get_dcc_main_window()`, `STANDALONE`, `HOUDINI`, `MAYA`, `NUKE` | Gone |

## fxicons

| 12.x | 13.0.0 |
|------|--------|
| `get_icon(..., include_active=False)` | Drop the argument. A hovered button's icon keeps its resting colour by default; only a menu's highlighted row, which is the accent, changes it |
| `get_icon(..., include_active=True)` | `get_icon(..., inks={"active": "icon_on_accent_secondary"})` |
| `set_icon(widget, name, theme_color=...)` | Drop `theme_color`. A token colour (`color="text_muted"`) follows the theme; a colour (`"#ff0000"`) stays fixed |
| `get_icon_color()` | `fxstyle.colors().icon` |
| `set_default_icon_library(library)` | Pass `library=` to each `get_icon` call |
| `set_icon_defaults(**kwargs)` | Pass `color=`, `width=`, `height=` to each `get_icon` call |
| `refresh_all_icons()`, `sync_colors_with_theme()` | Delete the call. An icon reads its theme colours each time Qt draws it |
| `clear_icon_cache()` | `QPixmapCache.clear()`, Qt's own: fxicons keeps its drawings there |
| `convert_icon_to_pixmap(icon, size)` | Qt's own `icon.pixmap(size)` |
| `change_pixmap_color(pixmap, color)` | Gone. For a library icon, `fxicons.get_pixmap(name, color=...)` |
| `superpose_icons(*icons)` | Gone. `fxicons.badged(icon, color)` adds a dot, which is a different picture |
| `get_available_libraries()`, `get_available_icons_in_library(library)` | Gone |

## fxstyle

The colour getters are one call now, `fxstyle.colors()`. It returns an
object, not a dict: read a token as an attribute.

```python
from fxgui import fxstyle

surface = fxstyle.colors().surface          # 12.x: get_theme_colors()["surface"]
name = "accent_primary"
accent = getattr(fxstyle.colors(), name)    # a token name held in a variable
```

| 12.x | 13.0.0 |
|------|--------|
| `get_theme_colors()["surface"]` | `colors().surface` |
| `get_accent_colors()["primary"]`, `["secondary"]` | `colors().accent_primary`, `colors().accent_secondary` |
| `get_icon_color()` | `colors().icon` |
| `get_icon_on_accent_primary()`, `get_icon_on_accent_secondary()` | `colors().icon_on_accent_primary`, `colors().icon_on_accent_secondary` |
| `get_feedback_colors()["error"]["foreground"]` | `colors().feedback_error_foreground` (also `_background` and `_ink`); `fxstyle.qcolor("feedback_error_foreground")` for a `QColor` |
| `get_contrast_text_color(background)` | `fxstyle.readable_ink(background)`. It keeps white while white reads at 4.5:1, so the answer can differ from 12.x's black-or-white |
| `get_fonts(theme)["body"]` | `fxstyle.font(theme, role="body")`, a `QFont` rather than a stylesheet string |
| `get_font_family(role)` | `fxstyle.font(role=role).family()`: one installed family, unquoted |
| `theme_manager.theme_changed`, `FXThemeManager` | `fxstyle.theme_changed`, which sends the theme's name |
| `FXThemeAware` | Gone. Follow the custom widget contract in [Theming](how-to/theming.md#the-custom-widget-contract) |
| `apply_theme(widget, theme)` | `fxstyle.register_themed_root(widget)` once, then `fxstyle.apply_theme(theme)` |
| `build_stylesheet()`, `load_stylesheet()` | `fxstyle.register_themed_root(window)`: the window gets the sheet now and on every switch |
| `replace_colors(qss, colors)` | `fxstyle.resolve(qss)` for the theme's tokens; write `@button_radius` where you wrote `@radius` |
| `invalidate_standard_icon_map()` | Delete the call |
| `FXProxyStyle.set_icon_color(color)` | Gone. Qt's standard icons use the theme's `icon` token; change the theme to change them |

## fxutils

| 12.x | 13.0.0 |
|------|--------|
| `add_shadows(parent, widget, ...)` | `fxutils.add_shadow(widget, offset=(x, y))`. The colour and blur come from the theme |
| `set_formatted_tooltip(widget, title, text)` | `fxwidgets.apply_tip(widget, title, text)`. No `duration`; markup in `text` shows as text |
| `get_formatted_time()` | `datetime.now().strftime("%H:%M")` |
| `deprecated` | Python's `warnings.warn(..., DeprecationWarning)` |
| `create_action(parent, name, icon, trigger, ...)` | `create_action(parent, name, trigger, ..., icon_name="save")`. `icon` is gone, so a positional call now passes your icon as the trigger: name the arguments. `visible=False` becomes `action.setVisible(False)` |
| `filter_tree(line_edit, tree, column)` | `filter_tree(tree, line_edit.text())`. It matches every column, keeps a match's parents and children, and `mark=` decides what happens to the rest (hidden by default) |

## fxwidgets

### Gone or moved

| 12.x | 13.0.0 |
|------|--------|
| `FXTooltip`, `FXTooltipManager`, `FXTooltipPosition`, `set_tooltip(target, description, title)` | `apply_tip(target, title, body, shortcut)`: Qt's own tooltip. Note the order, title before body. No icon, image or position |
| `FXWidget(ui_file=path)` | `QWidget`, and `fxutils.load_ui(widget, path)` |
| `FXAccordionSection` | `FXCollapsibleWidget` |
| `FXItemDelegate` | `QStyledItemDelegate` |
| `FXFuzzySearchTree` | `FXFilteredTree(tree, placeholder)` over an `FXKeyboardTree` you fill. Fuzzy ranking stays in `fxcore.FXSortFilterProxyModel` |
| `FXFuzzySearchList` | `FXFilteredTree` with top-level items only |
| `FXColorLabelDelegate` | Gone |
| `FXThemeColors` | `fxstyle.FXThemeColors` |
| `FXThemeManager`, `theme_manager`, `FXThemeAware` | See [fxstyle](#fxstyle) |
| `apply_tip(widget=w, ...)` | `apply_tip(w, ...)`: the first argument is now called `target` |

### FXMainWindow

| 12.x | 13.0.0 |
|------|--------|
| `self.ERROR`, `self.WARNING`, `self.INFO`, ... | `fxwidgets.ERROR`, `fxwidgets.WARNING`, `fxwidgets.INFO`, ... |
| `set_theme(theme)` | `fxstyle.apply_theme(theme)` |
| `get_available_themes()` | `fxstyle.get_available_themes()` |
| `hide_banner()`, `show_banner()` | `window.title_corner.hide()`, `.show()`: the name sits in the menu bar's corner |
| `use_corner_title()` | Delete the call: every window shows its name there |
| `set_project_label(p)`, `set_version_label(v)`, `set_company_label(c)` | `window.statusBar().project_label.setText(p)`, and `version_label`, `company_label` |
| `set_status_line_colors(a, b)`, `hide_status_line()`, `show_status_line()` | The same names on `window.statusBar()` |
| `set_ui_file(path)` | `FXMainWindow(ui_file=path)` |
| `FXMainWindow(set_stylesheet=..., rich_tooltips=..., toolbar=...)` | Drop all three. Add a toolbar with `addToolBar`. Pass `fit_to_contents` and `framed` by name: they moved |

### Status bar, banner, splash screen, tray, progress, spinner, dialog

| 12.x | 13.0.0 |
|------|--------|
| `statusBar().showMessage(..., pixmap=..., background_color=...)` | Drop both: the severity sets the look |
| `FXNotificationBanner(action_text=...)`, `action_clicked` | `FXNotificationBanner(actions={"Retry": retry})` or `banner.add_action("Retry", retry)`. Pass the arguments after `message` by name: they moved |
| `FXNotificationBanner.SEVERITY_ICONS`, `SEVERITY_TITLES` | Gone |
| `FXSplashScreen.set_title(t)`, `set_information_text`, `set_icon`, `set_pixmap`, `set_project_label`, `set_version_label`, `set_company_label`, `set_overlay_opacity`, `set_corner_radius`, `set_border`, `toggle_fade_in` | Constructor arguments: `title=`, `information=`, `icon=`, `image_path=`, `project=`, `version=`, `company=`, `overlay_opacity=`, `corner_radius=`, `border_width=`, `border_color=`, `fade_in=`. After that, `splash.title_label.setText(...)` |
| `FXSplashScreen.toggle_progress_bar_visibility(b)` | `show_progress_bar=` in the constructor, or `splash.progress_bar.setVisible(b)` |
| `FXSplashScreen(set_stylesheet=...)` | Drop it, and pass the arguments after it by name |
| `FXSystemTray.add_action(action)` | `tray.contextMenu().insertAction(tray.quit_action, action)` |
| `FXSystemTray.set_icon(path)` | `tray.setIcon(QIcon(path))` |
| `FXProgressCard.progress = v` | `card.set_progress(v)`; keep the value yourself or listen to `progress_changed` |
| `FXProgressCard.increment(n)` | `card.set_progress(value + n)` |
| `FXProgressCard.reset()` | `card.set_progress(0)` then `card.set_status(None)` |
| `FXProgressCard.STATUS_ICONS` | Gone |
| `FXLoadingSpinner(style=...)`, `set_style`, `angle` | Drop them: the ring is the only spinner. `color` takes a token |
| `FXFloatingDialog(parent_package=...)` | Drop it, and pass `popup` by name |

### Inputs

`FXSearchBar`, `FXPasswordLineEdit` and `FXIconLineEdit` are each a
`QLineEdit` now, so Qt's own line edit calls work on them.

| 12.x | 13.0.0 |
|------|--------|
| `FXSearchBar.set_placeholder(t)` | `setPlaceholderText(t)` |
| `FXSearchBar.text` | `text()`, `setText(t)` |
| `FXSearchBar(filters=..., show_filter=...)`, `filter`, `filter_changed`, `set_filters`, `show_filter` | Gone. Put a `QComboBox` beside the search bar |
| `FXPasswordLineEdit.line_edit`, `toggle_reveal()` | Call the widget itself. The eye has no public handle |
| `FXIconLineEdit("search")` | `FXIconLineEdit(icon_name="search")`: `parent` is first now |

### Collapsible and accordion

| 12.x | 13.0.0 |
|------|--------|
| `get_title()` | `title()` |
| `get_icon()`, `get_title_icon()` | `icon()` |
| `set_title_icon(icon)` | `set_icon(icon)` |
| `header_widget`, `content_area`, `toggle_button`, `title_label`, `title_icon_label` | Gone. Use `set_content_widget`, `set_content_layout`, `set_title`, `set_icon` |
| `resized` | Gone |
| `FXCollapsibleWidget.NO_CAP` | `fxutils.NO_CAP` |

### Other widgets

| 12.x | 13.0.0 |
|------|--------|
| `FXBreadcrumb.RADIUS` | `fxstyle.BUTTON_RADIUS` |
| `FXFilePathWidget.get_path()` | `path()`. `mode="directory"` is now `mode="folder"` |
| `FXDropZone.show_placeholder()`, `show_file_tree()` | Gone: the zone switches by itself |
| `FXRangeSlider.set_range(low, high)` | `set_values(low, high)`. The bounds are `set_minimum`, `set_maximum` |
| `FXRatingWidget.get_rating()` | `rating()` |
| `FXResizedScrollArea.resized` | Gone. Use your own `resizeEvent` |
| `FXOutputLogWidget(capture_output=True)` | Gone: add `logger.addHandler(fxwidgets.FXOutputLogHandler(widget))`. Pass `max_blocks` by name |
| `FXOutputLogWidget.restore_output_streams()`, `ANSI_COLORS` | Gone. The log's colours are theme tokens |

### FXThumbnailDelegate

| 12.x | 13.0.0 |
|------|--------|
| `TRANSPARENT_SELECTION_STYLE` | `FXThumbnailDelegate.apply_transparent_selection(view)` |
| `markdown_to_plain_text(text)` | `fxutils.markdown_to_plain_text(text)` |
| `show_child_count` | Gone. Set `CHILD_COUNT_VISIBLE_ROLE` to `False` on a row to hide its count |
| `show_starred`, `STARRED_ROLE`, `STARRED_COLOR_ROLE`, `STATUS_LABEL_ICON_ROLE` | Gone |
| `Qt.UserRole + n` for a role of your own | `FXThumbnailDelegate.FIRST_FREE_ROLE + n`: every role number moved |
