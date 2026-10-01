"""The collapsible header toggles on a left click only and styles through QSS."""

# Third-party
from qtpy.QtCore import QPoint, Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLabel

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXCollapsibleWidget


def _section(qtbot):
    section = FXCollapsibleWidget(title="Notes", animation_duration=0)
    qtbot.addWidget(section)
    section.show()
    qtbot.waitExposed(section)
    return section


def test_only_a_left_click_on_the_header_toggles(qtbot, qapp):
    section = _section(qtbot)
    header = section._header
    assert "mousePressEvent" not in vars(header)
    spot = QPoint(header.width() - 10, header.height() // 2)

    QTest.mouseClick(header, Qt.RightButton, Qt.NoModifier, spot)
    assert not section.is_expanded()
    QTest.mouseClick(header, Qt.MiddleButton, Qt.NoModifier, spot)
    assert not section.is_expanded()
    QTest.mouseClick(header, Qt.LeftButton, Qt.NoModifier, spot)
    assert section.is_expanded()


def test_expanded_header_is_a_property_the_theme_sheet_styles(qtbot, qapp):
    section = _section(qtbot)
    section.expand(animate=False)
    assert section._header.property("expanded") is True
    assert section._header.styleSheet() == ""
    assert section._title_label.styleSheet() == ""
    assert 'fx_collapsible_header[expanded="true"]' in fxstyle.build_stylesheet()


def test_a_named_title_icon_follows_the_theme(qtbot, qapp):
    fxstyle.apply_theme("dark")
    section = FXCollapsibleWidget(title="Notes", icon="settings")
    qtbot.addWidget(section)
    section._icon_label.resize(16, 16)
    before = section._icon_label.grab().toImage()
    fxstyle.apply_theme("light")
    assert section._icon_label.grab().toImage() != before
    assert section.icon() is not None
    section.set_icon(None)
    assert section.icon() is None and section._icon_label.isHidden()


def test_the_toggle_button_holds_no_state_of_its_own(qtbot, qapp):
    section = _section(qtbot)

    section._toggle_btn.click()
    assert section.is_expanded()
    section._toggle_btn.click()
    assert not section.is_expanded()
    assert not section._toggle_btn.isCheckable()


def test_title_and_set_title_are_one_value(qtbot, qapp):
    section = _section(qtbot)

    section.set_title("Comments")

    assert section.title() == "Comments"
    assert section._title_label.text() == "Comments"


def test_a_new_cap_applies_to_an_open_section(qtbot, qapp):
    section = _section(qtbot)
    content = QLabel("tall")
    content.setFixedHeight(200)
    section.set_content_widget(content)
    section.expand(animate=False)

    section.set_max_content_height(50)

    assert section.max_content_height() == 50
    assert section._content_area.maximumHeight() == 50
    assert section._content_area.minimumHeight() == 50


def _header_fill(section):
    from qtpy.QtGui import QColor

    header = section._header
    image = header.grab().toImage()
    return image.pixelColor(header.width() - 6, header.height() // 2).name()


def test_a_header_is_a_section_header_hover_fills_open_weighs(qtbot, qapp):
    """Hover fills the header; the open one is told by its 600 title and
    chevron, not by a fill that reads as a hover that never ends."""
    from qtpy.QtGui import QColor, QFont

    fxstyle.apply_theme("dark")
    window = QLabel()
    fxstyle.register_themed_root(window)
    section = FXCollapsibleWidget(window, title="Notes", animation_duration=0)
    window.resize(300, 80)
    window.show()
    qtbot.addWidget(window)
    qtbot.waitExposed(window)
    hover = QColor(fxstyle.colors().state_hover).name()
    resting = _header_fill(section)

    section.expand(animate=False)
    assert _header_fill(section) == resting
    assert section._title_label.font().weight() == QFont.DemiBold
    section.collapse(animate=False)
    assert section._title_label.font().weight() == QFont.Normal

    section._header.setAttribute(Qt.WA_UnderMouse, True)
    assert _header_fill(section) == hover
