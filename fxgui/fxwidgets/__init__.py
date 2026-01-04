"""FXWidgets - Custom Qt widgets for fxgui.

This package provides a collection of custom Qt widgets built on top of qtpy,
offering enhanced functionality and consistent styling for DCC applications.

All public classes are re-exported here for backward compatibility:
    from fxgui.fxwidgets import FXMainWindow, FXSplashScreen

Or import from the package directly:
    from fxgui import fxwidgets
    window = fxwidgets.FXMainWindow()
"""

from fxgui.fxwidgets._constants import (
    CRITICAL,
    ERROR,
    WARNING,
    SUCCESS,
    INFO,
    DEBUG,
)
from fxgui.fxstyle import FXThemeAware, FXThemeManager, theme_manager
from fxgui.fxwidgets._singleton import FXSingleton
from fxgui.fxwidgets._validators import (
    FXCamelCaseValidator,
    FXLowerCaseValidator,
    FXLettersUnderscoreValidator,
    FXCapitalizedLetterValidator,
)
from fxgui.fxwidgets._scroll_area import FXResizedScrollArea
from fxgui.fxwidgets._collapsible import FXCollapsibleWidget
from fxgui.fxwidgets._log_widget import (
    FXOutputLogHandler,
    FXOutputLogWidget,
)
from fxgui.fxwidgets._labels import FXElidedLabel
from fxgui.fxwidgets._inputs import (
    FXPasswordLineEdit,
    FXIconLineEdit,
)
from fxgui.fxwidgets._tree_items import FXSortedTreeWidgetItem
from fxgui.fxwidgets._delegates import (
    FXColorLabelDelegate,
    FXThumbnailDelegate,
)
from fxgui.fxwidgets._application import FXApplication
from fxgui.fxwidgets._splash_screen import FXSplashScreen
from fxgui.fxwidgets._status_bar import FXStatusBar
from fxgui.fxwidgets._main_window import FXMainWindow
from fxgui.fxwidgets._widget import FXWidget
from fxgui.fxwidgets._dialogs import FXFloatingDialog
from fxgui.fxwidgets._system_tray import FXSystemTray
from fxgui.fxwidgets._toggle_switch import FXToggleSwitch
from fxgui.fxwidgets._tag_input import FXTagInput, FXTagChip
from fxgui.fxwidgets._range_slider import FXRangeSlider
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._notification_banner import FXNotificationBanner
from fxgui.fxwidgets._loading_spinner import FXLoadingSpinner, FXLoadingOverlay
from fxgui.fxwidgets._breadcrumb import FXBreadcrumb
from fxgui.fxwidgets._timeline_slider import FXTimelineSlider
from fxgui.fxwidgets._rating_widget import FXRatingWidget
from fxgui.fxwidgets._accordion import FXAccordion, FXAccordionSection
from fxgui.fxwidgets._progress_card import FXProgressCard
from fxgui.fxwidgets._file_path_widget import FXFilePathWidget
from fxgui.fxwidgets._tooltip import FXTooltip, FXTooltipPosition


__all__ = [
    "CRITICAL",
    "ERROR",
    "WARNING",
    "SUCCESS",
    "INFO",
    "DEBUG",
    "FXThemeAware",
    "FXThemeManager",
    "theme_manager",
    "FXSingleton",
    "FXCamelCaseValidator",
    "FXLowerCaseValidator",
    "FXLettersUnderscoreValidator",
    "FXCapitalizedLetterValidator",
    "FXResizedScrollArea",
    "FXCollapsibleWidget",
    "FXOutputLogHandler",
    "FXOutputLogWidget",
    "FXElidedLabel",
    "FXPasswordLineEdit",
    "FXIconLineEdit",
    "FXSortedTreeWidgetItem",
    "FXColorLabelDelegate",
    "FXThumbnailDelegate",
    "FXApplication",
    "FXSplashScreen",
    "FXStatusBar",
    "FXMainWindow",
    "FXWidget",
    "FXFloatingDialog",
    "FXSystemTray",
    "FXToggleSwitch",
    "FXTagInput",
    "FXTagChip",
    "FXRangeSlider",
    "FXSearchBar",
    "FXNotificationBanner",
    "FXLoadingSpinner",
    "FXLoadingOverlay",
    "FXBreadcrumb",
    "FXTimelineSlider",
    "FXRatingWidget",
    "FXAccordion",
    "FXAccordionSection",
    "FXProgressCard",
    "FXFilePathWidget",
    "FXTooltip",
    "FXTooltipPosition",
]
