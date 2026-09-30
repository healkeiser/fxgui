"""The capitalised-name validator fixes a lowercase start instead of refusing it."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import QValidator
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLineEdit

# Internal
from fxgui.fxwidgets import FXCapitalizedLetterValidator


def test_a_lowercase_start_is_capitalised_on_enter(qtbot, qapp):
    edit = QLineEdit()
    edit.setValidator(FXCapitalizedLetterValidator())
    qtbot.addWidget(edit)
    QTest.keyClicks(edit, "hello")
    assert edit.text() == "hello"
    QTest.keyClick(edit, Qt.Key_Return)
    assert edit.text() == "Hello"


def test_non_letters_are_still_refused(qapp):
    validator = FXCapitalizedLetterValidator()
    assert validator.validate("Hel1o", 5)[0] == QValidator.Invalid
    assert validator.validate("hel1o", 5)[0] == QValidator.Invalid
    assert validator.validate("Hello", 5)[0] == QValidator.Acceptable
