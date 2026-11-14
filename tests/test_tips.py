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
    hover = QColor(fxstyle.colors().tooltip).rgb()
    box = f"background: {fxstyle.colors().surface};"

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


# ' Facts, code and a hint

_PATH = (
    "X:\\pipeline_episodic\\production\\episodes\\ep010\\seq010\\sh0020"
    "\\lighting\\publish\\render\\livetest\\v001\\.pipeline"
    "\\pipeline_episodic_ep010_seq010_sh0020_lighting_livetest_v001"
    ".preview.mov"
)
_FACTS = [("Product", "render/livetest"), ("Files", "8 x .exr")]


def _code_rows_of(html: str) -> list:
    """Return the rows of the code block in `html`, as the user reads them."""
    from html import unescape

    cell = re.search(r'<td style="white-space:pre;">(.*?)</td>', html, re.S)
    return unescape(_strip_markup(cell[1])).split("\n")


def test_a_tip_without_the_new_parts_is_the_html_it_always_was(qtbot):
    muted = fxstyle.colors().text_muted

    assert _tips.tip("Back", "Navigate\nback") == (
        "<div><b>Back</b></div>"
        f'<div style="margin-top:3px;"><span style="color:{muted};">'
        "Navigate<br>back</span></div>"
    )
    assert _tips.tip("Save", "Write", "Ctrl+S") == _tips.tip(
        "Save", "Write", "Ctrl+S", facts=[("Status", "")], code="", hint=""
    )


def test_facts_are_a_table_in_the_order_given(qtbot):
    html = _tips.tip("livetest v001", facts=_FACTS)

    rows = re.findall(r"<tr><td[^>]*>(.*?)</td><td>(.*?)</td></tr>", html)
    assert rows == [("Product", "render/livetest"), ("Files", "8 x .exr")]
    # The label is dimmed and stands off its value; the value is not dimmed.
    muted = fxstyle.colors().text_muted
    assert html.count(f'<td style="color:{muted}; padding-right:14px;">') == 2
    assert "<td>render/livetest</td>" in html


def test_a_fact_without_a_value_is_left_out(qtbot):
    html = _tips.tip(
        "livetest v001",
        facts=[("Product", ""), ("Files", "8"), ("Status", None)],
    )

    assert "Files" in html
    assert "Product" not in html and "Status" not in html
    # With no fact left there is no table, and with nothing left no tip.
    assert "<table" not in _tips.tip("livetest v001", facts=[("Product", "")])
    assert _tips.tip("", facts=[("Product", ""), ("Status", None)]) == ""


def test_a_fact_takes_any_iterable_and_a_number(qtbot):
    html = _tips.tip("Render", facts=(pair for pair in [("Errors", 0)]))

    assert "<td>0</td>" in html


def test_code_is_small_text_on_a_fill(themed_app, qtbot):
    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        colors = fxstyle.colors()
        html = _tips.tip("Shot", code="publish.render")

        assert f'bgcolor="{colors.tooltip}"' in html
        assert f"color:{colors.text};" in html
        assert f"font-size:{fxstyle.FONT_SIZE - 2}px" in html
        assert _code_rows_of(html) == ["publish.render"]


def test_code_names_the_family_of_the_mono_role(qtbot, monkeypatch):
    from qtpy.QtGui import QFont

    monkeypatch.setattr(fxstyle, "font", lambda role: QFont(["Brand's Mono"]))
    assert "font-family:'Brand&#x27;s Mono';" in _tips.tip("", code="a.key")

    # A role with no family leaves the face to the tip's own font.
    def without_a_family(role):
        font = QFont()
        font.setFamilies([])
        return font

    monkeypatch.setattr(fxstyle, "font", without_a_family)
    assert "font-family" not in _tips.tip("", code="a.key")


def test_a_short_path_stays_on_one_row(qtbot):
    path = "X:\\show\\ep010\\sh0020\\render_v001.exr"

    assert _code_rows_of(_tips.tip("", code=path)) == [path]


def test_a_long_path_is_cut_after_folder_separators(qtbot):
    rows = _code_rows_of(_tips.tip("livetest v001", code=_PATH))

    # Nothing is lost or added: the rows put end to end are the path.
    assert "".join(rows) == _PATH
    assert len(rows) > 1
    assert all(len(row) <= _tips._CODE_COLUMNS for row in rows)
    # A row ends at a folder; the file name, longer than a row and with
    # no folder in it, is cut after an underscore.
    assert all(row.endswith(("\\", "_")) for row in rows[:-1])
    assert rows[0].endswith("\\") and rows[1].endswith("\\")
    assert rows[2].startswith("pipeline_episodic_")


def test_code_has_no_zero_width_character(qtbot):
    html = _tips.tip("livetest v001", code=_PATH)

    assert not re.search("[\u200b\u200c\u200d\u2060\ufeff]", html)


def test_code_without_a_separator_is_cut_at_the_last_column(qtbot):
    columns = _tips._CODE_COLUMNS

    assert _tips._code_rows("x" * (columns * 2 + 3)) == [
        "x" * columns,
        "x" * columns,
        "xxx",
    ]
    # A command is cut after a space, a posix path after a slash.
    command = "lsd publish " + "--flag value " * 6
    assert all(row.endswith(" ") for row in _tips._code_rows(command)[:-1])
    posix = "/mnt/show" + "/folder" * 12
    assert all(row.endswith("/") for row in _tips._code_rows(posix)[:-1])


def test_a_newline_in_code_starts_a_row(qtbot):
    html = _tips.tip("", code="first\\path\nsecond  indented")

    assert _code_rows_of(html) == ["first\\path", "second  indented"]


def test_a_long_path_does_not_widen_the_tooltip(qtbot):
    """Qt cannot break a path, so before the rows were cut a tooltip was
    as wide as its path."""

    def width(code):
        label = QLabel(_tips.tip("livetest v001", code=code))
        label.setWordWrap(True)
        return label.sizeHint().width()

    one_row = width("x" * _tips._CODE_COLUMNS)

    assert width(_PATH) <= one_row
    assert width(_PATH * 4) <= one_row


def test_code_is_drawn_as_its_rows(qtbot):
    """Qt wraps none of the rows again, however narrow the tooltip, and a
    command is not broken at its spaces or hyphens."""
    for code in (_PATH, "lsd publish --shot sh0020 --task lighting-final"):
        html = _tips.tip("", code=code)
        document = QTextDocument()
        document.setHtml(html)
        document.setTextWidth(60)
        document.size()

        drawn = []
        block = document.begin()
        while block.isValid():
            if block.text():
                drawn.append((block.text(), block.layout().lineCount()))
            block = block.next()

        assert drawn == [(row, 1) for row in _code_rows_of(html)]


def test_a_hint_closes_the_tip_dimmed(qtbot):
    muted = fxstyle.colors().text_muted
    html = _tips.tip(
        "livetest v001", facts=_FACTS, code=_PATH, hint="Double-click to play"
    )

    assert html.endswith(
        f'<div style="margin-top:8px;"><span style="color:{muted};">'
        "Double-click to play</span></div>"
    )


def test_the_blocks_come_in_order_with_air_between_them(qtbot):
    html = _tips.tip(
        "Publish",
        "Send the scene to the farm",
        "Ctrl+P",
        facts=_FACTS,
        code="publish.render",
        hint="Right-click for more",
    )

    order = [
        html.index(part)
        for part in (
            "<b>Publish</b>",
            "Send the scene",
            "Product",
            "publish.render",
            "Right-click",
        )
    ]
    assert order == sorted(order)
    # The body stays close under its title; each later block stands off.
    assert re.findall(r"margin-top:(\d+)px", html) == ["3", "8", "8", "8"]


def test_facts_code_or_a_hint_alone_make_a_tip(qtbot):
    for parts in ({"facts": _FACTS}, {"code": "a.key"}, {"hint": "Click"}):
        html = _tips.tip("", **parts)

        assert html.startswith("<div>")
        assert "<b>" not in html and "margin-top" not in html


def test_the_new_parts_are_escaped(qtbot):
    html = _tips.tip(
        "Shot",
        facts=[("A&B <label>", "C&D <value>")],
        code="X:\\a&b\\<shot>",
        hint="Click & <drag>",
    )

    for raw in ("<label>", "<value>", "<shot>", "<drag>"):
        assert raw not in html
    assert "A&amp;B &lt;label&gt;" in html
    assert "C&amp;D &lt;value&gt;" in html
    assert "X:\\a&amp;b\\&lt;shot&gt;" in html
    assert "Click &amp; &lt;drag&gt;" in html


def test_the_new_parts_are_written_in_the_theme_in_force(qtbot):
    for theme in ("dark", "light"):
        fxstyle.apply_theme(theme)
        colors = fxstyle.colors()
        html = _tips.tip("Shot", facts=_FACTS, code="a.key", hint="Click")

        assert html.count(f"color:{colors.text_muted};") == 3
        assert f'bgcolor="{colors.tooltip}"' in html


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
        assert f"background:{fxstyle.colors().tooltip};" in html
        assert "palette(" not in html


def test_a_fill_on_a_tooltip_shows_in_every_theme(themed_app, qtbot):
    """A tooltip is a `surface` card: a keycap or a code block filled with
    `surface` would have no fill at all."""
    button = QPushButton("Save")
    qtbot.addWidget(button)
    button.show()
    _tips.apply_tip(button, "Save", shortcut="Ctrl+S")
    point = QPoint(2, 2)
    QApplication.sendEvent(
        button, QHelpEvent(QEvent.ToolTip, point, button.mapToGlobal(point))
    )
    image = _visible_tip().grab().toImage()
    card = image.pixelColor(3, image.height() // 2).name()
    QToolTip.hideText()

    assert card == fxstyle.colors().surface.lower()
    for theme in fxstyle.get_available_themes():
        fxstyle.apply_theme(theme)
        colors = fxstyle.colors()
        assert colors.tooltip.lower() != colors.surface.lower(), theme
        assert f"background:{colors.tooltip};" in _tips.keycap("S"), theme


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

    # No fill of its own: inside, the host shows through.
    fill = image.pixelColor(second.left() + 2, second.center().y()).name()
    assert fill == image.pixelColor(second.right() + 3, second.top()).name()
    # The border is drawn and the corner is cut round.
    edge = image.pixelColor(second.center().x(), second.top()).name()
    assert edge == fxstyle.colors().border_light.lower()
    corner = image.pixelColor(second.topLeft()).name()
    assert corner != edge


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


def test_apply_tip_status_without_a_title_is_the_body(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)

    _tips.apply_tip(button, "", "Write the scene")

    assert button.statusTip() == "Write the scene"


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


_RICH = {
    "facts": [("Product", "render/livetest"), ("Files", "8"), ("Status", "")],
    "code": _PATH,
    "hint": "Double-click to play the preview",
}


def test_apply_tip_carries_the_new_parts_on_a_widget(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)
    button.show()
    fxstyle.apply_theme("dark")
    _tips.apply_tip(button, "livetest v001", **_RICH)
    assert button.toolTip() == _tips.tip("livetest v001", **_RICH)
    fxstyle.apply_theme("light")

    point = QPoint(2, 2)
    QApplication.sendEvent(
        button, QHelpEvent(QEvent.ToolTip, point, button.mapToGlobal(point))
    )

    # Rebuilt as it shows: the parts came back whole, in the new theme.
    assert QToolTip.text() == _tips.tip("livetest v001", **_RICH)
    assert f'bgcolor="{fxstyle.colors().tooltip}"' in QToolTip.text()
    QToolTip.hideText()


def test_apply_tip_carries_the_new_parts_on_an_action(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    action = QAction("Play", host)
    fxstyle.apply_theme("dark")
    _tips.apply_tip(action, "livetest v001", **_RICH)
    fxstyle.apply_theme("light")

    action.hover()

    assert action.toolTip() == _tips.tip("livetest v001", **_RICH)


def test_apply_tip_carries_the_new_parts_on_items(qtbot):
    from qtpy.QtWidgets import QTableWidget, QTableWidgetItem

    tree = QTreeWidget()
    tree.setColumnCount(2)
    listing = QListWidget()
    table = QTableWidget(1, 1)
    cell = QTableWidgetItem("livetest")
    table.setItem(0, 0, cell)
    views = {
        tree: QTreeWidgetItem(tree, ["livetest", "v001"]),
        listing: QListWidgetItem("livetest", listing),
        table: cell,
    }
    fxstyle.apply_theme("dark")
    for view, item in views.items():
        qtbot.addWidget(view)
        view.show()
        _tips.apply_tip(item, "livetest v001", **_RICH)
    fxstyle.apply_theme("light")

    for view, item in views.items():
        if view is tree:
            point = view.visualItemRect(item).center()
        else:
            point = view.visualRect(view.indexFromItem(item)).center()
        viewport = view.viewport()
        QApplication.sendEvent(
            viewport,
            QHelpEvent(QEvent.ToolTip, point, viewport.mapToGlobal(point)),
        )

        assert QToolTip.text() == _tips.tip("livetest v001", **_RICH), view
        QToolTip.hideText()
    assert all(
        tree.topLevelItem(0).toolTip(column)
        for column in range(tree.columnCount())
    )


def test_the_new_parts_are_spoken_as_plain_words(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)

    _tips.apply_tip(
        button, "livetest v001", "A <render>", "Ctrl+P", **_RICH
    )

    assert button.accessibleName() == "livetest v001"
    # One part per line, the fact without a value left out, the path whole.
    assert button.accessibleDescription() == "\n".join(
        (
            "A <render>",
            "Product: render/livetest",
            "Files: 8",
            _PATH,
            "Double-click to play the preview",
        )
    )
    # The status bar line stays the title and the body.
    assert button.statusTip() == "livetest v001 - A <render>"


def test_spoken_words_follow_a_later_tip(qtbot):
    label = QLabel()
    qtbot.addWidget(label)

    _tips.apply_tip(label, "Version", code="a\\path", hint="Click")
    assert label.accessibleDescription() == "a\\path\nClick"
    _tips.apply_tip(label, "Version", facts=[("Files", "8")])

    assert label.accessibleDescription() == "Files: 8"
    assert "a\\path" not in label.toolTip()


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
            (
                "Mark In",
                "Set the loop in point at the current frame; "
                "Shift-drag the track to set both",
            ),
            (
                "Mark Out",
                "Set the loop out point at the current frame; "
                "Shift-drag the track to set both",
            ),
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

    icon = FXIconButton("paperclip", tip="Attach")
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


def test_importing_on_a_worker_thread_leaves_no_filter_there(qapp):
    import importlib.util
    import threading

    from qtpy.QtCore import QObject

    spec = importlib.util.find_spec("fxgui.fxwidgets._tips")
    found = {}

    def load():
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        found["module"] = module
        found["threads"] = [
            value.thread()
            for value in vars(module).values()
            if isinstance(value, QObject)
        ]

    worker = threading.Thread(target=load)
    worker.start()
    worker.join()

    assert all(thread == qapp.thread() for thread in found["threads"])
    button = QPushButton()
    found["module"].apply_tip(button, "Save")
    refresher = found["module"]._refresher
    assert refresher.thread() == qapp.thread()
    assert refresher.parent() is qapp
