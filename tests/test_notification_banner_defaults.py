"""An error waits to be read, a banner says its message, and one is enough."""

# Built-in
import logging

# Third-party
import pytest
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import CRITICAL, ERROR, INFO, FXNotificationBanner


def _host(qtbot):
    parent = QWidget()
    parent.resize(800, 600)
    qtbot.addWidget(parent)
    parent.show()
    return parent


@pytest.mark.parametrize("level", [ERROR, CRITICAL])
def test_an_error_waits_to_be_dismissed(qtbot, level):
    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "refused", severity_type=level)
    banner.show()

    assert not banner._dismiss_timer.isActive()


def test_any_other_banner_times_out_by_default(qtbot):
    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "sent", severity_type=INFO)
    banner.show()

    assert banner._dismiss_timer.isActive()


def test_an_error_given_a_timeout_keeps_it(qtbot):
    parent = _host(qtbot)
    banner = FXNotificationBanner(
        parent, "refused", severity_type=ERROR, timeout=3000
    )
    banner.show()

    assert banner._dismiss_timer.isActive()


def test_message_reads_what_the_banner_says(qtbot):
    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "first")
    assert banner.message() == "first"

    banner.set_message("second")

    assert banner.message() == "second"


def test_a_unique_banner_already_standing_shows_no_second_card(qtbot):
    parent = _host(qtbot)
    FXNotificationBanner(parent, "offline", timeout=0).show()
    second = FXNotificationBanner(parent, "offline", timeout=0)

    shown = second.show(unique=True)

    assert shown is False and second.isHidden()
    standing = parent.findChildren(FXNotificationBanner)
    assert [b for b in standing if not b.isHidden()][0].message() == "offline"


def test_a_unique_banner_with_new_words_shows(qtbot):
    parent = _host(qtbot)
    FXNotificationBanner(parent, "offline", timeout=0).show()
    second = FXNotificationBanner(parent, "back online", timeout=0)

    assert second.show(unique=True) is True
    assert second.isVisible()


def test_a_leaving_banner_does_not_block_its_repeat(qtbot):
    parent = _host(qtbot)
    first = FXNotificationBanner(parent, "offline", timeout=0)
    first.show()
    first.dismiss()

    assert FXNotificationBanner(parent, "offline").show(unique=True) is True


def test_a_banner_is_a_log_line_and_a_repeat_is_not(qtbot, caplog):
    parent = _host(qtbot)
    logger = logging.getLogger("fxgui.tests.banner")

    with caplog.at_level(logging.INFO, logger=logger.name):
        FXNotificationBanner(
            parent, "cannot feed path", ERROR, logger=logger
        ).show(unique=True)
        FXNotificationBanner(
            parent, "cannot feed path", ERROR, logger=logger
        ).show(unique=True)

    assert [(r.getMessage(), r.levelno) for r in caplog.records] == [
        ("cannot feed path", logging.ERROR)
    ]


def test_a_new_timeout_on_a_shown_banner_replaces_the_running_one(qtbot):
    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "sent", severity_type=INFO)
    banner.show()

    banner.set_timeout(0)
    assert not banner._dismiss_timer.isActive()
    banner.set_timeout(250)
    assert banner._dismiss_timer.isActive()
    assert banner._dismiss_timer.interval() == 250


def test_the_top_and_the_side_are_set_apart(qtbot):
    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "sent", margin=10, top=40, width=300)
    banner.show()
    banner._slide_animation.setCurrentTime(banner._slide_animation.duration())

    assert banner.pos().y() == 40
    assert banner.pos().x() == parent.width() - 300 - 10


def test_the_title_is_a_section_title_in_the_theme_font(qtbot):
    from fxgui import fxstyle

    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "sent", severity_type=INFO)

    assert banner._title_label.property(fxstyle.TITLE_PROPERTY) == "section"
    assert "font-size" not in fxstyle._build_stylesheet().split(
        "FXNotificationBanner QLabel#fxBannerTitle {")[1].split("}")[0]
