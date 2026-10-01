"""Every dcc logo draws centred in a square frame at the same apparent size."""

import re
from pathlib import Path
from statistics import median

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QImage, QPainter

SVG_DIR = Path(__file__).parent.parent / "fxgui" / "icons" / "dcc" / "svg"
LOGOS = sorted(SVG_DIR.glob("*.svg"))
SIZE = 256


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


@pytest.mark.parametrize("path", LOGOS, ids=lambda p: p.stem)
def test_artwork_is_centred(bounds, path):
    left, top, right, bottom = bounds[path.stem]
    assert abs(left - (SIZE - right)) <= 2
    assert abs(top - (SIZE - bottom)) <= 2


def test_every_logo_fills_the_same_share(bounds):
    shares = {
        name: max(right - left, bottom - top) / SIZE
        for name, (left, top, right, bottom) in bounds.items()
    }
    middle = median(shares.values())
    off = {n: round(s, 4) for n, s in shares.items() if abs(s - middle) > 0.01}
    assert not off, f"median share {middle:.4f}"
