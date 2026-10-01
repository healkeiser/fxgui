"""FXLoadingSpinner idles while hidden and reads in every theme; the overlay
follows its parent."""

# Third-party
import pytest
from qtpy.QtWidgets import QPushButton, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXLoadingOverlay, FXLoadingSpinner


def test_a_hidden_spinner_stops_its_timer_and_resumes_when_shown(qtbot):
    spinner = FXLoadingSpinner()
    qtbot.addWidget(spinner)
    spinner.start()
    qtbot.waitExposed(spinner)

    spinner.hide()
    assert not spinner._timer.isActive()
    assert spinner.is_spinning()

    spinner.show()
    assert spinner._timer.isActive()


def test_a_stopped_spinner_stays_stopped_when_shown(qtbot):
    spinner = FXLoadingSpinner()
    qtbot.addWidget(spinner)
    spinner.start()
    spinner.stop()

    spinner.hide()
    spinner.show()

    assert not spinner._timer.isActive()


def test_the_spinner_has_no_angle_property():
    assert not hasattr(FXLoadingSpinner, "angle")


def test_the_overlay_follows_its_parent_resizing(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    parent.resize(200, 100)
    overlay = FXLoadingOverlay(parent, "Loading")
    parent.show()
    overlay.show()

    parent.resize(400, 300)

    assert overlay.geometry() == parent.rect()


def test_the_overlay_carries_no_dead_sheet(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)

    overlay = FXLoadingOverlay(parent, "Loading")

    assert overlay.styleSheet() == ""
    assert overlay._message_label.styleSheet() == ""


def _lazy_tree(qtbot):
    """A tree whose one branch holds a started spinner on its stand-in row."""
    from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem

    tree = QTreeWidget()
    qtbot.addWidget(tree)
    branch = QTreeWidgetItem(tree, ["shots"])
    placeholder = QTreeWidgetItem(branch, [""])
    spinner = FXLoadingSpinner(size=16, line_width=2)
    tree.setItemWidget(placeholder, 0, spinner)
    spinner.start()
    tree.show()
    qtbot.waitExposed(tree)
    qtbot.wait(10)
    return tree, branch, spinner


def test_a_spinner_on_a_closed_branch_does_not_animate(qtbot):
    _tree, _branch, spinner = _lazy_tree(qtbot)

    assert spinner.is_spinning()
    assert not spinner._timer.isActive()


def test_a_spinner_animates_while_its_branch_is_open(qtbot):
    tree, branch, spinner = _lazy_tree(qtbot)

    branch.setExpanded(True)
    qtbot.waitUntil(spinner.isVisible, timeout=1000)
    assert spinner._timer.isActive()

    branch.setExpanded(False)
    qtbot.waitUntil(lambda: not spinner.isVisible(), timeout=1000)
    assert not spinner._timer.isActive()


def test_clearing_a_tree_with_a_running_spinner_needs_no_stop(qtbot):
    tree, branch, spinner = _lazy_tree(qtbot)
    branch.setExpanded(True)
    qtbot.waitUntil(spinner.isVisible, timeout=1000)

    tree.clear()
    qtbot.wait(50)

    assert tree.topLevelItemCount() == 0


def _covered(qtbot, **kwargs):
    """A parent holding a button, with an overlay shown over both."""
    from qtpy.QtWidgets import QPushButton, QVBoxLayout

    parent = QWidget()
    qtbot.addWidget(parent)
    button = QPushButton("Publish")
    QVBoxLayout(parent).addWidget(button)
    parent.resize(300, 200)
    parent.show()
    qtbot.waitExposed(parent)
    bare = parent.grab().toImage()
    overlay = FXLoadingOverlay(parent, **kwargs)
    overlay.show()
    return parent, button, overlay, bare


def test_an_overlay_dims_and_takes_the_mouse_by_default(qtbot):
    parent, button, _overlay, bare = _covered(qtbot)

    assert parent.grab().toImage().pixelColor(2, 2) != bare.pixelColor(2, 2)
    assert parent.childAt(button.geometry().center()) is not button


def test_an_overlay_can_leave_the_view_undimmed_and_clickable(qtbot):
    parent, button, overlay, bare = _covered(
        qtbot, dim=False, block_input=False
    )

    assert parent.grab().toImage().pixelColor(2, 2) == bare.pixelColor(2, 2)
    assert parent.childAt(button.geometry().center()) is button
    assert overlay._spinner.is_spinning()


def test_the_overlay_spinner_takes_a_size(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)

    overlay = FXLoadingOverlay(parent, size=32)

    assert overlay._spinner.size().width() == 32


def _inks(spinner):
    """Return every opaque colour the spinner draws, by count."""
    image = spinner.grab().toImage()
    found = {}
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() == 255:
                found[color.name()] = found.get(color.name(), 0) + 1
    return found


@pytest.mark.parametrize("theme", fxstyle.get_available_themes())
@pytest.mark.parametrize("style", ["spinner", "dots", "pulse"])
def test_the_spinner_moves_in_the_accent_over_a_muted_track(qtbot, theme, style):
    fxstyle.apply_theme(theme)
    spinner = FXLoadingSpinner(style=style)
    qtbot.addWidget(spinner)
    inks = _inks(spinner)
    colors = fxstyle.colors()
    assert inks.get(colors.accent_primary.lower(), 0) > 0, "no accent part"
    assert inks.get(colors.border_light.lower(), 0) > 0, "no muted track"
    # The moving part reads on the surface at a control's 3:1.
    ratio = fxstyle.get_contrast_ratio(colors.accent_primary, colors.surface)
    assert ratio >= fxstyle.CONTROL_CONTRAST


def test_the_spinner_is_as_tall_as_a_button_by_default(qtbot):
    spinner, button = FXLoadingSpinner(), QPushButton("x")
    qtbot.addWidget(spinner)
    qtbot.addWidget(button)
    assert spinner.height() == fxstyle.control_height(button)
