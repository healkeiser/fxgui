"""Every brand logo draws centred in a square frame at the same apparent size."""

import re
from pathlib import Path
from statistics import median

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QImage, QPainter

SVG_DIR = Path(__file__).parent.parent / "fxgui" / "icons" / "brands" / "svg"
LOGOS = sorted(SVG_DIR.glob("*.svg"))
SIZE = 256
# Marks that keep their letters where the app tiles put them: one shared
# frame for the family, so each mark alone is neither centred nor full.
ADOBE_MARKS = sorted(p.stem for p in SVG_DIR.glob("adobe_*_mark.svg"))


def _view_box(path):
    root = re.search(r"<svg\b[^>]*>", path.read_text(encoding="ascii"))
    match = re.search(r'\sviewBox="([^"]+)"', root.group(0))
    return [float(v) for v in match.group(1).replace(",", " ").split()]


def _alpha_bounds(path):
    from qtpy.QtSvg import QSvgRenderer

    image = QImage(SIZE, SIZE, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(str(path)).render(painter)
    painter.end()
    alpha = image.convertToFormat(QImage.Format_Alpha8)
    data = bytes(alpha.constBits())
    stride = alpha.bytesPerLine()
    left, right, top, bottom = SIZE, -1, SIZE, -1
    for y in range(SIZE):
        row = data[y * stride : y * stride + SIZE]
        lead = SIZE - len(row.lstrip(b"\0"))
        if lead == SIZE:
            continue
        top, bottom = min(top, y), y
        left = min(left, lead)
        right = max(right, len(row.rstrip(b"\0")) - 1)
    return left, top, right + 1, bottom + 1


@pytest.fixture(scope="module")
def bounds(qapp):
    return {path.stem: _alpha_bounds(path) for path in LOGOS}


@pytest.mark.parametrize("path", LOGOS, ids=lambda p: p.stem)
def test_view_box_is_square(path):
    _, _, width, height = _view_box(path)
    assert width == pytest.approx(height)


@pytest.mark.parametrize("path", LOGOS, ids=lambda p: p.stem)
def test_no_filter_or_blur(path):
    text = path.read_text(encoding="ascii")
    assert not re.search(r"<(filter|feGaussianBlur)\b|filter=", text)


@pytest.mark.parametrize("path", LOGOS, ids=lambda p: p.stem)
def test_no_near_transparent_shape(path):
    text = path.read_text(encoding="ascii")
    found = re.findall(r'(?<![-\w])opacity\s*[:=]\s*"?([0-9.]+)', text)
    assert all(float(v) >= 0.1 for v in found)


@pytest.mark.parametrize(
    "path", [p for p in LOGOS if p.stem not in ADOBE_MARKS], ids=lambda p: p.stem
)
def test_artwork_is_centred(bounds, path):
    left, top, right, bottom = bounds[path.stem]
    assert abs(left - (SIZE - right)) <= 2
    assert abs(top - (SIZE - bottom)) <= 2


def test_every_logo_fills_the_same_share(bounds):
    shares = {
        name: max(right - left, bottom - top) / SIZE
        for name, (left, top, right, bottom) in bounds.items()
        if name not in ADOBE_MARKS
    }
    middle = median(shares.values())
    off = {n: round(s, 4) for n, s in shares.items() if abs(s - middle) > 0.01}
    assert not off, f"median share {middle:.4f}"


def _letter_bounds(path):
    """Bounds of an Adobe tile's letters, as fractions of the tile's width."""
    from qtpy.QtSvg import QSvgRenderer

    image = QImage(SIZE, SIZE, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(str(path)).render(painter)
    painter.end()
    tile, letters = [], []
    for y in range(SIZE):
        for x in range(SIZE):
            colour = image.pixelColor(x, y)
            if colour.alpha() > 127:
                tile.append((x, y))
                if max(colour.red(), colour.green(), colour.blue()) > 120:
                    letters.append((x, y))
    left = min(x for x, _ in tile)
    top = min(y for _, y in tile)
    width = max(x for x, _ in tile) + 1 - left
    return (
        (min(x for x, _ in letters) - left) / width,
        (min(y for _, y in letters) - top) / width,
        (max(x for x, _ in letters) + 1 - left) / width,
    )


def test_adobe_marks_share_one_frame(bounds):
    """Overlaid, the Adobe marks fill and centre like one logo."""
    boxes = [bounds[name] for name in ADOBE_MARKS]
    left = min(b[0] for b in boxes)
    top = min(b[1] for b in boxes)
    right = max(b[2] for b in boxes)
    bottom = max(b[3] for b in boxes)
    others = [
        max(r - l, b - t) / SIZE
        for name, (l, t, r, b) in bounds.items()
        if name not in ADOBE_MARKS
    ]
    assert max(right - left, bottom - top) / SIZE == pytest.approx(
        median(others), abs=0.01
    )
    assert abs(left - (SIZE - right)) <= 2
    assert abs(top - (SIZE - bottom)) <= 2


def test_adobe_marks_place_letters_as_their_tiles_do(bounds):
    """One scale and one offset carry every tile's letters onto its mark."""
    scales, offsets = [], []
    for name in ADOBE_MARKS:
        tile_left, tile_top, tile_right = _letter_bounds(
            SVG_DIR / f"{name[: -len('_mark')]}.svg"
        )
        left, top, right, _ = bounds[name]
        scale = (right - left) / (tile_right - tile_left)
        scales.append(scale)
        offsets.append((left - tile_left * scale, top - tile_top * scale))
    assert max(scales) / min(scales) == pytest.approx(1, abs=0.02)
    assert max(x for x, _ in offsets) - min(x for x, _ in offsets) <= 3
    assert max(y for _, y in offsets) - min(y for _, y in offsets) <= 3
