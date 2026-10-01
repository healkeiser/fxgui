"""Every widget that shows a severity names and logs it the same way."""

# Built-in
import logging

# Third-party
import pytest
from qtpy.QtWidgets import QWidget

# Internal
from fxgui.fxwidgets import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    SUCCESS,
    WARNING,
    FXNotificationBanner,
    FXProgressCard,
)
from fxgui.fxwidgets._status_bar import FXStatusBar

_EXPECTED = {
    CRITICAL: ("Critical", logging.CRITICAL),
    ERROR: ("Error", logging.ERROR),
    WARNING: ("Warning", logging.WARNING),
    SUCCESS: ("Success", logging.INFO),
    INFO: ("Info", logging.INFO),
    DEBUG: ("Debug", logging.DEBUG),
}


@pytest.fixture
def logger():
    logger = logging.getLogger("fxgui.test_severity")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.mark.parametrize("level", sorted(_EXPECTED))
def test_the_status_bar_names_and_logs_a_severity(qtbot, caplog, logger, level):
    title, log_level = _EXPECTED[level]
    bar = FXStatusBar()
    qtbot.addWidget(bar)

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        bar.showMessage("hello", level, duration=30, logger=logger)

    assert bar.message_label.text().startswith(f"<b>{title}</b>")
    assert [record.levelno for record in caplog.records] == [log_level]


@pytest.mark.parametrize("level", sorted(_EXPECTED))
def test_the_banner_names_and_logs_a_severity(qtbot, caplog, logger, level):
    title, log_level = _EXPECTED[level]
    parent = QWidget()
    qtbot.addWidget(parent)
    banner = FXNotificationBanner(
        parent, "hello", level, timeout=0, logger=logger)

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        banner.show()

    assert banner._title_label.text() == title
    assert [record.levelno for record in caplog.records] == [log_level]
    assert not hasattr(banner, "SEVERITY_TITLES")


@pytest.mark.parametrize("level", sorted(_EXPECTED))
def test_the_progress_card_shows_every_severity(qtbot, level):
    card = FXProgressCard(status=level)
    qtbot.addWidget(card)

    assert not card._status_icon.pixmap().isNull()


def test_a_banner_without_a_severity_is_a_notification(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    banner = FXNotificationBanner(parent, "hello")

    assert banner._title_label.text() == "Notification"
