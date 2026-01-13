"""Custom Qt widgets for fxgui.

This package provides a collection of custom Qt widgets built on top of qtpy,
offering enhanced functionality and consistent styling for DCC applications.
"""

from fxgui.fxstyle import (
    FXThemeAware,
    FXThemeManager,
    FXThemeColors,
    theme_manager,
)
from fxgui.fxwidgets._accordion import FXAccordion, FXAccordionSection
from fxgui.fxwidgets._application import FXApplication
from fxgui.fxwidgets._breadcrumb import FXBreadcrumb
from fxgui.fxwidgets._code_block import FXCodeBlock
from fxgui.fxwidgets._collapsible import FXCollapsibleWidget
from fxgui.fxwidgets._constants import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    SUCCESS,
    WARNING,
)
from fxgui.fxwidgets._delegates import (
    FXColorLabelDelegate,
    FXThumbnailDelegate,
)
from fxgui.fxwidgets._dialogs import FXFloatingDialog
from fxgui.fxwidgets._file_path_widget import FXFilePathWidget
from fxgui.fxwidgets._fuzzy_search_list import FXFuzzySearchList
from fxgui.fxwidgets._fuzzy_search_tree import FXFuzzySearchTree
from fxgui.fxwidgets._inputs import (
    FXIconLineEdit,
    FXPasswordLineEdit,
    FXValidatedLineEdit,
)
from fxgui.fxwidgets._labels import FXElidedLabel
from fxgui.fxwidgets._loading_spinner import FXLoadingOverlay, FXLoadingSpinner
from fxgui.fxwidgets._log_widget import (
    FXOutputLogHandler,
    FXOutputLogWidget,
)
from fxgui.fxwidgets._main_window import FXMainWindow
from fxgui.fxwidgets._notification_banner import FXNotificationBanner
from fxgui.fxwidgets._progress_card import FXProgressCard
from fxgui.fxwidgets._range_slider import FXRangeSlider
from fxgui.fxwidgets._rating_widget import FXRatingWidget
from fxgui.fxwidgets._scroll_area import FXResizedScrollArea
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._singleton import FXSingleton
from fxgui.fxwidgets._splash_screen import FXSplashScreen
from fxgui.fxwidgets._status_bar import FXStatusBar
from fxgui.fxwidgets._system_tray import FXSystemTray
from fxgui.fxwidgets._tag_input import FXTagChip, FXTagInput
from fxgui.fxwidgets._timeline_slider import FXTimelineSlider
from fxgui.fxwidgets._toggle_switch import FXToggleSwitch
from fxgui.fxwidgets._tooltip import (
    FXTooltip,
    FXTooltipManager,
    FXTooltipPosition,
    set_tooltip,
)
from fxgui.fxwidgets._tree_items import FXSortedTreeWidgetItem
from fxgui.fxwidgets._validators import (
    FXCamelCaseValidator,
    FXCapitalizedLetterValidator,
    FXLettersUnderscoreValidator,
    FXLowerCaseValidator,
)
from fxgui.fxwidgets._widget import FXWidget


__all__ = [
    "CRITICAL",
    "DEBUG",
    "ERROR",
    "INFO",
    "SUCCESS",
    "WARNING",
    "FXAccordion",
    "FXAccordionSection",
    "FXApplication",
    "FXBreadcrumb",
    "FXCamelCaseValidator",
    "FXCapitalizedLetterValidator",
    "FXCodeBlock",
    "FXCollapsibleWidget",
    "FXColorLabelDelegate",
    "FXElidedLabel",
    "FXFilePathWidget",
    "FXFloatingDialog",
    "FXFuzzySearchList",
    "FXFuzzySearchTree",
    "FXIconLineEdit",
    "FXLettersUnderscoreValidator",
    "FXLoadingOverlay",
    "FXLoadingSpinner",
    "FXLowerCaseValidator",
    "FXMainWindow",
    "FXNotificationBanner",
    "FXOutputLogHandler",
    "FXOutputLogWidget",
    "FXPasswordLineEdit",
    "FXProgressCard",
    "FXRangeSlider",
    "FXRatingWidget",
    "FXResizedScrollArea",
    "FXSearchBar",
    "FXSingleton",
    "FXSortedTreeWidgetItem",
    "FXSplashScreen",
    "FXStatusBar",
    "FXSystemTray",
    "FXTagChip",
    "FXTagInput",
    "FXThemeAware",
    "FXThemeManager",
    "FXThemeColors",
    "FXThumbnailDelegate",
    "FXTimelineSlider",
    "FXToggleSwitch",
    "FXTooltip",
    "FXTooltipManager",
    "FXTooltipPosition",
    "set_tooltip",
    "FXValidatedLineEdit",
    "FXWidget",
    "theme_manager",
]
