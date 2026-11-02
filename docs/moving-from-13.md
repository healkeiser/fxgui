# :material-swap-horizontal: Moving from 13.x

14.0.0 draws icons from [Lucide](https://lucide.dev/icons) by default, and
an icon is named the way Lucide spells it: `house`, `chevron-down`, `x`.
13.x took Material's names (`home`, `expand_more`, `close`), and 14.0.0
does not translate them. Code written for 13.x can stop with a
`FileNotFoundError` naming a file under `lucide/svg/`.

Find the name on [lucide.dev/icons](https://lucide.dev/icons), or in the
table below, and write that instead.

## Where a Material name now fails

A Material name raises `FileNotFoundError` everywhere fxgui takes a name
without a `library=`:

| Where | 13.x | 14.0.0 |
|-------|------|--------|
| `get_icon`, `get_pixmap`, `get_icon_path`, `set_icon` | `get_icon("home")` | `get_icon("house")` |
| `fallback=` | `get_icon(tool, library="brands", fallback="apps")` | `fallback="layout-grid"`. A fallback is looked up in Lucide even when the call names another library, so it only fails once the first name misses |
| `~icon(...)` in your own stylesheet | `image: ~icon(expand_more, icon);` | `image: ~icon(chevron-down, icon);`. One wrong name stops the whole sheet, not just that one image |
| A name handed to a widget | `FXIconLineEdit(icon_name="visibility")`, `FXBreadcrumb(home_icon="home")`, `FXRatingWidget(empty_icon="star_border")`, `FXDropZone(icon_name="upload_file")`, `create_action(..., icon_name="save")` | The Lucide name. The widget raises when it is built, or when it first draws that state |

## Keep a Material icon

Material ships beside Lucide. Name it on the call:

```python
from fxgui import fxicons

icon = fxicons.get_icon("expand_more", library="material")
```

| 13.x | 14.0.0 |
|------|--------|
| `fxicons.set_default_library(library)`, `fxicons.default_library()` | Gone. Lucide is always the default: pass `library=` to each call that wants another library |

## Common renames

| 13.x (Material) | 14.0.0 (Lucide) |
|-----------------|-----------------|
| `home` | `house` |
| `close`, `clear` | `x` |
| `add` | `plus` |
| `remove` | `minus` |
| `delete` | `trash` |
| `edit` | `pencil` |
| `done` | `check` |
| `expand_more`, `expand_less` | `chevron-down`, `chevron-up` |
| `chevron_left`, `chevron_right` | `chevron-left`, `chevron-right` |
| `arrow_back`, `arrow_forward` | `arrow-left`, `arrow-right` |
| `apps` | `layout-grid` |
| `widgets` | `layout-dashboard` |
| `error` | `circle-alert` |
| `warning` | `triangle-alert` |
| `check_circle` | `circle-check` |
| `cancel` | `circle-x` |
| `help` | `circle-question-mark` |
| `bug_report` | `bug` |
| `content_copy` | `copy` |
| `refresh` | `refresh-cw` |
| `folder_open` | `folder-open` |
| `open_in_new` | `external-link` |
| `filter_list` | `list-filter` |
| `more_horiz` | `ellipsis` |
| `visibility`, `visibility_off` | `eye`, `eye-off` |
| `play_arrow` | `play` |
| `stop` | `square` |
| `schedule` | `clock` |
| `person` | `user` |
| `star_border` | `star` |
| `upload_file` | `file-up` |

Some Material names are also Lucide names for a different picture. They
load without an error and draw the wrong thing: Lucide's `delete` is a
backspace key, not a bin. Check a renamed screen by eye.
