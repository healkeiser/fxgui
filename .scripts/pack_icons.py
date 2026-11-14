"""Pack an upstream icon set into the zip fxgui ships, one file per library.

A library of thousands of SVGs as loose files makes every clone, build and
Rez install slow; one zip per library does not. `fxicons.get_icon_path`
extracts an icon from it the first time it is asked for.

Usage:
    python .scripts/pack_icons.py material ~/src/material-icons
    python .scripts/pack_icons.py fontawesome ~/src/Font-Awesome
    python .scripts/pack_icons.py simple ~/src/simple-icons
    python .scripts/pack_icons.py lucide ~/src/lucide

Upstream repositories:
    material: https://github.com/material-icons/material-icons
    fontawesome: https://github.com/FortAwesome/Font-Awesome (free, svgs/)
    simple: https://github.com/simple-icons/simple-icons
    lucide: https://github.com/lucide-icons/lucide
"""

# Built-in
import argparse
import zipfile
from pathlib import Path
from typing import Optional

# What each library keeps, as globs relative to the upstream root. The paths
# inside the zip match the library's pattern in `fxicons`.
_CONTENTS = {
    "material": ["svg/*/*.svg", "LICENSE"],
    "fontawesome": ["svgs/*/*.svg", "LICENSE.txt"],
    "simple": ["icons/*.svg", "LICENSE.md"],
    "lucide": ["icons/*.svg", "LICENSE"],
}

# Where an upstream path lands in the zip when fxicons expects another.
_RENAMES = {"lucide": {"icons/": "svg/", "LICENSE": "LICENSE.txt"}}

_ICONS_ROOT = Path(__file__).resolve().parent.parent / "fxgui" / "icons"


def pack(library: str, source: Path, target: Optional[Path] = None) -> Path:
    """Write `fxgui/icons/<library>.zip` from an upstream checkout.

    Args:
        library: One of the keys of `_CONTENTS`.
        source: The root of the upstream checkout.
        target: Where to write the zip; fxgui/icons/<library>.zip by default.

    Returns:
        Path: The zip written.
    """

    target = target or _ICONS_ROOT / f"{library}.zip"
    files = sorted(
        path for glob in _CONTENTS[library] for path in source.glob(glob)
    )
    if not any(path.suffix == ".svg" for path in files):
        raise SystemExit(f"No SVG found in {source} for {library}.")
    with zipfile.ZipFile(target, "w") as archive:
        for path in files:
            name = path.relative_to(source).as_posix()
            for old, new in _RENAMES.get(library, {}).items():
                if name.startswith(old):
                    name = new + name[len(old):]
                    break
            # A fixed date, so packing the same icons twice gives the same zip.
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    print(f"{target}: {len(files)} files, {target.stat().st_size / 1e6:.1f} MB")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("library", choices=sorted(_CONTENTS))
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    pack(args.library, args.source.expanduser(), args.output)
