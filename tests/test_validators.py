"""Each validator accepts its pattern; a lowercase start gets capitalised."""

# Third-party
from qtpy.QtCore import Qt
from qtpy.QtGui import QValidator
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QLineEdit

# Internal
from fxgui.fxwidgets import (
    FXCamelCaseValidator,
    FXCapitalizedLetterValidator,
    FXLettersUnderscoreValidator,
    FXLowerCaseValidator,
)


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


def _ok(validator, text):
    return validator.validate(text, 0)[0] == QValidator.Acceptable


def test_camel_case(qapp):
    assert _ok(FXCamelCaseValidator(), "myAsset")
    assert not _ok(FXCamelCaseValidator(), "MyAsset")
    assert not _ok(FXCamelCaseValidator(), "my1")


def test_lower_case_options(qapp):
    assert _ok(FXLowerCaseValidator(), "abc")
    assert not _ok(FXLowerCaseValidator(), "a_1")
    assert _ok(FXLowerCaseValidator(True, True), "a_1")
    assert not _ok(FXLowerCaseValidator(allow_numbers=True), "a_")


def test_letters_and_underscores(qapp):
    assert _ok(FXLettersUnderscoreValidator(), "Ab_")
    assert not _ok(FXLettersUnderscoreValidator(), "A1")
    assert _ok(FXLettersUnderscoreValidator(True), "A1_")
