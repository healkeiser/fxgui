"""rounded_pixmap crops an image to a rounded square at a pixel ratio."""

from qtpy.QtGui import QColor, QImage, QPainter, QPixmap

from fxgui import fxicons, fxstyle


def _wide(tmp_path):
    """Write a 300x100 image: red, then green, then blue thirds."""
    image = QImage(300, 100, QImage.Format_ARGB32)
    painter = QPainter(image)
    for index, color in enumerate(("#ff0000", "#00ff00", "#0000ff")):
        painter.fillRect(index * 100, 0, 100, 100, QColor(color))
    painter.end()
    path = tmp_path / "wide.png"
    image.save(str(path))
    return path


def test_it_covers_the_square_from_the_middle(qapp, tmp_path):
    pixmap = fxicons.rounded_pixmap(_wide(tmp_path), 32, ratio=2.0)
    assert pixmap.devicePixelRatio() == 2.0
    assert (pixmap.width(), pixmap.height()) == (64, 64)
    image = pixmap.toImage()
    assert image.pixelColor(32, 32).name() == "#00ff00"


def test_the_corners_are_cut_and_the_edge_is_outlined(qapp, tmp_path):
    image = fxicons.rounded_pixmap(_wide(tmp_path), 32, ratio=1.0).toImage()
    assert image.pixelColor(0, 0).alpha() == 0
    edge = image.pixelColor(16, 0)
    assert edge.alpha() > 0
    assert edge.name() == QColor(fxstyle.colors().border_light).name()


def test_it_takes_a_pixmap(qapp, tmp_path):
    source = QPixmap(str(_wide(tmp_path)))
    assert fxicons.rounded_pixmap(source, 16, ratio=1.0).width() == 16


def test_an_unreadable_file_gives_none(qapp, tmp_path):
    broken = tmp_path / "half.png"
    broken.write_bytes(b"\x89PNG not really")
    assert fxicons.rounded_pixmap(broken, 16, ratio=1.0) is None
