"""The fxgui gallery: every public widget on one window, a page per kind.

Run it with `python -m fxgui.examples`. `build()` returns the window
unshown, which the tests build in every bundled theme.
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
import logging
from pathlib import Path

# Third-party
from qtpy.QtCore import QPoint, QRect, Qt, QTimer
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import __version__, fxstyle, fxwidgets
from fxgui.fxicons import get_icon, set_icon

_IMAGES = Path(__file__).parent / "images"
_LOGGER = logging.getLogger("fxgui.examples")
_FEEDBACK = ("success", "warning", "error", "info", "debug")
_SEVERITIES = {
    "Success": fxwidgets.SUCCESS,
    "Warning": fxwidgets.WARNING,
    "Error": fxwidgets.ERROR,
    "Info": fxwidgets.INFO,
    "Debug": fxwidgets.DEBUG,
}


def _section(title: str, *items) -> QGroupBox:
    """Return a box titled with the names it shows, holding `items`."""
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    for item in items:
        if isinstance(item, QLayout):
            layout.addLayout(item)
        else:
            layout.addWidget(item)
    return box


def _row(*widgets) -> QHBoxLayout:
    """Return `widgets` side by side, pushed to the left."""
    row = QHBoxLayout()
    for widget in widgets:
        row.addWidget(widget)
    row.addStretch()
    return row


def _button(text: str, slot, icon: str = "") -> QPushButton:
    """Return a push button running `slot` on a click."""
    button = QPushButton(text)
    if icon:
        set_icon(button, icon)
    button.clicked.connect(slot)
    return button


def _page(*sections: QWidget) -> QScrollArea:
    """Return `sections` stacked in a scroll area."""
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    for section in sections:
        layout.addWidget(section)
    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(content)
    return scroll


def _buttons_page() -> QWidget:
    composer = []
    for icon_name, text in (
        ("mood", "Insert an emoji"),
        ("attach_file", "Attach a file"),
    ):
        composer.append(fxwidgets.FXIconButton(icon_name, tip=text))
    composer.append(
        fxwidgets.FXIconButton(
            "visibility_off",
            tip="Show to the client",
            checkable=True,
            checked_icon="visibility",
        )
    )
    joined = fxwidgets.FXJoinedGroup()
    status = QComboBox()
    status.addItems(["WIP", "Retake", "Done"])
    joined.add_widget(status)
    joined.add_widget(fxwidgets.FXPrimaryButton("Post", icon="send"))

    split = fxwidgets.FXSplitButton()
    split.setText("Publish")
    menu = QMenu(split)
    menu.addAction("Publish and close")
    menu.addAction("Publish as a draft")
    split.setMenu(menu)
    split.setToolTip(f"Open the menu with {split.dropdown_hint()}")

    toggles = []
    for text, on in (("Autosave", True), ("Notify", False)):
        toggle = fxwidgets.FXToggleSwitch()
        toggle.setChecked(on)
        toggles += [QLabel(text), toggle]

    comment = QLineEdit()
    comment.setPlaceholderText("Write a comment...")
    emoji = fxwidgets.FXEmojiButton()
    emoji.attach(comment)

    return _page(
        _section(
            "FXPrimaryButton / FXIconButton / FXJoinedGroup",
            _row(*composer, QPushButton("Cancel"), joined),
        ),
        _section("FXSplitButton", _row(split)),
        _section("FXToggleSwitch", _row(*toggles)),
        _section("FXEmojiButton / FXEmojiPicker", _row(comment, emoji)),
    )


def _inputs_page() -> QWidget:
    validators = QFormLayout()
    for name, validator, example in (
        ("FXCamelCaseValidator", fxwidgets.FXCamelCaseValidator(), "myAsset"),
        (
            "FXLowerCaseValidator",
            fxwidgets.FXLowerCaseValidator(allow_underscores=True),
            "my_asset",
        ),
        (
            "FXLettersUnderscoreValidator",
            fxwidgets.FXLettersUnderscoreValidator(allow_numbers=True),
            "asset_01",
        ),
        (
            "FXCapitalizedLetterValidator",
            fxwidgets.FXCapitalizedLetterValidator(),
            "Asset",
        ),
    ):
        edit = fxwidgets.FXValidatedLineEdit()
        edit.setValidator(validator)
        edit.setPlaceholderText(f"e.g. {example}")
        validators.addRow(name, edit)

    icon_edit = fxwidgets.FXIconLineEdit("search")
    icon_edit.setPlaceholderText("Shot name")
    password = fxwidgets.FXPasswordLineEdit()
    password.line_edit.setPlaceholderText("Password")

    search = fxwidgets.FXSearchBar(
        placeholder="Search assets...",
        show_filter=True,
        filters=["All", "Models", "Textures"],
    )
    tags = fxwidgets.FXTagInput()
    tags.set_tags(["comp", "lighting", "fx"])
    chip = fxwidgets.FXTagChip("read only", removable=False)

    combo = fxwidgets.FXCheckableComboBox()
    combo.add_items(["render", "cache", "plate"])
    combo.set_checked_items(["cache"])

    mention = fxwidgets.FXMentionEdit(lines=2)
    mention.set_people(
        {"anne.martin": "Anne Martin", "bob.stone": "Bob Stone"}
    )
    mention.setPlaceholderText("Type @ to name someone")

    breadcrumb = fxwidgets.FXBreadcrumb(show_navigation=True)
    breadcrumb.set_path(["Projects", "pipeline", "seq010", "sh0010"])

    return _page(
        _section(
            "FXValidatedLineEdit / FXCamelCaseValidator / "
            "FXLowerCaseValidator / FXLettersUnderscoreValidator / "
            "FXCapitalizedLetterValidator",
            QLabel("Type a refused character to see the shake and flash."),
            validators,
        ),
        _section(
            "FXIconLineEdit / FXPasswordLineEdit", icon_edit, password
        ),
        _section("FXSearchBar", search),
        _section("FXTagInput / FXTagChip", tags, _row(chip)),
        _section("FXCheckableComboBox", _row(combo)),
        _section(
            "FXFilePathWidget", fxwidgets.FXFilePathWidget(mode="directory")
        ),
        _section(
            "FXRangeSlider", fxwidgets.FXRangeSlider(low=25, high=75)
        ),
        _section(
            "FXRatingWidget",
            _row(fxwidgets.FXRatingWidget(initial_rating=3.5, allow_half=True)),
        ),
        _section("FXMentionEdit", mention),
        _section("FXBreadcrumb", breadcrumb),
    )


def _thread() -> QWidget:
    """Return a comment with two replies, joined by an `FXThreadLine`."""
    thread = QWidget()
    layout = QVBoxLayout(thread)
    head = fxwidgets.FXAvatar("Anne Martin", size=32)
    layout.addLayout(_row(head, QLabel("The edge flickers on frame 1042.")))
    faces = []
    for name, text in (("Bob Stone", "Fixed in v005."), ("Madonna", "Agreed.")):
        face = fxwidgets.FXAvatar(name, size=26)
        reply = _row(face, QLabel(text))
        reply.insertSpacing(0, 40)
        layout.addLayout(reply)
        faces.append(face)
    fxwidgets.FXThreadLine(thread).join(head, faces)
    return thread


def _display_page() -> QWidget:
    avatars = [
        fxwidgets.FXAvatar(name, size=32)
        for name in ("Anne Martin", "Madonna", "Bob Stone", "")
    ]

    dots = []
    for key in (*_FEEDBACK, None):
        dot = fxwidgets.FXStatusDot(diameter=10)
        dot.set_feedback(key, key or "Off")
        dots += [dot, QLabel(key or "off")]

    icons = []
    for key, icon_name in (
        ("success", "check_circle"),
        ("warning", "warning"),
        ("error", "error"),
        ("info", "info"),
    ):
        label = fxwidgets.FXIconLabel(size=18)
        set_icon(label, icon_name, color=f"feedback_{key}_foreground")
        icons.append(label)

    elided = fxwidgets.FXElidedLabel(
        "X:/projects/pipeline/sequences/seq010/sh0010/comp/v005/sh0010.exr",
        mode=Qt.ElideMiddle,
    )
    elided.setMaximumWidth(260)

    code = (
        "from fxgui import fxwidgets\n\n"
        "def build():\n"
        '    return fxwidgets.FXPrimaryButton("Post", icon="send")\n'
    )
    highlighted = QPlainTextEdit(code)
    highlighted.setReadOnly(True)
    highlighted.setFixedHeight(100)
    highlighted.highlighter = fxwidgets.FXPygmentsHighlighter(
        highlighted.document(), "python"
    )

    spinners = []
    for style in ("spinner", "dots", "pulse"):
        spinner = fxwidgets.FXLoadingSpinner(size=28, style=style)
        spinner.start()
        spinners.append(spinner)
    covered = QTextEdit("Content under an overlay.")
    covered.setFixedHeight(80)
    overlay = fxwidgets.FXLoadingOverlay(covered, message="Loading...")
    shown = {"on": False}

    def toggle_overlay():
        shown["on"] = not shown["on"]
        overlay.show() if shown["on"] else overlay.hide()

    flow_box = QWidget()
    flow = fxwidgets.FXFlowLayout(flow_box, spacing=4)
    for tag in (
        "comp", "lighting", "fx", "layout", "animation", "matte painting",
        "roto", "paint", "tracking", "grading", "editorial", "lookdev",
    ):
        flow.addWidget(fxwidgets.FXTagChip(tag, removable=False))

    plain = QPushButton("Native rich tooltip")
    fxwidgets.apply_tip(plain, "Save", "Write the scene to disk", "Ctrl+S")
    rich = QPushButton("FXTooltip")
    fxwidgets.set_tooltip(
        rich,
        description="Write the scene to disk.",
        title="Save",
        icon="save",
        shortcut="Ctrl+S",
    )

    return _page(
        _section("FXAvatar", _row(*avatars)),
        _section("FXStatusDot", _row(*dots)),
        _section("FXIconLabel", _row(*icons)),
        _section("FXElidedLabel", elided),
        _section(
            "FXCodeBlock / FXPygmentsHighlighter",
            fxwidgets.FXCodeBlock(code),
            highlighted,
        ),
        _section(
            "FXLoadingSpinner / FXLoadingOverlay",
            _row(*spinners),
            covered,
            _row(_button("Toggle the overlay", toggle_overlay)),
        ),
        _section(
            "FXProgressCard",
            fxwidgets.FXProgressCard(
                title="Rendering sh0010",
                description="Frame 42 of 100",
                progress=42,
                icon="movie",
            ),
        ),
        _section("FXFlowLayout", flow_box),
        _section("FXThreadLine", _thread()),
        _section(
            "FXTooltip / set_tooltip / apply_tip / tip / keycap",
            _row(plain, rich),
        ),
    )


def _containers_page() -> QWidget:
    accordion = fxwidgets.FXAccordion()
    for title, icon_name in (
        ("Render", "movie"),
        ("Cache", "storage"),
        ("Output", "folder"),
    ):
        form = QFormLayout()
        form.addRow("Path:", QLineEdit(f"X:/{title.lower()}"))
        form.addRow("Frames:", QSpinBox())
        accordion.add_section(title, form, icon=icon_name)

    collapsible = fxwidgets.FXCollapsibleWidget(
        title="Settings", icon="settings"
    )
    form = QFormLayout()
    form.addRow("Name:", QLineEdit())
    form.addRow("Value:", QSpinBox())
    form.addRow("Enabled:", QCheckBox())
    collapsible.set_content_layout(form)

    scroll = fxwidgets.FXResizedScrollArea(cap=120)
    scroll.setWidgetResizable(True)
    rows = QWidget()
    rows_layout = QVBoxLayout(rows)
    for number in range(10, 130, 10):
        rows_layout.addWidget(QLabel(f"Shot {number:04d}"))
    scroll.setWidget(rows)

    plain = fxwidgets.FXWidget()
    plain.main_layout.addWidget(QLabel("An FXWidget holding a label."))

    return _page(
        _section("FXAccordion", accordion),
        _section("FXCollapsibleWidget", collapsible),
        _section("FXResizedScrollArea", scroll),
        _section(
            "FXDropZone", fxwidgets.FXDropZone(extensions={".exr", ".png"})
        ),
        _section("FXWidget", plain),
    )


def _thumbnail_tree() -> QTreeWidget:
    """Return an episode, sequence and shot tree drawn with thumbnails."""
    delegate = fxwidgets.FXThumbnailDelegate
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Frame range", "Status"])
    tree.setItemDelegate(delegate(tree))
    delegate.apply_transparent_selection(tree)
    thumbnail = str(_IMAGES / "missing_image.png")
    for episode in ("ep101", "ep102"):
        top = QTreeWidgetItem(tree, [episode, "", "In progress"])
        top.setIcon(0, get_icon("movie"))
        top.setData(0, delegate.DESCRIPTION_ROLE, "Episode")
        top.setData(0, delegate.STARRED_ROLE, episode == "ep101")
        for shot, status, key in (
            ("sh0010", "WIP", "warning"),
            ("sh0020", "Approved", "success"),
        ):
            item = QTreeWidgetItem(top, [shot, "1001-1100", status])
            item.setIcon(0, get_icon("image"))
            item.setData(0, delegate.DESCRIPTION_ROLE, f"{episode}_{shot}")
            item.setData(0, delegate.THUMBNAIL_VISIBLE_ROLE, True)
            item.setData(0, delegate.THUMBNAIL_PATH_ROLE, thumbnail)
            item.setData(0, delegate.STATUS_LABEL_TEXT_ROLE, status)
            color = f"feedback_{key}_foreground"
            item.setData(0, delegate.STATUS_DOT_COLOR_ROLE, color)
            item.setData(0, delegate.STATUS_LABEL_COLOR_ROLE, color)
    tree.setColumnWidth(0, 340)
    tree.expandAll()
    tree.setMinimumHeight(260)
    return tree


def _lists_page() -> QWidget:
    fuzzy_list = fxwidgets.FXFuzzySearchList(
        placeholder="Search shots...", show_ratio_slider=True
    )
    fuzzy_list.set_items([f"sh{number:04d}" for number in range(10, 200, 10)])
    fuzzy_list.setMinimumHeight(180)

    fuzzy_tree = fxwidgets.FXFuzzySearchTree(placeholder="Search assets...")
    for category, assets in (
        ("Characters", ("hero_body", "hero_head", "villain")),
        ("Vehicles", ("car_sports", "truck_pickup")),
    ):
        fuzzy_tree.add_item(category)
        for asset in assets:
            fuzzy_tree.add_item(asset, parent=category)
    fuzzy_tree.expand_all()
    fuzzy_tree.setMinimumHeight(180)

    filtered = fxwidgets.FXFilteredTree(placeholder="Filter, or type on the tree")
    filtered.tree.setHeaderHidden(True)
    for sequence in ("seq010", "seq020"):
        parent = QTreeWidgetItem(filtered.tree, [sequence])
        for shot in ("sh0010", "sh0020", "sh0030"):
            QTreeWidgetItem(parent, [shot])
    filtered.tree.expandAll()
    filtered.tree.set_primary_act(
        lambda item: _LOGGER.info("Opened %s", item.text(0))
    )
    filtered.setMinimumHeight(180)

    sorted_tree = QTreeWidget()
    sorted_tree.setHeaderLabels(["Version"])
    sorted_tree.setSortingEnabled(True)
    for text in ("v1", "v9", "v10", "v2", "v20", "v11"):
        sorted_tree.addTopLevelItem(fxwidgets.FXSortedTreeWidgetItem([text]))
    sorted_tree.sortByColumn(0, Qt.AscendingOrder)
    sorted_tree.setRootIsDecorated(False)
    sorted_tree.setFixedHeight(190)

    icon_list = QListWidget()
    icon_list.setItemDelegate(fxwidgets.FXItemDelegate(icon_list))
    for text, icon_name in (
        ("Documents", "folder"),
        ("Images", "image"),
        ("Settings", "settings"),
    ):
        icon_list.addItem(QListWidgetItem(get_icon(icon_name), text))
    icon_list.setFixedHeight(100)

    labels = QTreeWidget()
    labels.setHeaderHidden(True)
    labels.setRootIsDecorated(False)
    labels.setItemDelegate(
        fxwidgets.FXColorLabelDelegate(
            {
                key: (
                    f"feedback_{key}_background",
                    f"feedback_{key}_foreground",
                    f"feedback_{key}_foreground",
                    get_icon(icon_name),
                    True,
                )
                for key, icon_name in (
                    ("success", "check_circle"),
                    ("warning", "warning"),
                    ("error", "error"),
                    ("info", "info"),
                )
            },
            labels,
        )
    )
    for text in ("Success", "Warning", "Error", "Info", "Unknown"):
        QTreeWidgetItem(labels, [text])
    labels.setFixedHeight(140)

    return _page(
        _section("FXFuzzySearchList", fuzzy_list),
        _section("FXFuzzySearchTree", fuzzy_tree),
        _section("FXFilteredTree / FXKeyboardTree", filtered),
        _section("FXSortedTreeWidgetItem", sorted_tree),
        _section("FXThumbnailDelegate", _thumbnail_tree()),
        _section("FXItemDelegate", icon_list),
        _section("FXColorLabelDelegate", labels),
    )


def _timeline_page() -> QWidget:
    basic = fxwidgets.FXTimelineSlider(
        start_frame=1,
        end_frame=120,
        current_frame=1,
        show_keyframe_controls=True,
    )
    for key in (1, 30, 60, 90, 120):
        basic.add_keyframe(key)

    full = fxwidgets.FXTimelineSlider(
        start_frame=1001,
        end_frame=1240,
        current_frame=1050,
        show_loop_controls=True,
        show_keyframe_controls=True,
        controls_position="below",
    )
    full.set_marker_frames(
        "cached",
        set(range(1020, 1081)) | set(range(1150, 1201)),
        color="#22c55e",
        style="strip",
    )
    full.set_marker_frames(
        "errors", {1035, 1036, 1132, 1197}, color="#ef4444", style="line"
    )
    # The in and out buttons only ask; the caller sets the loop region.
    loop = {"in": 1040, "out": 1120}

    def mark(which, frame):
        loop[which] = frame
        full.set_loop_region(loop["in"], loop["out"])

    full.in_point_requested.connect(lambda frame: mark("in", frame))
    full.out_point_requested.connect(lambda frame: mark("out", frame))
    full.set_loop_region(loop["in"], loop["out"])

    return _page(
        _section("FXTimelineSlider", basic),
        _section(
            "FXTimelineSlider with markers, a loop region and zoom",
            QLabel(
                "Wheel over the track zooms around the pointer and a "
                "middle-button drag pans."
            ),
            full,
            _row(_button("Reset view", full.reset_view, "fit_screen")),
        ),
    )


# Demo panes: a surface card with a well inside, on the frame.
fxstyle.register_widget_style("""
QFrame#fxShowcasePane {
    background-color: @surface;
    border: 1px solid @pane_border;
    border-radius: @button_radius;
}
QFrame#fxShowcasePane > QListWidget,
QFrame#fxShowcasePane > QTextEdit {
    background-color: @well;
}
""")


def _pane(title: str, content: QWidget) -> QFrame:
    """Return a titled pane card holding `content`."""
    pane = QFrame()
    pane.setObjectName("fxShowcasePane")
    layout = QVBoxLayout(pane)
    layout.setContentsMargins(8, 6, 8, 8)
    layout.addWidget(QLabel(title))
    layout.addWidget(content)
    return pane


def _framed_body() -> QWidget:
    """Return two panes in splitters on the frame."""
    shots = QListWidget()
    shots.addItems([f"Shot {number:03d}" for number in range(10, 90, 10)])
    right = QSplitter(Qt.Vertical)
    right.addWidget(_pane("Notes", QTextEdit("A note")))
    right.addWidget(_pane("Log", QTextEdit("Session log")))
    splitter = QSplitter(Qt.Horizontal)
    splitter.addWidget(_pane("Shots", shots))
    splitter.addWidget(right)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6, 0, 6, 6)
    layout.addWidget(splitter)
    for widget in (body, right, splitter):
        fxstyle.mark_as_frame(widget)
    return body


def _open_framed(gallery: QWidget) -> None:
    window = fxwidgets.FXMainWindow(
        parent=gallery,
        title="Framed window",
        project="fxgui",
        version=__version__,
        toolbar=False,
        framed=True,
    )
    window.setWindowFlag(Qt.Window)
    row = fxwidgets.FXCommandRow(margins=(6, 6, 6, 0), spacing=6)
    row.addAction(get_icon("arrow_back"), "Back")
    row.addAction(get_icon("refresh"), "Refresh")
    window.addToolBar(Qt.TopToolBarArea, row)
    window.setCentralWidget(_framed_body())
    window.resize(760, 480)
    window.show()


def _open_floating(gallery: QWidget) -> None:
    dialog = fxwidgets.FXFloatingDialog(gallery, title="Quick info", popup=True)
    dialog.main_layout.addWidget(QLabel("A popup dialog; click outside."))
    dialog.show_under_cursor()


def _open_confirm(gallery: QWidget) -> None:
    fxwidgets.FXConfirmDeleteDialog(
        gallery,
        title="Delete beauty v004",
        body="The render and its frames go. This cannot be undone.",
        confirm_word="beauty",
    ).open()


def _open_splash(gallery: QWidget) -> None:
    # No parent: a splash is its own window, so the gallery holds it.
    gallery.splash = splash = fxwidgets.FXSplashScreen(
        image_path=str(_IMAGES / "splash.png"),
        title="fxgui",
        information="A splash screen with a progress bar; click to close.",
        show_progress_bar=True,
        project="fxgui",
        corner_radius=12,
        border_width=1,
    )
    splash.set_progress(60)
    splash.show()
    QTimer.singleShot(4000, splash.close)


def _open_seated(gallery: QWidget) -> None:
    panel = QFrame(gallery, Qt.Tool | Qt.FramelessWindowHint)
    panel.setAttribute(Qt.WA_DeleteOnClose)
    layout = QVBoxLayout(panel)
    layout.addWidget(QLabel("A panel seated at the pointer."))
    layout.addWidget(_button("Close", panel.close))
    panel.seating = fxwidgets.FXSeating(panel)
    panel.seating.show_at(QRect(), QCursor.pos())


def _open_tray(button: QPushButton) -> None:
    if getattr(button, "tray", None) is None:
        button.tray = fxwidgets.FXSystemTray()
    button.tray.show()


def _grab_into(gallery: QWidget, label: QLabel) -> None:
    pixmap = fxwidgets.grab_screen_region(gallery)
    if pixmap is not None:
        label.setPixmap(pixmap.scaledToHeight(80, Qt.SmoothTransformation))


def _windows_page(window: fxwidgets.FXMainWindow) -> QWidget:
    bar = window.statusBar()
    warnings = fxwidgets.FXStatusItem("3", "warning")
    warnings.set_tip("Warnings", "Show the log")
    warnings.clicked.connect(lambda: _LOGGER.warning("3 warnings"))
    bar.add_item(warnings)
    bar.add_item(
        fxwidgets.FXStatusItem("Online", "cloud_done", clickable=False),
        side="right",
    )
    busy = QCheckBox("Busy")
    busy.toggled.connect(bar.set_busy)

    banners = [
        _button(
            text,
            lambda _=False, text=text, severity=severity: (
                fxwidgets.FXNotificationBanner(
                    parent=window.centralWidget(),
                    message=f"A {text.lower()} banner.",
                    severity_type=severity,
                    timeout=4000,
                ).show()
            ),
        )
        for text, severity in _SEVERITIES.items()
    ]
    messages = [
        _button(
            text,
            lambda _=False, text=text, severity=severity: bar.showMessage(
                f"A {text.lower()} message.", severity
            ),
        )
        for text, severity in _SEVERITIES.items()
    ]

    palette = fxwidgets.FXCommandPalette(
        window,
        lambda: [
            fxwidgets.FXCommand(
                "Toggle theme", window.toggle_theme, "Ctrl+T", "View"
            ),
            fxwidgets.FXCommand(
                "Log a message",
                lambda: _LOGGER.info("From the palette"),
                section="Log",
            ),
            fxwidgets.FXCommand(
                "Publish", lambda: None, enabled=False, tip="Nothing to publish"
            ),
        ],
    )

    log = fxwidgets.FXOutputLogWidget()
    log.setMinimumHeight(160)
    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.addHandler(fxwidgets.FXOutputLogHandler(log))
    levels = [
        _button(
            name,
            lambda _=False, name=name, level=level: _LOGGER.log(level, name),
        )
        for name, level in (
            ("Debug", logging.DEBUG),
            ("Info", logging.INFO),
            ("Warning", logging.WARNING),
            ("Error", logging.ERROR),
        )
    ]

    grabbed = QLabel()
    tray = QPushButton("Show the tray icon")
    tray.clicked.connect(lambda: _open_tray(tray))

    return _page(
        _section(
            "FXMainWindow / FXCommandRow",
            _row(_button("Open a framed window", lambda: _open_framed(window))),
        ),
        _section("FXStatusBar / FXStatusItem", _row(*messages, busy)),
        _section("FXNotificationBanner", _row(*banners)),
        _section(
            "FXCommandPalette / FXCommand",
            _row(
                _button(
                    "Open the palette",
                    lambda: palette.open_commands(
                        window.mapToGlobal(QPoint(window.width() // 2, 40))
                    ),
                )
            ),
        ),
        _section(
            "FXFloatingDialog / FXConfirmDeleteDialog",
            _row(
                _button("Floating dialog", lambda: _open_floating(window)),
                _button("Confirm a delete", lambda: _open_confirm(window)),
            ),
        ),
        _section(
            "FXSplashScreen / FXSystemTray / FXSeating",
            _row(
                _button("Splash screen", lambda: _open_splash(window)),
                tray,
                _button("Seat a panel", lambda: _open_seated(window)),
            ),
        ),
        _section(
            "grab_screen_region",
            _row(
                _button("Grab a region", lambda: _grab_into(window, grabbed)),
                grabbed,
            ),
        ),
        _section("FXOutputLogWidget / FXOutputLogHandler", log, _row(*levels)),
    )


def _docking_page() -> QWidget:
    try:
        from fxgui import fxdocking
    except ImportError:
        return _page(
            _section(
                "FXDockArea",
                QLabel("Install the docking extra: pip install fxgui[docking]"),
            )
        )
    docks = fxdocking.FXDockArea()
    docks.set_central(QTextEdit("The body the panes dock around."))
    shots = QListWidget()
    shots.addItems([f"sh{number:04d}" for number in range(10, 90, 10)])
    docks.add_dock("shots", "Shots", shots, "left", size=(1, 3))
    docks.add_dock("log", "Log", QTextEdit("Session log"), "bottom")
    docks.setMinimumHeight(420)
    return _page(_section("FXDockArea", docks))


def build() -> fxwidgets.FXMainWindow:
    """Return the gallery window, built in the current theme and unshown."""
    window = fxwidgets.FXMainWindow(
        title="fxgui gallery",
        project="fxgui",
        version=__version__,
        company="Valentin Beaumont",
    )
    tabs = QTabWidget()
    window.setCentralWidget(tabs)
    for title, page in (
        ("Buttons", _buttons_page()),
        ("Inputs", _inputs_page()),
        ("Display", _display_page()),
        ("Containers", _containers_page()),
        ("Lists and trees", _lists_page()),
        ("Timeline", _timeline_page()),
        ("Windows", _windows_page(window)),
        ("Docking", _docking_page()),
    ):
        tabs.addTab(page, title)
    window.resize(1000, 800)
    return window


def main() -> None:
    """Show the gallery until it is closed."""
    application = fxwidgets.FXApplication()
    window = build()
    window.show()
    window.center_on_screen()
    application.exec_()


if __name__ == "__main__":
    main()
