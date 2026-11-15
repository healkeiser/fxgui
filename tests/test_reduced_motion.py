"""Under FXGUI_REDUCED_MOTION=1 every widget lands at once, no timer left.

The suite runs with the variable set (see conftest): each test checks the
end state the moment the call returns, with no wait.
"""

# Third-party
from qtpy.QtCore import QAbstractAnimation, QRect
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import (
    FXAccordion,
    FXCollapsibleWidget,
    FXLowerCaseValidator,
    FXNotificationBanner,
    FXSeating,
    FXSplashScreen,
    FXToggleSwitch,
    FXValidatedLineEdit,
)


def _running(widget: QWidget) -> list:
    return [
        animation
        for animation in widget.findChildren(QAbstractAnimation)
        if animation.state() == QAbstractAnimation.Running
    ]


def test_the_suite_runs_with_reduced_motion():
    assert not fxstyle.motion()


def test_a_shown_switch_jumps_to_its_state(qtbot):
    switch = FXToggleSwitch()
    qtbot.addWidget(switch)
    switch.show()
    switch.setChecked(True)
    assert switch.position == 1.0
    assert not _running(switch)


def _section(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    section = FXCollapsibleWidget(title="Section")
    content = QVBoxLayout()
    content.addWidget(QLabel("row"))
    section.set_content_layout(content)
    QVBoxLayout(host).addWidget(section)
    host.show()
    qtbot.waitExposed(host)
    # The test holds the host: qtbot keeps only a weak reference.
    return host, section


def test_a_collapsible_opens_and_shuts_at_once(qtbot):
    _host_widget, section = _section(qtbot)
    area = section._content_area
    section.expand()
    assert area.minimumHeight() == section._target_height() > 0
    assert not _running(section)
    section.collapse()
    assert area.maximumHeight() == 0
    assert not _running(section)


def test_an_accordion_section_opens_at_once(qtbot):
    accordion = FXAccordion()
    qtbot.addWidget(accordion)
    content = QVBoxLayout()
    content.addWidget(QLabel("row"))
    section = accordion.add_section("One", content)
    accordion.show()
    qtbot.waitExposed(accordion)
    section.expand()
    assert section._content_area.minimumHeight() == section._target_height() > 0
    assert not _running(accordion)


def _host(qtbot):
    parent = QWidget()
    parent.resize(800, 600)
    qtbot.addWidget(parent)
    parent.show()
    return parent


def test_banners_slide_in_out_and_restack_at_once(qtbot):
    parent = _host(qtbot)
    first = FXNotificationBanner(parent, "one", timeout=0)
    second = FXNotificationBanner(parent, "two", timeout=0)
    first.show()
    second.show()
    assert first.pos() == first._target_pos
    assert first.pos().x() == first._resting_x()
    assert second.pos().y() > first.pos().y()
    assert not _running(first) and not _running(second)

    top = first.pos().y()
    first.dismiss()
    assert first.isHidden()
    assert second.pos().y() == top
    assert not _running(second)


def test_a_seated_panel_arrives_at_once(qtbot):
    panel = QWidget()
    qtbot.addWidget(panel)
    panel.resize(200, 150)
    seating = FXSeating(panel)
    seating.show_at(QRect(1600, 1000, 24, 24), None)
    seated = panel.pos()
    assert seating.entrance.state() == QAbstractAnimation.Stopped
    assert panel.windowOpacity() == 1.0
    seating.seat()
    assert panel.pos() == seated


def test_a_splash_asked_to_fade_in_shows_opaque(qtbot):
    splash = FXSplashScreen(fade_in=True)
    qtbot.addWidget(splash)
    splash.show()
    assert splash.windowOpacity() == 1.0
    assert not _running(splash)


def test_a_rejected_key_flashes_without_a_shake(qtbot):
    edit = FXValidatedLineEdit(shake_duration=50, flash_duration=50)
    edit.setValidator(FXLowerCaseValidator())
    qtbot.addWidget(edit)
    edit.show()
    qtbot.waitExposed(edit)
    QTest.keyClicks(edit, "1")
    # The flash still says no; the field never moves.
    assert edit._shake_group.state() == QAbstractAnimation.Stopped
    assert edit._shake_offset == 0.0
    assert edit._flash_group.state() == QAbstractAnimation.Running
