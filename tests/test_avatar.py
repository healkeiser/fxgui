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
        ink = fxstyle.get_contrast_text_color(disc)
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
    assert avatar.sizeHint() == QSize(26, 26)
    assert avatar.minimumSizeHint() == QSize(26, 26)
    avatar.set_size(48)
    assert avatar.sizeHint() == QSize(48, 48)
    assert avatar.size() == QSize(48, 48)


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
