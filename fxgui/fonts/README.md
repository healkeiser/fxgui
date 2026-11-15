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

## Why the roles say `hinting: vertical`

Hinting "none" ignores the instructions above: the file then rasterizes
exactly like the upstream download. Measured with Qt's Windows font engine
at 13 px, the share of fully covered ink pixels and the ink mass:

| Face, weight, hinting | Covered | Ink |
|---|---|---|
| Inter 400, none | 0.028 | 1162 |
| Inter 400, vertical | 0.097 | 1289 |
| Inter 500, none | 0.076 | 1355 |
| Inter 500, vertical | 0.126 | 1473 |
| Segoe UI 400, vertical | 0.108 | 1037 |
| JetBrains Mono 400 (12 px), none | 0.031 | 1025 |
| JetBrains Mono 400 (12 px), vertical | 0.126 | 1071 |

Vertical hinting is the crispest, and the snapped stems make Inter 400 as
dark as Inter 500 without hinting, so body text keeps weight 400 and 500
stays the step above it.

## Replacing or updating a face

Download the upstream variable font, run the snippet above over it, and
commit the result, never the raw download.
