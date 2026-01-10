"""Automated screenshot capture for all fxwidgets examples.

This script runs each widget module as a subprocess and captures a screenshot
before the app exits by patching the example() function.

Examples:
    >>> python .scripts/capture_widget_screenshots.py
    >>> python .scripts/capture_widget_screenshots.py --widget accordion
    >>> python .scripts/capture_widget_screenshots.py --list
"""

# Built-in
import sys
import subprocess
from pathlib import Path


# Project root
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs" / "images" / "widgets"

# Widget modules that have example() functions
WIDGET_MODULES = [
    "accordion",
    "breadcrumb",
    "collapsible",
    "delegates",
    "dialogs",
    "file_path_widget",
    "inputs",
    "labels",
    "loading_spinner",
    "log_widget",
    "main_window",
    "notification_banner",
    "progress_card",
    "range_slider",
    "rating_widget",
    "scroll_area",
    "search_bar",
    # "splash_screen",
    "status_bar",
    # "system_tray",
    "tag_input",
    "timeline_slider",
    "toggle_switch",
    "tooltip",
    "tree_items",
    "validators",
    "widget",
]


def capture_widget(module_name: str) -> bool:
    """Run a widget example and capture its screenshot via subprocess.

    Args:
        module_name: Name of the widget module (without underscore prefix).

    Returns:
        True if successful, False otherwise.
    """
    # Python code to inject screenshot capture into the example
    capture_code = f"""
import os
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")
os.environ["DEVELOPER_MODE"] = "1"

from pathlib import Path
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication

OUTPUT_DIR = Path(r"{OUTPUT_DIR}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

from fxgui.fxwidgets import _{module_name} as module

if not hasattr(module, "example"):
    print("No example() function")
    sys.exit(1)

# Patch FXApplication.exec to inject screenshot capture
from fxgui.fxwidgets._application import FXApplication

original_exec = FXApplication.exec

def patched_exec(self):
    def do_capture():
        for widget in self.topLevelWidgets():
            if widget.isVisible():
                # Capture the full window including title bar and frame
                # Use frameGeometry to get the window rect with decorations
                screen = QApplication.primaryScreen()
                frame = widget.frameGeometry()
                pixmap = screen.grabWindow(
                    0,  # Capture from desktop
                    frame.x(),
                    frame.y(),
                    frame.width(),
                    frame.height()
                )
                output_path = OUTPUT_DIR / "{module_name}.png"
                pixmap.save(str(output_path), "PNG")
                print(f"Saved: {{output_path.name}}")
                self.quit()
                return
    QTimer.singleShot(500, do_capture)
    return original_exec()

FXApplication.exec = patched_exec

module.example()
"""

    result = subprocess.run(
        [sys.executable, "-c", capture_code],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    if result.returncode == 0 and "Saved:" in result.stdout:
        print(f"  [OK] {result.stdout.strip()}")
        return True
    else:
        error = (
            result.stderr.strip() or result.stdout.strip() or "Unknown error"
        )
        # Shorten error for display
        if len(error) > 200:
            error = error[:200] + "..."
        print(f"  [FAIL] {error}")
        return False


def main():
    """Run widget examples and capture screenshots."""
    import argparse

    parser = argparse.ArgumentParser(description="Capture widget screenshots")
    parser.add_argument(
        "--widget",
        "-w",
        choices=WIDGET_MODULES,
        help="Capture a specific widget (default: all)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all available widgets",
    )

    args = parser.parse_args()

    if args.list:
        print("Available widgets:")
        for name in sorted(WIDGET_MODULES):
            print(f"  - {name}")
        return

    widgets = [args.widget] if args.widget else WIDGET_MODULES

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Capturing {len(widgets)} widget screenshot(s)...")
    print(f"Output: {OUTPUT_DIR}")
    print()

    success = 0
    for name in widgets:
        print(f"> {name}")
        if capture_widget(name):
            success += 1

    print()
    print(f"Done! {success}/{len(widgets)} captured successfully.")


if __name__ == "__main__":
    main()
