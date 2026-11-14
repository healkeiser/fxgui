# Plan 014: Thumbnails are decoded at the size they are drawn, upright

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/2026-11-14-audit/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat b283eb13..HEAD -- fxgui/fxwidgets/_delegates.py tests/test_delegate_fixes.py tests/test_thumbnail_decode.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (plan 009 also edits `fxgui/fxwidgets/_delegates.py`,
  in other functions; whichever lands second rebases)
- **Category**: perf
- **Planned at**: commit `b283eb13`, 2026-11-14

## Why this matters

`FXThumbnailDelegate` draws a small picture on each tree row. To make it,
`_read_thumbnail` decodes the **whole** image file, then shrinks it. For a
local file this happens on the UI thread, during paint, so a tree of 4K
renders stutters as it scrolls: measured 27 ms per 3840×2160 JPEG, against
2.6 ms when Qt's `QImageReader` is told the target size before decoding
(JPEG can decode at 1/2, 1/4, 1/8 size directly). Also, `QImage(path)`
ignores a photo's EXIF orientation tag, so a phone or camera picture shot
in portrait shows on its side. After this plan, thumbnails decode about 10×
faster and come out upright; nothing else changes.

## Current state

Files:

- `fxgui/fxwidgets/_delegates.py` — `_read_thumbnail` (lines 115–140) is
  the only place a thumbnail file is decoded. It runs on the UI thread for
  local files (`_ThumbnailReads.source`, lines 166–184) and on reader
  threads for network shares (`_work`, lines 214–226). Imports at lines
  29–43 (`QImage` is imported from `qtpy.QtGui`; `QImageReader` is not yet).
- `tests/test_delegate_fixes.py:72-93` — `test_a_thumbnail_is_loaded_once_across_paints`
  counts `QImage(str)` constructions by patching `_delegates.QImage`. After
  this plan the file is read through `QImageReader`, so this test must
  count reader constructions instead (Step 3).
- `tests/test_item_views.py:315-390` — monkeypatches `_read_thumbnail`
  itself; unaffected as long as the signature stays.

`fxgui/fxwidgets/_delegates.py:115-140`:

```python
def _read_thumbnail(
    path: str, known: Optional[float], size: Tuple[int, int]
) -> Tuple[Optional[float], Optional[QImage]]:
    """Return a file's mtime and, unless it is `known`, its scaled picture.

    A QImage, which a reader thread may make: a QPixmap is the UI thread's.
    """
    try:
        stamp = os.path.getmtime(path)
    except (OSError, TypeError):
        return None, None
    if stamp == known:
        return stamp, None
    image = QImage(path)
    if image.isNull():
        image = QImage(str(_FALLBACK_THUMBNAIL))
    # The format a QPixmap holds it in, so it scales as one would.
    image = image.convertToFormat(
        QImage.Format_ARGB32_Premultiplied
        if image.hasAlphaChannel()
        else QImage.Format_RGB32
    )
    return stamp, image.scaled(
        size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
```

`size` is the thumbnail box in device pixels, e.g. `(160, 90)` at 100 %
scale. The cache keys (`_ThumbnailReads._sources[(path, stamp, size)]`
and the `fxgui.thumbnail|...` pixmap key in `_bordered_thumbnail`) are
built by the callers from `path`, mtime and `size`; this plan does not
touch them, so their semantics stay.

Facts measured during planning (offscreen probe, this commit):

- 3840×2160 JPEG into a 320×180 box: 25–27 ms with the code above,
  2.2–2.6 ms with `QImageReader.setScaledSize`; same output size.
- `QImageReader.setScaledSize(QSize(100, 50))` on a 200×400 image returns
  100×50: it does **not** keep the aspect ratio. The aspect-correct size
  must be computed first.
- A JPEG with a hand-written EXIF APP1 segment, orientation 6: `QImage(path)`
  reads it 400×200 (sideways); `QImageReader` with `setAutoTransform(True)`
  reads it 200×400 (upright); `reader.autoTransform()` defaults to False.
  `setScaledSize` applies to the stored orientation, before the rotation.
- `QImageWriter.setTransformation(...)` does not write an EXIF tag (it
  rotates the pixels), so a test must write the EXIF segment by hand
  (Test plan, test 3).

Conventions: Google-style docstrings, type annotations, Qt only through
`qtpy`, comments explain why in one line. A reader thread must never raise
(`_work` already catches `Exception`).

## Commands you will need

Run from the repo root (Windows; Git Bash or PowerShell).

| Purpose | Command | Expected on success |
|---|---|---|
| New tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_thumbnail_decode.py` | all pass |
| Existing thumbnail tests | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_delegate_fixes.py tests/test_item_views.py tests/test_delegate_layout.py` | all pass |
| Whole suite | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q -n 8` | `3178 passed, 6 skipped` plus this plan's new tests, 0 failed |
| Lint (as CI) | `C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\ruff.exe check --select F,B,BLE .` (CI runs `ruff check --select F,B,BLE .`) | `All checks passed!` |

The test conftest forces `QT_QPA_PLATFORM=offscreen` and isolates settings
and the temp folder per test. Never run tests on the real platform. Any
ad-hoc script must first run
`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`
before any fxgui theme call, and write its images to a temp folder, never
the repo.

## Scope

**In scope** (the only files you should modify):

- `fxgui/fxwidgets/_delegates.py` — the `qtpy.QtGui` import list and
  `_read_thumbnail` only.
- `tests/test_delegate_fixes.py` — `test_a_thumbnail_is_loaded_once_across_paints` only.
- `tests/test_thumbnail_decode.py` (create)

**Out of scope** (do NOT touch):

- `_ThumbnailReads` (threading, caches, staleness) and `_bordered_thumbnail`
  (framing, cache keys).
- Moving local reads off the UI thread: with a 10× cheaper decode it is
  not needed now; a separate decision.
- A timing assertion in a test: timings are flaky on CI. Step 4 measures
  once, by hand.
- `CHANGELOG.md`, any Pascal file.

## Git workflow

- Work in a git worktree, not the shared checkout. Branch:
  `fix/thumbnails-decoded-at-size`. (No `.gitmodules`: no submodule step.)
- Commit style, e.g. `[FIX] Thumbnails decode at their drawn size and honour EXIF orientation`.
- Do not push, tag or release; do not edit `CHANGELOG.md`.

## Steps

### Step 1: Decode through QImageReader at the target size

In `fxgui/fxwidgets/_delegates.py`:

1. Add `QImageReader` to the `from qtpy.QtGui import (...)` list
   (alphabetical, after `QImage`). Add `QSize` only if you use it (it is
   already imported from `qtpy.QtCore`).
2. Replace `image = QImage(path)` with a reader:

```python
    reader = QImageReader(path)
    # A camera's portrait shot is stored sideways with an EXIF tag.
    reader.setAutoTransform(True)
    stored = reader.size()
    # Decode near the box, not the file: a 4K JPEG decodes 10x faster.
    # The box's longer side both ways, since the size applies before the
    # EXIF turn. Never larger than the file: the reader would upscale.
    box = max(size)
    if stored.isValid() and (stored.width() > box or stored.height() > box):
        reader.setScaledSize(stored.scaled(box, box, Qt.KeepAspectRatio))
    image = reader.read()
```

   Keep the rest unchanged: the `if image.isNull():` fallback to
   `QImage(str(_FALLBACK_THUMBNAIL))`, the `convertToFormat`, and the final
   `image.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)`
   (it brings the decoded picture to the exact box and costs little on a
   small image).
3. Update the docstring: one sentence that the file is decoded near the
   box's size and turned upright by its EXIF orientation.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_item_views.py tests/test_delegate_layout.py`
→ all pass. Then
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_delegate_fixes.py`
→ exactly one failure, `test_a_thumbnail_is_loaded_once_across_paints`
(it counts `QImage(path)`, which is no longer called). Any other failure
is a STOP.

### Step 2: Write the new tests

Create `tests/test_thumbnail_decode.py` (cases in "Test plan").

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_thumbnail_decode.py`
→ 4 passed.

### Step 3: Make the load-once test count reader decodes

In `tests/test_delegate_fixes.py`, `test_a_thumbnail_is_loaded_once_across_paints`
(lines 72–93): patch `_delegates.QImageReader` instead of `_delegates.QImage`,
with a subclass that records `args[0]` when it is a `str`, and keep the
final assertion `loads.count(_IMAGE) == 1`. The test's intent (one decode
across three paints) is unchanged.

**Verify**:
`C:\Users\ValentinBeaumont\Documents\GitHub\fxgui\.venv\Scripts\python.exe -m pytest -q tests/test_delegate_fixes.py`
→ all pass.

### Step 4: Measure once (not a test)

Write a throwaway script **outside the repo** (e.g. in your system temp
folder) that sets `QT_QPA_PLATFORM=offscreen`, scopes `QSettings` as in
"Commands", builds a `QGuiApplication`, saves a 3840×2160 `QImage` (fill it
and draw a few lines so it is not trivially compressible) as JPEG quality
90 to a temp folder, and times `_delegates._read_thumbnail(path, None, (320, 180))`
over 5 runs. Run it with the repo root as the current directory and
`sys.path.insert(0, os.getcwd())` at the top so the repo's own `fxgui`
is imported (the venv's editable install points at another checkout).

**Verify**: the mean is under 8 ms (it was 25–27 ms before; about 2.5 ms
expected). Put the number in your report. Delete the script.

### Step 5: Whole suite and lint

**Verify**: whole suite → `3182 passed, 6 skipped` (3178 + 4), 0 failed;
ruff → `All checks passed!`

## Test plan

New file `tests/test_thumbnail_decode.py`; write images under pytest's
`tmp_path`. Import `_delegates` as `from fxgui.fxwidgets import _delegates`
(as `tests/test_delegate_fixes.py` does).

1. `test_a_large_picture_comes_out_at_the_box_size` — save a 2000×1000
   `QImage` (RGB32, filled) as PNG; `_delegates._read_thumbnail(str(p), None, (160, 90))`
   returns a stamp equal to `os.path.getmtime(p)` and an image of
   `QSize(160, 80)`.
2. `test_the_file_is_decoded_near_the_box_not_at_full_size` — patch
   `_delegates.QImageReader` with a subclass whose `setScaledSize` records
   its argument and calls the real one; read a 2000×1000 PNG into
   `(160, 90)`: exactly one recorded size, `QSize(160, 80)` (fit into the
   160×160 box). Read an 80×40 PNG: nothing recorded (never upscaled by
   the reader) and the result is `QSize(160, 80)` as before (the final
   `scaled` still fits the box, matching the old behaviour).
   Why a spy and not a timer: it proves the reduced decode deterministically;
   a timing assertion is flaky.
3. `test_an_exif_portrait_comes_out_upright` — save a 400×200 `QImage` as
   JPEG to `plain.jpg`; read its bytes; build an EXIF APP1 segment and
   insert it right after the first two bytes (the JPEG SOI marker), write
   `exif.jpg`. The segment, big-endian (this exact recipe was verified to
   make Qt report `TransformationRotate90`):

```python
import struct

tiff = (
    b"MM\x00\x2a" + struct.pack(">I", 8)        # TIFF header, IFD at 8
    + struct.pack(">H", 1)                      # one entry
    + struct.pack(">HHI", 0x0112, 3, 1)         # Orientation, SHORT, 1
    + struct.pack(">HH", 6, 0)                  # 6 = rotate 90 clockwise
    + struct.pack(">I", 0)                      # no next IFD
)
payload = b"Exif\x00\x00" + tiff
app1 = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
data = plain.read_bytes()
exif.write_bytes(data[:2] + app1 + data[2:])
```

   Assert `QImageReader(str(exif)).transformation()` is
   `QImageIOHandler.TransformationRotate90` (guards the recipe), then
   `_read_thumbnail(str(exif), None, (160, 90))[1].size() == QSize(45, 90)`
   (upright portrait fitted in the box; the old code gave `QSize(160, 80)`).
4. `test_an_unreadable_file_falls_back_to_the_missing_picture` — write
   `b"not an image"` to `broken.png`; the result is not null and equals, in
   size, `_read_thumbnail` of `str(_delegates._FALLBACK_THUMBNAIL)` with
   the same box.

## Done criteria

- [ ] `pytest -q tests/test_thumbnail_decode.py` → 4 passed.
- [ ] `pytest -q tests/test_delegate_fixes.py tests/test_item_views.py tests/test_delegate_layout.py` → all pass.
- [ ] Whole suite `3182 passed, 6 skipped`, 0 failed; ruff passes.
- [ ] `grep -n "QImage(path)" fxgui/fxwidgets/_delegates.py` → no match.
- [ ] The Step 4 measurement is in the report, and the script is deleted.
- [ ] `git status` shows only the three in-scope files.
- [ ] `plans/2026-11-14-audit/README.md` status row updated.

## STOP conditions

- `_read_thumbnail` differs from the excerpt (drift), or its signature or
  return shape changed (the reader threads and `tests/test_item_views.py`
  depend on it).
- After Step 1, a test other than `test_a_thumbnail_is_loaded_once_across_paints`
  fails.
- Test 3's guard fails (`transformation()` is not `TransformationRotate90`):
  the Qt JPEG plugin no longer reads hand-made EXIF; report, do not drop
  the test silently.
- Step 4 measures 8 ms or more: the reduced decode is not happening;
  report the number.

## Maintenance notes

- Public behaviour change (defect fix): a JPEG with an EXIF orientation
  tag now shows upright in `FXThumbnailDelegate`. Output size, cache keys
  and signatures are unchanged.
- The decoded picture may differ by a pixel or a shade from the old one
  (JPEG's reduced-size decode, then a smooth scale). No test compares
  pixels of a photo thumbnail; if one is added, compare with a tolerance.
- Reviewer: check the scaled size is computed with `Qt.KeepAspectRatio`
  (the reader does not keep aspect on its own) and that the reader never
  upscales.
- Follow-up, not done: local reads still run on the UI thread; at about
  2.5 ms each that is acceptable for now.
- Pascal: nothing to delete; its trees with thumbnails (e.g. the hub's
  shot lists) scroll faster and show portrait photos upright with no
  change.
