"""The Row height setting reaches every view of rows, live.

A table's rows kept Qt's 30 px, a plain list's 28; a dense view's rows
were 28 px at both Small and Normal; a skeleton over a view drew normal
rows and a normal picture whatever the view showed.
"""

# Third-party
import pytest
from qtpy.QtWidgets import (
    QApplication,
    QListWidget,
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Internal
from fxgui import fxstyle
from fxgui.fxwidgets import FXSkeleton, FXThumbnailDelegate

_SIZES = list(fxstyle.ROW_SIZES)


@pytest.fixture
def rows(qtbot):
    """A themed window of views; the row size goes back to normal after."""
    fxstyle.apply_theme("dark")
    window = QWidget()
    column = QVBoxLayout(window)
    views = {
        "table": QTableWidget(3, 2),
        "list": QListWidget(),
        "wrapping": QListWidget(),
        "tree": QTreeWidget(),
        "dense_tree": QTreeWidget(),
        "dense_table": QTableWidget(3, 2),
        "own_table": QTableWidget(3, 2),
    }
    views["wrapping"].setWordWrap(True)
    views["own_table"].verticalHeader().setDefaultSectionSize(44)
    for name in ("list", "wrapping"):
        views[name].addItems(["one", "two"])
    for name in ("tree", "dense_tree"):
        QTreeWidgetItem(views[name], ["one"])
    for name in ("dense_tree", "dense_table"):
        fxstyle.mark_dense(views[name])
    for view in views.values():
        column.addWidget(view)
    fxstyle.register_themed_root(window)
    qtbot.addWidget(window)
    window.resize(400, 900)
    window.show()
    qtbot.waitExposed(window)
    yield views
    fxstyle.apply_row_size("normal", save=False)


def _height(view) -> int:
    QApplication.processEvents()
    QApplication.processEvents()
    if isinstance(view, QTableWidget):
        return view.rowHeight(0)
    if isinstance(view, QTreeWidget):
        return view.visualItemRect(view.topLevelItem(0)).height()
    return view.visualItemRect(view.item(0)).height()


def test_every_view_of_rows_follows_the_row_size_live(rows):
    seen = {}
    for size in _SIZES + ["normal"]:
        fxstyle.apply_row_size(size, save=False)
        seen[size] = {name: _height(view) for name, view in rows.items()}

    assert [seen[size]["table"] for size in _SIZES] == [28, 36, 52]
    assert [seen[size]["list"] for size in _SIZES] == [28, 36, 52]
    assert [seen[size]["tree"] for size in _SIZES] == [28, 36, 52]
    # A dense view is one real step under, so all three choices differ.
    assert [seen[size]["dense_tree"] for size in _SIZES] == [24, 28, 36]
    assert [seen[size]["dense_table"] for size in _SIZES] == [24, 28, 36]
    # A wrapping list is text: its rows start at the small row.
    assert {seen[size]["wrapping"] for size in _SIZES} == {28}
    # A row height the application set stays.
    assert {seen[size]["own_table"] for size in _SIZES} == {44}


@pytest.mark.parametrize("size", _SIZES)
@pytest.mark.parametrize("dense", [False, True])
def test_a_skeleton_draws_the_rows_of_the_view_it_covers(rows, size, dense):
    fxstyle.apply_row_size(size, save=False)
    tree = rows["dense_tree" if dense else "tree"]
    pitch = fxstyle.row_height(tree)
    skeleton = FXSkeleton.cover(tree)
    skeleton._animation.stop()
    QApplication.processEvents()
    image = skeleton.grab().toImage()
    ground = image.pixelColor(image.width() - 3, 3)
    # The thumbnail slot's column, 2 px into the slot: one run per row.
    runs = []
    for y in range(image.height()):
        if image.pixelColor(18, y) != ground:
            if runs and runs[-1][1] == y - 1:
                runs[-1][1] = y
            else:
                runs.append([y, y])
    middle = (runs[0][0] + runs[0][1]) // 2
    left = next(
        x for x in range(image.width())
        if image.pixelColor(x, middle) != ground)
    right = next(
        x for x in range(left, image.width())
        if image.pixelColor(x, middle) == ground)
    FXSkeleton.uncover(tree)

    width, tall = FXThumbnailDelegate.thumbnail_size(pitch)
    assert runs[1][0] - runs[0][0] == pitch, "the view's row pitch"
    assert runs[0][1] - runs[0][0] + 1 == tall
    assert right - left == width


def _save_elsewhere(path: str, size: str) -> None:
    """Save `size` as the row size from another process, as a launcher does."""
    import subprocess
    import sys

    code = (
        "from qtpy.QtCore import QSettings\n"
        f"settings = QSettings({path!r}, QSettings.IniFormat)\n"
        f"settings.setValue('rows/size', {size!r})\n"
        "settings.sync()\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True, timeout=60)


def test_a_row_size_saved_by_another_process_reaches_open_windows(
    qtbot, rows
):
    from fxgui import fxconfig

    # The file exists, as a person's settings do once anything is saved.
    fxconfig.set_value("rows/size", "normal")
    fxstyle._watch_settings()
    path = fxconfig._settings().fileName()

    _save_elsewhere(path, "big")

    qtbot.waitUntil(lambda: fxstyle.row_size() == "big", timeout=5000)
    assert _height(rows["list"]) == 52
    assert _height(rows["table"]) == 52


def test_a_size_chosen_here_stays_until_the_file_says_something_new(
    qtbot, rows
):
    from fxgui import fxconfig

    fxconfig.set_value("rows/size", "normal")
    fxconfig.set_value("window/geometry", "a")
    fxstyle._watch_settings()
    fxstyle.apply_row_size("small", save=False)

    # Another write to the file, the row size in it unchanged.
    fxconfig.set_value("window/geometry", "b")
    qtbot.wait(300)

    assert fxstyle.row_size() == "small"
