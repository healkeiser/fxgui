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
| `accent_primary` | Selection, keyboard focus, the current menu item, a filled span, the primary action |
| `accent_secondary` | A primary button's hover fill and a pressed menu item; never a hover fill |

### Surface Colors (Backgrounds)

| Role | Purpose |
|------|---------|
| `surface` | Main widget/window backgrounds, buttons, selected tabs, toolbar |
| `surface_alt` | Alternate surface - odd rows in lists/tables, secondary panels |
| `surface_sunken` | Recessed/inset areas - input fields, lists, status bar |
| `frame` | The chrome around the panes of a framed window (optional) |
| `well` | Lists and logs set into a pane (optional) |
| `pane_border` | The 1 px edge of a pane on the frame (optional) |
| `splitter_mark` | The dots on a marked splitter's handles (optional) |
| `tooltip` | Tooltip popup backgrounds |

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
| `border_light` | Subtle borders - tooltips, button borders, tab borders |
| `border_strong` | Emphasized borders - frames, separator lines |

### Text Colors

| Role | Purpose |
|------|---------|
| `text` | Primary text for all widgets |
| `text_muted` | Secondary text: placeholders, secondary labels, headers, the tabs that are not current |
| `text_disabled` | Disabled widget text |
| `text_on_accent_primary` | *(Optional)* Text on `accent_primary` backgrounds (e.g., selected items). Auto-computed if omitted |
| `text_on_accent_secondary` | *(Optional)* Text on `accent_secondary` backgrounds (a hovered primary button). Auto-computed if omitted |

`text` and `text_muted` are held to 4.5:1 (`fxstyle.TEXT_CONTRAST`, WCAG AA) on every surface they sit on: `surface`, `surface_sunken`, `surface_alt`, `well`, `frame`, `tooltip` and `state_hover`, and `text` on `state_pressed` too. A theme's value that misses it is darkened or lightened until it reads, so `fxstyle.colors().text` can differ from the file. `text` then moves on until it stands 1.5:1 off `text_muted` (`fxstyle.MUTED_STEP`), so the two always read as two ranks; where `text` is already black or white, `text_muted` steps back toward the surface instead, as far as it still reads at 4.5:1.

An omitted `text_on_accent_*` is black or white, whichever reads better on the accent.

### Interactive State Colors

| Role | Purpose |
|------|---------|
| `state_hover` | Every hover fill: rows, buttons, tool buttons, menu bar items, a hovered tab; the current tab's pill. Pushed to 1.2:1 off `surface` when a theme sets it closer |
| `state_pressed` | Pressed and checked fills, an open menu bar item. Pushed to 1.2:1 off `state_hover` (`fxstyle.STATE_MIN_CONTRAST`) when a theme sets the two closer |

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
| `shadow_blur` | Its blur radius in pixels (20) |

### Icon Color

| Role | Purpose |
|------|---------|
| `icon` | Tint color for monochrome icons via `fxicons.get_icon()` and standard Qt icons |

## Feedback Colors Reference

Each theme has a `feedback:` block; a theme without one takes `dark`'s. Used by `FXNotificationBanner`, `FXLogWidget`, and other status widgets. `fxstyle.get_feedback_colors()` returns the current theme's block; one colour is `fxstyle.colors().feedback_error_foreground`.

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

app.exec_()
```

!!! note
    `FXApplication` is a themed root (see "Registering Themed Roots" further down), so `apply_theme()` reaches every window without you touching one.

## Switching Themes at Runtime

```python
from fxgui import fxstyle

fxstyle.apply_theme("monokai")
```

`apply_theme(name)` takes one theme name. It saves the choice, rebuilds
the stylesheet, puts the theme's stylesheet, palette and font on every
themed root, and emits `theme_changed`. A name that is not a theme raises
`ValueError`; anything that is not a string raises `TypeError`.

!!! tip
    The choice is saved through `fxconfig`. The next time the application
    starts, `FXApplication` loads it again.

!!! note
    Built-in themes: `dark`, `light`, `dracula`, `one_dark_pro`, `github_dark`, `github_light`, `catppuccin_mocha`, `catppuccin_latte`, `nord`, `material_dark`, and `solarized_light`.

## What a Theme Puts on a Window

A themed root (see below) gets three things, and each has one job:

| Part | Where it comes from | What it carries |
|------|---------------------|-----------------|
| Stylesheet | `style.qss` plus every registered fragment, `@tokens` resolved | Shapes, borders, radii, states (hover, pressed, focus) and each widget's own look. The text colour. |
| Palette | `fxstyle.palette()` | Default fills: a window's `Window`, an item view's `Base`, `Highlight`, and the rest |
| Font | `fxstyle.font()` | The body family of the theme at `fxstyle.FONT_SIZE` (12 px) |

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
| Height | 28 px at the 12 px body font | `fxstyle.control_height(widget)`: the font's line plus 5 px of padding and a 1 px border on each side |
| Corner radius of a control, a row, a tab, a pane or a tooltip | 4 px | `fxstyle.BUTTON_RADIUS`, `@button_radius` in QSS |
| Corner radius of a popup or a floating card (menu, combo list, completer list, banner, progress card, drop zone, `FXFloatingDialog`) | 8 px | `fxstyle.CARD_RADIUS`, `@card_radius` |
| Menu row | 24 px at the 12 px body font | `QMenu::item` padding |
| Tool button | a 22 px box around a 16 px icon | `QToolButton` margin 2 px, padding 2 px, a reserved 1 px edge |
| Border | 1 px, solid | Every control |

No rule names a 2, 4 or 8 px radius in pixels. Two shapes do keep pixels:
a pill (a slider groove, a scroll thumb, a progress bar) rounds at half
its thickness, and a part set inside a 1 px border rounds 1 px less
than its frame.

Two sizes set every height, so controls side by side share one centre
line:

| Size | Value | Who takes it |
|------|-------|--------------|
| `fxstyle.control_height(widget)` | 28 px at the 12 px body font | Every control with text or a button's box: push buttons, `FXIconButton`, `FXSplitButton`, `FXJoinedGroup`, line edits, combo boxes, spin boxes, `FXSearchBar`, `FXFilePathWidget`, `FXBreadcrumb`, the `FXTagInput` field, the `FXTimelineSlider` row |
| `fxstyle.INDICATOR_SIZE`, `@indicator_size` | 18 px | An on/off mark: a check box or radio indicator, and the track of `FXToggleSwitch` (twice as wide as tall) |

A mark is smaller than the row and centres in it: an `FXToggleSwitch` is
`control_height` tall, its 18 px track in the middle, so it lines up
with the button beside it. A slider handle (14 px) and a status dot do
the same. A control that sizes itself returns these from `sizeHint()`.
A plain icon `QToolButton` in a toolbar sizes to its icon. The Buttons
page of the gallery shows one row of every control.

A spin box reaches a line edit's height by its padding, which differs by
Qt version: PySide6 6.5 sizes a spin box 3 px shorter than later Qt for
the same padding, so fxstyle picks the padding when it builds the sheet.

### Fills and edges by state

One rule under every row of the table: **the accent marks keyboard
focus, a selection, the current item and the primary action. Hover is
never the accent.** Hover is a neutral fill, so a hovered control never
looks like the focused one.

| State | Push button, `FXSplitButton` | Tool button (flat) | Input (line edit, combo box, spin box) | Row in a list, tree or table | Menu item, combo or completer row | Tab |
|-------|------|------|------|------|------|------|
| Rest | fill `@surface`, edge `@border_light` | no fill | fill `@surface_sunken`, edge `@border` | no fill | no fill | text `@text_muted` |
| Hover | fill `@state_hover`, edge kept | fill `@state_hover`, no edge | edge `@border_light` | fill `@state_hover`, text kept | fill `@accent_primary`, text `@text_on_accent_primary` | fill `@state_hover` in the pill's shape, no edge, text kept |
| Pressed | fill `@state_pressed` | fill `@state_pressed` | | fill `@accent_primary` | fill `@accent_secondary` | |
| Checked or current | fill `@state_pressed`, edge `@grid` | fill `@state_pressed`, edge `@accent_primary` | | selected: fill `@accent_primary`, focused view or not | check mark | pill `@state_hover`, edge `@control_edge` |
| Keyboard focus | edge `@accent_primary` | edge `@accent_primary` | edge `@accent_primary` | the delegate's ring | | edge `@accent_primary` |
| Disabled | fill `@surface`, edge `@border`, text `@text_disabled` | no fill | text `@text_disabled` | | text `@text_disabled` | |

A primary button (`FXPrimaryButton`) is filled `@primary_button`, hovers
`@primary_button_hover` and presses `@primary_button_pressed`; its focus
edge is `@text`, and disabled it is `@surface_alt` with `@text_disabled`.
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
`fxstyle.focus_visible(widget)` instead of `hasFocus()`.

Inside a host, the property reaches the host's own widgets too, but only
fxgui's widgets are restyled when it changes.

### Parts that must be seen

The bundled `@border` tokens sit close to the surface (about 1.2:1).
That is fine for a button, whose text says what it is. A control whose
shape is the only thing you see (a switch, a slider handle) needs more.

| Part | Token | Rule |
|------|-------|------|
| Edge of a switch or a slider handle, and a slider's empty groove | `@control_edge` | `border_strong`, darkened or lightened until it reads at 3:1 on `@surface` |
| Text of a tab that is not the current one | `@text_muted` | 4.5:1 on `@surface`, as every text ink is |
| Current tab | `@control_edge` edge on a `@state_hover` pill | The edge reads at 3:1 on `@surface`; the same look on `QTabBar` and QtAds pane tabs. A hovered tab shows the same pill without the edge, its text still `@text_muted` |
| Filled part of a slider | `@accent_primary` | Reads at 3:1 on `@surface`; told from the groove by its hue and the handle |
| Thumb of a switch | `@text_muted` off, `@text_on_accent_primary` on | Pushed to 3:1 on the track |
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
  `FXCommandPalette`) is `@surface` with a 1 px `@border` at
  `@card_radius`, its rows inset 4 px. A menu row is 24 px tall and a
  separator runs the menu's full width. A hovered menu item, combo row or
  completer row is `@accent_primary` with `@text_on_accent_primary` text.
  No state moves a row's text.
- A menu bar item keeps one box, at the button radius, in every state.
  At rest it is bare; hovered, `@state_hover`; with its menu open,
  `@state_pressed` with `@text`.
- A table or tree header is flat `@text_muted` text over one 1 px
  `@border` rule, with no box around a section.
- A splitter handle and the gap between dock widgets show nothing until
  the pointer finds them, then fill with `@accent_primary`. A splitter
  marked with `mark_as_frame` keeps its painted dots.
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
| Popup: a window that closes when you click away | `QMenu`, a combo box list, `FXCommandPalette`, a completer or calendar popup | `@border`, `@card_radius` | The platform's own. Windows draws one under every popup window. Every popup under a themed root asks Windows 11 for flyout corners (`fxutils.round_window_corners`) when it shows, which is the 8 px flyout radius. fxgui paints none. |
| Floating card: a panel over the window that stays until it is done | `FXNotificationBanner`, `FXProgressCard`, `FXFloatingDialog` | `@border`, `@card_radius` | One painted shadow: `fxutils.add_shadow(card)`, in the theme's `@shadow` and `@shadow_blur`, no offset unless you pass one |

A shadow reads its colour and blur from the theme each time it draws, so
it follows a switch with no call. A tooltip is no popup: the compositor
does not round its window, so it keeps `@button_radius`.

`FXCommandPalette` opens centred across its window. `position` puts it
at `"top"` (under the menu bar and the command rows), `"center"` (the
default) or `"bottom"` (over the status bar). It stays inside a window
too small for it. Anything else raises `ValueError`.

### Sliders and switches

| Control | Rest | Hover | Focus | Disabled |
|---------|------|-------|-------|----------|
| `QSlider` handle | fill `@surface`, edge `@accent_primary` | a thicker edge | edge `@text` | fill `@surface`, edge `@border` |
| `QSlider`, `FXRangeSlider` groove and span | groove `@control_edge`, span `@accent_primary` | | | span `@border_strong` |
| `FXToggleSwitch` off | fill `@surface_sunken`, edge `@control_edge` | fill `@state_hover`, edge kept | edge `@accent_primary` | fill `@surface`, edge `@border` |
| `FXToggleSwitch` on | fill `@accent_primary` | fill `@primary_button_hover` | edge `@text` | fill `@surface_alt`, edge `@border` |

The switch's fills are pushed to 3:1 on `@surface` when a theme's own
accent misses it.

Every `QSlider` gets these rules from the base sheet, the threshold
slider of `FXFuzzySearchTree` included.

### Cards in item views

`FXThumbnailDelegate` draws a row as a card when the row has a
`Qt.BackgroundRole`. The fill is that colour. Give it a token name, and
the card follows every theme switch:

```python
item.setData(0, Qt.BackgroundRole, "surface")
```

The card's edge is `@border_light`. A selected card is filled and edged
with `@accent_primary`. A row with no background has no card.

A hovered row is filled with `@state_hover` and keeps its own text
colour, as in a plain list. Call
`FXThumbnailDelegate.apply_transparent_selection(view)` on the view so
Qt's own highlight does not show under the delegate's.

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

An image in a rule names an icon and a token: `image: ~icon(expand_more,
icon);` draws the icon library's `expand_more` in the theme's `@icon`
colour. Every arrow and chevron of the base sheet is drawn this way.

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
from fxgui import fxutils

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
`@control_edge`, `@card_radius`, `@shadow`, `@shadow_blur`,
the flattened feedback colours (`@feedback_error_foreground`,
`@feedback_info_background`, ...), `@button_radius` and the
font roles (`@font_body`, `@font_title`, `@font_mono`).
