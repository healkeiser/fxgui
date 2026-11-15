# The faces fxgui ships

Inter (body and titles) and JetBrains Mono (code, logs, anything whose
columns line up), each under the SIL Open Font License 1.1; the notice sits
beside each file, and neither declares a Reserved Font Name, so the family
names stay. fxgui registers them with Qt the first time a GUI application
resolves a font, and names them in `fxstyle`'s default `fonts:` roles; a
colour file may name other families.

## What is in these files

One static file per weight: Inter at 400, 500, 600 and 700, JetBrains Mono
at 400, 500 and 700, each upright and italic. Qt 6.5's Windows font
database (Houdini 21's Qt) reads a variable font as Regular and Bold only,
so weight 500 drew as Regular and 600 as Bold; static files resolve every
weight on Qt 6.5 and on 6.11 alike.

Each file is cut from the upstream variable font, grid-fitted first (the
upstream builds carry no hinting instructions), then instanced at its
weight (Inter at its text optical size, `opsz` 14), without the STAT table
a static face does not need:

```python
from pathlib import Path
from fontTools.ttLib import TTFont  # pip install fonttools ttfautohint-py
from fontTools.varLib import instancer
from ttfautohint import ttfautohint

STYLES = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}


def cut(variable: Path, stem: str, italic: bool, weights, fixed, out: Path):
    hinted = variable.with_suffix(".hinted.ttf")
    hinted.write_bytes(ttfautohint(
        in_file=str(variable), no_info=True, gray_stem_width_mode=1,
        gdi_cleartype_stem_width_mode=1, dw_cleartype_stem_width_mode=1))
    for weight in weights:
        face = instancer.instantiateVariableFont(
            TTFont(hinted), {"wght": weight, **fixed},
            updateFontNames=True, static=True)
        del face["STAT"]
        style = STYLES[weight]
        if italic:
            style = "Italic" if weight == 400 else style + "Italic"
        face.save(out / f"{stem}-{style}.ttf")


# cut(Path("Inter-VariableFont_opsz,wght.ttf"), "Inter", False,
#     (400, 500, 600, 700), {"opsz": 14}, Path("fxgui/fonts/inter"))
# cut(Path("JetBrainsMono-VariableFont_wght.ttf"), "JetBrainsMono", False,
#     (400, 500, 700), {}, Path("fxgui/fonts/jetbrains_mono"))
# ... and each family's italic file with italic=True.
```

A grid-fitted file carries `fpgm`, `prep` and `cvt ` tables; an upstream
download has none.

## Why the roles say `hinting: none`

Measured at 13 px against a browser drawing the same Inter: vertical
hinting rounds Inter's x-height up a pixel (8 px against 7), so text read
larger and narrower than the web look. Unhinted, the outlines match the
browser's to a fraction of a pixel. The grid-fitting stays in the files for
a role that asks for `vertical`.

## Why a dark theme draws a step heavier

`fxstyle.BODY_WEIGHT`, `EMPHASIS_WEIGHT` and `STRONG_WEIGHT` are the web
look's CSS weights (400, 500, 600). `fxstyle.drawn_weight` draws them a step
heavier in a theme whose text is lighter than its surface.

Why: Qt blends DirectWrite's coverage with the system's ClearType gamma
(`SPI_GETFONTSMOOTHINGCONTRAST` / 1000) and applies no contrast boost
(`qwindowsfontenginedirectwrite.cpp`, `qdrawhelper.cpp`); Qt offers no
setting for either. Chromium boosts light text on a dark ground; dark text
on a light ground draws alike in both. Measured on Windows (ClearType on,
contrast 1200), Qt 6.11 and 6.5.3 the same, against Brave drawing Carmen's
font file and CSS. Ink is the summed coverage of one line, relative to the
browser's:

| Text on ground | CSS 400 | CSS 500 | CSS 600 |
|---|---|---|---|
| Dark theme `text` (#D6D9DD on #101113), Qt +100 | -4 % | -1 % | -1 % |
| Dark theme `text_muted` (#A2A7B0) | +2 % | +4 % | +4 % |
| Dark theme `text_strong` (#F7F8F8) | -10 % | -7 % | -6 % |
| Light theme `text` (#2C2D33 on #FFFFFF), same weight | -2 % | 0 % | 0 % |

The step costs width: the same words are 290 px at Qt 500 against 287 px at
400, about 1 %. No font engine (`fontengine=gdi`, `freetype`), hinting, style
strategy or image format came closer at the CSS weight itself.
