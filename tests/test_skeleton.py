"""FXSkeleton: its shapes, its grey, its sweep, and covering a view."""

# Third-party
import pytest
from qtpy.QtCore import QAbstractAnimation
from qtpy.QtWidgets import QApplication, QTreeWidget, QWidget

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXSkeleton


def _on_page(qtbot, skeleton, size):
    """Show `skeleton` alone in a themed window, `size` big."""
    window = QWidget()
    qtbot.addWidget(window)
    fxstyle.register_themed_root(window)
    skeleton.setParent(window)
    skeleton.resize(*size)
    window.resize(*size)
    window.show()
    qtbot.waitExposed(window)
    # The window's grab: the page shows where the skeleton draws nothing.
    return window.grab().toImage()


def _children(view):
    return [
        child for child in view.viewport().children()
        if isinstance(child, FXSkeleton) and child._covering
    ]


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        FXSkeleton(kind="grid")


def test_screen_readers_hear_loading(qtbot):
    skeleton = FXSkeleton()
    qtbot.addWidget(skeleton)
    assert skeleton.accessibleName() == "Loading"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_rows_are_a_row_tall_with_a_soft_grey_thumbnail_slot(qtbot, theme):
    fxstyle.apply_theme(theme)
    skeleton = FXSkeleton(count=2)
    image = _on_page(qtbot, skeleton, (400, 200))
    height = fxstyle.row_height()
    surface = fxstyle.colors().surface
    # The thumbnail slot, 44 x 24, 16 px in, in each of the two rows.
    for row in (0, 1):
        grey = image.pixelColor(16 + 22, int(row * height + height / 2))
        assert grey.name() != surface.lower()
        # A soft grey: lighter or darker than the page by a little.
        assert 1.02 < fxstyle.get_contrast_ratio(grey.name(), surface) < 1.4
    # No third row.
    assert image.pixelColor(16 + 22, int(2.5 * height)).name() == (
        surface.lower()
    )


@pytest.mark.parametrize("kind", ["rows", "cards", "lines"])
def test_every_kind_draws_something(qtbot, kind):
    skeleton = FXSkeleton(kind=kind)
    image = _on_page(qtbot, skeleton, (700, 300))
    surface = fxstyle.colors().surface.lower()
    inked = {
        image.pixelColor(x, y).name()
        for x in range(0, 700, 7)
        for y in range(0, 300, 7)
    }
    assert inked - {surface}


def test_the_sweep_runs_only_with_motion_and_while_shown(qtbot, motion):
    skeleton = FXSkeleton()
    qtbot.addWidget(skeleton)
    skeleton.show()
    assert skeleton._animation.state() == QAbstractAnimation.Running
    skeleton.hide()
    assert skeleton._animation.state() == QAbstractAnimation.Stopped


def test_reduced_motion_holds_the_light_still(qtbot):
    skeleton = FXSkeleton()
    qtbot.addWidget(skeleton)
    skeleton.show()
    assert skeleton._animation.state() == QAbstractAnimation.Stopped


def test_cover_fills_a_view_follows_it_and_uncover_removes_it(qtbot):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.resize(300, 200)
    tree.show()
    skeleton = FXSkeleton.cover(tree)
    # Inside the frame: the header stays.
    assert skeleton.parent() is tree.viewport()
    assert skeleton.geometry() == tree.viewport().rect()
    assert skeleton.isVisible()
    assert FXSkeleton.cover(tree) is skeleton
    tree.resize(400, 300)
    QApplication.processEvents()
    assert skeleton.size() == tree.viewport().size()

    FXSkeleton.uncover(tree)
    assert not skeleton.isVisible()
    assert _children(tree) == []
    again = FXSkeleton.cover(tree)
    assert again is not skeleton
    assert _children(tree) == [again]


def test_a_covering_skeleton_hides_what_it_covers(qtbot):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.resize(300, 200)
    tree.show()
    skeleton = FXSkeleton.cover(tree, count=1)
    image = skeleton.grab().toImage()
    ground = tree.viewport().palette().color(tree.viewport().backgroundRole())
    assert image.pixelColor(skeleton.width() - 2, skeleton.height() - 2) == (
        ground
    )
