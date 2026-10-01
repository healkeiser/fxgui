"""The item-data roles fxgui's item views claim, in one table."""

# Third-party
from qtpy.QtCore import Qt

# One range, so no two roles can share a number and FIRST_FREE is always
# the first one past them. A role added here goes before SORT.
(
    THUMBNAIL_VISIBLE,
    THUMBNAIL_PATH,
    DESCRIPTION,
    STATUS_DOT_COLOR,
    STATUS_LABEL_COLOR,
    STATUS_LABEL_TEXT,
    STATUS_DOT_VISIBLE,
    STATUS_LABEL_VISIBLE,
    CHILD_COUNT_VISIBLE,
    PICKER_TEXT,
    PICKER_CHOICES,
    PICKER_UNAVAILABLE,
    SORT,
    FIRST_FREE,
) = range(int(Qt.UserRole) + 1, int(Qt.UserRole) + 15)
