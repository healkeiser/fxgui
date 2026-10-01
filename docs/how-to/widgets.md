# :material-widgets:{.scale-in-center} Widgets

## Subclass the `FXMainWindow`

You can subclass any widgets in the `fxwidgets` module. Here's a practical example with `FXMainWindow`:

``` python
# Third-party
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton

# Internal
from fxgui import fxwidgets, fxicons


class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.add_layout()
        self.add_buttons()

    def add_layout(self):
        """Adds a vertical layout to the main layout of the widget."""

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

    def add_buttons(self):
        """Adds buttons to the main layout of the widget."""

        # Use fxicons for theme-aware icons
        home_button = QPushButton("Home")
        fxicons.set_icon(home_button, "home")

        settings_button = QPushButton("Settings")
        fxicons.set_icon(settings_button, "settings")

        self.main_layout.addWidget(home_button)
        self.main_layout.addWidget(settings_button)
        self.main_layout.addStretch()


class MyWindow(fxwidgets.FXMainWindow):
    def __init__(self, parent=None):
        # `toolbar=False` rather than hiding it afterwards: a hidden
        # toolbar is still in the layout's own bookkeeping, so the menu
        # bar's right-click "Toolbars" entry offers it straight back.
        super().__init__(parent, toolbar=False)

        self.setCentralWidget(MyWidget(parent=self))
        self.adjustSize()


application = fxwidgets.FXApplication()
window = MyWindow()
window.setWindowTitle("Subclassed FXMainWindow")
window.show()
application.exec_()
```

## The Gallery

```bash
python -m fxgui.examples
```

A window opens with every public widget, a page per kind: buttons,
inputs, display, containers, lists and trees, the timeline, windows and
dialogs, and docking. Each box is titled with the class names it shows.
**Window > Theme** switches the theme, so you can see a widget in each.
The Docking page needs the `docking` extra (`pip install fxgui[docking]`).

## Available Widgets

The [fxwidgets](../technical/fxwidgets/index.md) module provides many pre-styled widgets:

| Widget | Description |
|--------|-------------|
| `FXAccordion` | Accordion container with expandable sections |
| `FXApplication` | Application with automatic theming and style |
| `FXAvatar` | Round avatar: a photo, or initials on a disc coloured by the name |
| `FXBreadcrumb` | Clickable breadcrumb trail for hierarchical navigation |
| `FXCheckableComboBox` | Combo box whose popup stays open while several rows are ticked |
| `FXCollapsibleWidget` | Expandable/collapsible container |
| `FXCommandPalette` | Popup search over a window's commands (`FXCommand` rows) or rows to go to |
| `FXColorLabelDelegate` | Delegate for color label rendering in views |
| `FXConfirmDeleteDialog` | Asks for a name typed exactly before an act with no undo; Enter never deletes |
| `FXElidedLabel` | Label with automatic text elision |
| `FXEmojiButton` | Round icon button that opens an emoji picker and can insert into an editor |
| `FXEmojiPicker` | Popup grid of emoji, keyboard navigable |
| `FXFilePathWidget` | File/folder path input with browse button |
| `FXFlowLayout` | Layout that wraps its widgets onto new lines, like words |
| `FXFloatingDialog` | Styled floating dialog |
| `FXIconButton` | Round icon button; checkable, filled with the accent when checked |
| `FXIconLineEdit` | Line edit with icon support |
| `FXJoinedGroup` | Widgets side by side in one pill outline, such as a status and a Post button |
| `FXLoadingSpinner` | Animated loading spinner |
| `FXLoadingOverlay` | Loading overlay for widgets |
| `FXMainWindow` | Main window with toolbar, status bar, and theme toggle |
| `FXMentionEdit` | Text box that offers people by name after an @ and lists who it names |
| `FXNotificationBanner` | Notification banner for messages |
| `FXOutputLogWidget` | Log display with level filtering |
| `FXPasswordLineEdit` | Password input with visibility toggle |
| `FXPrimaryButton` | The main action of a form, on the theme's accent |
| `FXProgressCard` | Progress indicator card |
| `FXRangeSlider` | Dual-handle range slider |
| `FXRatingWidget` | Star rating input widget |
| `FXResizedScrollArea` | Smooth-scrolling scroll area |
| `FXSearchBar` | Search input with filtering |
| `FXSeating` | Seats a tray panel off its icon or the pointer and slides it in |
| `FXSplashScreen` | Customizable splash screen |
| `FXStatusDot` | Small clickable circle in a feedback colour, grey for no state |
| `FXStatusBar` | Themed status bar |
| `FXSystemTray` | System tray icon with menu |
| `FXTagInput` | Tag/chip input widget |
| `FXThumbnailDelegate` | Delegate for thumbnail rendering in views |
| `FXThreadLine` | Line over a comment thread, from the comment's face into each reply's |
| `FXTimelineSlider` | Timeline slider for media/animation |
| `FXToggleSwitch` | iOS-style toggle switch |
| `FXTooltip` | Widget-hosting tooltip, for what native tooltips cannot do |
| `FXWidget` | Base widget with optional UI file loading |

!!! tip
    All widgets automatically inherit the current theme and update when the theme changes.

## Breadcrumbs

``` python
crumb = FXBreadcrumb(home_icon="", segments_focusable=False)
crumb.set_path(["pilot", "sq010", "sh0040", "comp"])
crumb.set_edit_placeholder("Type a shot")
```

- Every segment but the last is a button: it tints under the pointer
  and shows a pointing hand. The last one is where the path already is,
  so it is bold and does nothing.
- The strip behind the segments is a filled field, brighter while the
  pointer is over it. Double-click it to type a path; a press anywhere
  outside closes the editor, and so does `exit_edit_mode()`.
- The colours are worked out each time the strip paints, from the
  theme and from what the breadcrumb sits on: the frame colour on a
  framed window's toolbar or a band marked with `mark_as_frame`, the
  surface anywhere else. The text reads at 4.5:1 on both fills and the
  edge shows at 1.3:1 against the ground and both fills, in every
  bundled theme. A theme switch needs no call.
- `segments_focusable=False` takes the segments out of the Tab order.
  The back and forward buttons and the path editor keep their stops.

The starting colours are class attributes, so a subclass names its own
tokens:

``` python
class HouseCrumb(FXBreadcrumb):
    STRIP_RESTING_TOKEN = "surface_alt"
    SEGMENT_HOVER_TOKEN = "accent_secondary"
    SEGMENT_HOVER_ALPHA = 120
```

Do not point `STRIP_RESTING_TOKEN` at `surface`: in every bundled theme
that is the window's own colour, so on a plain window the strip
disappears.

## Your Own Item-Data Roles

`FXThumbnailDelegate` reads its own item-data roles off the items it
paints, and it claims `Qt.UserRole + 1` through `Qt.UserRole + 14`. A
view that stamps roles of its own on the same items must derive them from
the delegate's published ceiling rather than guess a margin past that
range:

``` python
from fxgui.fxwidgets import FXThumbnailDelegate

ROW_KIND_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE
ROW_COLOR_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE + 1
```

!!! warning
    Guessing here has already cost real time. A studio view picked
    `Qt.UserRole + 10` as its own and met `CHILD_COUNT_VISIBLE_ROLE`,
    which showed up as a child count on rows that had no children --
    a bug with no obvious connection to the role that caused it.

Roles added to the delegate move `FIRST_FREE_ROLE` up, and anything
derived from it moves with them.

## Tooltips

`apply_tip` is the everyday path. It formats a small HTML string and hands it to Qt's own `setToolTip`, plus a markup-free status tip for the window's status bar:

``` python
# Internal
from fxgui.fxwidgets import apply_tip

apply_tip(
    save_button,
    "Save",
    "Write the current scene to disk, overwriting the last version",
    "Ctrl+S",
)
```

The title renders in the theme's primary text, the body dimmed, and the shortcut sits right-aligned as a keycap. Colors are read from the active theme on every call, so tooltips follow a theme switch and a studio's custom theme with no extra wiring. Every string is HTML-escaped, so a path holding `&` or `<` reaches the user as text.

Two lower-level helpers are exported alongside it: `tip()` returns the HTML if you need to set it yourself, and `keycap()` renders one shortcut as a key (through `QKeySequence`, so a Mac shows the platform glyphs rather than the literal "Ctrl").

Reach for [`FXTooltip`](../technical/fxwidgets/index.md) instead when a native tooltip cannot do the job:

- hosting live widgets (icons, images, action buttons)
- staying up while the pointer is over the tooltip itself
- persistent or programmatic show/hide
- arrow-anchored placement relative to a specific widget

### Opting in to FXTooltipManager

`FXTooltipManager` installs an application-wide event filter that replaces *every* tooltip with an `FXTooltip`. It is opt-in:

``` python
window = fxwidgets.FXMainWindow(rich_tooltips=True)
```

!!! warning "Changed in 12.0.0"
    Constructing an `FXMainWindow` under an `FXApplication` used to install the manager automatically. It no longer does, so tooltips are Qt's own unless you pass `rich_tooltips=True`. If your application relied on the manager without asking for it, you lose the following until you opt in:

    - **Tooltips that survive the pointer.** The manager's tooltips are persistent and hide on a delay, so a user can move onto one to finish reading. Native tooltips vanish on the first mouse move.
    - **Automatic item-view tooltips.** With the manager, hovering a row in any item view builds a tooltip from `FXThumbnailDelegate` roles: a 200px thumbnail preview, `name (type)`, and the description. Native tooltips show `Qt.ToolTipRole` only, and nothing sets it for you.
    - **Configurable delays.** `FXTooltipManager.install(show_delay=..., hide_delay=...)` controls appearance timing application-wide. Native tooltips use the platform style's delay, which the application cannot override per widget.
    - **The arrow and anchored placement.** Manager tooltips are positioned against the widget or item rectangle with an arrow pointing at it. Native tooltips appear at the cursor.
    - **Icons and images inside a tooltip**, fade animations, and the drop shadow.
    - **`set_tooltip()` return value.** With the manager it returns `None` and stores rich fields as dynamic properties; without it, it falls back to creating a per-widget `FXTooltip` and returns that instance. The tooltip still renders; only the return value and the delay source change.

    Nothing was removed: `FXTooltip`, `FXTooltipManager` and `set_tooltip` behave exactly as before once `rich_tooltips=True`.
