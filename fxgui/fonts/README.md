# The faces fxgui ships

Inter (body and titles) and JetBrains Mono (code, logs, anything whose
columns line up), each under the SIL Open Font License 1.1; the notice sits
beside each file, and neither declares a Reserved Font Name, so the family
names stay. fxgui registers them with Qt the first time a GUI application
resolves a font, and names them in `fxstyle`'s default `fonts:` roles; a
colour file may name other families.

## What is in these files

Each file is the upstream variable font, grid-fitted here: the upstream
builds carry no hinting instructions and leave grid-fitting to the
rasterizer, which reads soft on Windows. Regenerated with `ttfautohint` at
strong stem width in all three rendering modes:

```python
from pathlib import Path
from ttfautohint import ttfautohint  # pip install ttfautohint-py

for source in sorted(Path("fxgui/fonts").glob("*/*.ttf")):
    source.write_bytes(
        ttfautohint(
            in_file=str(source),
            no_info=True,
            gray_stem_width_mode=1,
            gdi_cleartype_stem_width_mode=1,
            dw_cleartype_stem_width_mode=1,
        )
    )
```

A grid-fitted file carries `fpgm`, `prep` and `cvt ` tables; an upstream
download has none.

## Why the roles say `hinting: none` and weight 500

The roles draw these files unhinted, which rasterizes them exactly like the
upstream download, and one weight step above the web look. Measured at
13 px against Edge drawing the same Inter (`@fontsource-variable/inter`),
light text on `#101113`, Qt 6.11's Windows font engine:

| Renderer, weight, hinting | x-height | Ink of one line | Line width |
|---|---|---|---|
| Edge 400 | 7 px | 230510 | 370 px |
| Edge 500 | | 258821 | 374 px |
| Qt 400, vertical | 8 px | 215507 | |
| Qt 400, none | 7 px | 197173 | 370 px |
| Qt 500, none | 7 px | 225494 | 373 px |
| Qt 600, none | 7 px | 259214 | 377 px |

Vertical hinting rounds Inter's x-height up a pixel at 13 px, so text read
larger and narrower than the same face in a browser. Unhinted, Qt draws a
weight as light as the browser draws the weight below it, so the body is
500 and emphasis 600 (`fxstyle.BODY_WEIGHT`, `fxstyle.EMPHASIS_WEIGHT`).
The grid-fitting stays in the files for a role that asks for `vertical`.

## Replacing or updating a face

Download the upstream variable font, run the snippet above over it, and
commit the result, never the raw download.
