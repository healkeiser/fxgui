"""The collapsible header toggles on a left click only and styles through QSS."""

# Third-party
from qtpy.QtCore import QPoint, Qt
from qtpy.QtTest import QTest

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
    assert not section.is_expanded
    QTest.mouseClick(header, Qt.MiddleButton, Qt.NoModifier, spot)
    assert not section.is_expanded
    QTest.mouseClick(header, Qt.LeftButton, Qt.NoModifier, spot)
    assert section.is_expanded


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
    assert section.get_icon() is not None
    section.set_icon(None)
    assert section.get_icon() is None and section._icon_label.isHidden()
