"""FXWidgets - Custom Qt widgets for fxgui.

This package provides a collection of custom Qt widgets built on top of qtpy,
offering enhanced functionality and consistent styling for DCC applications.

All public classes are re-exported here for backward compatibility:
    from fxgui.fxwidgets import FXMainWindow, FXSplashScreen

Or import from the package directly:
    from fxgui import fxwidgets
    window = fxwidgets.FXMainWindow()
"""

# Constants
from fxgui.fxwidgets._constants import (
    CRITICAL,
    ERROR,
    WARNING,
    SUCCESS,
    INFO,
    DEBUG,
)

# Singleton metaclass
from fxgui.fxwidgets._singleton import FXSingleton

# Validators
from fxgui.fxwidgets._validators import (
    FXCamelCaseValidator,
    FXLowerCaseValidator,
    FXLettersUnderscoreValidator,
    FXCapitalizedLetterValidator,
)

# Scroll area
from fxgui.fxwidgets._scroll_area import FXResizedScrollArea

# Collapsible widget
from fxgui.fxwidgets._collapsible import FXCollapsibleWidget

# Log widget
from fxgui.fxwidgets._log_widget import (
    FXOutputLogHandler,
    FXOutputLogWidget,
)

# Labels
from fxgui.fxwidgets._labels import FXElidedLabel

# Input widgets
from fxgui.fxwidgets._inputs import (
    FXPasswordLineEdit,
    FXIconLineEdit,
)

# Tree items
from fxgui.fxwidgets._tree_items import FXSortedTreeWidgetItem

# Delegates
from fxgui.fxwidgets._delegates import (
    FXColorLabelDelegate,
    FXThumbnailDelegate,
)

# Application
from fxgui.fxwidgets._application import FXApplication

# Splash screen
from fxgui.fxwidgets._splash_screen import FXSplashScreen

# Status bar
from fxgui.fxwidgets._status_bar import FXStatusBar

# Main window
from fxgui.fxwidgets._main_window import FXMainWindow

# Base widget
from fxgui.fxwidgets._widget import FXWidget

# Dialogs
from fxgui.fxwidgets._dialogs import FXFloatingDialog

# System tray
from fxgui.fxwidgets._system_tray import FXSystemTray

# New widgets
from fxgui.fxwidgets._toggle_switch import FXToggleSwitch
from fxgui.fxwidgets._tag_input import FXTagInput, FXTagChip
from fxgui.fxwidgets._range_slider import FXRangeSlider
from fxgui.fxwidgets._search_bar import FXSearchBar
from fxgui.fxwidgets._notification_banner import FXNotificationBanner
from fxgui.fxwidgets._loading_spinner import FXLoadingSpinner, FXLoadingOverlay
from fxgui.fxwidgets._breadcrumb import FXBreadcrumb
from fxgui.fxwidgets._color_picker import FXColorPicker, FXColorSwatch
from fxgui.fxwidgets._timeline_slider import FXTimelineSlider
from fxgui.fxwidgets._rating_widget import FXRatingWidget
from fxgui.fxwidgets._accordion import FXAccordion, FXAccordionSection
from fxgui.fxwidgets._button_group import FXButtonGroup
from fxgui.fxwidgets._progress_card import FXProgressCard
from fxgui.fxwidgets._file_path_widget import FXFilePathWidget


__all__ = [
    # Constants
    "CRITICAL",
    "ERROR",
    "WARNING",
    "SUCCESS",
    "INFO",
    "DEBUG",
    # Singleton
    "FXSingleton",
    # Validators
    "FXCamelCaseValidator",
    "FXLowerCaseValidator",
    "FXLettersUnderscoreValidator",
    "FXCapitalizedLetterValidator",
    # Scroll area
    "FXResizedScrollArea",
    # Collapsible
    "FXCollapsibleWidget",
    # Log widget
    "FXOutputLogHandler",
    "FXOutputLogWidget",
    # Labels
    "FXElidedLabel",
    # Inputs
    "FXPasswordLineEdit",
    "FXIconLineEdit",
    # Tree items
    "FXSortedTreeWidgetItem",
    # Delegates
    "FXColorLabelDelegate",
    "FXThumbnailDelegate",
    # Application
    "FXApplication",
    # Splash screen
    "FXSplashScreen",
    # Status bar
    "FXStatusBar",
    # Main window
    "FXMainWindow",
    # Base widget
    "FXWidget",
    # Dialogs
    "FXFloatingDialog",
    # System tray
    "FXSystemTray",
    # New widgets
    "FXToggleSwitch",
    "FXTagInput",
    "FXTagChip",
    "FXRangeSlider",
    "FXSearchBar",
    "FXNotificationBanner",
    "FXLoadingSpinner",
    "FXLoadingOverlay",
    "FXBreadcrumb",
    "FXColorPicker",
    "FXColorSwatch",
    "FXTimelineSlider",
    "FXRatingWidget",
    "FXAccordion",
    "FXAccordionSection",
    "FXButtonGroup",
    "FXProgressCard",
    "FXFilePathWidget",
]
