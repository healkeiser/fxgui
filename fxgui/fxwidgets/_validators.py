"""Input validators for Qt widgets."""

# Built-in
import os
from typing import Optional

# Third-party
from qtpy.QtCore import QRegularExpression
from qtpy.QtGui import QRegularExpressionValidator, QValidator
from qtpy.QtWidgets import QWidget


class FXCamelCaseValidator(QRegularExpressionValidator):
    """Validator for camelCase without special characters or numbers.

    This validator ensures input follows camelCase format: starts with
    a lowercase letter, followed by zero or more groups of an uppercase
    letter followed by lowercase letters.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXCamelCaseValidator())
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Regular expression for camelCase without special characters or
        # numbers
        camel_case_regex = QRegularExpression("^[a-z]+([A-Z][a-z]*)*$")

        # Use the correct method based on what's available
        if hasattr(self, "setRegularExpression"):
            self.setRegularExpression(camel_case_regex)
        else:
            self.setRegExp(camel_case_regex)


class FXLowerCaseValidator(QRegularExpressionValidator):
    """Validator for lowercase letters only, with optional numbers and
    underscores support.

    Args:
        allow_numbers: If `True`, allows numbers in addition to lowercase
            letters.
        allow_underscores: If `True`, allows underscores in addition to
            lowercase letters.
        parent: Parent widget.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXLowerCaseValidator(allow_numbers=True))
    """

    def __init__(
        self,
        allow_numbers: bool = False,
        allow_underscores: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # Build regex pattern based on options
        pattern = "^[a-z"
        if allow_numbers:
            pattern += "0-9"
        if allow_underscores:
            pattern += "_"
        pattern += "]+$"

        lowercase_regex = QRegularExpression(pattern)

        # Use the correct method based on what's available
        if hasattr(self, "setRegularExpression"):
            self.setRegularExpression(lowercase_regex)
        else:
            self.setRegExp(lowercase_regex)


class FXLettersUnderscoreValidator(QRegularExpressionValidator):
    """Validator for letters and underscores, with optional numbers support.

    Args:
        allow_numbers: If `True`, allows numbers in addition to letters and
            underscores.
        parent: Parent widget.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXLettersUnderscoreValidator(allow_numbers=True))
    """

    def __init__(
        self, allow_numbers: bool = False, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # Regular expression for letters, underscores, and optionally numbers
        if allow_numbers:
            letters_underscore_regex = QRegularExpression("^[a-zA-Z0-9_]+$")
        else:
            letters_underscore_regex = QRegularExpression("^[a-zA-Z_]+$")

        # Use the correct method based on what's available
        if hasattr(self, "setRegularExpression"):
            self.setRegularExpression(letters_underscore_regex)
        else:
            self.setRegExp(letters_underscore_regex)


class FXCapitalizedLetterValidator(QValidator):
    """Validator for names that must start with a capital letter and contain
    only letters.

    This validator ensures the first character is uppercase and all
    characters are alphabetic.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXCapitalizedLetterValidator())
    """

    def validate(self, input_string: str, pos: int):
        """Allow only letters and must start with a capital letter."""
        if input_string:
            if not input_string[0].isupper() or not input_string.isalpha():
                return (QValidator.Invalid, input_string, pos)
        return (QValidator.Acceptable, input_string, pos)

    def fixup(self, input_string: str) -> str:
        """Automatically capitalize the first letter."""
        if input_string:
            return input_string[0].upper() + input_string[1:]
        return input_string


def example() -> None:
    import sys
    from qtpy.QtWidgets import (
        QFormLayout,
        QLabel,
        QLineEdit,
        QVBoxLayout,
        QWidget,
    )
    from fxgui.fxwidgets import FXApplication, FXMainWindow

    app: FXApplication = FXApplication(sys.argv)

    # Main window
    window = FXMainWindow()
    window.setWindowTitle("FXValidators Demo")
    window.resize(400, 300)

    # Central widget with form layout
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # Description
    description = QLabel(
        "Test different validators by typing in the fields below.\n"
        "Invalid input will be rejected."
    )
    layout.addWidget(description)

    # Form layout for validators
    form_layout = QFormLayout()
    layout.addLayout(form_layout)

    # CamelCase validator
    camel_case_edit = QLineEdit()
    camel_case_edit.setValidator(FXCamelCaseValidator())
    camel_case_edit.setPlaceholderText("camelCase (e.g., myVariableName)")
    form_layout.addRow("CamelCase:", camel_case_edit)

    # Lowercase validator
    lowercase_edit = QLineEdit()
    lowercase_edit.setValidator(FXLowerCaseValidator())
    lowercase_edit.setPlaceholderText("lowercase only (e.g., hello)")
    form_layout.addRow("Lowercase:", lowercase_edit)

    # Lowercase with numbers
    lowercase_num_edit = QLineEdit()
    lowercase_num_edit.setValidator(FXLowerCaseValidator(allow_numbers=True))
    lowercase_num_edit.setPlaceholderText("lowercase + numbers (e.g., test123)")
    form_layout.addRow("Lowercase + Numbers:", lowercase_num_edit)

    # Lowercase with underscores
    lowercase_underscore_edit = QLineEdit()
    lowercase_underscore_edit.setValidator(
        FXLowerCaseValidator(allow_numbers=True, allow_underscores=True)
    )
    lowercase_underscore_edit.setPlaceholderText(
        "lowercase + numbers + underscores (e.g., my_var_1)"
    )
    form_layout.addRow("Snake Case:", lowercase_underscore_edit)

    # Letters and underscores
    letters_underscore_edit = QLineEdit()
    letters_underscore_edit.setValidator(FXLettersUnderscoreValidator())
    letters_underscore_edit.setPlaceholderText(
        "letters + underscores (e.g., My_Variable)"
    )
    form_layout.addRow("Letters + Underscore:", letters_underscore_edit)

    # Letters, underscores, and numbers
    letters_underscore_num_edit = QLineEdit()
    letters_underscore_num_edit.setValidator(
        FXLettersUnderscoreValidator(allow_numbers=True)
    )
    letters_underscore_num_edit.setPlaceholderText(
        "letters + underscores + numbers (e.g., My_Var_1)"
    )
    form_layout.addRow(
        "Letters + Underscore + Num:", letters_underscore_num_edit
    )

    # Capitalized letter validator
    capitalized_edit = QLineEdit()
    capitalized_edit.setValidator(FXCapitalizedLetterValidator())
    capitalized_edit.setPlaceholderText("starts with capital (e.g., Hello)")
    form_layout.addRow("Capitalized:", capitalized_edit)

    layout.addStretch()
    window.setCentralWidget(widget)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE") == "1":
    example()
