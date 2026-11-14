"""A breadcrumb can show words of its own; the path keeps the raw parts."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QPushButton

# Internal
from fxgui.fxwidgets import FXBreadcrumb


PATH = ["Projects", "MyShow", "Assets", "Hero"]


def UPPER(parts):
    return [p.upper() for p in parts]


def _crumb(qtbot, cls=FXBreadcrumb, **kwargs):
    kwargs.setdefault("home_icon", "")
    crumb = cls(**kwargs)
    qtbot.addWidget(crumb)
    crumb.resize(500, 32)
    crumb.set_path(PATH)
    crumb.show()
    qtbot.waitExposed(crumb)
    return crumb


def _buttons(crumb):
    layout = crumb._layout
    return [
        layout.itemAt(index).widget()
        for index in range(layout.count())
        if isinstance(layout.itemAt(index).widget(), QPushButton)
    ]


def test_the_segments_show_the_labels(qtbot, qapp):
    crumb = _crumb(qtbot, segment_labels=UPPER)
    assert [b.text() for b in _buttons(crumb)] == [
        "PROJECTS",
        "MYSHOW",
        "ASSETS",
        "HERO",
    ]


def test_the_path_keeps_the_raw_parts(qtbot, qapp):
    crumb = _crumb(qtbot, segment_labels=UPPER)
    assert crumb.path() == PATH


def test_a_segment_click_says_the_raw_parts(qtbot, qapp):
    crumb = _crumb(qtbot, segment_labels=UPPER)
    clicks = []
    crumb.segment_clicked.connect(lambda i, p: clicks.append((i, p)))
    # Index 2, not 0: the first segment is the home button.
    QTest.mouseClick(_buttons(crumb)[2], Qt.LeftButton)
    assert clicks == [(2, PATH[:3])]


def test_the_editor_shows_the_raw_path(qtbot, qapp):
    crumb = _crumb(qtbot, segment_labels=UPPER)
    crumb.enter_edit_mode()
    assert crumb._line_edit.text() == "Projects/MyShow/Assets/Hero"
    crumb.exit_edit_mode()


def test_labels_of_the_wrong_length_fall_back_to_the_parts(qtbot, qapp):
    crumb = _crumb(qtbot, segment_labels=lambda parts: ["only one"])
    assert [b.text() for b in _buttons(crumb)] == PATH


def test_a_subclass_names_its_own_labels(qtbot, qapp):
    calls = []

    class Labelled(FXBreadcrumb):
        def segment_labels(self, path):
            calls.append(list(path))
            return [f"<{p}>" for p in path]

    crumb = _crumb(qtbot, cls=Labelled)
    assert [b.text() for b in _buttons(crumb)] == [f"<{p}>" for p in PATH]
    # Once per rebuild, not once per segment.
    assert calls == [PATH]
    crumb.set_path(PATH[:2])
    assert calls == [PATH, PATH[:2]]


def test_the_home_icon_tooltip_is_the_label(qtbot, qapp):
    crumb = _crumb(qtbot, home_icon="house", segment_labels=UPPER)
    home = _buttons(crumb)[0]
    assert home.toolTip() == "PROJECTS"
    assert home.text() == ""
