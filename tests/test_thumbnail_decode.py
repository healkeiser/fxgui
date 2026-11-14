"""Thumbnails decode at the size they are drawn, upright."""

# Built-in
import os
import struct

# Third-party
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QImage, QImageIOHandler, QImageReader

# Internal
from fxgui.fxwidgets import _delegates


def _save(path, width, height, alpha=False):
    image = QImage(
        width, height, QImage.Format_ARGB32 if alpha else QImage.Format_RGB32
    )
    image.fill(QColor(200, 120, 40, 128 if alpha else 255))
    for x in range(0, width, 7):
        image.setPixelColor(x, x * height // width, QColor(10, 60, 220, 200))
    assert image.save(str(path))
    return str(path)


def _spy(monkeypatch):
    sizes = []

    class SpyReader(QImageReader):
        def setScaledSize(self, size):
            sizes.append(QSize(size))
            super().setScaledSize(size)

    monkeypatch.setattr(_delegates, "QImageReader", SpyReader)
    return sizes


def _read_the_old_way(path, size):
    image = QImage(path)
    image = image.convertToFormat(
        QImage.Format_ARGB32_Premultiplied
        if image.hasAlphaChannel()
        else QImage.Format_RGB32
    )
    return image.scaled(
        size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation
    )


def test_a_large_picture_comes_out_at_the_box_size(tmp_path):
    path = _save(tmp_path / "large.png", 2000, 1000)

    stamp, image = _delegates._read_thumbnail(path, None, (160, 90))

    assert stamp == os.path.getmtime(path)
    assert image.size() == QSize(160, 80)


def test_the_file_is_decoded_near_the_box_not_at_full_size(
    tmp_path, monkeypatch
):
    sizes = _spy(monkeypatch)
    large = _save(tmp_path / "large.jpg", 2000, 1000)
    small = _save(tmp_path / "small.jpg", 80, 40)

    large_image = _delegates._read_thumbnail(large, None, (160, 90))[1]
    assert sizes == [QSize(160, 80)]
    assert large_image.size() == QSize(160, 80)

    sizes.clear()
    small_image = _delegates._read_thumbnail(small, None, (160, 90))[1]
    # Never upscaled by the reader; the final scale still fits the box.
    assert sizes == []
    assert small_image.size() == QSize(160, 80)


def test_a_png_decodes_in_full_as_before(tmp_path, monkeypatch):
    sizes = _spy(monkeypatch)
    path = _save(tmp_path / "large.png", 970, 410, alpha=True)

    image = _delegates._read_thumbnail(path, None, (92, 52))[1]

    assert sizes == []
    assert image == _read_the_old_way(path, (92, 52))


def test_an_exif_portrait_comes_out_upright(tmp_path):
    plain = tmp_path / "plain.jpg"
    exif = tmp_path / "exif.jpg"
    _save(plain, 400, 200)
    tiff = (
        b"MM\x00\x2a" + struct.pack(">I", 8)  # TIFF header, IFD at 8
        + struct.pack(">H", 1)  # one entry
        + struct.pack(">HHI", 0x0112, 3, 1)  # Orientation, SHORT, 1
        + struct.pack(">HH", 6, 0)  # 6 = rotate 90 clockwise
        + struct.pack(">I", 0)  # no next IFD
    )
    payload = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    data = plain.read_bytes()
    exif.write_bytes(data[:2] + app1 + data[2:])

    # Guards the recipe: Qt must read the hand-made tag.
    assert (
        QImageReader(str(exif)).transformation()
        == QImageIOHandler.TransformationRotate90
    )
    image = _delegates._read_thumbnail(str(exif), None, (160, 90))[1]
    assert image.size() == QSize(45, 90)


def test_an_unreadable_file_falls_back_to_the_missing_picture(tmp_path):
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not an image")

    image = _delegates._read_thumbnail(str(broken), None, (160, 90))[1]
    fallback = _delegates._read_thumbnail(
        str(_delegates._FALLBACK_THUMBNAIL), None, (160, 90)
    )[1]

    assert not image.isNull()
    assert image.size() == fallback.size()
