# :material-widgets: Widgets

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

The [fxwidgets](../technical/fxgui/fxwidgets/index.md) module holds these classes:

| Class | What it is |
|-------|------------|
| `FXAccordion` | Collapsible sections stacked; one open at a time unless `exclusive=False` |
| `FXApplication` | The `QApplication` that themes every window it owns |
| `FXAvatar` | Round avatar: a photo, or initials on a disc coloured by the name |
| `FXBreadcrumb` | Clickable breadcrumb trail; double-click it to type a path |
| `FXCamelCaseValidator` | Accepts camelCase letters only |
| `FXCapitalizedLetterValidator` | Accepts a name starting with a capital letter |
| `FXCheckableComboBox` | Combo box whose popup stays open while several rows are ticked |
| `FXCodeBlock` | Read-only code with syntax highlighting |
| `FXCollapsibleWidget` | A titled section that opens and shuts its content |
| `FXColorLabelDelegate` | Item delegate drawing each row as a coloured label chosen by its text |
| `FXCommand` | One row of an `FXCommandPalette`: a label, a callable, keys, a section |
| `FXCommandPalette` | Popup search over a window's commands, or over rows to go to |
| `FXCommandRow` | A toolbar fixed in place, whose margins survive style changes |
| `FXConfirmDeleteDialog` | Asks for a name typed exactly before an act with no undo; Enter never deletes |
| `FXDropZone` | Drop target for files or folders, with a browse button and a file list |
| `FXElidedLabel` | Label that cuts its text with "..." when it does not fit |
| `FXEmojiButton` | Round icon button that opens an `FXEmojiPicker` and can insert into an editor |
| `FXEmojiPicker` | Popup grid of emoji, keyboard navigable |
| `FXFilePathWidget` | File or folder path field with a browse button |
| `FXFilteredTree` | An `FXKeyboardTree` under a filter bar, with expand-all and collapse-all |
| `FXFloatingDialog` | Dialog that opens at the pointer |
| `FXFlowLayout` | Layout that wraps its widgets onto new lines, like words |
| `FXFuzzySearchList` | List with a search field that matches loosely |
| `FXFuzzySearchTree` | Tree with a search field that matches loosely |
| `FXIconButton` | Round icon button; checkable, filled with the accent when checked |
| `FXIconLabel` | Label that draws an icon in the theme's colours at paint time |
| `FXIconLineEdit` | Line edit with an icon on the left or right |
| `FXItemDelegate` | Item delegate that switches icons to their hover and selected looks |
| `FXJoinedGroup` | Widgets side by side in one pill outline, such as a status and a Post button |
| `FXKeyboardTree` | Tree whose row menus, Enter and typing work from the keyboard |
| `FXKeycap` | One shortcut drawn as a key, round at the button radius; follows every theme switch |
| `FXLettersUnderscoreValidator` | Accepts letters and underscores, numbers optional |
| `FXLoadingOverlay` | Spinner over a widget, dimming it and blocking its input |
| `FXLoadingSpinner` | Animated loading indicator: spinner, dots or pulse |
| `FXLowerCaseValidator` | Accepts lowercase letters, numbers and underscores optional |
| `FXMainWindow` | Main window with menus, toolbar, status bar and a theme menu |
| `FXMentionEdit` | Text box that offers people by name after an @ and lists who it names |
| `FXNotificationBanner` | Card with a message that slides in from a window's right edge |
| `FXOutputLogHandler` | Logging handler that writes records into an `FXOutputLogWidget` |
| `FXOutputLogWidget` | Read-only log display with search |
| `FXPasswordLineEdit` | Password field with a show/hide button |
| `FXPrimaryButton` | The main action of a form, on the theme's accent |
| `FXProgressCard` | Card showing a task's progress and status |
| `FXPygmentsHighlighter` | Pygments syntax highlighter for any `QTextDocument` |
| `FXRangeSlider` | Slider with two handles for a low and a high value |
| `FXRatingWidget` | Star rating input, halves optional |
| `FXResizedScrollArea` | Scroll area that says when it is resized and can fit its content |
| `FXSearchBar` | Search field with an optional filter dropdown |
| `FXSeating` | Seats a tray panel off its icon or the pointer and slides it in |
| `FXSingleInstance` | Lock on a local socket name; a second start wakes the first |
| `FXSingleton` | Metaclass for Qt classes that have one instance |
| `FXSortedTreeWidgetItem` | Tree row that sorts numbers in text naturally (v2 before v10) |
| `FXSplashScreen` | Splash screen with a title, a text and a progress bar |
| `FXSplitButton` | Split button whose click and dropdown both have keys |
| `FXStatusBar` | Status bar with an accent line, messages, items and a busy line |
| `FXStatusDot` | Small clickable circle in a feedback colour, grey for no state |
| `FXStatusItem` | Icon and word on a status bar, lit when clickable |
| `FXSystemTray` | System tray icon with a menu |
| `FXTagChip` | One tag, removable or not |
| `FXTagInput` | Field that turns what you type into `FXTagChip`s |
| `FXThemeColors` | The theme's colours by dot name, as `fxstyle.colors()` returns them |
| `FXThemeManager` | Holds the `theme_changed` signal; `theme_manager` is its one instance |
| `FXThreadLine` | Line over a comment thread, from the comment's face into each reply's |
| `FXThumbnailDelegate` | Item delegate with thumbnails, status dots, labels and stars |
| `FXTimelineSlider` | Timeline with playback, keyframes, markers and a loop region |
| `FXToggleSwitch` | On/off switch that slides |
| `FXTooltip` | Widget-hosting tooltip, for what native tooltips cannot do |
| `FXTooltipManager` | Replaces every tooltip of the application with an `FXTooltip` |
| `FXTooltipPosition` | Where an `FXTooltip` sits against its anchor |
| `FXValidatedLineEdit` | Line edit that shakes and flashes when its validator refuses a key |
| `FXWidget` | Widget holding an optional Designer file in a padded box layout |

`fxdocking.FXDockArea` docks named panes around a body; it needs the
`docking` extra (`pip install fxgui[docking]`).

And these functions and constants:

| Name | What it does |
|------|--------------|
| `align_labels` | Gives the labels of several forms one right-aligned column |
| `apply_tip` | Sets a rich tooltip and a plain status tip on a widget (see [Tooltips](#tooltips)) |
| `fix_wrapped_heights` | Gives every word-wrapped label under a widget the height its width needs |
| `grab_screen_region` | Lets the user drag out a screen region and returns it, or `None` on Escape |
| `keycap` | Renders one shortcut as a key in a tooltip's HTML; on a window, use `FXKeycap` |
| `set_tooltip` | Attaches an `FXTooltip` to a widget or an item |
| `tip` | Returns the HTML `apply_tip` sets |
| `theme_manager` | The `FXThemeManager` instance |
| `DEFAULT_EMOJIS` | The emoji an `FXEmojiPicker` offers by default |
| `CRITICAL`, `ERROR`, `WARNING`, `SUCCESS`, `INFO`, `DEBUG` | Severities for messages, banners and progress cards |

!!! tip
    Every widget follows a theme switch with no call of its own.

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

`FXThumbnailDelegate` reads item-data roles of its own off the items it
paints, from `Qt.UserRole + 1` up to `FIRST_FREE_ROLE`. A view that puts
roles of its own on the same items derives them from `FIRST_FREE_ROLE`:

``` python
from fxgui.fxwidgets import FXThumbnailDelegate

ROW_KIND_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE
ROW_COLOR_ROLE = FXThumbnailDelegate.FIRST_FREE_ROLE + 1
```

!!! warning
    Do not guess a margin instead. `Qt.UserRole + 10` is
    `CHILD_COUNT_VISIBLE_ROLE`: a view storing its own value there gets a
    child count drawn on rows with no children.

A role added to the delegate moves `FIRST_FREE_ROLE` up, and every role
derived from it moves too.

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

The title renders in the theme's primary text, the body dimmed, and the shortcut sits right-aligned as a keycap. The HTML names palette roles, not colours, and Qt reads them when the tooltip shows, so a tooltip set in one theme shows in the theme of the moment. Inside a host, those are the host's colours, as the host draws the tooltip box. Qt's rich text draws no rounded background, so the keycap in a tooltip is square. Every string is HTML-escaped, so a path holding `&` or `<` reaches the user as text.

Two lower-level helpers are exported alongside it: `tip()` returns the HTML if you need to set it yourself, and `keycap()` renders one shortcut as a key (through `QKeySequence`, so a Mac shows the platform glyphs rather than the literal "Ctrl"). A label reads rich text once, when its text is set, so a keycap on a window is an `FXKeycap` instead: a widget, round at the button radius, that follows every theme switch.

Reach for [`FXTooltip`](../technical/fxgui/fxwidgets/index.md) instead when a native tooltip cannot do the job:

- hosting live widgets (icons, images, action buttons)
- staying up while the pointer is over the tooltip itself
- persistent or programmatic show/hide
- arrow-anchored placement relative to a specific widget

### Opting in to FXTooltipManager

`FXTooltipManager` installs an application-wide event filter that replaces *every* tooltip with an `FXTooltip`. It is opt-in:

``` python
window = fxwidgets.FXMainWindow(rich_tooltips=True)
```

Without `rich_tooltips=True`, tooltips are Qt's own. The manager adds:

- **Tooltips that stay while the pointer is on them.** They hide on a delay, so a user can move onto one to finish reading. Native tooltips vanish on the first mouse move.
- **Item-view tooltips with no code.** Hovering a row in any item view builds a tooltip from the `FXThumbnailDelegate` roles: a 200 px thumbnail, `name (type)` and the description. Native tooltips show `Qt.ToolTipRole` only.
- **Delays of your own.** `FXTooltipManager.install(show_delay=..., hide_delay=...)` sets them for the whole application. Native tooltips use the platform style's delay.
- **An arrow and anchored placement.** The tooltip sits against the widget or item with an arrow pointing at it. Native tooltips appear at the pointer.
- **Icons and images inside a tooltip**, fade animations and a drop shadow.

`set_tooltip()` returns `None` while the manager is installed, and stores the rich fields on the widget for it. Without the manager it creates an `FXTooltip` for the widget and returns it.
