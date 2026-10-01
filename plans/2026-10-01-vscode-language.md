# One control language, close to VS Code

Status: spec, nothing implemented. Read-only research; the only files written
are this spec and the renders in the scratchpad (paths at the end).

Baseline: `fxgui/qss/style.qss` as it stood in this worktree on 2026-10-01 at
16:50, which is HEAD `17541eaf` plus the uncommitted "tab option B" work (the
current tab is a rounded `@state_hover` pill with a `@control_edge` edge). That
snapshot is `render/before/style.qss` in the scratchpad. If the tab work lands
differently, re-check section 5.3.

VS Code sources: `microsoft/vscode` at commit `9816d35f69ae` (main, fetched
2026-10-01). Every VS Code value below names its file under that commit. Paths
are shortened: `base/` is `src/vs/base/browser/ui/`, `modernUI/` is
`src/vs/workbench/contrib/modernUI/browser/media/`, `themes/` is
`extensions/theme-defaults/themes/`.

## 1. What to take from where

1. The two in-house references win where they speak. The owner already likes
   them.
2. VS Code fills what they leave open. VS Code now ships an experimental
   "Modern UI" (`workbench.experimental.modernUI`,
   `src/vs/workbench/contrib/modernUI/`). It is the closest match to what fxgui
   already does: panes as rounded cards on a gap, a 3-dot grip on the gap,
   focus rings only after the keyboard, pill tabs. So Modern UI is the VS Code
   source of choice, and the classic workbench CSS is the fallback.
3. VS Code sizes are for a 13 px body font. fxgui's body is 12 px. Heights are
   kept on fxgui's own scale (28 px control, 26 px row) and only the shape
   rules are taken.

## 2. The language the two references share

Read from `fxgui/fxdocking.py` (the `register_widget_style` block and
`_inset`, `_sweep`), the base sheet, and the Hub as rendered in
`ls-pipeline/docs/en/images/apps/hub.png` (rendered 2026-09-30) with
`apps/widgets/layout.py`.

| Part | Value | Where it is today |
|------|-------|-------------------|
| Window behind panes | `@frame`, a step darker than `@surface` | `#fxDocks ... { background: @frame }` |
| Pane | a card: `@surface`, 1 px `@pane_border`, 4 px radius | `#fxDocks ads--CDockAreaWidget` |
| Gap between panes and to the window edge | 6 px | `FXDockManager(gap=6)`; Hub `GAP = 6` |
| Grip on a gap | 5 dots, 2 px, painted | `fxstyle._SplitterMark` |
| Pane tab bar | inside the card, inset by the radius (4 px) left and right, no fill | `_inset`, `ads--CDockAreaTitleBar { background: transparent }` |
| Pane tabs | bare muted text; current tab a 4 px pill, `@state_hover` fill, `@control_edge` edge | style.qss `QTabBar::tab`, `ads--CDockWidgetTab` (option B) |
| Pane buttons (close, undock, tabs menu) | flat icons, no padding, as tall as a tab at most | `#fxDocks ads--CTitleBarButton` |
| List or log inside a pane | a "well": `@well`, between `@surface` and `@frame` | `#fxDocks ads--CDockAreaWidget QAbstractItemView` |
| Table header inside a pane | flat `@surface`, one 1 px `@border` rule under it | `#fxDocks ads--CDockAreaWidget QHeaderView::section` |
| Control height | 28 px (filter field, combo, buttons, breadcrumb) | `fxstyle.control_height` |
| Row height | 26 px in fxgui views; the Hub's card rows pitch at 30 px | `QListView::item { min-height: 26px }`; Hub delegate |
| Row inset from the view edge | 4 px | `QListView, QTreeView { padding: 4px }` |
| Selected row | solid `@accent_primary`, `@text_on_accent_primary` text | `QListView::item:selected` and the Hub's orange `lighting` row |
| Radius | 4 px on controls, rows and panes; 8 px on floating cards | `BUTTON_RADIUS`, `CARD_RADIUS` |
| Edges | 1 px, solid, everywhere | every rule |
| Focus | recolour the edge the control already has, keyboard only | KEYBOARD FOCUS block, `fxFocusVisible` |
| Menu bar and status bar | flat, on `@frame`, no rule under or over them | `QMenuBar[fxFrame="true"]` |
| Type | body 12 px; section 15 px / 600; card 16 px / 600; Lotchi body Inter 500 | `FONT_SIZE`, `_DEFAULT_RANKS`, ls-pipeline `apps/theme.py` |
| Icons | 16 px, `@icon` ink; on an accent fill `@icon_on_accent_primary` | `~icon(name, icon)`; `ICON_SIZE = 14` for Hub status items |

Two things the references show that the base sheet does not yet do:

- The dock block's flat header rule is better than the base sheet's boxed,
  gridded header. The Hub reads well because of it.
- Nothing in either reference uses the accent for hover. The accent appears
  on the selected row, the current pane's frame and the primary action only.

## 3. What VS Code adds

### 3.1 Shape

| Fact | Value | Source |
|------|-------|--------|
| Three radius tiers | controls and rows 4 px; inner containers 6 px; overlays 8 px (menus, quick input, hovers, toasts, dialogs) | `modernUI/roundedCorners.css` header comment and rules; sizes in `src/vs/platform/theme/common/sizes/baseSizes.ts` (`cornerRadius.small` 4, `.medium` 6, `.large` 8, `.xLarge` 12) |
| Menu box | 8 px radius, 1 px border, min width 160 px | `base/menu/menu.ts`, `getMenuWidgetCSS`, `.monaco-menu` |
| Menu rows | 24 px tall, inset 4 px left and right, label padded `0 2em` (24 px at 12 px) | `base/menu/menu.ts`, `.action-menu-item` (height 24px, margin 0 4px) and the vertical action bar rules |
| Menu box padding | 4 px top and bottom | `base/menu/menu.ts`, `.monaco-action-bar.vertical { padding: 4px 0 }` |
| Menu separator | 1 px, full width, 5 px above and below | `base/menu/menu.ts`, `.action-label.separator { margin: 5px 0 }` |
| Shortcut and submenu mark | 70% opacity; 40% when disabled; chevron 16 px | `base/menu/menu.ts`, `.keybinding, .submenu-indicator` |
| Button | padding 4 px 8 px, radius 4, 1 px border, 12 px text on a 16 px line (26 px tall) | `base/button/button.css`, `.monaco-text-button` |
| Split button | the two halves share one outer radius, a 1 px separator between them, the seam square | `base/button/button.css` (`.monaco-button-dropdown`); `modernUI/roundedCorners.css` (split buttons) |
| Disabled | the whole control at 40% opacity | `base/button/button.css`, `.monaco-button.disabled` |
| Input | padding 4 px 6px, radius 4 | `base/inputbox/inputBox.css` |
| Toolbar icon button | 16 px icon, 3 px padding (22 px box), radius 4 in Modern UI | `base/actionbar/actionbar.css`; `modernUI/roundedCorners.css` |
| Check box | 18 px, radius 3, 1 px border | `base/toggle/toggle.css` |
| List rows | 22 px; inset 4 px from the pane edge in Modern UI, the scroll bar stays at the edge | `explorerViewer.ts` (`ITEM_HEIGHT = 22`); `modernUI/padding.css` (`.monaco-list-row { left/right: spacing-size40 }`) |
| Tree indent | 8 px per level plus a 16 px twistie | `base/tree/abstractTree.ts` (`DefaultIndent = 8`), `base/tree/media/tree.css` |
| Part title (pane header) | 35 px classic, 32 px Modern UI | `src/vs/workbench/browser/part.ts` (`TITLE_HEIGHT`, `AREA_HEIGHT_MODERN_UI`); `modernUI/padding.css` |
| Panel tabs, Modern UI | 32 px bar, each tab a 24 px pill at radius 4, 10 px side padding, regular weight, no uppercase | `modernUI/tabs.css`, `.pane-composite-part ... .action-item` and `.active-item-indicator` |
| Section headers (stacked panes) | 28 px in Modern UI, radius 4, hover tint, separator inset 4 px | `modernUI/paneHeaders.css`; `modernUI.contribution.ts` (`MODERN_UI_PANE_HEADER_SIZE = 28`) |
| Scroll bar | 8 px in Modern UI (10 px classic), no arrows, slider radius 4 | `modernUI.contribution.ts` (`MODERN_UI_SCROLLBAR_SIZE = 8`); `base/scrollbar/scrollableElement.ts` (`DEFAULT_SCROLLBAR_SIZE = 10`); `modernUI/roundedCorners.css` |
| Gap grip | 3 dots, 2 px, 5 px apart, 40% foreground | `modernUI/sashHandles.css`; `src/vs/workbench/common/theme.ts` (`modernSash.gripForeground`) |
| Shadows | flat parts, no shadow between panes; overlays keep theirs | `modernUI/shadows.css` |
| Toast | radius 4 classic, 8 Modern UI; 42 px row; 22 px lines; 16 px icon | `notificationsToasts.css`; `notificationsViewer.ts` (`DEFAULT_NOTIFICATION_ROW_HEIGHT = 42`); `notificationsList.css` |
| Hover (tooltip) | padding 4 px 8 px, max width 500 px, 8 px radius in Modern UI | `base/hover/hoverWidget.css`; `modernUI/roundedCorners.css` |
| Spacing ramp | 0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 28, 32, 36, 40 | `baseSizes.ts` (`spacing.size*`) |
| Type ramp | body 13; label 12 (tabs, section titles); metadata 11; badge 10; headings 26 / 18 / 13; two weights, 400 and 600 | `baseSizes.ts` (`fontSize.*`, `fontWeight.*`) |
| Icon | 16 px, 12 px compact | `baseSizes.ts` (`codiconFontSize`) |

### 3.2 Colour by state

The rule VS Code follows across its default themes:

| State | Fill | Edge | Text | Source |
|-------|------|------|------|--------|
| Rest | none or the surface | the control's border | `foreground` | all themes |
| Hover, rows and toolbar buttons | a neutral tint: white at 8% (dark) or black at 8% (light) | unchanged | unchanged | `themes/2026-dark.json` `list.hoverBackground #FFFFFF14`; `2026-light.json` `#00000014`; `listColors.ts` defaults `#2A2D2E` / `#F0F0F0` |
| Hover, buttons | the button's own hover fill | unchanged | unchanged | `button.css` (`.default-colors:hover`) |
| Hover, inputs | no change | no change | no change | `inputBox.css` has no hover rule |
| Pressed | the hover fill; nothing moves | unchanged | unchanged | `button.css` |
| Selected, view has focus | the theme's selection fill | none | selection text | `listColors.ts` `list.activeSelectionBackground` |
| Selected, view without focus | a neutral fill (`list.inactiveSelectionBackground`) | none | `foreground` | `listColors.ts` defaults `#37373D` / `#E4E6F1` |
| Current menu item | accent fill with white text in Dark/Light Modern; a 10 to 15% accent tint with normal text in 2026 Dark/Light | none | see left | `dark_modern.json` `menu.selectionBackground #0078d4`; `2026-dark.json` `#3994BC26` |
| Keyboard focus | 1 px `focusBorder` outline, inset 1 px, only for keyboard focus | | | `src/vs/workbench/browser/media/style.css` (`outline-offset: -1px`); `modernUI/keyboardFocusOnly.css` (`:focus:not(:focus-visible)`) |
| Disabled | the whole control at 40% | | | `button.css` |
| Primary action | accent fill, white text, its own hover fill | same as fill | white | `button.background`, `button.hoverBackground` in every theme |
| Secondary action | neutral fill with a border | `button.secondaryBorder` | `foreground` | `2026-dark.json`, `light_modern.json` |

The one rule under all of it: **the accent marks focus, selection, the
current tab or item, and the primary action. Hover is never the accent.**

## 4. Tokens

No new colour role is needed. Two size tokens and one alias make the rules
readable.

| Token | Value | Kind | Use |
|-------|-------|------|-----|
| `@button_radius` | 4 px | kept | controls, rows, tabs, panes, menu items |
| `@card_radius` | 8 px | kept, use widened | floating cards **and now every popup**: `QMenu`, a combo list frame, `FXCommandPalette`, `QToolTip` |
| `@pane_radius` | 6 px | new, optional | VS Code's inner tier. Not adopted by default: the owner likes 4 px panes. Add only if the owner asks |
| `@row_height` | 26 px | new | `QListView::item`, `QTreeView::item` min/max height, and the menu row (24 + 2 px edge, see 5.4) |
| `@hover` | `@state_hover` | new alias | every hover fill: rows, tool buttons, push buttons, combo rows are excluded (see 5.4) |
| `@selection_inactive` | `@state_pressed` | new alias | a selected row in a view that does not have focus |
| `@text_on_accent_secondary`, `@icon_on_accent_secondary` | as today | kept, fewer uses | after this spec they are read by the primary button's hover only |
| `@accent_secondary` | as today | kept, fewer uses | primary button hover and pressed shade; no longer a hover fill |
| `@separator` | as today | dropped from splitters | a hovered splitter turns `@accent_primary` instead |

Per state, the whole table:

| State | Push button | Tool button (flat) | Input, combo, spin | Row in a view | Menu item | Tab |
|-------|-------------|--------------------|--------------------|---------------|-----------|-----|
| Rest | `@surface`, edge `@border_light` | none | `@surface_sunken`, edge `@border` | none | none | `@tab_muted` text |
| Hover | fill `@hover`, edge unchanged | fill `@hover`, no edge | edge `@border_light` | fill `@hover`, text unchanged | `@accent_primary`, `@text_on_accent_primary` | text `@text` |
| Pressed | fill `@state_pressed` | fill `@state_pressed` | | `@accent_primary` | `@accent_secondary` | |
| Checked / current | fill `@state_pressed`, edge `@grid` | fill `@state_pressed`, edge `@accent_primary` | | selected: `@accent_primary` when the view is active, `@selection_inactive` when not | check mark | pill `@state_hover`, edge `@control_edge` |
| Focus (keyboard) | edge `@accent_primary` | edge `@accent_primary` | edge `@accent_primary` | delegate ring | | edge `@accent_primary` |
| Disabled | `@surface`, edge `@border`, text `@text_disabled` | no fill | text `@text_disabled` | | text `@text_disabled` | |

## 5. Control by control

Each line: what fxgui does now, what changes, where. All in
`fxgui/qss/style.qss` unless a file is named.

### 5.1 Push buttons

- Now: hover sets the edge to `@accent_primary` and the fill to
  `@state_hover`. Keyboard focus also sets the edge to `@accent_primary`. So a
  hovered button and a focused button look the same. That is a real defect:
  after Tab, moving the pointer over another button shows two "focused"
  buttons.
- Change: `QPushButton:hover` keeps its edge and changes the fill only.
  Source: `button.css`, hover changes the background only.
- Now: `QPushButton:disabled` writes its text in `@border_strong`, a border
  colour. Change: `@text_disabled`. Same for `QToolButton[popupMode="1"]:disabled`.
  VS Code dims the whole control to 40%; Qt sheets have no opacity, so the
  disabled ink is the honest equivalent.
- Primary (`[fxRole="primary"]`), flat (`[fxRole="flat"]`): no change.
- `FXSplitButton` / `QToolButton[popupMode="1"]`: hover keeps the edge;
  `::menu-button:hover` keeps its `@border_light` seam instead of turning it
  accent. Matches `modernUI/roundedCorners.css` (one outer radius, flat seam).

### 5.2 Tool buttons

- Now: `QToolButton:hover` is `@accent_secondary` fill, `@accent_primary`
  edge, `@text_on_accent_secondary` ink. In the Lotchi theme that is a dark
  orange box on every toolbar icon the pointer crosses.
- Change: hover is `@hover`, no edge, ink unchanged. Pressed is
  `@state_pressed`, no edge. Checked keeps `@state_pressed` with the
  `@accent_primary` edge, so a toggle that is on still reads as on (VS Code
  `inputOption.activeBorder`). Split `QToolButton:checked, :pressed` into two
  rules.
- The icon then never needs its on-accent colour on hover, so the comment
  above `QToolButton:hover` about the icon hover colour goes.

### 5.3 Tabs

- Now (option B, uncommitted): bare `@tab_muted` text; current tab a 4 px
  pill, `@state_hover` fill, `@control_edge` edge; hover changes text only;
  focus recolours the reserved edge. This already matches VS Code Modern UI
  panel tabs (`modernUI/tabs.css`: 24 px pill at radius 4,
  `modernTab.activeBackground` is a neutral selection fill, regular weight).
  Keep it.
- Change: none to the tabs. One gap: VS Code tints a hovered tab
  (`modernTab.hoverBackground` = `list.hoverBackground`). fxgui changes text
  only. Leave it: the owner ruled text-only hover.
- `QTabWidget::pane`: now a bare 1 px `@border_light` box. Change: a pane card
  like a dock area, `@surface` fill and `@pane_border` edge, so a tab widget
  and a dock pane look the same.
- `QToolBox::tab` (bordered top-rounded boxes, bold when selected): restyle
  as a VS Code section header: no box, 28 px tall, `@button_radius`, a
  chevron at left (`chevron_right` closed, `expand_more` open), hover fill
  `@hover`, text `@text`, weight 600 for the open one. Source:
  `modernUI/paneHeaders.css`.
- `QDockWidget::title` (old `QDockWidget`, not QtAds): `@surface_sunken`
  strip with a `@state_hover` border. Change: flat, `@surface`, the tab
  text style, no border, so a plain dock widget reads as a QtAds pane.

### 5.4 Menus and popups

- Now: `QMenu` radius `@button_radius` (4 px). Windows 11 clips every themed
  popup to its own rounded shape through `fxutils.round_window_corners`
  (`DWMWCP_ROUND`, value 2, `fxutils.py:74`). As I recall Microsoft's
  Windows 11 guidance, `ROUND` is the large radius (8 px) and `ROUNDSMALL`
  the 4 px one; I have no source open for it. If so, the 4 px sheet border
  and the 8 px clip disagree at the corners. Not checked on screen: the
  render is offscreen and has no compositor.
- Change: `QMenu` and the combo list frame use `@card_radius` (8 px), the VS
  Code overlay tier, which is also the Windows 11 flyout radius.
- Now: `QMenu::item` padding `5px 25px`, plus `border: 3px transparent`,
  which names no style and draws nothing. Change: `padding: 4px 24px`,
  `border: none`. A row comes out 24 px at the 12 px body font, VS Code's
  menu row.
- Now: `QMenu::separator` inset 10 px left and 5 px right (lopsided).
  Change: full width inside the 4 px menu padding, `margin: 4px 0px`.
  Source: `menu.ts` separator rule.
- Current item stays `@accent_primary` with `@text_on_accent_primary`
  (Dark/Light Modern do this; 2026 Dark uses a tint instead). A menu is the
  one place the pointer moves the current item, so accent hover is right
  here. Combo popup rows follow the menu, as today.
- Shortcut text at 70%: Qt sheets cannot style a `QMenu` shortcut on its own.
  Not adopted.

### 5.5 Lists, trees, tables

- Now: `QWidget:item:hover` and `QListView/QTreeView::item:!selected:hover`
  fill with `@accent_secondary` and flip the text to
  `@text_on_accent_secondary`. Every row the pointer crosses lights up in a
  second accent.
- Change: hover is `@hover`, text unchanged. Source: `list.hoverBackground`.
- Now: a selected row is `@accent_primary` whether or not its view has
  focus. Change: `::item:selected:active` stays `@accent_primary`;
  `::item:selected:!active` becomes `@selection_inactive` with `@text`. With
  several panes (the Hub), only the pane being worked in shows the accent;
  the others keep their selection in grey. Source:
  `list.inactiveSelectionBackground`. This changes the Hub's look; see open
  point 1.
- Now: `QTreeView:hover`, `QListView:hover`, `QTableView:hover` and the
  widget forms turn the whole view's border accent on hover. Change: drop
  them. A view's edge turns accent on keyboard focus only.
- `QHeaderView::section`: now filled `@border` with a `@grid` box around each
  section. Change: the dock rule, made global: transparent, `@text_muted`,
  left-aligned, one 1 px `@border` rule under it, no vertical lines. Then the
  dock block's two header rules in `fxdocking.py` can go.
- Row height: keep 26 px (`@row_height`). VS Code's 22 px is for a 13 px font
  with no row radius; fxgui's rows are rounded and 12 px.
- `FXThumbnailDelegate` (`fxgui/fxwidgets/_delegates.py`): hover there is
  also `@accent_secondary`. Same change, `@hover` with `@text`. Its
  inactive-selection case needs the same split.

### 5.6 Inputs

- Now: `QLineEdit`, `QComboBox`, `QAbstractSpinBox`, the text edits turn
  their edge accent on hover, the same as keyboard focus.
- Change: hover lifts the edge to `@border_light` (combo, spin box, line
  edit) and changes nothing on the text edits. Keyboard focus alone is the
  accent. VS Code inputs have no hover rule (`inputBox.css`); the small edge
  lift keeps a pointer cue for Qt users. My call, easy to drop.
- Padding `4px 6px` and radius 4 already match `inputBox.css`.

### 5.7 Scroll bars

- Now: 8 px bar, no track, no arrows, a 4 px thumb at radius 2 that widens to
  8 px at radius 4 on hover. Matches Modern UI (8 px, radius 4).
- Change: none. VS Code's thumb is translucent so it reads on any surface
  (`scrollbarSlider.background` is `#797979` at 40%); fxgui's is opaque per
  theme. Fine as long as the thumb reads on `@well`; not measured here.

### 5.8 Splitters and gaps

- Now: a plain `QSplitter::handle` and `QMainWindow::separator` draw a 1 px
  **dashed** border at rest and fill `@separator` on hover.
- Change: nothing at rest; `@accent_primary` on hover. VS Code sashes are
  invisible until hovered, then take `focusBorder`
  (`sash.hoverBorder`). The framed splitter (`[fxFrame="true"]`) keeps its
  painted dots, which already match `modernUI/sashHandles.css` (VS Code uses
  3 dots, fxgui 5; keep 5).

### 5.9 Progress bar

- Now: 8 px, 1 px border, 1 px padding, a reflected gradient from
  `@accent_secondary` to `@accent_primary`.
- Change: a flat 4 px pill, `@control_edge` track, `@accent_primary` chunk,
  no border, no gradient, text off by default. This is the slider's groove,
  so the two read as one family. VS Code's progress bar is a flat 2 px line
  (`progressBar.background`); 4 px keeps it visible on a 28 px row.

### 5.10 Notifications, tooltips, command palette

- `FXNotificationBanner`, `FXProgressCard`, `FXFloatingDialog`: 8 px card,
  painted shadow. Matches the overlay tier. No change.
- `QToolTip`: now `@button_radius`. Change: `@card_radius`, padding
  `4px 8px` unchanged. Source: hover widget in `roundedCorners.css`.
  Caveat: a tooltip is not translucent, so on a platform without
  `round_window_corners` the corners outside 8 px show square. Check on
  Linux before shipping.
- `FXCommandPalette`: 8 px, rows as menu rows (24 px, inset 4 px). VS Code's
  quick input is 600 px wide at radius 8 (Modern UI) with 22 px rows
  (`quickInput.css`). Width is fxgui's own call.

### 5.11 Menu bar

- Now: an item hovered is `@state_hover`; with its menu open it is
  `@accent_primary`. Change: open is `@state_pressed` with `@text`. VS Code
  uses a neutral `menubar.selectionBackground` (`2026-dark.json`
  `#242526`). The accent then means one thing less.
- `QMenuBar::item` margin and padding 5 px: VS Code pads `0 8px` at radius
  5 (`base/menu/menubar.css`). Change padding to `4px 8px`, keep radius 4.

### 5.12 Check boxes, radios, sliders, switches

- 18 px marks already match `toggle.css` (18 px). No change.
- Slider, `FXToggleSwitch`: no change; their rules already follow 3.2.

### 5.13 Type and spacing

- Keep body 12 px, section 15 / 600, card 16 / 600. Add one small rank,
  "meta", 11 px / 400 in `@text_muted`, for secondary lines in rows and
  status items (VS Code `fontSize.label2`). Badge text 10 px / 600
  (`fontSize.label3`).
- Two weights only: the body weight and 600. The Lotchi theme's Inter 500
  body stays a theme choice.
- Spacing: name fxgui's steps on VS Code's ramp, 2, 4, 6, 8, 12, 16, 24, as
  `fxstyle` constants for widgets that lay themselves out. Today's 3 px
  `QToolButton` margin and 2 px padding become 2 and 3 to give a 22 px icon
  box around a 16 px icon, as `actionbar.css` does. ls-pipeline's
  `BLOCK_SPACING = 5` sits off the ramp; that is ls-pipeline's call, noted
  only.

## 6. Renders

Built offscreen (`QT_QPA_PLATFORM=offscreen`, `QT_QPA_FONTDIR=C:/Windows/Fonts`)
from two scratch sheets: `before/style.qss` (the baseline snapshot) and
`after/style.qss` (the snapshot with sections 5.1, 5.2, 5.3 pane, 5.4, 5.5,
5.6, 5.8, 5.9 applied by `make_after.py`). The repo's sheet was not touched.
Each image shows a button row (rest, forced hover, primary, flat icon, tool
button forced hover, disabled), a tab widget, two lists (row 2 forced hover,
row 3 selected; left view active, right inactive) and a menu with "Copy
path" current.

Scratchpad root: `C:/Users/ValentinBeaumont/AppData/Local/Temp/claude/C--Users-ValentinBeaumont-Documents-GitHub-ls-pipeline/ce4aec2c-f8ce-429e-b78b-baa571edbe90/scratchpad/render/`

- `vscode_language_dark.png`: before and after, side by side, dark
- `vscode_language_light.png`: the same, light
- `before_dark.png`, `after_dark.png`, `before_light.png`, `after_light.png`: the halves

What the renders show:

- Hovered button: before, an accent edge (same as focus); after, a fill only.
- Tool button: before, a solid accent square; after, a grey square.
- Lists: before, hover and selection are two blues side by side and hard to
  tell apart; after, hover is grey, the active selection blue, the inactive
  one grey.
- Menu: after, rows 24 px instead of 26, the separators full width, 8 px box.
- Tabs: identical apart from the pane card, by design (5.3).

Defects the renders found in the "after" sheet itself:

1. In the inactive view, the selected row's folder icon stays white (Qt
   draws the icon in its Selected mode). On light grey that is about 1.5:1.
   The view needs normal-mode icons when inactive, which is delegate work
   (`FXThumbnailDelegate`, and plain views via `QStyledItemDelegate`), not a
   sheet rule. Must be solved before 5.5's inactive split ships.
2. In dark, `@state_hover` (`#403f3f`) and `@state_pressed` (`#4a4949`) sit
   close, so a hovered row next to an inactive selection reads almost the
   same. VS Code's own pair is similarly close (`#2A2D2E` / `#37373D`). Worth
   a contrast floor, as `@tab_muted` got: `@state_pressed` pushed to a set
   step from `@state_hover`.
3. Offscreen there is no compositor, so the menu's 8 px corners show the
   sheet's own radius only. The DWM claim in 5.4 is untested.

## 7. Open points and blind spots

1. **Inactive selection grey (5.5) changes the Hub.** Today the Browse tree
   keeps its orange `lighting` row while you work in Workfiles. After, it
   goes grey. VS Code does this, and it tells you which pane has the
   keyboard. The owner's screenshot has the orange row in an unfocused pane,
   so this may be one of the things they like. Ask before shipping that one
   rule; everything else stands without it.
2. VS Code Modern UI is experimental. Its values can move. Each value is
   pinned to commit `9816d35f69ae`.
3. VS Code's 2026 themes tint the current menu item instead of filling it.
   fxgui follows Dark/Light Modern (fill). If the owner prefers the 2026 look,
   it is one token per state in 5.4.
4. I did not render the Hub with the "after" sheet. The Hub rows are drawn
   by `FXThumbnailDelegate`, whose hover is painted in Python, so a sheet-only
   render would not show the Hub's real hover. Do it once the delegate
   follows 5.5.
5. Anchoring risk: VS Code was the brief, so every gap was filled from it.
   Where VS Code's choice exists for its 13 px, no-radius rows (22 px rows,
   2 px progress line), fxgui keeps its own value and says so above.
6. The theming page `docs/how-to/theming.md`, "Fills and edges by state" and
   "Accent, text and icons", must be rewritten with the table in section 4
   when this lands; both still describe accent hover.
