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

    2. **FXThemeAware Mixin** - For custom widget classes (recommended):
        >>> class MyWidget(fxstyle.FXThemeAware, QWidget):
        ...     def _on_theme_changed(self, _theme_name: str = None):
        ...         # Called on init and theme changes
        ...         self.setStyleSheet(f"background: {self.theme.surface};")

    3. **Custom Colors** - Define palettes for dark/light themes:
        >>> COLORS = {
        ...     "dark": {"red": QColor("#4a2020")},
        ...     "light": {"red": QColor("#ffcccc")},
        ... }
        >>> def update_colors(_theme_name: str = None):
        ...     palette = COLORS["light" if fxstyle.is_light_theme() else "dark"]
        ...     item.setBackground(0, palette["red"])
        >>> fxstyle.theme_manager.theme_changed.connect(update_colors)

    4. **Delegate Backgrounds** - Update item data on theme change:
        >>> def update_item_colors(_theme_name: str = None):
        ...     theme = fxstyle.FXThemeColors(fxstyle.get_theme_colors())
        ...     for item in items:
        ...         item.setBackground(0, QColor(theme.surface_sunken))
        ...     tree.viewport().update()
        >>> fxstyle.theme_manager.theme_changed.connect(update_item_colors)

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
    QDockWidget,
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
        QLabel(
            "Use <code>set_icon()</code> instead of <code>setIcon()</code> "
            "for automatic color updates:"
        )
    )
    icons_layout.addWidget(
        fxwidgets.FXCodeBlock(
            'set_icon(button, "check")  # Updates on theme change'
        )
    )

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
    colors_layout.addWidget(
        fxwidgets.FXCodeBlock(
            """
theme = FXThemeColors(get_theme_colors())
widget.setStyleSheet(f"background: {theme.surface};")
"""
        )
    )

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
    feedback_layout.addWidget(
        fxwidgets.FXCodeBlock(
            """
feedback = get_feedback_colors()
color = feedback["success"]["foreground"]
"""
        )
    )

    feedback_labels = {}
    for key in ["success", "warning", "error", "info", "debug"]:
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
                f"color: {feedback[key]['foreground']}; "
                f"border: 1px solid {feedback[key]['foreground']}; "
                f"border-radius: 4px; padding: 8px;"
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

    scroll_area = fxwidgets.FXResizedScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_content = QWidget()
    layout = QVBoxLayout(scroll_content)
    layout.setSpacing(16)

    # Header
    header = QLabel(
        "Custom delegates with theme-aware backgrounds. The item colors "
        "update automatically when you switch themes."
    )
    header.setWordWrap(True)
    layout.addWidget(header)

    # Code example with syntax-highlighted code block
    code_group = QGroupBox("Theme-Aware Custom Colors Pattern")
    code_layout = QVBoxLayout(code_group)

    code_block = fxwidgets.FXCodeBlock(
        """
# Define custom color palettes for dark and light themes
CUSTOM_COLORS = {
    "dark": {"red": QColor("#4a2020"), "blue": QColor("#1a3a5c")},
    "light": {"red": QColor("#ffcccc"), "blue": QColor("#cce5ff")},
}

def update_item_colors(_theme_name: str = None):
    # Use fxstyle.is_light_theme() to detect current theme type
    palette = CUSTOM_COLORS["light" if fxstyle.is_light_theme() else "dark"]

    for i, item in enumerate(items):
        color_key = ["red", "blue"][i % 2]
        item.setBackground(0, palette[color_key])
    tree.viewport().update()

fxstyle.theme_manager.theme_changed.connect(update_item_colors)
"""
    )
    code_layout.addWidget(code_block)
    layout.addWidget(code_group)

    # Tree widget with thumbnail delegate
    tree_group = QGroupBox("Task Tracker with Status Indicators")
    tree_group_layout = QVBoxLayout(tree_group)

    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Type", "Status"])
    tree.setRootIsDecorated(False)

    delegate = fxwidgets.FXThumbnailDelegate()
    delegate.show_thumbnail = False
    delegate.show_status_dot = True
    delegate.show_status_label = True
    tree.setItemDelegate(delegate)
    # Apply transparent selection for branch area (items handled by delegate)
    fxwidgets.FXThumbnailDelegate.apply_transparent_selection(tree)

    # Sample items

    items_data = [
        ("Project Alpha", "Feature", "Ready", "success", "folder"),
        ("Bug Fix #123", "Bug", "Testing", "warning", "bug_report"),
        ("Documentation", "Task", "Done", "success", "description"),
        ("API Refactor", "Enhancement", "Review", "error", "code"),
    ]

    # Role for storing icon name for theme-aware updates
    ICON_NAME_ROLE = Qt.UserRole + 101

    tree_items = []
    for name, item_type, status, feedback_key, icon_name in items_data:
        item = QTreeWidgetItem(tree, [name, item_type, status])
        item.setIcon(0, get_icon(icon_name))
        item.setData(0, ICON_NAME_ROLE, icon_name)  # Store icon name
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
    tree_group_layout.addWidget(tree)
    layout.addWidget(tree_group)

    # Custom color palettes for dark and light themes
    # These semantic colors adapt to the current theme
    custom_colors = {
        "dark": {
            "red": QColor("#4a2020"),  # Dark red for dark theme
            "blue": QColor("#1a3a5c"),  # Dark blue for dark theme
            "green": QColor("#1a3a1a"),  # Dark green for dark theme
            "purple": QColor("#3a1a4a"),  # Dark purple for dark theme
        },
        "light": {
            "red": QColor("#ffcccc"),  # Light red/pink for light theme
            "blue": QColor("#cce5ff"),  # Light blue for light theme
            "green": QColor("#ccffcc"),  # Light green for light theme
            "purple": QColor("#e5ccff"),  # Light purple for light theme
        },
    }
    color_keys = ["red", "blue", "green", "purple"]

    # Theme-aware background update function
    def update_delegate_colors(_theme_name: str = None):
        """Update item backgrounds, status colors, and icons based on theme."""
        feedback = fxstyle.get_feedback_colors()
        palette_key = "light" if fxstyle.is_light_theme() else "dark"

        for i, item in enumerate(tree_items):
            # Update icon with current theme color
            icon_name = item.data(0, ICON_NAME_ROLE)
            if icon_name:
                item.setIcon(0, get_icon(icon_name))

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

            # Custom theme-aware background colors
            color_key = color_keys[i % len(color_keys)]
            bg_color = custom_colors[palette_key][color_key]
            item.setBackground(0, bg_color)
            item.setBackground(1, bg_color)
            item.setBackground(2, bg_color)

        tree.viewport().update()

    # Apply initial and connect to theme changes
    update_delegate_colors()
    fxstyle.theme_manager.theme_changed.connect(update_delegate_colors)

    # Second tree: Episodic production hierarchy with thumbnails
    episodic_group = QGroupBox("Episodic Production Hierarchy")
    episodic_layout = QVBoxLayout(episodic_group)

    episodic_tree = QTreeWidget()
    episodic_tree.setHeaderLabels(["Name", "Frame Range", "Status"])
    episodic_tree.setRootIsDecorated(True)

    episodic_delegate = fxwidgets.FXThumbnailDelegate()
    episodic_delegate.show_thumbnail = True
    episodic_delegate.show_status_dot = True
    episodic_delegate.show_status_label = True
    episodic_tree.setItemDelegate(episodic_delegate)
    # Apply transparent selection for branch area (items handled by delegate)
    fxwidgets.FXThumbnailDelegate.apply_transparent_selection(episodic_tree)

    # Thumbnail path
    thumbnail_path = Path(__file__).parent / "images" / "missing_image.png"

    # Episodic data structure: Episode > Sequence > Shot
    episodic_data = {
        "ep101": {
            "seq010": ["sh0010", "sh0020", "sh0030"],
            "seq020": ["sh0010", "sh0020"],
        },
        "ep102": {
            "seq010": ["sh0010", "sh0020", "sh0030", "sh0040"],
            "seq020": ["sh0010"],
            "seq030": ["sh0010", "sh0020"],
        },
    }

    episodic_items = []  # Store all items for theme updates

    # Role for storing icon name for theme-aware updates
    EPISODIC_ICON_NAME_ROLE = Qt.UserRole + 201

    for episode_name, sequences in episodic_data.items():
        # Episode level (darkest)
        episode_item = QTreeWidgetItem(
            episodic_tree, [episode_name, "", "In Progress"]
        )
        episode_item.setIcon(0, get_icon("movie"))
        episode_item.setData(0, EPISODIC_ICON_NAME_ROLE, "movie")
        episode_item.setData(
            0, fxwidgets.FXThumbnailDelegate.DESCRIPTION_ROLE, "Episode"
        )
        episode_item.setData(
            0, fxwidgets.FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False
        )
        episode_item.setData(
            0,
            fxwidgets.FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE,
            "In Progress",
        )
        episode_item.setData(0, Qt.UserRole + 200, "episode")  # Level marker
        episodic_items.append(episode_item)

        for seq_name, shots in sequences.items():
            # Sequence level (medium)
            seq_item = QTreeWidgetItem(episode_item, [seq_name, "", "Active"])
            seq_item.setIcon(0, get_icon("video_library"))
            seq_item.setData(0, EPISODIC_ICON_NAME_ROLE, "video_library")
            seq_item.setData(
                0, fxwidgets.FXThumbnailDelegate.DESCRIPTION_ROLE, "Sequence"
            )
            seq_item.setData(
                0, fxwidgets.FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False
            )
            seq_item.setData(
                0,
                fxwidgets.FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE,
                "Active",
            )
            seq_item.setData(0, Qt.UserRole + 200, "sequence")  # Level marker
            episodic_items.append(seq_item)

            for shot_name in shots:
                # Shot level (lightest) - with thumbnail
                frame_range = f"1001-1{len(shot_name) * 10:03d}"
                shot_item = QTreeWidgetItem(
                    seq_item, [shot_name, frame_range, "WIP"]
                )
                shot_item.setIcon(0, get_icon("image"))
                shot_item.setData(0, EPISODIC_ICON_NAME_ROLE, "image")
                shot_item.setData(
                    0,
                    fxwidgets.FXThumbnailDelegate.DESCRIPTION_ROLE,
                    f"{episode_name}_{seq_name}_{shot_name}",
                )
                shot_item.setData(
                    0,
                    fxwidgets.FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE,
                    True,
                )
                shot_item.setData(
                    0,
                    fxwidgets.FXThumbnailDelegate.THUMBNAIL_PATH_ROLE,
                    str(thumbnail_path),
                )
                shot_item.setData(
                    0,
                    fxwidgets.FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE,
                    "WIP",
                )
                shot_item.setData(0, Qt.UserRole + 200, "shot")  # Level marker
                episodic_items.append(shot_item)

    episodic_tree.setColumnWidth(0, 250)
    episodic_tree.setColumnWidth(1, 100)
    episodic_tree.expandAll()
    episodic_layout.addWidget(episodic_tree)
    layout.addWidget(episodic_group)

    # Hierarchy colors for dark and light themes
    hierarchy_colors = {
        "dark": {
            "episode": QColor("#1a1a2e"),  # Darkest blue
            "sequence": QColor("#16213e"),  # Medium blue
            "shot": QColor("#1f4068"),  # Lightest blue
        },
        "light": {
            "episode": QColor("#b8c5d6"),  # Darkest (still light)
            "sequence": QColor("#d0dae8"),  # Medium
            "shot": QColor("#e8eff7"),  # Lightest
        },
    }

    # Theme-aware update function for episodic tree
    def update_episodic_colors(_theme_name: str = None):
        """Update episodic tree backgrounds, icons, and colors based on theme."""
        feedback = fxstyle.get_feedback_colors()
        palette_key = "light" if fxstyle.is_light_theme() else "dark"

        for item in episodic_items:
            # Update icon with current theme color
            icon_name = item.data(0, EPISODIC_ICON_NAME_ROLE)
            if icon_name:
                item.setIcon(0, get_icon(icon_name))

            level = item.data(0, Qt.UserRole + 200)
            if level in hierarchy_colors[palette_key]:
                bg_color = hierarchy_colors[palette_key][level]
                for col in range(3):
                    item.setBackground(col, bg_color)

            # Set status colors based on level
            if level == "episode":
                status_color = QColor(feedback["info"]["foreground"])
            elif level == "sequence":
                status_color = QColor(feedback["warning"]["foreground"])
            else:  # shot
                status_color = QColor(feedback["success"]["foreground"])

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

        episodic_tree.viewport().update()

    # Apply initial and connect to theme changes
    update_episodic_colors()
    fxstyle.theme_manager.theme_changed.connect(update_episodic_colors)

    # Third tree: Fuzzy Search Tree with FXThumbnailDelegate
    fuzzy_group = QGroupBox("Fuzzy Search Tree with Thumbnails")
    fuzzy_layout = QVBoxLayout(fuzzy_group)

    fuzzy_tree = fxwidgets.FXFuzzySearchTree(
        placeholder="Search assets (try 'hero', 'char', 'veh')...",
        ratio=0.4,
        show_ratio_slider=True,
        color_match=False,  # We handle colors via delegate backgrounds
    )

    # Set up the delegate
    fuzzy_delegate = fxwidgets.FXThumbnailDelegate()
    fuzzy_delegate.show_thumbnail = True
    fuzzy_delegate.show_status_dot = True
    fuzzy_delegate.show_status_label = True
    fuzzy_tree.tree_view.setItemDelegate(fuzzy_delegate)
    fxwidgets.FXThumbnailDelegate.apply_transparent_selection(
        fuzzy_tree.tree_view
    )

    # Role for storing icon name for theme-aware updates
    FUZZY_ICON_NAME_ROLE = Qt.UserRole + 301

    # Asset data with metadata
    fuzzy_assets = {
        "Characters": {
            "items": [
                ("character_hero_body", "Main hero body mesh", "Approved"),
                ("character_hero_head", "Hero facial rig", "WIP"),
                ("character_villain_body", "Antagonist body", "Review"),
                ("character_sidekick", "Supporting character", "Approved"),
            ],
            "icon": "person",
        },
        "Vehicles": {
            "items": [
                ("vehicle_car_sports", "Red sports car", "Approved"),
                ("vehicle_truck_pickup", "Utility truck", "WIP"),
                ("vehicle_motorcycle", "Motorcycle asset", "Review"),
            ],
            "icon": "directions_car",
        },
        "Environment": {
            "items": [
                ("environment_tree_oak", "Oak tree with leaves", "Approved"),
                ("environment_tree_pine", "Pine tree variations", "Approved"),
                ("environment_rock_large", "Boulder asset", "WIP"),
            ],
            "icon": "park",
        },
    }

    fuzzy_items = []  # Store all items for theme updates

    for category_name, category_data in fuzzy_assets.items():
        # Add category as parent
        category_item = fuzzy_tree.add_item(category_name)
        category_item.setIcon(get_icon(category_data["icon"]))
        category_item.setData(category_data["icon"], FUZZY_ICON_NAME_ROLE)
        category_item.setData(
            "Category", fxwidgets.FXThumbnailDelegate.DESCRIPTION_ROLE
        )
        category_item.setData(
            False, fxwidgets.FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE
        )
        category_item.setData("category", Qt.UserRole + 300)  # Level marker
        fuzzy_items.append(category_item)

        for asset_name, description, status in category_data["items"]:
            # Add asset as child
            asset_item = fuzzy_tree.add_item(asset_name, parent=category_name)
            asset_item.setIcon(get_icon("image"))
            asset_item.setData("image", FUZZY_ICON_NAME_ROLE)
            asset_item.setData(
                description, fxwidgets.FXThumbnailDelegate.DESCRIPTION_ROLE
            )
            asset_item.setData(
                True, fxwidgets.FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE
            )
            asset_item.setData(
                str(thumbnail_path),
                fxwidgets.FXThumbnailDelegate.THUMBNAIL_PATH_ROLE,
            )
            asset_item.setData(
                status, fxwidgets.FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE
            )
            asset_item.setData("asset", Qt.UserRole + 300)  # Level marker
            asset_item.setData(status, Qt.UserRole + 302)  # Store status
            fuzzy_items.append(asset_item)

    fuzzy_tree.expand_all()
    fuzzy_layout.addWidget(fuzzy_tree)
    layout.addWidget(fuzzy_group)

    # Colors for fuzzy tree
    fuzzy_colors = {
        "dark": {
            "category": QColor("#2a2a3a"),
            "asset": QColor("#1f3a2a"),
        },
        "light": {
            "category": QColor("#d8d8e8"),
            "asset": QColor("#d0e8d8"),
        },
    }

    # Status to feedback mapping
    status_feedback_map = {
        "Approved": "success",
        "WIP": "warning",
        "Review": "info",
    }

    def update_fuzzy_colors(_theme_name: str = None):
        """Update fuzzy tree backgrounds and status colors based on theme."""
        feedback = fxstyle.get_feedback_colors()
        palette_key = "light" if fxstyle.is_light_theme() else "dark"

        for item in fuzzy_items:
            # Update icon
            icon_name = item.data(FUZZY_ICON_NAME_ROLE)
            if icon_name:
                item.setIcon(get_icon(icon_name))

            level = item.data(Qt.UserRole + 300)
            if level in fuzzy_colors[palette_key]:
                bg_color = fuzzy_colors[palette_key][level]
                item.setBackground(bg_color)

            # Set status colors
            status = item.data(Qt.UserRole + 302)
            if status and status in status_feedback_map:
                feedback_key = status_feedback_map[status]
                status_color = QColor(feedback[feedback_key]["foreground"])
                item.setData(
                    status_color,
                    fxwidgets.FXThumbnailDelegate.STATUS_DOT_COLOR_ROLE,
                )
                item.setData(
                    status_color,
                    fxwidgets.FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE,
                )

        fuzzy_tree.tree_view.viewport().update()

    # Apply initial and connect to theme changes
    update_fuzzy_colors()
    fxstyle.theme_manager.theme_changed.connect(update_fuzzy_colors)

    layout.addStretch()
    scroll_area.setWidget(scroll_content)

    # Return a container with the scroll area
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    return container


def _create_widgets_tab() -> QWidget:
    """Create a tab showcasing various fxgui widgets.

    Returns:
        Widget containing widget demonstrations.
    """

    scroll_area = fxwidgets.FXResizedScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_content = QWidget()
    layout = QVBoxLayout(scroll_content)
    layout.setSpacing(16)

    # Header
    header = QLabel(
        "A selection of fxgui widgets. Each widget has its own "
        "<code>example()</code> function - run with: "
        "<code>DEVELOPER_MODE=1 python -m fxgui.fxwidgets._&lt;module&gt;</code>"
    )
    header.setWordWrap(True)
    layout.addWidget(header)

    # Collapsible sections
    settings_section = fxwidgets.FXCollapsibleWidget(
        title="FXCollapsibleWidget",
        icon="settings",
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
        title="FXToggleSwitch",
        icon="toggle_on",
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

    # Input validators with visual feedback
    validators_section = fxwidgets.FXCollapsibleWidget(
        title="FXValidatedLineEdit",
        icon="spellcheck",
        animation_duration=200,
    )
    validators_layout = QFormLayout()

    validators_hint = QLabel(
        "Type invalid characters to see the shake + red flash feedback."
    )
    validators_hint.setWordWrap(True)
    validators_layout.addRow(validators_hint)

    camel_edit = fxwidgets.FXValidatedLineEdit()
    camel_edit.setValidator(fxwidgets.FXCamelCaseValidator())
    camel_edit.setPlaceholderText("e.g., myVariableName")
    validators_layout.addRow("<code>FXCamelCaseValidator</code>:", camel_edit)

    lower_edit = fxwidgets.FXValidatedLineEdit()
    lower_edit.setValidator(
        fxwidgets.FXLowerCaseValidator(allow_underscores=True)
    )
    lower_edit.setPlaceholderText("e.g., my_variable")
    validators_layout.addRow("<code>FXLowerCaseValidator</code>:", lower_edit)

    validators_section.set_content_layout(validators_layout)
    layout.addWidget(validators_section)

    # Search bar
    search_section = fxwidgets.FXCollapsibleWidget(
        title="FXSearchBar",
        icon="search",
        animation_duration=200,
    )
    search_layout = QVBoxLayout()
    search_bar = fxwidgets.FXSearchBar(placeholder="Search...")
    search_layout.addWidget(search_bar)
    search_section.set_content_layout(search_layout)
    layout.addWidget(search_section)

    # Tag input
    tags_section = fxwidgets.FXCollapsibleWidget(
        title="FXTagInput",
        icon="label",
        animation_duration=200,
    )
    tags_layout = QVBoxLayout()
    tag_input = fxwidgets.FXTagInput()
    tag_input.add_tag("Python")
    tag_input.add_tag("Qt")
    tag_input.add_tag("fxgui")
    tags_layout.addWidget(tag_input)
    tags_section.set_content_layout(tags_layout)
    layout.addWidget(tags_section)

    # Range slider
    slider_section = fxwidgets.FXCollapsibleWidget(
        title="FXRangeSlider",
        icon="tune",
        animation_duration=200,
    )
    slider_layout = QVBoxLayout()
    range_slider = fxwidgets.FXRangeSlider()
    range_slider.set_range(0, 100)
    range_slider.set_minimum(25)
    range_slider.set_maximum(75)
    slider_layout.addWidget(range_slider)
    slider_section.set_content_layout(slider_layout)
    layout.addWidget(slider_section)

    # Rating widget
    rating_section = fxwidgets.FXCollapsibleWidget(
        title="FXRatingWidget",
        icon="star",
        animation_duration=200,
    )
    rating_layout = QHBoxLayout()
    rating_widget = fxwidgets.FXRatingWidget()
    rating_widget.set_rating(3)
    rating_layout.addWidget(rating_widget)
    rating_layout.addStretch()
    rating_section.set_content_layout(rating_layout)
    layout.addWidget(rating_section)

    # Loading spinner
    spinner_section = fxwidgets.FXCollapsibleWidget(
        title="FXLoadingSpinner",
        icon="refresh",
        animation_duration=200,
    )
    spinner_layout = QHBoxLayout()
    spinner = fxwidgets.FXLoadingSpinner()
    spinner.setFixedSize(32, 32)
    spinner.start()
    spinner_layout.addWidget(spinner)
    spinner_layout.addWidget(QLabel("Loading..."))
    spinner_layout.addStretch()
    spinner_section.set_content_layout(spinner_layout)
    layout.addWidget(spinner_section)

    # File path widget
    filepath_section = fxwidgets.FXCollapsibleWidget(
        title="FXFilePathWidget",
        icon="folder",
        animation_duration=200,
    )
    filepath_layout = QVBoxLayout()
    filepath_widget = fxwidgets.FXFilePathWidget(mode="directory")
    filepath_layout.addWidget(filepath_widget)
    filepath_section.set_content_layout(filepath_layout)
    layout.addWidget(filepath_section)

    layout.addStretch()
    scroll_area.setWidget(scroll_content)

    # Return a container with the scroll area
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    return container


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
    window.set_banner_icon("widgets")

    # Create tabbed interface with margins
    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    central_layout.setContentsMargins(8, 8, 8, 8)

    tabs = QTabWidget()
    tabs.addTab(_create_theme_awareness_tab(), "Theme Awareness")
    tabs.addTab(_create_delegates_tab(), "Delegates")
    tabs.addTab(_create_widgets_tab(), "Widgets")

    central_layout.addWidget(tabs)
    window.setCentralWidget(central_widget)

    # Add dockable log widget at the bottom
    log_dock = QDockWidget("Output Log", window)
    log_dock.setObjectName("OutputLogDock")
    log_container = QWidget()
    log_container_layout = QVBoxLayout(log_container)
    log_container_layout.setContentsMargins(10, 10, 10, 10)
    log_widget = fxwidgets.FXOutputLogWidget(capture_output=True)
    log_container_layout.addWidget(log_widget)
    log_dock.setWidget(log_container)
    window.addDockWidget(Qt.BottomDockWidgetArea, log_dock)

    # Log some initial messages to demonstrate the widget
    import logging

    logger = logging.getLogger(__name__)
    logger.info("fxgui Showcase application started")
    logger.debug("Theme system initialized")
    logger.warning("This is a sample warning message")

    # Finish splash screen and show window
    splashscreen.finish(window)
    window.resize(800, 900)
    window.show()
    # Center after show() so frame geometry is accurate
    window.center_on_screen()

    # Show welcome message in status bar
    _message = "Welcome to fxgui! Toggle theme with the toolbar menu in <b>Window</b> > <b>Theme</b>."
    window.statusBar().showMessage(
        _message,
        fxwidgets.INFO,
    )

    # Show welcome notification banner
    welcome_banner = fxwidgets.FXNotificationBanner(
        parent=window.centralWidget(),
        message=_message,
        severity_type=fxwidgets.INFO,
        timeout=8000,
    )
    welcome_banner.closed.connect(welcome_banner.deleteLater)
    welcome_banner.show()

    # Start application event loop
    application.exec_()


if __name__ == "__main__":
    main()
