"""Tests for the native rich-tooltip helpers in `fxwidgets._tips`."""

# Built-in
import re

# Third-party
import pytest
from qtpy.QtCore import QEvent, QPoint, QRect
from qtpy.QtGui import QAction, QHelpEvent, QKeySequence, QTextDocument
from qtpy.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QToolTip,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import _tips


def _strip_markup(html: str) -> str:
    """Return the text a user actually reads, with all tags removed."""
    return re.sub(r"<[^>]+>", "", html)


@pytest.fixture
def themed_app(qapp):
    """The application as a themed root, as FXApplication makes it."""
    sheet, font, palette = qapp.styleSheet(), qapp.font(), qapp.palette()
    fxstyle.register_themed_root(qapp)
    yield qapp
    fxstyle._themed_roots.discard(qapp)
    qapp.setStyleSheet(sheet)
    qapp.setFont(font)
    qapp.setPalette(palette)


# ' HTML shape


def test_title_only(qtbot):
    html = _tips.tip("Back")

    assert "<b>Back</b>" in html
    # No body row and no keycap when only a title was given.
    assert "margin-top" not in html
    assert "background:" not in html


def test_title_and_body(qtbot):
    html = _tips.tip("Back", "Navigate to previous location")

    assert "<b>Back</b>" in html
    assert "Navigate to previous location" in html
    # The body sits in its own block below the title.
    assert "margin-top" in html
    assert "background:" not in html


def test_title_and_shortcut(qtbot):
    html = _tips.tip("Save", shortcut="Ctrl+S")

    assert "<b>Save</b>" in html
    assert "background:" in html
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


def test_keycap_is_right_aligned(themed_app, qtbot):
    """The keycap must sit at the tooltip's right edge in both regimes,
    capped and shrink-to-content."""
    from qtpy.QtGui import QColor
    from qtpy.QtWidgets import QLabel

    from fxgui import fxstyle

    fxstyle.apply_theme("dark")
    # The keycap's fill on the tooltip box, as the QToolTip rule paints it.
    hover = QColor(fxstyle.colors().surface).rgb()
    box = f"background: {fxstyle.colors().surface_sunken};"

    for args in (
        ("Save", "", "Ctrl+S"),
        ("Save", "Write the scene to disk", "Ctrl+S"),
        ("Publish", "word " * 200, "Ctrl+Shift+P"),
    ):
        label = QLabel(_tips.tip(*args))
        label.setStyleSheet(box)
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
        # Flush right: the last cap reaches the last pixel column.
        assert max(xs) >= image.width() - 2, args
        # One cap per key, not one band: the fill breaks between keys.
        row = sorted(set(xs))
        runs = 1 + sum(1 for a, b in zip(row, row[1:]) if b - a > 1)
        assert runs == len(_tips._chords(args[2])[0]), args


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


def test_a_body_newline_breaks_the_line(qtbot):
    html = _tips.tip("Shot 0010", "On disk\nDouble-click to open <it>")

    assert "On disk<br>Double-click to open &lt;it&gt;" in html


def test_body_only_still_renders(qtbot):
    html = _tips.tip("", "Nothing is selected")

    assert "Nothing is selected" in html
    assert "<b>" not in html


# ' Shortcut rendering


def test_keycap_uses_native_text(qtbot):
    """A Mac must show the platform glyphs rather than the literal "Ctrl",
    which is what QKeySequence's NativeText format is for."""
    native = QKeySequence("Ctrl+Shift+E").toString(QKeySequence.NativeText)

    names = _tips._chords("Ctrl+Shift+E")[0]

    assert names[-1] == "E"
    assert all(name in native for name in names)
    assert "+" not in "".join(names)


def test_keycap_names_the_plus_key(qtbot):
    assert _tips._chords("Ctrl++")[0][-1] == "+"


def test_keycap_draws_one_cap_per_key(qtbot):
    html = _tips.keycap("Ctrl+Shift+E")

    caps = re.findall(r"<span[^>]*>&nbsp;([^<]*)&nbsp;</span>", html)

    assert caps == _tips._chords("Ctrl+Shift+E")[0]


def test_keycap_parts_chords_wider_than_keys(qtbot):
    html = _tips.keycap("Ctrl+K, Ctrl+S")

    gaps = re.findall(r"</span>((?:&nbsp;)+)<span", html)

    assert len(gaps) == 3
    assert len(gaps[1]) > len(gaps[0]) == len(gaps[2])


def test_keycap_falls_back_to_raw_string(qtbot):
    """Qt yields nothing for a sequence it cannot parse; the raw string is
    still more useful to the reader than an empty cap."""
    assert QKeySequence("not a shortcut").toString() == ""
    assert "not a shortcut" in _strip_markup(_tips.keycap("not a shortcut"))


# ' Theme awareness


def test_a_tip_is_written_in_the_theme_in_force(qtbot):
    """Qt 6.5 rich text has no name for the placeholder-text role."""
    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        html = _tips.tip("Save", "Write the scene to disk", "Ctrl+S")

        assert f"color:{fxstyle.colors().text_muted};" in html
        assert f"background:{fxstyle.colors().surface};" in html
        assert "palette(" not in html


def _visible_tip():
    return next(
        (
            top
            for top in QApplication.topLevelWidgets()
            if top.inherits("QTipLabel") and top.isVisible()
        ),
        None,
    )


def _tip_ink(widget, text: str) -> str:
    """Show `widget`'s tooltip; return the ink its label's document gives
    the fragment `text`."""
    point = QPoint(2, 2)
    QApplication.sendEvent(
        widget, QHelpEvent(QEvent.ToolTip, point, widget.mapToGlobal(point))
    )
    label = _visible_tip()
    block = label.findChild(QTextDocument).begin()
    try:
        while block.isValid():
            fragments = block.begin()
            while not fragments.atEnd():
                fragment = fragments.fragment()
                if fragment.text() == text:
                    return fragment.charFormat().foreground().color().name()
                fragments += 1
            block = block.next()
        raise AssertionError(f"{text!r} is not in the tooltip")
    finally:
        QToolTip.hideText()


def test_a_tip_set_in_one_theme_shows_in_the_theme_of_the_moment(
    themed_app, qtbot
):
    """Read from the label's own document: glyph pixels differ by platform."""
    button = QPushButton("Save")
    qtbot.addWidget(button)
    button.show()
    fxstyle.apply_theme("dark")
    _tips.apply_tip(button, "Save", "Write the scene to disk", "Ctrl+S")

    for theme in ("light", "dark"):
        fxstyle.apply_theme(theme)
        ink = _tip_ink(button, "Write the scene to disk")
        # Qt reuses a fading label, and its unchanged text is not re-read.
        qtbot.waitUntil(lambda: not _visible_tip())

        assert ink == fxstyle.colors().text_muted.lower(), theme


def _cap_pixels(host: QWidget, cap: QWidget):
    """Return the host's render and the cap's rectangle in it."""
    image = host.grab().toImage()
    origin = cap.mapTo(host, QPoint(0, 0))
    return image, QRect(origin, cap.size())


def test_a_keycap_follows_a_switch_and_has_round_corners(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    fxstyle.register_themed_root(host)
    fxstyle.apply_theme("dark")
    switched = _tips.FXKeycap("S", host)
    host.resize(120, 80)
    host.show()
    fxstyle.apply_theme("light")
    fresh = _tips.FXKeycap("S", host)
    fresh.move(0, 40)
    fresh.show()

    caps = [cap.findChildren(QLabel)[0] for cap in (switched, fresh)]
    image, first = _cap_pixels(host, caps[0])
    _image, second = _cap_pixels(host, caps[1])
    assert first.size() == second.size()
    assert image.copy(first) == image.copy(second)

    fill = image.pixelColor(second.center().x(), second.top() + 1).name()
    assert fill == fxstyle.colors().state_hover.lower()
    # The border is drawn and the corner is cut round.
    edge = image.pixelColor(second.center().x(), second.top()).name()
    assert edge == fxstyle.colors().border.lower()
    corner = image.pixelColor(second.topLeft()).name()
    assert corner not in (fill, edge)


def test_fxkeycap_draws_one_cap_per_key(qtbot):
    cap = _tips.FXKeycap("Ctrl+Shift+E")
    qtbot.addWidget(cap)

    names = [label.text() for label in cap.findChildren(QLabel)]

    assert names == _tips._chords("Ctrl+Shift+E")[0]
    assert len(names) == 3


def test_fxkeycap_parts_chords_wider_than_keys(qtbot):
    cap = _tips.FXKeycap("Ctrl+K, Ctrl+S")
    qtbot.addWidget(cap)
    cap.show()
    keys = sorted(cap.findChildren(QLabel), key=lambda label: label.x())

    gaps = [b.x() - a.geometry().right() for a, b in zip(keys, keys[1:])]

    assert len(keys) == 4
    assert gaps[1] > gaps[0] == gaps[2] > 0


def test_fxkeycap_set_keys_rebuilds_the_caps(qtbot):
    cap = _tips.FXKeycap("Ctrl+S")
    qtbot.addWidget(cap)

    cap.set_keys("F5")

    assert cap.keys() == "F5"
    assert [label.text() for label in cap.findChildren(QLabel)] == ["F5"]
    cap.set_keys("")
    assert cap.findChildren(QLabel) == []


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


def test_apply_tip_covers_every_column_of_a_tree_item(qtbot):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setColumnCount(2)
    item = QTreeWidgetItem(tree, ["sh0010", "Ready"])

    _tips.apply_tip(item, "Shot 0010", "Ready to render")

    assert all("<b>Shot 0010</b>" in item.toolTip(c) for c in (0, 1))
    assert item.statusTip(1) == "Shot 0010 - Ready to render"


def test_apply_tip_works_on_view_items(qtbot):
    """Item classes are annotated the same way as widgets."""
    view = QListWidget()
    qtbot.addWidget(view)
    item = QListWidgetItem("Shot 0010", view)

    _tips.apply_tip(item, "Shot 0010", "Ready to render")

    assert "<b>Shot 0010</b>" in item.toolTip()
    assert item.statusTip() == "Shot 0010 - Ready to render"


def test_apply_tip_refuses_an_item_in_no_view(qtbot):
    with pytest.raises(ValueError):
        _tips.apply_tip(QListWidgetItem("Shot 0010"), "Shot 0010")


def test_an_item_tip_is_built_when_it_shows(qtbot):
    view = QListWidget()
    qtbot.addWidget(view)
    item = QListWidgetItem("Shot 0010", view)
    view.show()
    fxstyle.apply_theme("dark")
    _tips.apply_tip(item, "Shot 0010", "Ready to render")
    fxstyle.apply_theme("light")

    point = view.visualItemRect(item).center()
    viewport = view.viewport()
    QApplication.sendEvent(
        viewport,
        QHelpEvent(QEvent.ToolTip, point, viewport.mapToGlobal(point)),
    )

    assert QToolTip.text() == _tips.tip("Shot 0010", "Ready to render")
    QToolTip.hideText()


def test_an_action_tip_is_built_when_it_is_hovered(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    action = QAction("Refresh", host)
    button = QToolButton(host)
    button.setDefaultAction(action)
    fxstyle.apply_theme("dark")
    _tips.apply_tip(action, "Refresh", "Reload the list", "F5")
    _tips.apply_tip(action, "Refresh", "Reload the list", "F5")
    fxstyle.apply_theme("light")

    action.hover()

    fresh = _tips.tip("Refresh", "Reload the list", "F5")
    assert action.toolTip() == fresh
    assert button.toolTip() == fresh


def test_a_second_apply_tip_replaces_the_first(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)
    button.show()
    _tips.apply_tip(button, "Save")
    _tips.apply_tip(button, "Save as", "Write a copy")

    point = QPoint(2, 2)
    QApplication.sendEvent(
        button, QHelpEvent(QEvent.ToolTip, point, button.mapToGlobal(point))
    )

    assert QToolTip.text() == _tips.tip("Save as", "Write a copy")
    QToolTip.hideText()


# ' Library widgets


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


def test_library_widgets_use_native_tooltips(qtbot):
    """The library's own buttons carry rich native tooltips."""
    from fxgui.fxwidgets import (
        FXBreadcrumb,
        FXFilePathWidget,
        FXFilteredTree,
    )

    breadcrumb = FXBreadcrumb(show_navigation=True)
    qtbot.addWidget(breadcrumb)
    assert "<b>Back</b>" in breadcrumb._back_button.toolTip()
    assert "<b>Forward</b>" in breadcrumb._forward_button.toolTip()
    assert breadcrumb._back_button.statusTip().startswith("Back - ")

    path_widget = FXFilePathWidget()
    qtbot.addWidget(path_widget)
    assert "<b>Browse</b>" in path_widget._browse_btn.toolTip()

    filtered = FXFilteredTree()
    qtbot.addWidget(filtered)
    assert "<b>Expand all</b>" in filtered.expand_button.toolTip()
    assert "<b>Collapse all</b>" in filtered.collapse_button.toolTip()


def test_timeline_playback_keeps_a_rich_tooltip(qtbot):
    """play() and stop() keep the rich tooltip, shortcut included."""
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


def test_library_tooltips_carry_their_words(qtbot):
    """Each library widget's tips carry their title and body words."""
    from fxgui.fxwidgets import (
        FXBreadcrumb,
        FXFilePathWidget,
        FXFilteredTree,
        FXOutputLogWidget,
        FXTimelineSlider,
    )

    # (title, body) per widget.
    expected = {
        "FXBreadcrumb": [
            ("Back", "Navigate to previous location"),
            ("Forward", "Navigate to next location"),
        ],
        "FXFilePathWidget": [
            ("Browse", "Open file browser to select a path"),
        ],
        "FXFilteredTree": [("Expand all", ""), ("Collapse all", "")],
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
        "FXFilteredTree": FXFilteredTree(),
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


# ' Accessible names


def test_a_tip_names_the_control_for_a_screen_reader(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)

    _tips.apply_tip(button, "Attach", "Add files to the comment")

    assert button.accessibleName() == "Attach"
    assert button.accessibleDescription() == "Add files to the comment"


def test_a_tip_keeps_a_name_the_caller_chose(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)
    button.setAccessibleName("Attach files")

    _tips.apply_tip(button, "Attach")

    assert button.accessibleName() == "Attach files"


def test_a_new_tip_replaces_the_words_the_last_one_spoke(qtbot):
    label = QLabel()
    qtbot.addWidget(label)

    _tips.apply_tip(label, "Assignees", "anne")
    _tips.apply_tip(label, "Assignees", "jean")

    assert label.accessibleDescription() == "jean"

    _tips.apply_tip(label, "")

    assert label.accessibleName() == ""
    assert label.accessibleDescription() == ""


def test_a_later_tip_keeps_a_name_the_caller_chose(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)
    _tips.apply_tip(button, "Attach")
    button.setAccessibleName("Attach files")

    _tips.apply_tip(button, "Attach", "Add files")

    assert button.accessibleName() == "Attach files"
    assert button.accessibleDescription() == "Add files"


def test_icon_only_buttons_carry_a_name(qtbot):
    from fxgui.fxwidgets import FXEmojiButton, FXEmojiPicker, FXIconButton

    icon = FXIconButton("attach_file", tip="Attach")
    emoji = FXEmojiButton()
    picker = FXEmojiPicker()
    for widget in (icon, emoji, picker):
        qtbot.addWidget(widget)

    assert icon.accessibleName() == "Attach"
    assert emoji.accessibleName() == "Insert an emoji"
    assert all(button.accessibleName() for button in picker.buttons())
    assert picker.buttons()[0].accessibleName() != picker.buttons()[0].text()


def test_apply_tip_shows_the_theme_in_force_when_it_shows(qtbot):
    from qtpy.QtCore import QEvent, QPoint
    from qtpy.QtGui import QHelpEvent
    from qtpy.QtWidgets import QApplication, QToolTip

    button = QPushButton()
    qtbot.addWidget(button)
    button.show()
    fxstyle.apply_theme("dark")
    _tips.apply_tip(button, "Save", "Write the scene to disk", "Ctrl+S")
    fxstyle.apply_theme("light")

    point = QPoint(2, 2)
    event = QHelpEvent(QEvent.ToolTip, point, button.mapToGlobal(point))
    QApplication.sendEvent(button, event)

    assert QToolTip.text() == _tips.tip(
        "Save", "Write the scene to disk", "Ctrl+S"
    )
    QToolTip.hideText()
