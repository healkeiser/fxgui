"""Example implementations demonstrating `fxgui` module usage.

This module provides a comprehensive showcase application demonstrating
the fxgui framework's capabilities, including:

- **Full Application Flow**: Splash screen -> Main window with widgets
- **Theme Awareness**: Complete guide to making widgets theme-aware
- **Custom Delegates**: Thumbnail and color label delegates
- **Various Widgets**: Collapsible sections, validators, log output, etc.

Theme Awareness Guide:
    fxgui provides a complete theme system with automatic updates when
    the user switches themes. There are several ways to make your code
    theme-aware:

    1. **Icons** - Use `set_icon()` for automatic icon color updates:
        >>> from fxgui.fxicons import set_icon
        >>> set_icon(button, "check")  # Updates on theme change

    2. **Custom Widgets** - Connect to `theme_manager.theme_changed`:
        >>> from fxgui import fxstyle
        >>> def update_colors(_theme_name: str = None):
        ...     theme = fxstyle.FXThemeColors(fxstyle.get_theme_colors())
        ...     widget.setStyleSheet(f"background: {theme.surface};")
        >>> fxstyle.theme_manager.theme_changed.connect(update_colors)
        >>> update_colors()  # Apply initial

    3. **Delegate Backgrounds** - Update item data on theme change:
        >>> def update_item_colors(_theme_name: str = None):
        ...     theme = fxstyle.FXThemeColors(fxstyle.get_theme_colors())
        ...     for item in items:
        ...         item.setBackground(0, QColor(theme.surface_sunken))
        ...     tree.viewport().update()
        >>> fxstyle.theme_manager.theme_changed.connect(update_item_colors)

    4. **FXThemeAware Mixin** - For custom widget classes:
        >>> class MyWidget(fxstyle.FXThemeAware, QWidget):
        ...     def _apply_theme_styles(self):
        ...         # Called on init and theme changes
        ...         colors = fxstyle.get_theme_colors()
        ...         self.setStyleSheet(f"background: {colors['surface']};")

Note:
    Most widgets have their own `example()` function in their module.
    Run individual widget examples with:
        DEVELOPER_MODE=1 python -m fxgui.fxwidgets._<module>

    For example:
        DEVELOPER_MODE=1 python -m fxgui.fxwidgets._accordion
        DEVELOPER_MODE=1 python -m fxgui.fxwidgets._delegates

Examples:
    Run this module directly to see the full showcase application:

    >>> python -m fxgui.examples
"""

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"

# Built-in
from pathlib import Path

# Third-party
from qtpy.QtWidgets import (
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QCheckBox,
    QWidget,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QSpinBox,
    QTabWidget,
    QGroupBox,
    QFrame,
)
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QColor

# Internal
from fxgui import fxwidgets, fxstyle
from fxgui.fxicons import get_icon, set_icon


# Constants
_pixmap = Path(__file__).parent / "images" / "splash.png"


def _create_theme_awareness_tab() -> QWidget:
    """Create the Theme Awareness demonstration tab.

    This tab demonstrates three key patterns for making widgets theme-aware:
    1. Icons with set_icon() - automatic updates
    2. Custom widgets connecting to theme_changed signal
    3. Delegate backgrounds with dynamic color updates

    Returns:
        Widget containing theme awareness demonstrations.
    """

    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(16)

    # Header
    header = QLabel(
        "Theme Awareness demonstrates how to make your widgets respond "
        "to theme changes. Use the theme toggle in the toolbar to see updates."
    )
    header.setWordWrap(True)
    layout.addWidget(header)

    # Section 1: Icons with set_icon()
    icons_group = QGroupBox("1. Icons with set_icon()")
    icons_layout = QVBoxLayout(icons_group)
    icons_layout.addWidget(
        QLabel("Use set_icon() instead of setIcon() for automatic color updates:")
    )
    icons_layout.addWidget(fxwidgets.FXCodeBlock(
        'set_icon(button, "check")  # Updates on theme change'
    ))

    icons_row = QHBoxLayout()
    for icon_name in ["check", "close", "settings", "folder", "search"]:
        btn = QPushButton(icon_name)
        set_icon(btn, icon_name)
        icons_row.addWidget(btn)
    icons_row.addStretch()
    icons_layout.addLayout(icons_row)
    layout.addWidget(icons_group)

    # Section 2: Theme Colors with FXThemeColors
    colors_group = QGroupBox("2. Theme Colors (FXThemeColors)")
    colors_layout = QVBoxLayout(colors_group)
    colors_layout.addWidget(QLabel("Access theme colors with dot notation:"))
    colors_layout.addWidget(fxwidgets.FXCodeBlock("""
theme = FXThemeColors(get_theme_colors())
widget.setStyleSheet(f"background: {theme.surface};")
"""))

    # Color swatches that update with theme
    swatches_frame = QFrame()
    swatches_frame.setFrameShape(QFrame.StyledPanel)
    swatches_layout = QVBoxLayout(swatches_frame)

    surface_label = QLabel()
    text_label = QLabel()
    border_label = QLabel()

    swatches_layout.addWidget(surface_label)
    swatches_layout.addWidget(text_label)
    swatches_layout.addWidget(border_label)
    colors_layout.addWidget(swatches_frame)

    # Section 3: Feedback Colors
    feedback_group = QGroupBox("3. Feedback Colors (get_feedback_colors)")
    feedback_layout = QVBoxLayout(feedback_group)
    feedback_layout.addWidget(QLabel("Semantic colors for status indicators:"))
    feedback_layout.addWidget(fxwidgets.FXCodeBlock("""
feedback = get_feedback_colors()
color = feedback["success"]["foreground"]
"""))

    feedback_labels = {}
    for key in ["success", "warning", "error", "info"]:
        feedback_labels[key] = QLabel()
        feedback_layout.addWidget(feedback_labels[key])

    colors_layout.addWidget(feedback_group)
    layout.addWidget(colors_group)

    # Theme update function
    def update_theme_swatches(_theme_name: str = None):
        """Update color swatches based on current theme."""
        theme = fxwidgets.FXThemeColors(fxstyle.get_theme_colors())
        feedback = fxstyle.get_feedback_colors()

        # Update theme color labels
        surface_label.setText(f"surface: {theme.surface}")
        surface_label.setStyleSheet(
            f"background-color: {theme.surface}; "
            f"color: {theme.text}; padding: 8px;"
        )

        text_label.setText(f"text: {theme.text}")
        text_label.setStyleSheet(
            f"background-color: {theme.surface_alt}; "
            f"color: {theme.text}; padding: 8px;"
        )

        border_label.setText(f"border: {theme.border}")
        border_label.setStyleSheet(
            f"background-color: {theme.surface}; "
            f"color: {theme.text}; "
            f"border: 2px solid {theme.border}; padding: 8px;"
        )

        # Update feedback color labels
        for key, label in feedback_labels.items():
            label.setText(f"{key}: {feedback[key]['foreground']}")
            label.setStyleSheet(
                f"background-color: {feedback[key]['background']}; "
                f"color: {feedback[key]['foreground']}; padding: 8px;"
            )

    # Apply initial and connect to theme changes
    update_theme_swatches()
    fxstyle.theme_manager.theme_changed.connect(update_theme_swatches)

    layout.addStretch()
    return tab


def _create_delegates_tab() -> QWidget:
    """Create the Delegates demonstration tab with theme-aware backgrounds.

    This tab demonstrates:
    - FXThumbnailDelegate with custom backgrounds
    - Theme-aware BackgroundRole colors
    - Status dots and labels

    Returns:
        Widget containing delegate demonstrations.
    """

    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(16)

    # Header
    header = QLabel(
        "Custom delegates with theme-aware backgrounds. The item colors "
        "update automatically when you switch themes."
    )
    header.setWordWrap(True)
    layout.addWidget(header)

    # Code example with syntax-highlighted code block
    code_group = QGroupBox("Theme-Aware Background Pattern")
    code_layout = QVBoxLayout(code_group)

    code_block = fxwidgets.FXCodeBlock("""
def update_item_colors(_theme_name: str = None):
    theme = FXThemeColors(get_theme_colors())
    feedback = get_feedback_colors()

    for item in items:
        bg = QColor(theme.surface_sunken).darker(110)
        item.setBackground(0, bg)
    tree.viewport().update()

# Apply initial and connect to theme changes
update_item_colors()
theme_manager.theme_changed.connect(update_item_colors)
""")
    code_layout.addWidget(code_block)
    layout.addWidget(code_group)

    # Tree widget with thumbnail delegate
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Type", "Status"])
    tree.setRootIsDecorated(False)

    delegate = fxwidgets.FXThumbnailDelegate()
    delegate.show_thumbnail = False
    delegate.show_status_dot = True
    delegate.show_status_label = True
    tree.setItemDelegate(delegate)
    fxwidgets.FXThumbnailDelegate.apply_transparent_selection(tree)

    # Sample items
    from fxgui import fxicons

    items_data = [
        ("Project Alpha", "Feature", "Ready", "success", "folder"),
        ("Bug Fix #123", "Bug", "Testing", "warning", "bug_report"),
        ("Documentation", "Task", "Done", "success", "description"),
        ("API Refactor", "Enhancement", "Review", "error", "code"),
    ]

    tree_items = []
    for name, item_type, status, feedback_key, icon_name in items_data:
        item = QTreeWidgetItem(tree, [name, item_type, status])
        item.setIcon(0, fxicons.get_icon(icon_name))
        item.setData(
            0,
            fxwidgets.FXThumbnailDelegate.DESCRIPTION_ROLE,
            f"A {item_type.lower()} item",
        )
        item.setData(
            0, fxwidgets.FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE, status
        )
        item.setData(0, Qt.UserRole + 100, feedback_key)
        item.setData(
            0, fxwidgets.FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False
        )
        tree_items.append(item)

    tree.setColumnWidth(0, 200)
    tree.setColumnWidth(1, 100)
    layout.addWidget(tree)

    # Theme-aware background update function
    def update_delegate_colors(_theme_name: str = None):
        """Update item backgrounds and status colors based on current theme."""
        theme = fxwidgets.FXThemeColors(fxstyle.get_theme_colors())
        feedback = fxstyle.get_feedback_colors()
        base_surface = QColor(theme.surface_sunken)

        for i, item in enumerate(tree_items):
            feedback_key = item.data(0, Qt.UserRole + 100)
            if feedback_key and feedback_key in feedback:
                status_color = QColor(feedback[feedback_key]["foreground"])
                item.setData(
                    0,
                    fxwidgets.FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE,
                    status_color,
                )
                item.setData(
                    0,
                    fxwidgets.FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE,
                    status_color,
                )

            # Varied background colors for visual hierarchy
            darkness = 105 + (i % 4) * 5
            bg_color = base_surface.darker(darkness)
            item.setBackground(0, bg_color)
            item.setBackground(1, bg_color)
            item.setBackground(2, bg_color)

        tree.viewport().update()

    # Apply initial and connect to theme changes
    update_delegate_colors()
    fxstyle.theme_manager.theme_changed.connect(update_delegate_colors)

    layout.addStretch()
    return tab


def _create_widgets_tab() -> QWidget:
    """Create a tab showcasing various fxgui widgets.

    Returns:
        Widget containing widget demonstrations.
    """

    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(16)

    # Header
    header = QLabel(
        "A selection of fxgui widgets. Each widget has its own example() "
        "function - run with: DEVELOPER_MODE=1 python -m fxgui.fxwidgets._<module>"
    )
    header.setWordWrap(True)
    layout.addWidget(header)

    # Collapsible sections
    settings_section = fxwidgets.FXCollapsibleWidget(
        title="Settings (FXCollapsibleWidget)",
        animation_duration=200,
    )
    settings_layout = QFormLayout()
    settings_layout.addRow("Name:", QLineEdit())
    settings_layout.addRow("Value:", QSpinBox())
    settings_layout.addRow("Enabled:", QCheckBox())
    settings_section.set_content_layout(settings_layout)
    layout.addWidget(settings_section)

    # Toggle switches
    toggles_section = fxwidgets.FXCollapsibleWidget(
        title="Toggle Switches (FXToggleSwitch)",
        animation_duration=200,
    )
    toggles_layout = QHBoxLayout()
    for label in ["Option A", "Option B", "Option C"]:
        toggle = fxwidgets.FXToggleSwitch()
        toggle_container = QWidget()
        toggle_hlayout = QHBoxLayout(toggle_container)
        toggle_hlayout.setContentsMargins(0, 0, 0, 0)
        toggle_hlayout.addWidget(QLabel(label))
        toggle_hlayout.addWidget(toggle)
        toggles_layout.addWidget(toggle_container)
    toggles_layout.addStretch()
    toggles_section.set_content_layout(toggles_layout)
    layout.addWidget(toggles_section)

    # Input validators
    validators_section = fxwidgets.FXCollapsibleWidget(
        title="Input Validators",
        animation_duration=200,
    )
    validators_layout = QFormLayout()

    camel_edit = QLineEdit()
    camel_edit.setValidator(fxwidgets.FXCamelCaseValidator())
    camel_edit.setPlaceholderText("e.g., myVariableName")
    validators_layout.addRow("CamelCase:", camel_edit)

    lower_edit = QLineEdit()
    lower_edit.setValidator(
        fxwidgets.FXLowerCaseValidator(allow_underscores=True)
    )
    lower_edit.setPlaceholderText("e.g., my_variable")
    validators_layout.addRow("Lowercase:", lower_edit)

    validators_section.set_content_layout(validators_layout)
    layout.addWidget(validators_section)

    layout.addStretch()
    return tab


def main():
    """Main showcase application demonstrating fxgui capabilities.

    This function creates a comprehensive example application with:
    - Splash screen with loading progress
    - Main window with tabbed interface
    - Theme awareness demonstrations
    - Custom delegate examples
    - Various widget showcases

    The application demonstrates best practices for:
    - Making icons theme-aware with set_icon()
    - Updating widget colors on theme change
    - Creating theme-aware delegate backgrounds
    """

    # Initialize the application
    from qtpy.QtUiTools import QUiLoader

    _ = QUiLoader()  # PySide6 bug workaround
    application = fxwidgets.FXApplication()

    # Show splash screen
    splashscreen = fxwidgets.FXSplashScreen(
        image_path=str(_pixmap),
        title="fxgui Showcase",
        information=(
            "A comprehensive Qt widget library for DCC applications. "
            "This showcase demonstrates theme-aware widgets, custom delegates, "
            "and various UI components designed for VFX and animation pipelines."
        ),
        show_progress_bar=True,
        project="fxgui",
        version="1.0.0",
        company="\u00a9 Valentin Beaumont",
        corner_radius=12,
        border_width=2,
        border_color="#4a4949",
    )
    splashscreen.set_overlay_opacity(0.85)
    splashscreen.show()

    # Simulate loading
    loading_steps = [
        "Loading theme system...",
        "Initializing widgets...",
        "Setting up delegates...",
        "Preparing UI components...",
        "Almost ready...",
    ]

    for i, step in enumerate(loading_steps):
        splashscreen.message_label.setText(step)
        for j in range(20):
            progress = (i * 20) + j + 1
            splashscreen.progress_bar.setValue(progress)
            application.processEvents()
            QTimer.singleShot(10, lambda: None)
            application.processEvents()

    # Create main window
    window = fxwidgets.FXMainWindow(
        title="fxgui Showcase",
        project="fxgui",
        version="1.0.0",
        company="\u00a9 Valentin Beaumont",
    )
    window.set_banner_text("Showcase")
    window.set_banner_icon(get_icon("widgets"))

    # Create tabbed interface
    tabs = QTabWidget()

    # Add tabs
    tabs.addTab(_create_theme_awareness_tab(), "Theme Awareness")
    tabs.addTab(_create_delegates_tab(), "Delegates")
    tabs.addTab(_create_widgets_tab(), "Widgets")

    window.setCentralWidget(tabs)

    # Finish splash screen and show window
    splashscreen.finish(window)
    window.resize(800, 700)
    window.show()

    # Show welcome message
    window.statusBar().showMessage(
        "Welcome to fxgui! Toggle theme with the toolbar button.",
        fxwidgets.INFO,
    )

    # Start application event loop
    application.exec_()


if __name__ == "__main__":
    main()
