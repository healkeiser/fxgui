"""A badged icon carries a filled dot at its lower right, punched clear."""

# Third-party
from qtpy.QtGui import QColor, QIcon, QPixmap

# Internal
from fxgui import fxicons, fxstyle


def _solid(color="#808080", side=32):
    pixmap = QPixmap(side, side)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


def _image(icon, side=32):
    return icon.pixmap(side, side).toImage()


def test_the_dot_sits_at_the_lower_right_in_the_accent(qapp):
    image = _image(fxicons.badged(_solid()))
    dot = image.pixelColor(26, 26)

    assert dot.name() == QColor(fxstyle.colors().accent_primary).name()
    assert image.pixelColor(4, 4).name() == "#808080", "the mark stays"


def test_a_ring_is_punched_clear_round_the_dot(qapp):
    image = _image(fxicons.badged(_solid()))

    assert image.pixelColor(18, 26).alpha() == 0


def test_the_dot_takes_a_token_or_a_colour(qapp):
    error = fxstyle.colors().feedback_error_foreground

    by_token = _image(fxicons.badged(_solid(), "feedback_error_foreground"))
    by_hex = _image(fxicons.badged(_solid(), "#00ff00"))

    assert by_token.pixelColor(26, 26).name() == QColor(error).name()
    assert by_hex.pixelColor(26, 26).name() == "#00ff00"


def test_the_source_icon_is_left_alone(qapp):
    source = _solid()

    fxicons.badged(source)

    assert _image(source).pixelColor(26, 26).name() == "#808080"
