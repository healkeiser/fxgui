# Widgets

This section provides detailed API documentation for all custom widgets available in `fxgui.fxwidgets`.

## Overview

The `fxwidgets` module provides a collection of custom Qt widgets built on top of `qtpy`, offering enhanced functionality and consistent styling for DCC applications.

::: fxgui.fxwidgets
    options:
      members: false
      show_root_heading: true
      show_root_full_path: true

## Widget Categories

### Core Widgets

- **[FXWidget](widget.md)** - Base widget class with theme support
- **[FXMainWindow](main_window.md)** - Enhanced main window with built-in features
- **[FXApplication](application.md)** - Application class with theme management

### Layout Widgets

- **[FXAccordion](accordion.md)** - Collapsible accordion container
- **[FXCollapsibleWidget](collapsible.md)** - Single collapsible section
- **[FXResizedScrollArea](scroll_area.md)** - Auto-resizing scroll area

### Input Widgets

- **[FXIconLineEdit](inputs.md#fxgui.fxwidgets.FXIconLineEdit)** - Line edit with icon support
- **[FXPasswordLineEdit](inputs.md#fxgui.fxwidgets.FXPasswordLineEdit)** - Password input with visibility toggle
- **[FXSearchBar](search_bar.md)** - Search input with suggestions
- **[FXTagInput](tag_input.md)** - Tag/chip input widget
- **[FXFilePathWidget](file_path_widget.md)** - File/folder path selector
- **[FXRangeSlider](range_slider.md)** - Dual-handle range slider
- **[FXTimelineSlider](timeline_slider.md)** - Timeline with markers
- **[FXToggleSwitch](toggle_switch.md)** - iOS-style toggle switch
- **[FXRatingWidget](rating_widget.md)** - Star rating input

### Display Widgets

- **[FXElidedLabel](labels.md)** - Label with text elision
- **[FXBreadcrumb](breadcrumb.md)** - Breadcrumb navigation
- **[FXNotificationBanner](notification_banner.md)** - Notification banners
- **[FXProgressCard](progress_card.md)** - Progress indicator card
- **[FXLoadingSpinner](loading_spinner.md)** - Loading animation
- **[FXTooltip](tooltip.md)** - Enhanced tooltips

### Dialog & Overlay Widgets

- **[FXFloatingDialog](dialogs.md)** - Floating dialog windows
- **[FXSplashScreen](splash_screen.md)** - Application splash screen
- **[FXLoadingOverlay](loading_spinner.md#fxgui.fxwidgets.FXLoadingOverlay)** - Loading overlay

### Tree & List Widgets

- **[FXSortedTreeWidgetItem](tree_items.md)** - Naturally sorted tree items
- **[FXColorLabelDelegate](delegates.md#fxgui.fxwidgets.FXColorLabelDelegate)** - Color label delegate
- **[FXThumbnailDelegate](delegates.md#fxgui.fxwidgets.FXThumbnailDelegate)** - Thumbnail delegate

### System Widgets

- **[FXStatusBar](status_bar.md)** - Enhanced status bar
- **[FXSystemTray](system_tray.md)** - System tray integration

### Logging Widgets

- **[FXOutputLogWidget](log_widget.md)** - Log output display
- **[FXOutputLogHandler](log_widget.md#fxgui.fxwidgets.FXOutputLogHandler)** - Log handler

### Validators

- **[Validators](validators.md)** - Input validators (CamelCase, LowerCase, etc.)

### Utilities

- **[FXSingleton](singleton.md)** - Singleton metaclass for widgets
- **[Constants](constants.md)** - Log level constants
