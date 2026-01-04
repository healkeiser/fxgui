"""Developer mode examples for new fxwidgets.

This module provides example usage of all the new pre-styled widgets.
Run with DEVELOPER_MODE=1 environment variable to see the demo.
"""

import os
import sys


def run_widget_examples():
    """Run examples of all new widgets in a demo window."""
    from qtpy.QtCore import Qt, QTimer
    from qtpy.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QScrollArea,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    from fxgui import fxstyle
    from fxgui.fxwidgets import (
        FXAccordion,
        FXBreadcrumb,
        FXButtonGroup,
        FXColorPicker,
        FXFilePathWidget,
        FXLoadingSpinner,
        FXNotificationBanner,
        FXProgressCard,
        FXRangeSlider,
        FXRatingWidget,
        FXSearchBar,
        FXTagInput,
        FXTimelineSlider,
        FXToggleSwitch,
        SUCCESS,
        WARNING,
        INFO,
    )

    # Create application
    app = QApplication.instance() or QApplication(sys.argv)

    # Main window
    window = QWidget()
    window.setWindowTitle("FXWidgets - New Widgets Demo")
    window.resize(900, 700)
    window.setStyleSheet(fxstyle.load_stylesheet())

    main_layout = QVBoxLayout(window)

    # Tab widget to organize examples
    tabs = QTabWidget()
    main_layout.addWidget(tabs)

    # ========== TAB 1: Basic Controls ==========
    basic_tab = QWidget()
    basic_layout = QVBoxLayout(basic_tab)
    basic_layout.setSpacing(20)

    # Toggle Switch
    toggle_group = QWidget()
    toggle_layout = QHBoxLayout(toggle_group)
    toggle_layout.addWidget(QLabel("Toggle Switch:"))
    toggle = FXToggleSwitch()
    toggle.toggled.connect(lambda checked: print(f"Toggle: {checked}"))
    toggle_layout.addWidget(toggle)
    toggle_layout.addWidget(QLabel("(Try clicking!)"))
    toggle_layout.addStretch()
    basic_layout.addWidget(toggle_group)

    # Button Group
    button_group_container = QWidget()
    bg_layout = QVBoxLayout(button_group_container)
    bg_layout.addWidget(QLabel("Button Group (Segmented Control):"))
    button_group = FXButtonGroup(buttons=[
        ("Grid", "grid_view"),
        ("List", "view_list"),
        ("Tree", "account_tree"),
    ])
    button_group.selection_changed.connect(
        lambda i: print(f"Button Group selection: {i}")
    )
    bg_layout.addWidget(button_group)
    basic_layout.addWidget(button_group_container)

    # Rating Widget
    rating_container = QWidget()
    rating_layout = QHBoxLayout(rating_container)
    rating_layout.addWidget(QLabel("Rating Widget:"))
    rating = FXRatingWidget(max_rating=5, initial_rating=3, allow_half=True)
    rating.rating_changed.connect(lambda r: print(f"Rating: {r}"))
    rating_layout.addWidget(rating)
    rating_layout.addStretch()
    basic_layout.addWidget(rating_container)

    # Range Slider
    range_container = QWidget()
    range_layout = QVBoxLayout(range_container)
    range_layout.addWidget(QLabel("Range Slider:"))
    range_slider = FXRangeSlider(minimum=0, maximum=100, low=25, high=75)
    range_slider.range_changed.connect(
        lambda l, h: print(f"Range: {l} - {h}")
    )
    range_layout.addWidget(range_slider)
    basic_layout.addWidget(range_container)

    basic_layout.addStretch()
    tabs.addTab(basic_tab, "Basic Controls")

    # ========== TAB 2: Input Widgets ==========
    input_tab = QWidget()
    input_layout = QVBoxLayout(input_tab)
    input_layout.setSpacing(20)

    # Search Bar
    search_container = QWidget()
    search_layout = QVBoxLayout(search_container)
    search_layout.addWidget(QLabel("Search Bar (with debounce):"))
    search = FXSearchBar(
        placeholder="Search assets...",
        show_filter=True,
        filters=["All", "Models", "Textures", "Materials"]
    )
    search.search_changed.connect(lambda t: print(f"Searching: {t}"))
    search.filter_changed.connect(lambda f: print(f"Filter: {f}"))
    search_layout.addWidget(search)
    input_layout.addWidget(search_container)

    # Tag Input
    tag_container = QWidget()
    tag_layout = QVBoxLayout(tag_container)
    tag_layout.addWidget(QLabel("Tag Input (type and press Enter):"))
    tags = FXTagInput(placeholder="Add tags...")
    tags.add_tag("python")
    tags.add_tag("qt")
    tags.add_tag("fxgui")
    tags.tags_changed.connect(lambda t: print(f"Tags: {t}"))
    tag_layout.addWidget(tags)
    input_layout.addWidget(tag_container)

    # File Path Widget
    filepath_container = QWidget()
    filepath_layout = QVBoxLayout(filepath_container)
    filepath_layout.addWidget(QLabel("File Path Widget:"))
    file_widget = FXFilePathWidget(mode="file", file_filter="Python (*.py)")
    file_widget.path_changed.connect(lambda p: print(f"Path: {p}"))
    filepath_layout.addWidget(file_widget)

    folder_widget = FXFilePathWidget(mode="folder", placeholder="Select folder...")
    filepath_layout.addWidget(folder_widget)
    input_layout.addWidget(filepath_container)

    # Color Picker
    color_container = QWidget()
    color_layout = QVBoxLayout(color_container)
    color_layout.addWidget(QLabel("Color Picker:"))
    color_picker = FXColorPicker(initial_color="#3498db")
    color_picker.color_changed.connect(lambda c: print(f"Color: {c}"))
    color_layout.addWidget(color_picker)
    input_layout.addWidget(color_container)

    input_layout.addStretch()
    tabs.addTab(input_tab, "Input Widgets")

    # ========== TAB 3: Navigation & Layout ==========
    nav_tab = QWidget()
    nav_layout = QVBoxLayout(nav_tab)
    nav_layout.setSpacing(20)

    # Breadcrumb
    bread_container = QWidget()
    bread_layout = QVBoxLayout(bread_container)
    bread_layout.addWidget(QLabel("Breadcrumb Navigation:"))
    breadcrumb = FXBreadcrumb()
    breadcrumb.set_path(["Home", "Projects", "MyProject", "Assets", "Characters"])
    breadcrumb.segment_clicked.connect(
        lambda i, p: print(f"Navigate to: {'/'.join(p)}")
    )
    bread_layout.addWidget(breadcrumb)
    nav_layout.addWidget(bread_container)

    # Accordion
    accordion_container = QWidget()
    accordion_layout = QVBoxLayout(accordion_container)
    accordion_layout.addWidget(QLabel("Accordion (mutually exclusive sections):"))

    accordion = FXAccordion(exclusive=True)

    # Section 1 content
    section1_content = QWidget()
    s1_layout = QVBoxLayout(section1_content)
    s1_layout.addWidget(QLabel("This is the General section content."))
    s1_layout.addWidget(QLabel("Only one section can be open at a time."))
    accordion.add_section("General", section1_content, icon="settings")

    # Section 2 content
    section2_content = QWidget()
    s2_layout = QVBoxLayout(section2_content)
    s2_layout.addWidget(QLabel("Advanced settings go here."))
    s2_layout.addWidget(FXToggleSwitch())
    accordion.add_section("Advanced", section2_content, icon="tune")

    # Section 3 content
    section3_content = QWidget()
    s3_layout = QVBoxLayout(section3_content)
    s3_layout.addWidget(QLabel("About information."))
    accordion.add_section("About", section3_content, icon="info")

    accordion_layout.addWidget(accordion)
    nav_layout.addWidget(accordion_container)

    nav_layout.addStretch()
    tabs.addTab(nav_tab, "Navigation & Layout")

    # ========== TAB 4: Feedback & Status ==========
    feedback_tab = QWidget()
    feedback_layout = QVBoxLayout(feedback_tab)
    feedback_layout.setSpacing(20)

    # Notification Banner
    notif_container = QWidget()
    notif_layout = QVBoxLayout(notif_container)
    notif_layout.addWidget(QLabel("Notification Banners:"))

    success_banner = FXNotificationBanner(
        message="Operation completed successfully!",
        severity=SUCCESS,
        timeout=0,  # Don't auto-dismiss for demo
        action_text="Undo"
    )
    success_banner.show()
    notif_layout.addWidget(success_banner)

    warning_banner = FXNotificationBanner(
        message="This is a warning message.",
        severity=WARNING,
        timeout=0
    )
    warning_banner.show()
    notif_layout.addWidget(warning_banner)

    info_banner = FXNotificationBanner(
        message="Informational message with an action button.",
        severity=INFO,
        timeout=0,
        action_text="Learn More"
    )
    info_banner.show()
    notif_layout.addWidget(info_banner)

    feedback_layout.addWidget(notif_container)

    # Progress Card
    progress_container = QWidget()
    progress_layout = QVBoxLayout(progress_container)
    progress_layout.addWidget(QLabel("Progress Cards:"))

    progress_card = FXProgressCard(
        title="Rendering Sequence",
        description="Frame 42/100 - Calculating lighting...",
        progress=42
    )
    progress_layout.addWidget(progress_card)

    completed_card = FXProgressCard(
        title="Asset Export",
        description="All assets exported successfully",
        progress=100,
        status=SUCCESS
    )
    progress_layout.addWidget(completed_card)

    feedback_layout.addWidget(progress_container)

    # Loading Spinner
    spinner_container = QWidget()
    spinner_layout = QHBoxLayout(spinner_container)
    spinner_layout.addWidget(QLabel("Loading Spinners:"))

    spinner1 = FXLoadingSpinner(size=32, style="spinner")
    spinner1.start()
    spinner_layout.addWidget(spinner1)

    spinner2 = FXLoadingSpinner(size=32, style="dots")
    spinner2.start()
    spinner_layout.addWidget(spinner2)

    spinner3 = FXLoadingSpinner(size=32, style="pulse")
    spinner3.start()
    spinner_layout.addWidget(spinner3)

    spinner_layout.addStretch()
    feedback_layout.addWidget(spinner_container)

    feedback_layout.addStretch()
    tabs.addTab(feedback_tab, "Feedback & Status")

    # ========== TAB 5: Timeline (DCC) ==========
    timeline_tab = QWidget()
    timeline_layout = QVBoxLayout(timeline_tab)
    timeline_layout.setSpacing(20)

    # Timeline Slider
    timeline_container = QWidget()
    tl_layout = QVBoxLayout(timeline_container)
    tl_layout.addWidget(QLabel("Timeline Slider (for DCC applications):"))

    timeline = FXTimelineSlider(
        start_frame=1,
        end_frame=250,
        current_frame=1,
        show_controls=True,
        show_spinbox=True
    )
    # Add some keyframes
    timeline.add_keyframe(1)
    timeline.add_keyframe(30)
    timeline.add_keyframe(60)
    timeline.add_keyframe(120)
    timeline.add_keyframe(180)
    timeline.add_keyframe(250)

    timeline.frame_changed.connect(lambda f: print(f"Frame: {f}"))
    tl_layout.addWidget(timeline)

    timeline_layout.addWidget(timeline_container)

    # Info label
    info_label = QLabel(
        "The timeline slider is designed for animation and compositing tools.\n"
        "Features:\n"
        "• Playback controls (start, previous, play/pause, next, end)\n"
        "• Keyframe markers (orange diamonds)\n"
        "• Scrubbing with mouse drag\n"
        "• Frame spinbox for precise input"
    )
    info_label.setWordWrap(True)
    timeline_layout.addWidget(info_label)

    # Animate the timeline for demo
    def animate_timeline():
        current = timeline.current_frame
        if current < timeline._end_frame:
            timeline.set_frame(current + 1)
        else:
            timeline.set_frame(timeline._start_frame)

    # Demo animation (commented out to not distract)
    # timer = QTimer()
    # timer.timeout.connect(animate_timeline)
    # timer.start(100)

    timeline_layout.addStretch()
    tabs.addTab(timeline_tab, "Timeline (DCC)")

    # Show window
    window.show()

    # Run event loop
    sys.exit(app.exec_())


if __name__ == "__main__" and os.getenv("DEVELOPER_MODE", "0") == "1":
    run_widget_examples()
