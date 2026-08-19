"""Tests for the native rich-tooltip helpers in `fxwidgets._tips`."""

# Built-in
import re

# Third-party
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QListWidgetItem, QPushButton

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import _tips


def _strip_markup(html: str) -> str:
    """Return the text a user actually reads, with all tags removed."""
    return re.sub(r"<[^>]+>", "", html)


# ' HTML shape


def test_title_only(qtbot):
    html = _tips.tip("Back")

    assert "<b>Back</b>" in html
    # No body row and no keycap when only a title was given.
    assert "margin-top" not in html
    assert "font-family:monospace" not in html


def test_title_and_body(qtbot):
    html = _tips.tip("Back", "Navigate to previous location")

    assert "<b>Back</b>" in html
    assert "Navigate to previous location" in html
    # The body sits in its own block below the title.
    assert "margin-top" in html
    assert "font-family:monospace" not in html


def test_title_and_shortcut(qtbot):
    html = _tips.tip("Save", shortcut="Ctrl+S")

    assert "<b>Save</b>" in html
    assert "font-family:monospace" in html
    # Title and keycap share one line, the cap pushed right by a cell.
    assert 'align="right"' in html
    assert "margin-top" not in html


def test_title_body_and_shortcut(qtbot):
    html = _tips.tip("Save", "Write the scene to disk", "Ctrl+S")

    assert "<b>Save</b>" in html
    assert "Write the scene to disk" in html
    assert 'align="right"' in html
    assert "margin-top" in html


def test_no_fixed_width_is_imposed(qtbot):
    """Qt applies a table `width` as a fixed width rather than a maximum, so
    any width attribute on the outer element would put a short tooltip in an
    oversized box. The popup wraps itself instead."""
    for args in (
        ("Back",),
        ("Back", "Navigate to previous location"),
        ("Save", "Write the scene to disk", "Ctrl+S"),
        ("Publish", "word " * 200, "Ctrl+Shift+P"),
    ):
        html = _tips.tip(*args)
        # The only table is the one that right-aligns the keycap, and it is
        # relative, so it inherits whatever width the popup settles on.
        assert 'width="100%"' in html or "<table" not in html, args


def test_tooltip_grows_with_its_content(qtbot):
    """A title-only tooltip must not be as wide as a paragraph. Measured
    through a word-wrapped QLabel, which is the widget QToolTip uses."""
    from qtpy.QtWidgets import QLabel

    def width(*args):
        label = QLabel(_tips.tip(*args))
        label.setWordWrap(True)
        return label.sizeHint().width()

    title_only = width("Back")
    with_body = width("Back", "Navigate to previous location")
    long_body = width("Publish", "word " * 200)

    assert title_only < with_body < long_body
    # A title-only tooltip is a small box, not a slab.
    assert title_only < 100


def test_keycap_is_right_aligned(qtbot):
    """The keycap must sit at the tooltip's right edge in both regimes,
    capped and shrink-to-content."""
    from qtpy.QtGui import QColor
    from qtpy.QtWidgets import QLabel

    from fxgui import fxstyle

    fxstyle.apply_theme("dark")
    hover = QColor(fxstyle.get_theme_colors()["state_hover"]).rgb()

    for args in (
        ("Save", "", "Ctrl+S"),
        ("Save", "Write the scene to disk", "Ctrl+S"),
        ("Publish", "word " * 200, "Ctrl+Shift+P"),
    ):
        label = QLabel(_tips.tip(*args))
        label.setWordWrap(True)
        label.resize(label.sizeHint())
        label.show()
        image = label.grab().toImage()
        xs = [
            x
            for y in range(image.height())
            for x in range(image.width())
            if image.pixel(x, y) == hover
        ]

        assert xs, f"no keycap drawn for {args}"
        # Flush right: the cap reaches the last pixel column.
        assert max(xs) >= image.width() - 2, args
        # And it is a cap, not a full-width band.
        assert min(xs) > image.width() // 3, args


# ' Escaping


def test_caller_strings_are_escaped(qtbot):
    html = _tips.tip("Fire & <Ice>", "path/to/A&B <shot>", "Ctrl+S")

    # The raw characters must not reach the markup...
    assert "<Ice>" not in html
    assert "<shot>" not in html
    # ...but the words survive as text.
    assert "Fire &amp; &lt;Ice&gt;" in html
    assert "path/to/A&amp;B &lt;shot&gt;" in html


def test_escaping_survives_as_text(qtbot):
    """What the user reads is the string they were given."""
    from html import unescape

    title = "Fire & <Ice>"
    html = _tips.tip(title)

    assert unescape(_strip_markup(html)).strip() == title


# ' Empty in, empty out


def test_all_blank_yields_empty_string(qtbot):
    assert _tips.tip("") == ""
    assert _tips.tip("", "", "") == ""


def test_keycap_empty_yields_empty_string(qtbot):
    assert _tips.keycap("") == ""


def test_body_only_still_renders(qtbot):
    html = _tips.tip("", "Nothing is selected")

    assert "Nothing is selected" in html
    assert "<b>" not in html


# ' Shortcut rendering


def test_keycap_uses_native_text(qtbot):
    """A Mac must show the platform glyphs rather than the literal "Ctrl",
    which is what QKeySequence's NativeText format is for."""
    native = QKeySequence("Ctrl+Shift+E").toString(QKeySequence.NativeText)
    html = _tips.keycap("Ctrl+Shift+E")

    assert native in _strip_markup(html).replace("&nbsp;", "")


def test_keycap_falls_back_to_raw_string(qtbot):
    """Qt yields nothing for a sequence it cannot parse; the raw string is
    still more useful to the reader than an empty cap."""
    assert QKeySequence("not a shortcut").toString() == ""
    assert "not a shortcut" in _strip_markup(_tips.keycap("not a shortcut"))


# ' Theme awareness


def test_colors_come_from_the_active_theme(qtbot):
    fxstyle.apply_theme("dark")
    dark = _tips.tip("Save", "Write the scene to disk", "Ctrl+S")

    fxstyle.apply_theme("light")
    light = _tips.tip("Save", "Write the scene to disk", "Ctrl+S")

    assert dark != light
    for token in ("text", "text_muted", "state_hover"):
        fxstyle.apply_theme("dark")
        dark_value = fxstyle.get_theme_colors()[token]
        fxstyle.apply_theme("light")
        light_value = fxstyle.get_theme_colors()[token]

        assert dark_value in dark
        assert light_value in light
        assert dark_value not in light


def test_tokens_used_exist_in_every_theme(qtbot):
    """A missing token would raise a KeyError on hover, in a studio theme
    nobody tested."""
    for name in fxstyle.get_available_themes():
        fxstyle.apply_theme(name)
        colors = fxstyle.get_theme_colors()
        for token in ("text", "text_muted", "state_hover"):
            assert token in colors, f"{name} is missing {token}"


# ' apply_tip


def test_apply_tip_sets_markup_and_plain_status(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)

    _tips.apply_tip(button, "Save", "Write the scene to disk", "Ctrl+S")

    assert "<b>Save</b>" in button.toolTip()
    status = button.statusTip()
    assert "<" not in status and ">" not in status
    assert "Save" in status and "Write the scene to disk" in status


def test_apply_tip_status_is_title_only_without_body(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)

    _tips.apply_tip(button, "Back")

    assert button.statusTip() == "Back"


def test_apply_tip_tolerates_missing_status_tip(qtbot):
    """Not every tooltip target carries a status tip; the guard must hold."""

    class ToolTipOnly:
        def __init__(self):
            self.tooltip = ""

        def setToolTip(self, text):
            self.tooltip = text

    target = ToolTipOnly()
    assert not hasattr(target, "setStatusTip")

    _tips.apply_tip(target, "Shot 0010", "Ready to render")

    assert "<b>Shot 0010</b>" in target.tooltip


def test_apply_tip_works_on_view_items(qtbot):
    """Item classes are annotated the same way as widgets."""
    item = QListWidgetItem("Shot 0010")

    _tips.apply_tip(item, "Shot 0010", "Ready to render")

    assert "<b>Shot 0010</b>" in item.toolTip()
    assert item.statusTip() == "Shot 0010 - Ready to render"


# ' Migrated widgets


def _all_tooltips(widget):
    """Every non-empty tooltip in a widget tree, markup stripped."""
    from html import unescape

    from qtpy.QtWidgets import QWidget

    out = []
    for child in [widget] + widget.findChildren(QWidget):
        html = child.toolTip()
        if html:
            plain = _strip_markup(html).replace("&nbsp;", " ")
            out.append(unescape(plain))
    return out


def test_migrated_widgets_use_native_tooltips(qtbot):
    """The library's own call sites went native; a missing tooltip here means
    the migration dropped one."""
    from fxgui.fxwidgets import (
        FXBreadcrumb,
        FXFilePathWidget,
        FXFuzzySearchList,
    )

    breadcrumb = FXBreadcrumb(show_navigation=True)
    qtbot.addWidget(breadcrumb)
    assert "<b>Back</b>" in breadcrumb._back_button.toolTip()
    assert "<b>Forward</b>" in breadcrumb._forward_button.toolTip()
    assert breadcrumb._back_button.statusTip().startswith("Back - ")

    path_widget = FXFilePathWidget()
    qtbot.addWidget(path_widget)
    assert "<b>Browse</b>" in path_widget._browse_btn.toolTip()

    search_list = FXFuzzySearchList(show_ratio_slider=True)
    qtbot.addWidget(search_list)
    assert "<b>Sensitivity</b>" in search_list._ratio_icon.toolTip()
    assert "<b>Match Threshold</b>" in search_list._ratio_slider.toolTip()


def test_no_widget_owns_both_a_native_and_an_fxtooltip(qtbot):
    """FXTooltipManager used to suppress the native tooltip on a widget that
    owned an FXTooltip. Without the manager nothing suppresses it, so a widget
    carrying both would show two tooltips on one hover."""
    from qtpy.QtWidgets import QWidget

    from fxgui.fxwidgets import (
        FXBreadcrumb,
        FXFilePathWidget,
        FXFuzzySearchList,
        FXFuzzySearchTree,
        FXOutputLogWidget,
        FXTimelineSlider,
    )

    roots = [
        FXBreadcrumb(show_navigation=True),
        FXFilePathWidget(),
        FXFuzzySearchList(show_ratio_slider=True),
        FXFuzzySearchTree(show_ratio_slider=True),
        FXOutputLogWidget(),
        FXTimelineSlider(
            show_controls=True,
            show_spinbox=True,
            show_loop_controls=True,
            show_keyframe_controls=True,
        ),
    ]
    for root in roots:
        qtbot.addWidget(root)

    doubled = []
    for root in roots:
        for child in [root] + root.findChildren(QWidget):
            if child.property("fx_has_explicit_tooltip") and child.toolTip():
                doubled.append(f"{type(root).__name__}.{child.objectName()}")

    assert doubled == []


def test_timeline_playback_keeps_a_rich_tooltip(qtbot):
    """play()/stop() used to overwrite the rich tooltip with a bare word,
    which was invisible while the manager suppressed it."""
    from fxgui.fxwidgets import FXTimelineSlider

    timeline = FXTimelineSlider(show_controls=True)
    qtbot.addWidget(timeline)

    assert "<b>Play</b>" in timeline._play_btn.toolTip()

    timeline.play()
    assert "<b>Pause</b>" in timeline._play_btn.toolTip()
    assert "Space" in timeline._play_btn.toolTip()

    timeline.stop()
    assert "<b>Play</b>" in timeline._play_btn.toolTip()
    assert "Space" in timeline._play_btn.toolTip()


def test_every_migrated_tooltip_kept_its_wording(qtbot):
    """The migration was a mechanism change. Every word that was in an
    FXTooltip before must still reach the user, on the widget it was on."""
    from fxgui.fxwidgets import (
        FXBreadcrumb,
        FXFilePathWidget,
        FXFuzzySearchList,
        FXFuzzySearchTree,
        FXOutputLogWidget,
        FXTimelineSlider,
    )

    # (title, body) as they read before the migration. The log widget's
    # output-area body carried `<br>` and `<code>` markup; the tags became
    # plain punctuation, every word survived.
    expected = {
        "FXBreadcrumb": [
            ("Back", "Navigate to previous location"),
            ("Forward", "Navigate to next location"),
        ],
        "FXFilePathWidget": [
            ("Browse", "Open file browser to select a path"),
        ],
        "FXFuzzySearchList": [
            ("Sensitivity", "Adjust fuzzy matching sensitivity"),
            (
                "Match Threshold",
                "Lower = more results (looser match), Higher = fewer "
                "results (stricter match)",
            ),
        ],
        "FXFuzzySearchTree": [
            ("Sensitivity", "Adjust fuzzy matching sensitivity"),
            (
                "Match Threshold",
                "Lower = more results (looser match), Higher = fewer "
                "results (stricter match)",
            ),
        ],
        "FXOutputLogWidget": [
            (
                "Output Area",
                "Displays log messages from the application. "
                "Press Ctrl+F to search",
            ),
            ("Find Previous", "Find previous match"),
            ("Find Next", "Find next match"),
            ("Close Search", "Close the search bar"),
            ("Clear Log", "Clear all log messages"),
        ],
        "FXTimelineSlider": [
            ("Start Frame", "First frame of the timeline range"),
            ("End Frame", "Last frame of the timeline range"),
            ("FPS", "Frames per second for playback"),
            ("Go to Start", "Jump to the first frame"),
            ("Previous Frame", "Go back one frame"),
            ("Play", "Start playback"),
            ("Next Frame", "Go forward one frame"),
            ("Go to End", "Jump to the last frame"),
            ("Loop Playback", "Restart from the first frame at the end"),
            ("Previous Keyframe", "Jump to the nearest keyframe before"),
            ("Next Keyframe", "Jump to the nearest keyframe after"),
            ("Mark In", "Set the loop in point at the current frame"),
            ("Mark Out", "Set the loop out point at the current frame"),
        ],
    }

    roots = {
        "FXBreadcrumb": FXBreadcrumb(show_navigation=True),
        "FXFilePathWidget": FXFilePathWidget(),
        "FXFuzzySearchList": FXFuzzySearchList(show_ratio_slider=True),
        "FXFuzzySearchTree": FXFuzzySearchTree(show_ratio_slider=True),
        "FXOutputLogWidget": FXOutputLogWidget(),
        "FXTimelineSlider": FXTimelineSlider(
            show_controls=True,
            show_spinbox=True,
            show_loop_controls=True,
            show_keyframe_controls=True,
        ),
    }
    for root in roots.values():
        qtbot.addWidget(root)

    missing = []
    for name, root in roots.items():
        tooltips = _all_tooltips(root)
        for title, body in expected[name]:
            if not any(title in t and body in t for t in tooltips):
                missing.append(f"{name}: {title!r} / {body!r}")

    assert missing == []
