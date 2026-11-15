"""The names a consumer reads instead of restating fxgui's values."""

# Built-in
import logging

# Third-party
import pytest
from qtpy.QtWidgets import QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import (
    ERROR,
    INFO,
    FXBreadcrumb,
    FXNotificationBanner,
    FXOutputLogWidget,
    FXStatusBar,
    FXStatusItem,
    FXThumbnailDelegate,
)


def test_font_rank_gives_the_body_and_each_title_rank():
    assert fxstyle.font_rank("body") == (fxstyle.FONT_SIZE, fxstyle.BODY_WEIGHT)
    assert fxstyle.font_rank("section") == (15, fxstyle.EMPHASIS_WEIGHT)
    assert fxstyle.font_rank("card") == (18, fxstyle.EMPHASIS_WEIGHT)


def test_font_rank_names_the_ranks_it_knows():
    with pytest.raises(ValueError, match="section"):
        fxstyle.font_rank("headline")


def test_the_metric_names_hold_the_look_s_values():
    assert (fxstyle.BODY_WEIGHT, fxstyle.EMPHASIS_WEIGHT) == (500, 600)
    assert (fxstyle.DIALOG_GUTTER, fxstyle.DIALOG_EDGE) == (20, 16)
    assert fxstyle.DIALOG_GAP == 12
    assert (FXThumbnailDelegate.PILL_HEIGHT,
            FXThumbnailDelegate.PILL_PADDING) == (20, 6)
    assert FXStatusBar.ICON_SIZE == FXStatusItem.ICON_SIZE == 14


def _host(qtbot):
    parent = QWidget()
    parent.resize(800, 600)
    qtbot.addWidget(parent)
    parent.show()
    return parent


def test_a_banner_says_its_severity_timeout_and_buttons(qtbot):
    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "refused", severity_type=ERROR,
                                  actions={"Retry": lambda: None})

    assert banner.severity() == ERROR
    assert banner.timeout() == 0
    assert [b.text() for b in banner.action_buttons()] == ["Retry"]
    banner.action_buttons().clear()
    assert len(banner.action_buttons()) == 1


def test_a_banner_is_placed_once_its_slide_ends(qtbot):
    parent = _host(qtbot)
    banner = FXNotificationBanner(parent, "sent", severity_type=INFO)
    assert banner.timeout() == 5000
    banner.show()
    qtbot.waitUntil(banner.is_placed)


def test_a_breadcrumb_hands_its_navigation_buttons(qtbot):
    crumb = FXBreadcrumb(show_navigation=True)
    bare = FXBreadcrumb(show_navigation=False)
    qtbot.addWidget(crumb)
    qtbot.addWidget(bare)

    assert crumb.back_button is not None
    assert crumb.forward_button is not None
    assert bare.back_button is None and bare.forward_button is None


def test_flush_writes_every_queued_record(qtbot):
    panel = FXOutputLogWidget()
    qtbot.addWidget(panel)
    panel.append_many([f"line {n}" for n in range(3 * panel.MAX_RECORDS_PER_FLUSH)])
    panel.append_log("last", logging.INFO)
    panel.flush()

    assert panel.output_area.toPlainText().rstrip().endswith("last")
