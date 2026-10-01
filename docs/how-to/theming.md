# :material-theme-light-dark: Theming

fxgui uses a YAML configuration file to define all theme colors. YAML supports **anchors and aliases** for theme inheritance, allowing you to create new themes that extend existing ones and override only specific colors.

## Understanding the Theme Structure

The default `style.yaml` file contains several sections:

```yaml
# Feedback colors for status messages
feedback:
  debug:
    foreground: "#26C6DA"
    background: "#006064"
  info:
    foreground: "#7661f6"
    background: "#372d75"
  success:
    foreground: "#8ac549"
    background: "#466425"
  warning:
    foreground: "#ffbb33"
    background: "#7b5918"
  error:
    foreground: "#ff4444"
    background: "#7b2323"

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

  dracula:
    <<: *dark  # Inherit from dark theme
    accent_primary: "#bd93f9"  # Override specific colors
```

## Theme Color Roles - Complete Reference

Each theme defines semantic color roles. All names are designed to clearly indicate their purpose:

### Accent Colors

| Role | Purpose |
|------|---------|
| `accent_primary` | Primary interactive color - hover borders, selections, progress/slider gradient end, menu selections |
| `accent_secondary` | Secondary interactive color - gradient starts, item hover backgrounds, menu pressed states |

### Surface Colors (Backgrounds)

| Role | Purpose |
|------|---------|
| `surface` | Main widget/window backgrounds, buttons, selected tabs, toolbar |
| `surface_alt` | Alternate surface - odd rows in lists/tables, secondary panels |
| `surface_sunken` | Recessed/inset areas - input fields, lists, menus, status bar, slider tracks |
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
| `text_muted` | De-emphasized text - inactive tabs, placeholders, secondary labels |
| `text_disabled` | Disabled widget text |
| `text_on_accent_primary` | *(Optional)* Text on `accent_primary` backgrounds (e.g., selected items). Auto-computed if omitted |
| `text_on_accent_secondary` | *(Optional)* Text on `accent_secondary` backgrounds (e.g., hovered items). Auto-computed if omitted |

### Interactive State Colors

| Role | Purpose |
|------|---------|
| `state_hover` | Hover state backgrounds - buttons, dock widgets |
| `state_pressed` | Pressed/checked/active backgrounds - buttons, tabs, tool buttons |

### Scrollbar Colors

| Role | Purpose |
|------|---------|
| `scrollbar_track` | Track/gutter background, also used for menubar/statusbar borders |
| `scrollbar_thumb` | Draggable thumb, also used for checked header backgrounds |
| `scrollbar_thumb_hover` | Thumb hover state |

### Layout Colors

| Role | Purpose |
|------|---------|
| `grid` | Table gridlines, header section borders |
| `separator` | Separator/splitter hover backgrounds |

### Slider Colors

| Role | Purpose |
|------|---------|
| `slider_thumb` | Slider handle/knob color |
| `slider_thumb_hover` | Slider handle hover and pressed states |

### Icon Color

| Role | Purpose |
|------|---------|
| `icon` | Tint color for monochrome icons via `fxicons.get_icon()` and standard Qt icons |

## Feedback Colors Reference

Used by `FXNotificationBanner`, `FXOutputLogWidget`, and other status/feedback widgets:

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
    separator: "#75715e"

    slider_thumb: "#f8f8f2"
    slider_thumb_hover: "#ffffff"

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
| Stylesheet | `fxstyle.build_stylesheet()`: `style.qss` plus every registered fragment, `@tokens` resolved | Shapes, borders, radii, states (hover, pressed, focus) and each widget's own look. The text colour. |
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
one attribute lookup. `fxstyle.get_theme_colors()` returns the same
colours as a plain dict. An unknown name raises `AttributeError` listing
the names that exist.

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
| `FXMainWindow`, `FXFloatingDialog`, `FXSplashScreen`, `FXSystemTray`'s menu, `FXTooltip` | Themselves, which counts only inside a host |

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
| Corner radius of a control or a menu | 4 px | `fxstyle.BUTTON_RADIUS`, `@button_radius` in QSS |
| Corner radius of a floating card (tooltip, banner, progress card, drop zone, `FXFloatingDialog`) | 8 px | `fxstyle.CARD_RADIUS`, `@card_radius` |
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

### Fills and edges by state

| State | Button (`QPushButton`, `FXSplitButton`) | Input (line edit, combo box, `FXSearchBar`) | Primary (`FXPrimaryButton`) |
|-------|------|-------|---------|
| Rest | fill `@surface`, edge `@border_light` | fill `@surface_sunken`, edge `@border` | fill and edge `@primary_button` |
| Hover | fill `@state_hover`, edge `@accent_primary` | edge `@accent_primary` | fill `@primary_button_hover` |
| Pressed or checked | fill `@state_pressed` | | fill `@primary_button_pressed` |
| Focus | edge `@accent_primary` | edge `@accent_primary` | edge `@text` |
| Disabled | fill `@surface`, edge `@border`, text `@border_strong` | | fill `@surface_alt`, edge `@border`, text `@text_disabled` |

Focus never draws a box around a control. It recolours the edge the
control already has, so nothing moves.

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
| Edge of a switch or a slider handle | `@control_edge` | `border_strong`, darkened or lightened until it reads at 3:1 on `@surface` |
| Filled part of a slider | `@accent_primary` | Reads at 3:1 on the `@surface_sunken` groove |
| Thumb of a switch | `@text_muted` off, `@text_on_accent_primary` on | Pushed to 3:1 on the track |
| Moving part of a spinner | `@accent_primary` | Over a `@border_light` track |

3:1 is the WCAG minimum for the parts of a control
(`fxstyle.CONTROL_CONTRAST`). `fxstyle.readable_ink(background, ink,
3.0)` pushes any colour of your own to it.

### Accent, text and icons

- The accent marks the one thing to look at: the main action, a
  selection, a filled span, a hovered or focused edge.
- Text is `@text`. Secondary text and placeholders are `@text_muted`.
  Text on an accent fill is `@text_on_accent_primary`.
- Icons take `color="icon"`; on an accent fill, `icon_on_accent_primary`.
- A menu is `@surface_sunken` with a 1 px `@border`. Its hovered item is
  `@accent_primary` with `@text_on_accent_primary` text.
- A menu bar item keeps one box, at the button radius, in every state.
  At rest it is bare; hovered, `@state_hover`; with its menu open,
  `@accent_primary` with `@text_on_accent_primary` text.

### Popups, cards and shadows

| Kind | Examples | Frame | Shadow |
|------|----------|-------|--------|
| Popup: a window that closes when you click away | `QMenu`, a combo box list, `FXCommandPalette` | `@border`, `@button_radius` | The platform's own. Windows draws one under every popup window, and `fxutils.round_window_corners` asks Windows 11 for flyout corners. fxgui paints none. |
| Floating card: a panel over the window that stays until it is done | `FXTooltip`, `FXNotificationBanner`, `FXProgressCard`, `FXFloatingDialog` | `@border`, `@card_radius` | One painted shadow: `fxutils.add_shadow(card)` with its defaults, black at 80 of 255, 20 px blur, no offset |

A shadow has no theme token. It is black at low opacity in every theme,
as the platform's own popup shadow is.

`FXCommandPalette` opens centred across its window. `position` puts it
at `"top"` (under the menu bar and the command rows), `"center"` (the
default) or `"bottom"` (over the status bar). It stays inside a window
too small for it. Anything else raises `ValueError`.

### Sliders and switches

| Control | Rest | Hover | Focus | Disabled |
|---------|------|-------|-------|----------|
| `QSlider`, `FXRangeSlider` handle | fill `@slider_thumb`, edge `@control_edge` | fill `@slider_thumb_hover` | fill `@text_on_accent_primary`, edge `@accent_primary` | fill `@surface`, edge `@border` |
| `QSlider`, `FXRangeSlider` groove and span | groove `@surface_sunken`, span `@accent_primary` | | | span `@border_strong` |
| `FXToggleSwitch` off | fill `@surface_sunken`, edge `@control_edge` | edge `@accent_primary` | edge `@accent_primary` | fill `@surface`, edge `@border` |
| `FXToggleSwitch` on | fill `@accent_primary` | fill `@primary_button_hover` | edge `@text` | fill `@surface_alt`, edge `@border` |

The switch's fills are pushed to 3:1 on `@surface` when a theme's own
accent misses it.

Every `QSlider` gets these rules from the base sheet, the threshold
slider of `FXFuzzySearchList` and `FXFuzzySearchTree` included.

### Cards in item views

`FXThumbnailDelegate` draws a row as a card when the row has a
`Qt.BackgroundRole`. The fill is that colour. Give it a token name, and
the card follows every theme switch:

```python
item.setData(0, Qt.BackgroundRole, "surface")
```

The card's edge is `@border_light`. A selected card is filled and edged
with `@accent_primary`. A row with no background has no card.

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

Fragments come after the base stylesheet and are resolved again on every
switch. Registering after themed roots exist re-applies the sheet to them
at once, so import order does not matter.

`fxstyle.build_stylesheet(theme=None)` returns the whole sheet: the base,
every fragment, tokens resolved. `fxstyle.load_stylesheet()` returns the
same sheet with the rules a window inside a host needs in front. Neither
changes anything; they only build the text.

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
`@control_edge`, `@card_radius`,
the flattened feedback colours (`@feedback_error_foreground`,
`@feedback_info_background`, ...), `@radius`, `@button_radius` and the
font roles (`@font_body`, `@font_title`, `@font_mono`).
