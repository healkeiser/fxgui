"""FXAvatar: a round face, from a photo or from a name's initials."""

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QPixmap
from qtpy.QtWidgets import QApplication, QWidget

from fxgui import fxstyle
from fxgui.fxwidgets import FXAvatar
from fxgui.fxwidgets._avatar import AVATAR_COLORS


def _centre(avatar) -> QColor:
    image = avatar.grab().toImage()
    return image.pixelColor(image.width() // 2, image.height() // 2)


def test_initials_take_the_first_letter_of_two_words(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    assert FXAvatar("anne martin", parent).initials() == "AM"
    assert FXAvatar("Madonna", parent).initials() == "M"
    assert FXAvatar("", parent).initials() == ""


def test_the_same_name_gets_the_same_colour(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    one = FXAvatar("Anne Martin", parent)
    two = FXAvatar("Anne Martin", parent)
    other = FXAvatar("Bob Stone", parent)
    assert one.color() == two.color()
    assert one.color() != other.color()


def test_the_colour_does_not_depend_on_the_run(qtbot):
    """crc32, not hash(): a person keeps their colour across launches."""
    parent = QWidget()
    qtbot.addWidget(parent)
    assert FXAvatar("Anne Martin", parent).color().name() == "#9e6a00"


def test_initials_read_on_every_disc(qapp):
    for disc in AVATAR_COLORS:
        ink = fxstyle.readable_ink(disc)
        assert fxstyle.get_contrast_ratio(disc, ink) >= 4.5, disc


def test_a_disc_paints_its_colour(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    avatar = FXAvatar("Madonna", parent, size=40)
    edge = avatar.grab().toImage().pixelColor(20, 4)
    assert edge.name() == avatar.color().name()


def test_a_pixmap_avatar_paints_the_photo_not_the_initials(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    photo = QPixmap(80, 40)
    photo.fill(QColor("#00ff00"))
    avatar = FXAvatar("Anne Martin", parent, size=40, pixmap=photo)
    centre = _centre(avatar)
    assert centre.name() != avatar.color().name()
    assert centre.green() > 240 and centre.red() < 20, centre.name()
    avatar.set_pixmap(None)
    assert _centre(avatar).name() != "#00ff00"


def test_size_is_fixed_and_follows_set_size(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    avatar = FXAvatar("Anne", parent)
    assert avatar.minimumSize() == avatar.maximumSize() == QSize(26, 26)
    avatar.set_size(48)
    assert avatar.minimumSize() == avatar.maximumSize() == QSize(48, 48)
    assert avatar.size() == QSize(48, 48)


def test_a_photo_s_ring_is_the_theme_s_light_border(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    photo = QPixmap(40, 40)
    photo.fill(QColor("#00ff00"))
    avatar = FXAvatar("Anne", parent, size=40, pixmap=photo)
    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        ring = avatar.grab().toImage().pixelColor(20, 0)
        want = QColor(fxstyle.colors().border_light)
        # Antialiasing lets a little of the photo through.
        apart = max(abs(ring.red() - want.red()),
                    abs(ring.green() - want.green()),
                    abs(ring.blue() - want.blue()))
        assert apart <= 16, (ring.name(), want.name())


def test_name_and_tooltip_follow_set_name(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    avatar = FXAvatar("Anne Martin", parent)
    assert avatar.name() == "Anne Martin"
    assert avatar.toolTip() == "Anne Martin"
    avatar.set_name("Bob Stone")
    assert avatar.initials() == "BS"
    assert avatar.toolTip() == "Bob Stone"


def test_building_one_opens_no_window(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    before = set(map(id, QApplication.topLevelWidgets()))
    avatar = FXAvatar("Anne", parent)
    avatar.show()
    after = {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()}
    assert not (after - before)
    assert avatar.window() is parent
    assert avatar.testAttribute(Qt.WidgetAttribute.WA_WState_Hidden) is False


def test_a_wide_photo_is_cropped_once(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    photo = QPixmap(200, 100)
    photo.fill(QColor("#00ff00"))
    avatar = FXAvatar("Anne", parent, size=40, pixmap=photo)
    one = avatar._cropped_face(1.0)
    two = avatar._cropped_face(1.0)
    assert one.cacheKey() == two.cacheKey()
    assert one.width() == one.height() == 40
    assert avatar._cropped_face(2.0).width() == 80


def test_the_placeholder_glyph_renders_at_the_avatar_ratio(
    qtbot, monkeypatch
):
    from fxgui import fxicons

    parent = QWidget()
    qtbot.addWidget(parent)
    avatar = FXAvatar("", parent, size=40)
    ratios = []
    real = fxicons.get_pixmap

    def spy(*args, **kwargs):
        ratios.append(kwargs.get("dpr"))
        return real(*args, **kwargs)

    monkeypatch.setattr(fxicons, "get_pixmap", spy)
    monkeypatch.setattr(avatar, "devicePixelRatioF", lambda: 2.0)
    avatar.grab()
    assert ratios == [2.0]


def test_get_pixmap_takes_a_ratio(qapp):
    from fxgui import fxicons

    pixmap = fxicons.get_pixmap("person", 16, 16, dpr=2.0)
    assert pixmap.size() == QSize(32, 32)
    assert pixmap.devicePixelRatio() == 2.0
