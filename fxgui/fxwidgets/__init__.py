"""The fxgui widgets, each in its own private module, exported here."""

from fxgui.fxwidgets._accordion import FXAccordion
from fxgui.fxwidgets._application import FXApplication
from fxgui.fxwidgets._avatar import FXAvatar
from fxgui.fxwidgets._breadcrumb import FXBreadcrumb
from fxgui.fxwidgets._buttons import (
    FXIconButton,
    FXJoinedGroup,
    FXPrimaryButton,
)
from fxgui.fxwidgets._checkable_combo import FXCheckableComboBox
from fxgui.fxwidgets._code_block import FXCodeBlock, FXPygmentsHighlighter
from fxgui.fxwidgets._collapsible import FXCollapsibleWidget
from fxgui.fxwidgets._command_palette import FXCommand, FXCommandPalette
from fxgui.fxwidgets._comments import FXMentionEdit, FXThreadLine
from fxgui.fxwidgets._confirm_delete import FXConfirmDeleteDialog
from fxgui.fxwidgets._severity import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    SUCCESS,
    WARNING,
)
from fxgui.fxwidgets._delegates import (
    FXItemDelegate,
    FXThumbnailDelegate,
)
from fxgui.fxwidgets._dialogs import FXFloatingDialog
from fxgui.fxwidgets._drop_zone import FXDropZone
from fxgui.fxwidgets._emoji_picker import (
    DEFAULT_EMOJIS,
    FXEmojiButton,
    FXEmojiPicker,
)
from fxgui.fxwidgets._file_path_widget import FXFilePathWidget
from fxgui.fxwidgets._flow_layout import FXFlowLayout
from fxgui.fxwidgets._fuzzy_search_list import FXFuzzySearchList
from fxgui.fxwidgets._fuzzy_search_tree import FXFuzzySearchTree
from fxgui.fxwidgets._inputs import (
    FXIconLineEdit,
    FXPasswordLineEdit,
    FXValidatedLineEdit,
)
from fxgui.fxwidgets._keyboard import (
    FXFilteredTree,
    FXKeyboardTree,
    FXSplitButton,
)
from fxgui.fxwidgets._labels import (
    FXElidedLabel,
    FXIconLabel,
    align_labels,
    fix_wrapped_heights,
)
from fxgui.fxwidgets._loading_spinner import FXLoadingOverlay, FXLoadingSpinner
from fxgui.fxwidgets._log_widget import (
    FXOutputLogHandler,
    FXOutputLogWidget,
)
from fxgui.fxwidgets._main_window import FXCommandRow, FXMainWindow
from fxgui.fxwidgets._notification_banner import FXNotificationBanner
from fxgui.fxwidgets._progress_card import FXProgressCard
from fxgui.fxwidgets._range_slider import FXRangeSlider
from fxgui.fxwidgets._rating_widget import FXRatingWidget
from fxgui.fxwidgets._screen_grab import grab_screen_region
from fxgui.fxwidgets._scroll_area import FXResizedScrollArea
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._seating import FXSeating
from fxgui.fxwidgets._single_instance import FXSingleInstance
from fxgui.fxwidgets._singleton import FXSingleton
from fxgui.fxwidgets._splash_screen import FXSplashScreen
from fxgui.fxwidgets._status_bar import FXStatusBar, FXStatusItem
from fxgui.fxwidgets._status_dot import FXStatusDot
from fxgui.fxwidgets._system_tray import FXSystemTray
from fxgui.fxwidgets._tag_input import FXTagChip, FXTagInput
from fxgui.fxwidgets._timeline_slider import FXTimelineSlider
from fxgui.fxwidgets._tips import FXKeycap, apply_tip, keycap, tip
from fxgui.fxwidgets._toggle_switch import FXToggleSwitch
from fxgui.fxwidgets._tree_items import FXSortedTreeWidgetItem
from fxgui.fxwidgets._validators import (
    FXCamelCaseValidator,
    FXCapitalizedLetterValidator,
    FXLettersUnderscoreValidator,
    FXLowerCaseValidator,
)
from fxgui.fxwidgets._widget import FXWidget


__all__ = [
    "align_labels",
    "apply_tip",
    "CRITICAL",
    "DEBUG",
    "DEFAULT_EMOJIS",
    "ERROR",
    "fix_wrapped_heights",
    "FXAccordion",
    "FXApplication",
    "FXAvatar",
    "FXBreadcrumb",
    "FXCamelCaseValidator",
    "FXCapitalizedLetterValidator",
    "FXCheckableComboBox",
    "FXCodeBlock",
    "FXCollapsibleWidget",
    "FXCommand",
    "FXCommandPalette",
    "FXCommandRow",
    "FXConfirmDeleteDialog",
    "FXDropZone",
    "FXElidedLabel",
    "FXEmojiButton",
    "FXEmojiPicker",
    "FXFilePathWidget",
    "FXFilteredTree",
    "FXFloatingDialog",
    "FXFlowLayout",
    "FXFuzzySearchList",
    "FXFuzzySearchTree",
    "FXIconButton",
    "FXIconLabel",
    "FXIconLineEdit",
    "FXItemDelegate",
    "FXJoinedGroup",
    "FXKeyboardTree",
    "FXKeycap",
    "FXLettersUnderscoreValidator",
    "FXLoadingOverlay",
    "FXLoadingSpinner",
    "FXLowerCaseValidator",
    "FXMainWindow",
    "FXMentionEdit",
    "FXNotificationBanner",
    "FXOutputLogHandler",
    "FXOutputLogWidget",
    "FXPasswordLineEdit",
    "FXPrimaryButton",
    "FXProgressCard",
    "FXPygmentsHighlighter",
    "FXRangeSlider",
    "FXRatingWidget",
    "FXResizedScrollArea",
    "FXSearchBar",
    "FXSeating",
    "FXSingleInstance",
    "FXSingleton",
    "FXSortedTreeWidgetItem",
    "FXSplashScreen",
    "FXSplitButton",
    "FXStatusBar",
    "FXStatusDot",
    "FXStatusItem",
    "FXSystemTray",
    "FXTagChip",
    "FXTagInput",
    "FXThreadLine",
    "FXThumbnailDelegate",
    "FXTimelineSlider",
    "FXToggleSwitch",
    "FXValidatedLineEdit",
    "FXWidget",
    "grab_screen_region",
    "INFO",
    "keycap",
    "SUCCESS",
    "tip",
    "WARNING",
]
