"""Input validators for Qt widgets."""

from typing import Optional

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
