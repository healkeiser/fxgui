"""Input validators for Qt widgets."""

# Built-in
from typing import Optional

# Third-party
from qtpy.QtCore import QRegularExpression
from qtpy.QtGui import QRegularExpressionValidator, QValidator
from qtpy.QtWidgets import QWidget


class FXCamelCaseValidator(QRegularExpressionValidator):
    """Accept camelCase letters: a lowercase start, no digits or symbols.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXCamelCaseValidator())
    """

    def __init__(self, parent=None):
        super().__init__(QRegularExpression("^[a-z]+([A-Z][a-z]*)*$"), parent)


class FXLowerCaseValidator(QRegularExpressionValidator):
    """Accept lowercase letters, and digits or underscores if allowed.

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
        digits = "0-9" if allow_numbers else ""
        underscore = "_" if allow_underscores else ""
        super().__init__(
            QRegularExpression(f"^[a-z{digits}{underscore}]+$"), parent
        )


class FXLettersUnderscoreValidator(QRegularExpressionValidator):
    """Accept letters and underscores, and digits if allowed.

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
        digits = "0-9" if allow_numbers else ""
        super().__init__(QRegularExpression(f"^[a-zA-Z{digits}_]+$"), parent)


class FXCapitalizedLetterValidator(QValidator):
    """Accept letters only; `fixup` capitalises the first.

    Examples:
        >>> from qtpy.QtWidgets import QLineEdit
        >>> line_edit = QLineEdit()
        >>> line_edit.setValidator(FXCapitalizedLetterValidator())
    """

    def validate(self, input_string: str, pos: int):
        """Allow only letters; a lowercase start waits for `fixup`."""
        if input_string:
            if not input_string.isalpha():
                return (QValidator.Invalid, input_string, pos)
            if not input_string[0].isupper():
                # Intermediate, not Invalid: Qt only calls fixup on it.
                return (QValidator.Intermediate, input_string, pos)
        return (QValidator.Acceptable, input_string, pos)

    def fixup(self, input_string: str) -> str:
        """Automatically capitalize the first letter."""
        if input_string:
            return input_string[0].upper() + input_string[1:]
        return input_string
