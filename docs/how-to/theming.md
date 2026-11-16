# :material-theme-light-dark: Theming

fxgui uses a YAML configuration file to define all theme colors. YAML supports **anchors and aliases** for theme inheritance, allowing you to create new themes that extend existing ones and override only specific colors.

## Understanding the Theme Structure

The default `style.yaml` file contains several sections:

```yaml
# DCC branding colors
dcc:
  houdini: "#ff6600"
  maya: "#38a6cc"
  nuke: "#fcb434"

# Theme definitions with inheritance
themes:
  dark: &dark  # Define anchor for inheritance
    accent_primary: "#2196F3"
    # ... all colors ...
    feedback:  # status colours: debug, info, success, warning, error
      error:
        foreground: "#ff4444"
        background: "#7b2323"

  dracula:
    <<: *dark  # Inherit from dark theme
    accent_primary: "#bd93f9"  # Override specific colors
```

## Theme Color Roles - Complete Reference

Each theme defines semantic color roles. All names are designed to clearly indicate their purpose:

### Accent Colors

| Role | Purpose |
|------|---------|
| `accent_primary` | Keyboard focus, the current item, a filled span, the primary action |
| `accent_secondary` | A primary button's hover fill and a pressed menu item; never a hover fill |
| `selection` | *(Optional)* A selected row's fill. Omitted, `accent_primary` at 15% over `surface` (`fxstyle.SELECTION_TINT`, mixed in OKLab), stepped toward `accent_primary` until it visibly differs from `surface`, `surface_sunken` and `well`, so the row keeps the theme's own text |
| `selection_border` | *(Optional)* The ring around a selected thumbnail row. `accent_primary` if omitted |

### Surface Colors (Backgrounds)

| Role | Purpose |
|------|---------|
| `surface` | Main widget/window backgrounds, buttons, selected tabs, toolbar |
| `surface_alt` | Alternate surface - odd rows in lists/tables, secondary panels |
| `surface_sunken` | Recessed/inset areas - input fields, lists, status bar |
| `frame` | The chrome around the panes of a framed window (optional) |
| `well` | Lists and logs set into a pane (optional) |
| `pane_border` | The 1 px edge of a pane on the frame (optional) |
| `splitter_mark` | Kept for themes and callers; fxgui no longer draws it, as a splitter handle is blank at rest (optional) |
| `tooltip` | Tooltip popup backgrounds |
| `card` | A raised card: `FXProgressCard`, a comment (optional). Omitted, `surface` stepped `fxstyle.CARD_STEP` (0.035, OKLab) toward `text` on a dark theme, `surface` itself on a light one |

`frame`, `well`, `pane_border` and `splitter_mark` are computed when a theme leaves them out, and a theme that states one keeps its own value:

- `frame` is `surface_sunken` when that is darker than `surface` by a contrast of at least `fxstyle.FRAME_MIN_CONTRAST` (1.06). Otherwise it is `surface` darkened toward black until it is, which keeps the pane's own tint and never brings in the accent. In every bundled dark theme, and in `github_light` and `catppuccin_latte`, that is `surface_sunken`; `light` and `solarized_light` have a sunken surface as light as the pane, so they get a darkened one.
- A pane too dark to darken (pure black, as in an OLED theme) gets a frame lighter than itself instead.
- `well` is half-way from `surface` to `frame`, so a list inside a pane reads one step deeper than the pane and one step shallower than the frame. Where half-way differs from `surface` by less than `fxstyle.WELL_MIN_CONTRAST` (1.04), the well moves on toward the frame until it does; `github_light` is the one bundled theme where that happens.
- `pane_border` is `border` when that differs from `frame` by a contrast of at least `fxstyle.PANE_BORDER_MIN_CONTRAST` (1.3). Otherwise it is `border` pushed further from the frame (darker on a light frame, lighter on a dark one) until it does. `light` and `catppuccin_latte` get a darker one; every other bundled theme keeps its `border`.
- `splitter_mark` is `border`, else `border_light`, else `border_light` moved toward `text`, whichever first differs from `frame` by `fxstyle.SPLITTER_MARK_MIN_CONTRAST` (1.3). `light` and `catppuccin_latte` use `border_light`.

### Border Colors

| Role | Purpose |
|------|---------|
| `border` | Standard borders - inputs, containers, menus, separators |
| `border_light` | Subtle borders - button borders, tab borders |
| `border_strong` | Emphasized borders - frames, separator lines |

### Text Colors

| Role | Purpose |
|------|---------|
| `text` | Primary text for all widgets |
| `text_muted` | Secondary text: placeholders, secondary labels, headers, the tabs that are not current |
| `text_disabled` | Disabled widget text |
| `text_strong` | *(Optional)* A row's name, a select's value, a sorted header, an empty state's title, a tooltip. Omitted, `text` moved 60% of the way to black or white (`fxstyle.STRONG_STEP`) |
| `text_toned` | *(Optional)* A task's name, a pane's values, a group header row. Omitted, half-way from `text` to `text_muted` (OKLab) |
| `text_dimmed` | *(Optional)* Chevrons, breadcrumb separators, dates, an empty cell's dash. Omitted, half a step past `text_muted`; never louder than `text_muted` |
| `text_on_accent_primary` | *(Optional)* Text on `accent_primary` backgrounds (e.g., selected items). Auto-computed if omitted |
| `text_on_accent_secondary` | *(Optional)* Text on `accent_secondary` backgrounds (a hovered primary button). Auto-computed if omitted |

`text` and `text_muted` are held to 4.5:1 (`fxstyle.TEXT_CONTRAST`, WCAG AA) on every surface they sit on: `surface`, `surface_sunken`, `surface_alt`, `well`, `frame`, `tooltip` and `state_hover`, and `text` on `state_pressed` and `state_checked_hover` too. A theme's value that misses it is darkened or lightened until it reads, so `fxstyle.colors().text` can differ from the file. `text` then moves on until it stands 1.5:1 off `text_muted` (`fxstyle.MUTED_STEP`), so the two always read as two ranks; where `text` is already black or white, `text_muted` steps back toward the surface instead, as far as it still reads at 4.5:1.

`text_toned` and `text_dimmed` are held to 4.5:1 on the same grounds (and on `card`): where `text_muted` already sits at that floor, `text_dimmed` comes to `text_muted`.

An omitted `text_on_accent_*` is black or white, whichever reads better on the accent.

### Interactive State Colors

| Role | Purpose |
|------|---------|
| `state_hover` | *(Optional)* Every hover fill: rows, buttons, tool buttons, menu bar items, a hovered tab. Omitted, `text` at 5% over `surface`. Pushed to 1.2:1 off `surface`, `surface_sunken`, `surface_alt`, `well` and `frame` when closer |
| `state_pressed` | *(Optional)* Pressed and checked fills, an open menu bar item, the current tab's pill. Omitted, `text` at 10% over `surface`. Pushed to 1.2:1 off `state_hover` and the grounds above (`fxstyle.STATE_MIN_CONTRAST`) when closer; omitted, also pushed past `state_hover`, toward black or white |
| `state_contrast` | *(Optional)* That 1.2:1 floor, for a brand that holds its fills closer, as Lumen's do |

Four more colours are derived, never set in a theme. `state_checked_hover`
fills a checked button under the pointer, so the click that unchecks it
shows: it is a step past `state_pressed` by the same floor, and `text`
reads at 4.5:1 on it. `state_hover_overlay`, `state_pressed_overlay` and
`state_checked_hover_overlay` are `text` as `#AARRGGBB`, at the least alpha
whose blend over `surface` stands off it as the opaque fill does, and that
holds fxgui's own floor on every ground (`surface`, `tooltip`, `frame`,
`surface_sunken`, `surface_alt`, `well`): 1.2:1 for hover, 1.2² for pressed,
1.2³ for checked and hovered, whatever the theme's `state_contrast`. A wide
row can carry a brand's faint fill; a 24 px icon button cannot, so a theme
that holds its states close keeps its opaque fills exactly as stated while
its flat buttons still show. Flat push buttons and plain tool buttons wear
them, so their states show on a band, a card or a tooltip, where an opaque
fill can equal the ground.
`fxstyle.colors()` has all four; `QColor(fxstyle.colors().state_hover_overlay)`
reads the alpha.

### Scrollbar Colors

| Role | Purpose |
|------|---------|
| `scrollbar_track` | Menu bar and status bar borders; a scroll bar has no track |
| `scrollbar_thumb` | Draggable thumb |
| `scrollbar_thumb_hover` | Thumb hover state |

### Layout Colors

| Role | Purpose |
|------|---------|
| `grid` | Table gridlines, a checked push button's edge |

### Shadow

| Role | Purpose |
|------|---------|
| `shadow` | Colour of a floating card's drop shadow, `#AARRGGBB` (dark `#50000000`, light `#28000000`) |
| `shadow_blur` | Its blur radius in pixels (16) |
| `scrim` | Fill dimming a pane behind `FXLoadingOverlay`, `#AARRGGBB` (`#80000000`) |
| `modal_scrim` | *(Optional)* Fill dimming a window behind a modal dialog (`fxutils.dim_behind`), `#AARRGGBB`. Black at 60 % on a dark theme, `#F3F3F5` at 75 % on a light one if omitted |

### Icon Color

| Role | Purpose |
|------|---------|
| `icon` | Tint color for monochrome icons via `fxicons.get_icon()` and standard Qt icons |

## Feedback Colors Reference

Each theme has a `feedback:` block; a theme without one takes `dark`'s. A level may name only its `foreground`: its `background` is then that colour at 12% over `surface` (`fxstyle.FEEDBACK_TINT`), and the foreground is darkened or lightened until it reads at 4.5:1 on it. A level that names both keeps both. Used by `FXNotificationBanner`, `FXOutputLogWidget`, and other status widgets. Each colour is a token, `feedback_<level>_<part>`: `fxstyle.colors().feedback_error_foreground`, or `fxstyle.qcolor("feedback_error_foreground")` for a QColor.

| Level | Property | Usage |
|-------|----------|-------|
| `debug` | `foreground` | Text/icon color for debug messages |
| `debug` | `background` | Background color for debug notifications |
| `info` | `foreground` | Text/icon color for info messages |
| `info` | `background` | Background color for info notifications |
| `success` | `foreground` | Text/icon color for success messages |
| `success` | `background` | Background color for success notifications |
| `warning` | `foreground` | Text/icon color for warning messages |
| `warning` | `background` | Background color for warning notifications |
| `error` | `foreground` | Text/icon color for error messages |
| `error` | `background` | Background color for error notifications |

## DCC Colors Reference

Used by DCC-specific widgets and branding elements:

| Key | Software | Default Color |
|-----|----------|---------------|
| `houdini` | SideFX Houdini | `#ff6600` (orange) |
| `maya` | Autodesk Maya | `#38a6cc` (teal/cyan) |
| `nuke` | Foundry Nuke | `#fcb434` (yellow/gold) |
| `megascans` | Quixel Megascans | `#8ecd4f` (green) |
| `bridge` | Quixel Bridge | `#1aa9f3` (blue) |

## Creating Your Custom Theme

1. **Copy the default file** as a starting point:

```python
from pathlib import Path
from fxgui import fxstyle

# The default style.yaml location
default_file = fxstyle.DEFAULT_COLOR_FILE
print(f"Default file: {default_file}")

# Copy it to your preferred location
import shutil
custom_file = Path.home() / ".fxgui" / "my_theme.yaml"
custom_file.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(default_file, custom_file)
```

2. **Add your theme** using YAML inheritance:

```yaml
themes:
  # Base dark theme with anchor
  dark: &dark
    accent_primary: "#2196F3"
    surface: "#302f2f"
    # ... existing dark colors ...

  # Your custom theme inheriting from dark
  monokai:
    <<: *dark  # Inherit ALL colors from dark theme

    # Override only the colors you want to change
    accent_primary: "#A6E22E"
    accent_secondary: "#66D9EF"

    surface: "#272822"
    surface_alt: "#1e1f1c"
    surface_sunken: "#1a1a17"
    tooltip: "#3e3d32"

    border: "#49483e"
    border_light: "#75715e"
    border_strong: "#49483e"

    text: "#f8f8f2"
    text_muted: "#a59f85"
    text_disabled: "#75715e"

    state_hover: "#3e3d32"
    state_pressed: "#49483e"

    scrollbar_track: "#1e1f1c"
    scrollbar_thumb: "#49483e"
    scrollbar_thumb_hover: "#75715e"

    grid: "#49483e"

    icon: "#f8f8f2"
```

!!! tip "YAML Inheritance"
    Use `&anchor_name` to define a base theme, then `<<: *anchor_name` to inherit from it.
    Any colors you specify after the inheritance line will override the inherited values.

## Using Your Custom Theme

```python
from fxgui import fxstyle, fxwidgets

# Set your custom color file BEFORE creating any widgets
fxstyle.set_color_file("/path/to/my_theme.yaml")

# Check available themes (includes your custom ones)
print(fxstyle.get_available_themes())
# ['dark', 'light', 'dracula', 'one_dark_pro', 'github_dark', 'github_light',
#  'catppuccin_mocha', 'catppuccin_latte', 'nord', 'material_dark',
#  'solarized_light', 'monokai']

# Create your application
app = fxwidgets.FXApplication()
window = fxwidgets.FXMainWindow(title="Custom Theme Demo")
window.show()

# Apply your custom theme, everywhere
fxstyle.apply_theme("monokai")

app.exec()
```

!!! note
    `FXApplication` is a themed root (see "Registering Themed Roots" further down), so `apply_theme()` reaches every window without you touching one.

A file that cannot be read raises `OSError` (`FileNotFoundError` for a wrong
path), and one that is no YAML raises `yaml.YAMLError`, both from
`set_color_file` itself. The colours already loaded stay in force.

## Switching Themes at Runtime

```python
from fxgui import fxstyle

fxstyle.apply_theme("dracula")
```

`apply_theme(name)` takes one theme name. It saves the choice (see below), rebuilds
the stylesheet, puts the theme's stylesheet, palette and font on every
themed root, and emits `theme_changed`. A name that is not a theme raises
`ValueError`; anything that is not a string raises `TypeError`.

!!! tip
    The choice is saved through `fxconfig`, and the next time the
    application starts, `FXApplication` loads it again. It is saved only
    when a person can have chosen it: on Qt's headless platforms
    (`offscreen`, `minimal`, as in tests and scripts) `apply_theme` does not
    save. Pass `save=True` to save anyway, or `save=False` to never save,
    for example when applying `load_saved_theme()` at startup.
    `apply_row_size` takes the same `save` keyword.

!!! note
    Built-in themes: `dark`, `light`, `dracula`, `one_dark_pro`, `github_dark`, `github_light`, `catppuccin_mocha`, `catppuccin_latte`, `nord`, `material_dark`, and `solarized_light`.

## What a Theme Puts on a Window

A themed root (see below) gets three things, and each has one job:

| Part | Where it comes from | What it carries |
|------|---------------------|-----------------|
| Stylesheet | `style.qss` plus every registered fragment, `@tokens` resolved | Shapes, borders, radii, states (hover, pressed, focus) and each widget's own look. The text colour. |
| Palette | `fxstyle.palette()` | Default fills: a window's `Window`, an item view's `Base`, `Highlight`, and the rest |
| Font | `fxstyle.font()` | The body family of the theme at `fxstyle.FONT_SIZE` (13 px), weight `fxstyle.drawn_weight(fxstyle.BODY_WEIGHT)` (500 in a dark theme, 400 in a light one), no hinting |

The base rule for every widget carries no fill and no font. So:

- `label.setFont(...)` keeps the size and family you gave it.
- A plain `QLabel` on a coloured card shows the card, not a box of its own.
- `item.setBackground(...)` on a list or tree item shows.
- Every list, tree and table scrolls by the pixel, in an app or inside a
  host. The sheet sets this each time it styles the view, so a
  `setVerticalScrollMode` call holds only until the next restyle. A view that wants to scroll by the
  row says so in a rule of its own, by objectName:
  `QTreeView#shots { qproperty-verticalScrollMode: ScrollPerItem; }`.

!!! warning "Inside a host application"
    Inside Houdini, Maya or Nuke, fxgui themes its own windows, never the
    host's `QApplication`. Qt then gives a widget made or moved into such
    a window after it was shown the host's palette and font, never the
    window's. So a window themed inside a host adds a few rules to its own
    stylesheet: the body font and size for every widget, and the surface
    behind the window and its dialogs. There, a widget's own `setFont()`
    loses to that rule, as it does to any stylesheet font. To set a font
    in a host, give the widget its own stylesheet (`font-size: 16px;`).

## Reading Theme Colors

For custom drawing, read colours when you paint instead of keeping them.

```python
from qtpy.QtGui import QColor, QPainter
from fxgui import fxstyle


def paintEvent(self, event):
    painter = QPainter(self)
    painter.fillRect(self.rect(), QColor(fxstyle.colors().surface))
```

`fxstyle.colors()` returns the current theme as a namespace of colour
names. It is cached per theme, so reading it in every `paintEvent` costs
one attribute lookup. It is the one way to read a colour; for a name held
in a variable, `getattr(fxstyle.colors(), name)`. An unknown name raises
`AttributeError` listing the names that exist.

## Registering Themed Roots

`fxstyle.register_themed_root(root)` makes a widget, or the `QApplication`
itself, a themed root. It gets the current stylesheet, palette and font at
once, and again on every later `apply_theme()`. Qt passes the stylesheet
down to every child, so you register the top-level widget once.

```python
from qtpy.QtWidgets import QApplication
from fxgui import fxstyle

application = QApplication([])
fxstyle.register_themed_root(application)
```

Most applications never call it:

| Class | Registers |
|-------|-----------|
| `FXApplication` | Itself, so every window is themed |
| `FXMainWindow`, `FXFloatingDialog`, `FXSplashScreen`, `FXSystemTray`'s menu | Themselves, which counts only inside a host |

While the `QApplication` is a themed root, `register_themed_root(widget)`
does nothing. The application's sheet already reaches every widget, and a
window that wore a sheet of its own as well would get the old theme's
palette back on the next switch: its edges and its tab area would stay in
the old colours.

A registered widget carries the `fxThemedRoot` property
(`fxstyle.ROOT_PROPERTY`), which a stylesheet may select on.

`fxstyle.unregister_themed_root(root)` forgets a root: later switches skip
it. It keeps the sheet, palette and font it wears; reset them yourself if
you need to, as a test fixture does.

## Reacting to Theme Changes

`fxstyle.theme_changed` is a signal emitted after a switch, with the new
theme's name. It is for side effects only: a cached pixmap to redraw, a
highlighter to run again.

```python
from fxgui import fxstyle


def _on_theme_changed(theme_name: str):
    print(f"Theme switched to {theme_name}")


fxstyle.theme_changed.connect(_on_theme_changed)
```

Connect a widget's own method, not a lambda. Qt drops a connection to a
method of a widget when the widget is deleted; a lambda has no widget for
Qt to drop it with, so it outlives the widget and runs on a dead one.

Nothing about looks needs this signal. The stylesheet, the palette, the
colours read in `paintEvent` and the icons all take the new theme by
themselves.

## The Control Language

Every fxgui control is built from the same few parts. A new control
reuses them, so it looks like it belongs.

### Size and shape

| Part | Value | Where it comes from |
|------|-------|---------------------|
| Height | 32 px at the 13 px body font | `fxstyle.control_height(widget)`: the font's line plus 5 px of padding and a 1 px border on each side |
| Corner radius of a control, a row, a tab or a pane | 9 px | `fxstyle.BUTTON_RADIUS`, `@button_radius` in QSS |
| Corner radius of a popup or a floating card (menu, combo list, completer list, tooltip, banner, progress card, drop zone, `FXFloatingDialog`) | 12 px | `fxstyle.CARD_RADIUS`, `@card_radius` |
| Menu row | 24 px at the 12 px body font | `QMenu::item` padding |
| Tool button | a 22 px box around a 16 px icon | `QToolButton` margin 2 px, padding 2 px, a reserved 1 px edge |
| Tab | one 4 px gap above, below and between pills | tab margin `4px 2px`, the same for `QTabBar` and QtAds tabs |
| Segmented tab (`mark_as_segmented`) | 28 px tabs side by side on a 36 px track: 4 px padding, 12 px corners | tab margin `4px 0`, the first and last 4 px off the track's ends |
| Tab count (`set_tab_count`) | a 20 px badge, 4 px after the label, 10 px text at weight 500 | `QTabBar QLabel#fxTabCount`, `@small_radius` |
| Splitter handle | an 8 px hit area, or the width `setHandleWidth` gives a marked one | `QSplitter::handle` width |
| Border | 1 px, solid | Every control |

No rule names a 2, 4 or 8 px radius in pixels. Two shapes do keep pixels:
a pill (a slider groove, a scroll thumb, a progress bar) rounds at half
its thickness, and a part set inside a 1 px border rounds 1 px less
than its frame.

Two sizes set every height, so controls side by side share one centre
line:

| Size | Value | Who takes it |
|------|-------|--------------|
| `fxstyle.control_height(widget)` | 32 px at the 13 px body font | Every control with text or a button's box: push buttons, `FXIconButton`, `FXSplitButton`, `FXJoinedGroup`, line edits, combo boxes, spin boxes, `FXSearchBar`, `FXFilePathWidget`, `FXBreadcrumb`, the `FXTagInput` field, the `FXTimelineSlider` row |
| `fxstyle.INDICATOR_SIZE`, `@indicator_size` | 16 px | An on/off mark: a check box or radio indicator, and the knob of `FXToggleSwitch` (its track is 36 x 20 px) |

A mark is smaller than the row and centres in it: an `FXToggleSwitch` is
`control_height` tall, its 20 px track in the middle, so it lines up
with the button beside it. A slider handle (14 px) and a status dot do
the same. A control that sizes itself returns these from `sizeHint()`.
A plain icon `QToolButton` in a toolbar sizes to its icon. The Buttons
page of the gallery shows one row of every control.

A spin box reaches a line edit's height by its padding, which differs by
Qt version: PySide6 6.5 sizes a spin box 3 px shorter than later Qt for
the same padding, so fxstyle picks the padding when it builds the sheet.

### Names for the look's values

Code that sizes or weighs something of its own reads these names, never
the numbers, so it follows fxgui when the look moves.

| Name | Value | What it is |
|------|-------|------------|
| `fxstyle.font_rank(name)` | In a dark theme `(13, 500)` for `"body"`, `(15, 600)` for `"section"`, `(18, 600)` for `"card"`; a step lighter in a light theme | A text rank's pixel size and the weight Qt draws it at in the current theme (or `theme=`); an unknown rank raises `ValueError` |
| `fxstyle.BODY_WEIGHT` | 400 | Body text's weight, on the CSS scale |
| `fxstyle.EMPHASIS_WEIGHT` | 500 | The step above: names, titles, headers, a tooltip's title, a selected or emphasised word |
| `fxstyle.STRONG_WEIGHT` | 600 | The step above emphasis: a group's title |
| `fxstyle.drawn_weight(weight)` | `weight` + 100 in a dark theme, `weight` in a light one | The weight to give a QFont: Qt draws light text on a dark ground lighter than a browser does (see `fxgui/fonts/README.md`). Sheets read `@body_weight`, `@emphasis_weight` and `@strong_weight`, already drawn |
| `fxstyle.DIALOG_GUTTER` | 20 px | A dialog's left and right margin |
| `fxstyle.DIALOG_EDGE` | 16 px | A dialog's top and bottom margin |
| `fxstyle.DIALOG_GAP` | 12 px | The space between a dialog's parts (text, fields, buttons) |
| `FXThumbnailDelegate.PILL_HEIGHT`, `.PILL_PADDING` | 20 px, 6 px | A neutral status tag's height and its text's side padding |
| `FXStatusBar.ICON_SIZE`, `FXStatusItem.ICON_SIZE` | 14 px | The side of a status item's or message's icon |

```python
from qtpy.QtGui import QFont
from fxgui import fxstyle

size, weight = fxstyle.font_rank("section")
font = QFont(fxstyle.font())
font.setPixelSize(size)
font.setWeight(QFont.Weight(weight))
layout.setContentsMargins(fxstyle.DIALOG_GUTTER, fxstyle.DIALOG_EDGE,
                          fxstyle.DIALOG_GUTTER, fxstyle.DIALOG_EDGE)
layout.setSpacing(fxstyle.DIALOG_GAP)
```

### The web look's parts

| Part | Value | Name |
|------|-------|------|
| A compact button, in a row or a panel | 24 px, small text, 16 px icon | `fxstyle.mark_compact(button)`, `fxstyle.COMPACT_HEIGHT` |
| A filter field | 28 px, small text, its text 32 px in | `FXSearchBar`, `fxstyle.FILTER_DROP` (4 px under a control) |
| Rows of a tree, a table or a list | the row size in force (28 / 36 / 52 px), live, also when another process of the application saves a new one | `fxstyle.apply_row_size(size)`, `fxstyle.row_height(view)`; a word-wrapping list (`setWordWrap(True)` before it shows) starts its rows at 28 px; a table keeps a row height the application set |
| A denser view's rows | one row size under the one in force (24 / 28 / 36 px) | `fxstyle.mark_dense(view)` |
| A view that fills its pane | no frame of its own | `fxstyle.mark_flush(view)`; `FXDockArea` marks a pane whose body is a view |
| A reading pane (a task's details) | content 24 px in, blocks 24 px apart | `fxstyle.READING_INSET` |
| Column rules | after the first column always; every column when chosen (Window > Column lines) | `fxstyle.column_lines()`, `fxstyle.apply_column_lines(on)`, `fxstyle.draw_column_rule(...)` for a delegate of your own |
| A meter's track | the text at 8 % over the pane (9 % light), held so the fill reads at 3:1 | `@meter_track`, `FXMeterBar` |
| A sorted header section | its label and arrow in `text_strong` | drawn by `FXProxyStyle` |
| One header section's ink | a weekend's day dimmed, today's in the accent: any of `INKS`, over the muted header and a sorted section's strong ink | `fxstyle.ink_section(header, section, token)`; None gives it back |
| A select | its value in `text_strong`, a 20 px chevron in `text_dimmed` | `QComboBox` |
| A tooltip | `text_strong`; one line at the body's weight, keys after a middle dot | `tip()`, `apply_tip()` |
| Keyboard focus | the control's 1 px accent edge plus a 3 px ring outside it at 25 %: the accent round inputs and primary buttons, the text round other buttons | `fxstyle.FOCUS_RING_WIDTH`, `fxstyle.FOCUS_RING_ALPHA` |

The focus ring is a sibling drawn over the control, grown by 3 px: a sheet
cannot draw outside a widget. It shows only for focus that came by
keyboard, and the parent's edge clips it, as a web page's overflow does;
the control's own accent edge still shows focus there. Check boxes, radio
buttons, switches and rows keep their own focus marks.

### Fills and edges by state

One rule under every row of the table: **the accent marks keyboard
focus, a selection, the current item and the primary action. Hover is
never the accent.** Hover is a neutral fill, so a hovered control never
looks like the focused one.

| State | Push button, `FXSplitButton` | Tool button (flat) | Input (line edit, combo box, spin box) | Row in a list, tree or table | Menu item, combo or completer row | Tab |
|-------|------|------|------|------|------|------|
| Rest | fill `@surface`, edge `@border_light` | no fill | fill `@surface_sunken`, edge `@border` | no fill | no fill | text `@text_muted` |
| Hover | fill `@state_hover`, edge kept | fill `@state_hover_overlay`, no edge | edge `@border_light` | fill `@state_hover`, text kept | fill `@accent_primary`, text `@text_on_accent_primary` | fill `@state_hover` in the pill's shape, no edge, text kept |
| Pressed | fill `@state_pressed` | fill `@state_pressed_overlay` | | fill `@accent_primary` | fill `@accent_secondary` | |
| Checked or current | fill `@state_pressed`, edge `@grid` | fill `@state_pressed_overlay`, no edge | | selected: fill `@accent_primary`, focused view or not | check mark | pill `@state_pressed`, no edge |
| Checked and hovered | fill `@state_checked_hover` | fill `@state_checked_hover_overlay` | | | | |
| Keyboard focus | edge `@accent_primary` | edge `@accent_primary` | edge `@accent_primary` | the delegate's ring | | edge `@accent_primary` |
| Disabled | fill `@surface`, edge `@border`, text `@text_disabled` | no fill | text `@text_disabled` | | text `@text_disabled` | |

A primary button (`FXPrimaryButton`) is filled `@primary_button`, hovers
`@primary_button_hover` and presses `@primary_button_pressed`; its focus
edge is `@text`, and disabled it is `@surface_alt` with `@text_disabled`.
A button with `fxRole="danger"` (the verb of `FXConfirmDeleteDialog`) is
filled the same way from `@feedback_error_foreground`: `@danger_button`,
`@danger_button_hover`, `@danger_button_pressed`, its text
`@text_on_danger`, the pole that reads on it at 4.5:1.
Text edits and views do not change on hover. A menu is the one place the
pointer moves the current item, so there alone hover is the accent.

Focus never draws a box around a control. It recolours the edge the
control already has, so nothing moves. Qt's own focus rectangle is off:
`FXProxyStyle` (which `FXApplication` installs) never draws it, and inside
a host each list, tree and table of a themed window gets its own
`FXProxyStyle` when it first shows, so a focused current cell keeps its
`BackgroundRole` on PySide6 6.5 as well.

### Focus shows only after the keyboard

A control wears its focus look only when focus came by keyboard: Tab,
Shift+Tab, or a shortcut. A click still gives the control focus, but it
looks as it does at rest once the pointer leaves. This is a browser's
`:focus-visible`.

| Focus came from | Focus look |
|-----------------|------------|
| Tab, Shift+Tab, a shortcut | Shown |
| A mouse click | Hidden |
| A menu closing, a window coming back, a `setFocus()` call | As the last input was: shown after a key, hidden after a click |

fxgui sets the `fxFocusVisible` property (`fxstyle.FOCUS_VISIBLE_PROPERTY`)
on the focused widget, true only for keyboard focus, and clears it when
focus leaves. A themed root turns this on for every widget under it,
including widgets made later and widgets inside a host. For your own
rules, select on the property, not on `:focus` alone:

```css
MyWidget[fxFocusVisible="true"]:focus { border-color: @accent_primary; }
```

A widget that paints its own focus look asks
`fxstyle.focus_visible(widget)` instead of `hasFocus()`. The first call
starts the focus watch, so ask once before the widget can take focus: in
`paintEvent`, or once when it is built.

A colour of your own can be a token name or a colour string:
`fxstyle.qcolor(value)` returns the QColor for either, read from the theme
in force, and an invalid QColor for anything else.

Inside a host, the property reaches the host's own widgets too, but only
fxgui's widgets are restyled when it changes.

### Parts that must be seen

The bundled `@border` tokens sit close to the surface (about 1.2:1).
That is fine for a button, whose text says what it is. A control whose
shape is the only thing you see (a switch, a slider handle) needs more.

| Part | Token | Rule |
|------|-------|------|
| Edge of a slider handle, and a slider's empty groove | `@control_edge` | `border_strong`, darkened or lightened until it reads at 3:1 on `@surface` |
| Text of a tab that is not the current one | `@text_muted` | 4.5:1 on `@surface`, as every text ink is |
| Current tab | A `@state_pressed` pill with `@text`, no edge | The same look on `QTabBar` and QtAds pane tabs. A hovered tab shows a lighter `@state_hover` pill, its text still `@text_muted`; a hovered current tab keeps its `@state_pressed` fill. The two fills stand at least 1.2:1 apart |
| Filled part of a slider | `@accent_primary` | Reads at 3:1 on `@surface`; told from the groove by its hue and the handle |
| Track of a switch, off | `@text_dimmed` | 4.5:1 on `@surface`, as every text ink is |
| Thumb of a switch | `@surface`, on and off | Pushed to 3:1 on the track |
| Moving part of a spinner | `@accent_primary` | Over a `@border_light` track |

A slider's groove and span both read at 3:1 on `@surface`, so they cannot
also read at 3:1 on each other: the bundled accents reach only 3.4:1 to
7.8:1 on their surface. The span's hue and the handle at its end tell the
two apart.

3:1 is the WCAG minimum for the parts of a control
(`fxstyle.CONTROL_CONTRAST`). `fxstyle.readable_ink(background, ink,
3.0)` pushes any colour of your own to it.

### Accent, text and icons

- The accent marks the one thing to look at: the main action, a
  selection, the current item, a filled span, a keyboard-focused edge.
- Text is `@text`. Secondary text and placeholders are `@text_muted`.
  Text on an accent fill is `@text_on_accent_primary`.
- Icons take `color="icon"`; on an accent fill, `icon_on_accent_primary`.
- A popup (a menu, a combo box's list, a completer's list,
  `FXCommandPalette`) and a tooltip are `@surface` with a 1 px `@border`
  at `@card_radius`, their rows inset 4 px. A menu, combo or completer row
  is its text plus 4 px above and below, 24 px at the 12 px body font, and
  a separator runs the menu's full width. A hovered menu item, combo row
  or completer row is `@accent_primary` with `@text_on_accent_primary`
  text. No state moves a row's text.
- A menu bar item keeps one box, at the button radius, in every state.
  At rest it is bare; hovered, `@state_hover`; with its menu open,
  `@state_pressed` with `@text`.
- A table or tree header is flat `@text_muted` text over one 1 px
  `@border` rule, with no box around a section. It sits flush with the
  view's frame: a view with a header has no inner padding. A list or a
  tree with its header hidden keeps a 4 px inset at the top only, and a
  tree follows its header hidden or shown at any time. Rows run to the
  frame's sides, and a scroll bar's thumb sits centred between the rows
  and the frame.
- A splitter handle and the gap between dock widgets show nothing at
  rest: a plain one is clear, one marked with `mark_as_frame` (as the
  dock gaps are) is the frame. Under the pointer, and for as long as it
  is dragged, a 1 px `@accent_primary` line lights down its middle,
  fading in over `MOTION_FAST` (150 ms; at once under reduced motion).
  The handle keeps its whole width as the hit area and its resize
  cursor. A splitter never takes keyboard focus, so the handle has no
  focus look: the keyboard never used the old dot grip either.
- A segmented bar (`fxstyle.mark_as_segmented(tabs)`) is for a view
  switch, as Table | Gantt. Its tabs sit side by side on a
  `@state_pressed` track; the current one is a chip in `@surface` with a
  1 px `@border` ring and a faint drop, its text `@text_strong`, the
  others `@text_muted`, turning `@text` under the pointer. The chip
  slides to a newly picked tab on the spring over `MOTION_SPRING`
  (400 ms), from wherever it is, or jumps under reduced motion. A plain
  bar keeps the pill look and its gaps.
- A tab's count (`fxstyle.set_tab_count(tabs, index, count)`) is a
  20 px badge 4 px after the label: 10 px `@text` at weight 500 on
  `@surface`, a 1 px `@border_light` ring. A screen reader reads the tab
  as "Label, N". On a plain or a segmented bar; on a closable bar whose
  close buttons stand on the right, the count stands before the label.
- A progress bar is a 4 px pill: a `@control_edge` track and an
  `@accent_primary` chunk, no text unless you turn it on with
  `setTextVisible(True)`. It is the slider's groove.
- A tab widget's page is a pane card (`@surface`, a 1 px `@pane_border`),
  as a dock pane is. A `QToolBox` section is a flat 28 px header with a
  chevron, a hover fill and the open one at weight 600. A plain
  `QDockWidget` title is flat `@surface` with `@text`.
- A tab bar too full for its tabs scrolls. Its two scroll buttons are
  opaque in the strip's colour, with a 4 px gap off the last tab's cut
  text.

### Popups, cards and shadows

| Kind | Examples | Frame | Shadow |
|------|----------|-------|--------|
| Popup: a window that closes when you click away, or a tooltip | `QMenu`, a combo box list, `FXCommandPalette`, a completer or calendar popup, a tooltip | `@border`, `@card_radius` | The platform's own. Windows draws one under every popup window. Every popup and tooltip under a themed root asks Windows 11 for flyout corners (`fxutils.round_window_corners`) when it shows, which is the 8 px flyout radius. fxgui paints none. |
| Floating card: a panel over the window that stays until it is done | `FXNotificationBanner`, `FXProgressCard`, `FXFloatingDialog` | `@border`, `@card_radius` | One painted shadow: `fxutils.add_shadow(card)`, in the theme's `@shadow` and `@shadow_blur`, 6 px down unless you pass another offset |

A shadow reads its colour and blur from the theme each time it draws, so
it follows a switch with no call.

A modal dialog dims the window behind it. `FXConfirmDeleteDialog` and
`FXFloatingDialog` do it on their own; any other dialog opts in with
`fxutils.dim_behind(dialog)`. While the dialog is up through `exec()`,
`open()` or `setModal(True)`, its parent's window wears `@modal_scrim`,
faded in over `fxstyle.MOTION_BASE` (at once under reduced motion). The
veil takes no clicks, follows the window's size and lifts when the
dialog hides. A dialog with no parent, a modeless one and a popup dim
nothing.

`FXCommandPalette` opens centred across its window. `position` puts it
at `"top"` (under the menu bar and the command rows), `"center"` (the
default) or `"bottom"` (over the status bar). It stays inside a window
too small for it. Anything else raises `ValueError`.

### Sliders and switches

| Control | Rest | Hover | Focus | Disabled |
|---------|------|-------|-------|----------|
| `QSlider` handle | fill `@surface`, edge `@accent_primary` | a thicker edge | edge `@text` | fill `@surface`, edge `@border` |
| `QSlider`, `FXRangeSlider` groove and span | groove `@control_edge`, span `@accent_primary` | | | span `@border_strong` |
| `FXToggleSwitch` off | fill `@text_dimmed`, no edge | fill `@text_toned` | edge `@accent_primary` | fill `@surface`, edge `@border` |
| `FXToggleSwitch` on | fill `@accent_primary`, no edge | fill `@primary_button_hover` | edge `@text` | fill `@surface_alt`, edge `@border` |

The switch's fills are pushed to 3:1 on `@surface` when a theme's own
accent misses it.

Every `QSlider` gets these rules from the base sheet.

### Cards in item views

`FXThumbnailDelegate` draws a row as a card when the row has a
`Qt.BackgroundRole`. The fill is that colour. Give it a token name, and
the card follows every theme switch:

```python
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QTreeWidgetItem

item = QTreeWidgetItem(["sh010"])
item.setData(0, Qt.BackgroundRole, "surface")
```

The card's edge is `@border_light`. A selected card is filled and edged
with `@accent_primary`. A row with no background has no card.

A hovered row is filled with `@state_hover` and keeps its own text
colour, as in a plain list. On a card whose shade comes within 1.2:1 of
`@state_hover`, as a deep row's does, the hover is the card itself made
1.2:1 lighter (darker on a light theme). Call
`FXThumbnailDelegate.apply_transparent_selection(view)` on the view so
Qt's own highlight does not show under the delegate's.

### Motion

Every animation takes one of five durations and one of two curves, so
things that move together feel alike.

| Duration | Value | Used for |
|----------|-------|----------|
| `fxstyle.MOTION_INSTANT` | 100 ms | A popup, a menu or a tooltip fading in (`POPUP_FADE_MS`) |
| `fxstyle.MOTION_FAST` | 150 ms | A row's hover fading once the pointer leaves; a banner sliding out |
| `fxstyle.MOTION_BASE` | 200 ms | A window fading in (`WINDOW_FADE_MS`), a switch's thumb, a collapsible section, a banner sliding in, a tray panel arriving |
| `fxstyle.MOTION_SLOW` | 300 ms | A page or a dock pane fading in as it rises 4 px (`PANEL_FADE_MS`, `PANEL_RISE`) |
| `fxstyle.MOTION_SPRING` | 400 ms | Anything that travels: a dock pane growing open (`PANEL_OPEN_MS`), banners closing up their stack |

`fxstyle.ease_out()` is the curve for fades and short slides: it leaves
fast and settles slowly, the cubic bezier (0.2, 0) (0, 1).
`fxstyle.ease_spring()` follows a damped spring (stiffness 520, damping
40) that settles in `MOTION_SPRING` with under 1 % overshoot. Each call
returns a new `QEasingCurve`:

```python
from qtpy.QtCore import QPropertyAnimation
from fxgui import fxstyle

slide = QPropertyAnimation(card, b"pos", card)
slide.setDuration(fxstyle.MOTION_SPRING)
slide.setEasingCurve(fxstyle.ease_spring())
```

Set the `FXGUI_REDUCED_MOTION` environment variable to `1` and every
animation fxgui runs is skipped: each one lands on its end state at
once, with no timer left running. That covers the window, popup, page
and pane fades, a pane growing open, a row's hover fade, a switch's
thumb, a collapsible or accordion section, a banner sliding in, out and
closing up its stack, a tray panel's entrance and a splash screen's
fade. A rejected key in `FXValidatedLineEdit` still flashes the border
red, but the field does not shake. Spinners and busy lines keep turning:
they say work is under way. Check `fxstyle.motion()` before you start an
animation of your own.

## Registering Your Own Widget Styles

`fxstyle.register_widget_style(qss)` adds a QSS fragment to the theme
stylesheet. Call it once, when your module is imported, with your class
name as the selector. The fragment may use any `@token`.

```python
from fxgui import fxstyle

fxstyle.register_widget_style("""
    MyWidget {
        background: @surface;
        border: 1px solid @border;
        border-radius: 4px;
    }
""")
```

An image in a rule names an icon and a token: `image: ~icon(chevron-down,
icon);` draws the icon library's `chevron-down` in the theme's `@icon`
colour. Every arrow and chevron of the base sheet is drawn this way. The
icon is written as a PNG at 16 px, and at 2x and 3x for scaled screens;
give the size the rule draws it at as a third value, `~icon(chevron-down,
icon, 12)`, or Qt shrinks the 16 px picture and blurs it. A PNG, unlike
an SVG, needs no Qt plugin, which some DCCs fail to load.

Fragments come after the base stylesheet and are resolved again on every
switch. Registering after themed roots exist re-applies the sheet to them
at once, so import order does not matter.

To style a window inside a DCC, register it with
`fxstyle.register_themed_root(window)`: it gets the sheet, the rules a
window inside a host needs, the palette and the font, and again on every
switch. `fxstyle.resolve(qss)` resolves the tokens of a sheet of your own.

## Repolishing After a Property Change

If your QSS uses a dynamic property in a selector, for example
`MyBanner[level="error"] { ... }`, Qt does not look at the rule again when
you call `setProperty()`. Call `fxutils.repolish()` after it:

```python
from qtpy.QtWidgets import QLabel
from fxgui import fxutils

banner = QLabel("Disk full")
banner.setProperty("level", "error")
fxutils.repolish(banner)
```

## The Custom Widget Contract

A custom widget follows the theme with no base class and no signal when
it does one of these:

| The widget | Do this |
|------------|---------|
| Has a look QSS can say | Register the rules with `register_widget_style()`, `@tokens` for colours, your class name as the selector |
| Paints itself | Read `fxstyle.colors()` inside `paintEvent()` |
| Shows an icon | `fxicons.set_icon()` or `get_icon()`, colours named by token (see [Icons](icons.md)) |
| Changes state | Set a dynamic property and call `fxutils.repolish()` |

Connect to `fxstyle.theme_changed` only for a side effect a switch has
beyond looks.

```python
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QWidget
from fxgui import fxstyle

fxstyle.register_widget_style("""
    MyStatusChip {
        border: 1px solid @border;
        border-radius: 10px;
    }
""")


class MyStatusChip(QWidget):
    """A chip that takes the theme's colours when painted."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(fxstyle.colors().surface))
        painter.setPen(QColor(fxstyle.colors().text))
        painter.drawText(self.rect(), Qt.AlignCenter, "Ready")
```

### Available Color Tokens

Every role in the tables at the top of this page is a token: `@surface`
in QSS, `fxstyle.colors().surface` in code. So are the computed ones:
`@text_on_accent_primary`, `@icon_on_accent_primary`, `@primary_button`,
`@danger_button`, `@text_on_danger`, `@modal_scrim`,
`@control_edge`, `@card_radius`, `@shadow`, `@shadow_blur`,
the flattened feedback colours (`@feedback_error_foreground`,
`@feedback_info_background`, ...), `@button_radius` and the
font roles (`@font_body`, `@font_title`, `@font_mono`).
