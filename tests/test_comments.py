"""FXMentionEdit names people after an `@`; FXThreadLine joins a thread's faces."""

# Third-party
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QColor
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXMentionEdit, FXThreadLine


PEOPLE = {"anne.martin": "Anne Martin", "bob.stone": "Bob Stone"}


def _box(qtbot, people=PEOPLE, **kwargs):
    host = QWidget()
    qtbot.addWidget(host)
    box = FXMentionEdit(host, **kwargs)
    QVBoxLayout(host).addWidget(box)
    box.set_people(people)
    host.show()
    qtbot.waitExposed(host)
    host.activateWindow()
    box.setFocus()
    return host, box


def test_a_chosen_name_is_written_and_counted(qtbot):
    _host, box = _box(qtbot)
    QTest.keyClicks(box, "rendered ")

    box.insert_mention("anne.martin")

    assert box.toPlainText() == "rendered @Anne Martin "
    assert box.mentions() == ("anne.martin",)


def test_a_mention_deleted_from_the_text_is_no_mention(qtbot):
    _host, box = _box(qtbot)
    box.insert_mention("anne.martin")

    box.setPlainText("changed my mind")

    assert box.mentions() == ()


def test_typing_an_at_offers_people_by_name(qtbot):
    _host, box = _box(qtbot)

    QTest.keyClicks(box, "hi @an")

    assert box.completer.completionPrefix() == "an"
    assert box.completer.currentCompletion() == "Anne Martin"


def test_two_people_of_one_name_are_told_apart(qtbot):
    _host, box = _box(qtbot, {"anne.a": "Anne", "anne.b": "Anne"})
    QTest.keyClicks(box, "@an")
    popup = box.completer.popup()
    assert popup.isVisible()
    shown = box.completer.completionModel()
    names = [shown.index(row, 0).data() for row in range(shown.rowCount())]
    assert sorted(names) == ["Anne (anne.a)", "Anne (anne.b)"]

    popup.setCurrentIndex(shown.index(names.index("Anne (anne.b)"), 0))
    QTest.keyClick(popup, Qt.Key_Return)

    assert box.toPlainText() == "@Anne "
    assert box.mentions() == ("anne.b",)


def test_a_name_is_found_without_its_accents(qtbot):
    _host, box = _box(qtbot, {"helene": "Hélène"})

    QTest.keyClicks(box, "@helen")

    shown = box.completer.completionModel()
    assert shown.rowCount() == 1
    assert shown.index(0, 0).data() == "Hélène"


def test_escape_shuts_the_list_first_then_cancels(qtbot):
    _host, box = _box(qtbot, closes=True)
    cancelled = []
    box.cancelled.connect(lambda: cancelled.append(1))
    QTest.keyClicks(box, "hi @an")
    popup = box.completer.popup()
    assert popup.isVisible()

    QTest.keyClick(popup, Qt.Key_Escape)
    assert cancelled == [], "Escape shut the list only"
    QTest.keyClick(box, Qt.Key_Escape)

    assert cancelled == [1]


def test_ctrl_enter_submits_and_writes_no_line(qtbot):
    _host, box = _box(qtbot)
    QTest.keyClicks(box, "done")

    with qtbot.waitSignal(box.submitted, timeout=500):
        QTest.keyClick(box, Qt.Key_Return, Qt.ControlModifier)

    assert box.toPlainText() == "done"


def test_kept_text_and_names_come_back(qtbot):
    _host, box = _box(qtbot)
    box.insert_mention("bob.stone")
    text, chosen = box.kept()
    box.reset()
    assert box.toPlainText() == "" and box.mentions() == ()

    box.restore(text, chosen)

    assert box.mentions() == ("bob.stone",)


def _thread(qtbot, width=300):
    thread = QWidget()
    qtbot.addWidget(thread)
    column = QVBoxLayout(thread)
    head = QLabel("C")
    head.setFixedSize(32, 32)
    column.addWidget(head)
    faces = []
    for name in ("R1", "R2"):
        row = QWidget()
        line = QVBoxLayout(row)
        line.setContentsMargins(48, 8, 0, 8)
        face = QLabel(name)
        face.setFixedSize(32, 32)
        line.addWidget(face)
        column.addWidget(row)
        faces.append(face)
    drawn = FXThreadLine(thread)
    drawn.join(head, faces)
    thread.resize(width, 260)
    thread.show()
    qtbot.waitExposed(thread)
    return thread, drawn, head, faces


def _line_drawn(thread, drawn):
    shot = thread.grab().toImage()
    drawn.hide()
    bare = thread.grab().toImage()
    drawn.show()
    return lambda x, y: shot.pixelColor(x, y) != bare.pixelColor(x, y)


@pytest.mark.parametrize("width", [300, 600])
def test_a_thread_line_joins_the_comment_to_its_last_reply(qtbot, width):
    thread, drawn, head, faces = _thread(qtbot, width)
    on_line = _line_drawn(thread, drawn)
    face = head.geometry()
    x = face.center().x()
    top = faces[0].mapTo(thread, QPoint(0, 0)).y()
    corner = faces[-1].mapTo(thread, QPoint(0, faces[-1].height() // 2))

    assert on_line(x, (face.bottom() + top) // 2)
    assert on_line(corner.x() - 6, corner.y()), "an elbow"
    assert not on_line(x, corner.y() + 12), "stops at the last"


def test_a_hidden_reply_takes_its_elbow_away(qtbot):
    thread, drawn, _head, faces = _thread(qtbot)
    full = drawn.path().boundingRect()

    faces[-1].hide()
    qtbot.wait(10)

    assert drawn.path().boundingRect().bottom() < full.bottom()


def test_the_line_wears_the_theme_s_border_after_a_switch(qtbot):
    thread, drawn, head, _faces = _thread(qtbot)
    x = head.geometry().center().x()
    y = head.geometry().bottom() + 12

    fxstyle.apply_theme("light")
    pixel = drawn.grab().toImage().pixelColor(x, y)

    assert pixel == QColor(fxstyle.get_theme_colors()["border"])
    assert drawn.testAttribute(Qt.WA_TransparentForMouseEvents)


def test_the_box_holds_its_lines_in_the_font_it_is_given_later(qtbot):
    box = FXMentionEdit(lines=3)
    qtbot.addWidget(box)
    font = box.font()
    font.setPixelSize(30)

    box.setFont(font)

    assert box.height() == _lines_tall(box, 3)


def _lines_tall(box, lines):
    margin = box.document().documentMargin()
    return int(box.fontMetrics().lineSpacing() * lines
               + 2 * (box.frameWidth() + margin)) + 1


def test_the_lines_fit_without_scrolling(qtbot):
    box = FXMentionEdit(lines=3)
    qtbot.addWidget(box)
    box.setPlainText("\n".join(["one", "two", "three"]))
    box.show()
    qtbot.waitExposed(box)

    assert box.verticalScrollBar().maximum() == 0


def test_the_box_holds_its_lines_inside_the_frame_its_sheet_gives(qtbot):
    box = FXMentionEdit(lines=2)
    qtbot.addWidget(box)
    before = box.height()

    box.setStyleSheet("FXMentionEdit { border: 6px solid red; }")
    box.ensurePolished()

    assert box.frameWidth() == 6
    assert box.height() == _lines_tall(box, 2) > before
