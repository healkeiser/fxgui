"""Item views: the thumbnail delegate, the fuzzy proxy, trees, sorting."""

# Built-in
import os

# Third-party
import pytest
from qtpy.QtCore import QRect, Qt
from qtpy.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QPainter,
    QStandardItem,
    QStandardItemModel,
)
from qtpy.QtWidgets import (
    QStyle,
    QStyleOptionViewItem,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
)

# Internal
from fxgui import _compat, fxcore, fxstyle, fxwidgets
from fxgui.fxcore import FXSortFilterProxyModel
from fxgui.fxwidgets import FXThumbnailDelegate
from fxgui.fxwidgets import _delegates


def _tree(qtbot, columns=1, width=420):
    tree = QTreeWidget()
    tree.setColumnCount(columns)
    tree.setRootIsDecorated(False)
    delegate = FXThumbnailDelegate(tree)
    tree.setItemDelegate(delegate)
    tree.resize(width, 200)
    qtbot.addWidget(tree)
    return tree, delegate


def _card_row(tree, columns):
    item = QTreeWidgetItem(tree, [f"cell {n}" for n in range(columns)])
    item.setData(0, Qt.BackgroundRole, "surface")
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    return item


# FXThumbnailDelegate ------------------------------------------------------


def test_row_ends_follow_the_visual_column_order(qtbot, monkeypatch):
    tree, delegate = _tree(qtbot, columns=3)
    _card_row(tree, 3)
    tree.header().moveSection(2, 0)
    tree.show()
    qtbot.waitExposed(tree)

    seen = {}
    real = delegate.paint

    def spy(painter, option, index):
        seen[index.column()] = delegate._row_ends(option, index)
        real(painter, option, index)

    monkeypatch.setattr(delegate, "paint", spy)
    tree.viewport().grab()
    # Logical column 2 is drawn first now, and logical 1 last.
    assert seen[2] == (True, False)
    assert seen[0] == (False, False)
    assert seen[1] == (False, True)


def test_size_hint_measures_the_items_own_font(qtbot):
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, ["A rather long asset title"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    big = QFont(tree.font())
    big.setPixelSize(40)
    item.setFont(0, big)
    index = tree.model().index(0, 0)
    option = QStyleOptionViewItem()
    option.font = tree.font()
    option.widget = tree
    hint = delegate.sizeHint(option, index)
    assert hint.width() >= QFontMetrics(big).horizontalAdvance(item.text(0))
    assert hint.height() >= QFontMetrics(big).height()


def test_row_height_grows_with_the_font(qtbot):
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, ["Asset"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    item.setData(0, FXThumbnailDelegate.DESCRIPTION_ROLE, "shading")
    index = tree.model().index(0, 0)
    option = QStyleOptionViewItem()
    option.widget = tree
    option.font = tree.font()
    small = delegate.sizeHint(option, index).height()
    big = QFont(tree.font())
    big.setPixelSize(30)
    option.font = big
    assert delegate.sizeHint(option, index).height() > small + 20


def test_the_description_font_is_one_step_smaller_in_pixels(qtbot):
    delegate = FXThumbnailDelegate()
    option = QStyleOptionViewItem()
    font = QFont()
    font.setPixelSize(20)
    option.font = font
    assert delegate._description_font(option).pixelSize() == 19



def test_the_delegate_s_type_is_the_body_weight_and_600_only(qtbot):
    """Title 600; metadata one step, 11 px at 12; badge 10 px at 12, 600."""
    option = QStyleOptionViewItem()
    font = QFont()
    font.setPixelSize(12)
    option.font = font
    FXThumbnailDelegate._badge_fonts.clear()
    assert FXThumbnailDelegate._title_font(option).weight() == QFont.DemiBold
    assert FXThumbnailDelegate._description_font(option).pixelSize() == 11
    badge = FXThumbnailDelegate._badge_font(option)
    assert (badge.pixelSize(), badge.weight()) == (10, QFont.DemiBold)
def test_every_role_is_claimed_once_from_one_table():
    from fxgui.fxwidgets import _roles

    claimed = [
        value for name, value in vars(_roles).items() if name.isupper()
    ]
    assert len(claimed) == len(set(claimed))
    assert fxwidgets.FXSortedTreeWidgetItem.SORT_ROLE == _roles.SORT
    assert FXThumbnailDelegate.FIRST_FREE_ROLE == _roles.FIRST_FREE
    assert _roles.FIRST_FREE == max(claimed)


def test_a_thumbnail_is_stat_once_per_window(qtbot, monkeypatch, tmp_path):
    calls = []
    real = os.path.getmtime

    def counting(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(_delegates.os.path, "getmtime", counting)
    image = tmp_path / "a.png"
    QImage(8, 8, QImage.Format_RGB32).save(str(image))
    delegate = FXThumbnailDelegate()
    for _ in range(5):
        delegate._bordered_thumbnail(str(image), 1.0)
        _thumbnails_read(qtbot)
    assert len(calls) == 1


def _thumbnails_read(qtbot):
    reads = _delegates._thumbnail_reads()
    qtbot.waitUntil(lambda: not reads._waiting, timeout=5000)


def _framed_the_old_way(delegate, path, ratio):
    """The framed thumbnail as paint built it, read in place, drawn here."""
    from qtpy.QtCore import QPointF, QRectF
    from qtpy.QtGui import QBrush, QPainterPath, QPen, QPixmap

    theme = fxstyle.colors()
    width, height = delegate._THUMBNAIL_WIDTH, delegate._THUMBNAIL_HEIGHT
    source = QPixmap(path).scaled(
        round(width * ratio), round(height * ratio),
        Qt.KeepAspectRatio, Qt.SmoothTransformation,
    )
    source.setDevicePixelRatio(ratio)
    outer_width = width + delegate._THUMBNAIL_BORDER
    outer_height = height + delegate._THUMBNAIL_BORDER
    framed = QPixmap(round(outer_width * ratio), round(outer_height * ratio))
    framed.setDevicePixelRatio(ratio)
    framed.fill(Qt.transparent)
    frame = QRectF(0.5, 0.5, outer_width - 1, outer_height - 1)
    radius = fxstyle.SMALL_RADIUS
    painter = QPainter(framed)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(theme.surface_sunken)))
    painter.drawRoundedRect(frame, radius, radius)
    corners = QPainterPath()
    corners.addRoundedRect(frame, radius, radius)
    painter.setClipPath(corners)
    painter.drawPixmap(
        QPointF(
            1 + (width - source.width() / ratio) / 2,
            1 + (height - source.height() / ratio) / 2,
        ),
        source,
    )
    painter.setClipping(False)
    painter.setPen(QPen(QColor(theme.border_light), 1))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(frame, radius, radius)
    painter.end()
    return framed.toImage()


def _sample_image(path, alpha):
    source = QImage(
        97, 41, QImage.Format_ARGB32 if alpha else QImage.Format_RGB32
    )
    for x in range(97):
        for y in range(41):
            source.setPixelColor(x, y, QColor(x * 2, y * 5, 90, 60 + y * 4))
    source.save(str(path))


@pytest.mark.parametrize("alpha", [False, True])
def test_a_local_thumbnail_shows_on_the_first_paint(qtbot, tmp_path, alpha):
    from qtpy.QtGui import QPixmapCache

    image = tmp_path / "local.png"
    _sample_image(image, alpha)
    delegate = FXThumbnailDelegate()
    expected = _framed_the_old_way(delegate, str(image), 2.0)
    QPixmapCache.clear()

    framed = delegate._bordered_thumbnail(str(image), 2.0).toImage()

    assert not _compat.can_stall(str(image))
    assert framed == expected


def test_a_share_path_can_stall():
    assert _compat.can_stall(r"\\server\share\shot.png")
    assert _compat.can_stall("//server/share/shot.png")


@pytest.mark.parametrize("alpha", [False, True])
def test_a_thumbnail_read_off_thread_is_the_one_paint_read(
    qtbot, tmp_path, monkeypatch, alpha
):
    from qtpy.QtGui import QPixmapCache

    monkeypatch.setattr(_compat, "can_stall", lambda _path: True)
    image = tmp_path / "c.png"
    _sample_image(image, alpha)
    delegate = FXThumbnailDelegate()
    expected = _framed_the_old_way(delegate, str(image), 2.0)
    QPixmapCache.clear()

    first = delegate._bordered_thumbnail(str(image), 2.0).toImage()
    _thumbnails_read(qtbot)
    framed = delegate._bordered_thumbnail(str(image), 2.0).toImage()

    assert first != expected
    assert framed == expected


def test_an_evicted_source_keeps_its_framed_thumbnail(
    qtbot, tmp_path, monkeypatch
):
    from qtpy.QtGui import QPixmapCache

    monkeypatch.setattr(_compat, "can_stall", lambda _path: True)
    image = tmp_path / "e.png"
    _sample_image(image, False)
    QPixmapCache.clear()
    delegate = FXThumbnailDelegate()
    delegate._bordered_thumbnail(str(image), 1.0)
    _thumbnails_read(qtbot)
    framed = delegate._bordered_thumbnail(str(image), 1.0).toImage()

    _delegates._thumbnail_reads()._sources.clear()

    assert delegate._bordered_thumbnail(str(image), 1.0).toImage() == framed
    _thumbnails_read(qtbot)


def test_paint_never_reads_a_share(qtbot, monkeypatch, tmp_path):
    import threading

    from qtpy.QtGui import QPixmapCache

    monkeypatch.setattr(_compat, "can_stall", lambda _path: True)
    painting = threading.current_thread()
    on_ui = []
    getmtime = os.path.getmtime
    monkeypatch.setattr(
        _delegates.os.path, "getmtime",
        lambda path: on_ui.append(threading.current_thread() is painting)
        or getmtime(path),
    )
    image = tmp_path / "d.png"
    QImage(8, 8, QImage.Format_RGB32).save(str(image))
    QPixmapCache.clear()
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    tree.setItemDelegate(FXThumbnailDelegate(tree))
    item = QTreeWidgetItem(tree, ["Shot"])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_PATH_ROLE, str(image))
    tree.resize(300, 120)

    tree.viewport().grab()
    _thumbnails_read(qtbot)
    tree.viewport().grab()

    assert on_ui == [False]


def test_stuck_share_reads_let_another_reader_start(
    qtbot, monkeypatch, tmp_path
):
    import threading
    from types import SimpleNamespace

    clock = [1000.0]
    monkeypatch.setattr(
        _delegates, "time", SimpleNamespace(monotonic=lambda: clock[0])
    )
    monkeypatch.setattr(_compat, "can_stall", lambda _path: True)
    gate = threading.Event()
    asked = []
    real = _delegates._read_thumbnail

    def read(path, known, size):
        asked.append(path)
        if path.startswith("stuck"):
            gate.wait(10)
        return real(path, known, size)

    monkeypatch.setattr(_delegates, "_read_thumbnail", read)
    image = tmp_path / "good.png"
    QImage(8, 8, QImage.Format_RGB32).save(str(image))
    reads = _delegates._ThumbnailReads()
    size = (8, 8)
    try:
        reads.source("stuck_a", size, None)
        reads.source("stuck_b", size, None)
        reads.source(str(image), size, None)
        qtbot.waitUntil(lambda: len(asked) == 2)
        qtbot.wait(100)
        assert str(image) not in asked

        clock[0] += _delegates._STUCK_SECONDS
        reads.source(str(image), size, None)
        qtbot.waitUntil(lambda: str(image) in reads._stamps)
        reads.source("stuck_a", size, None)
        qtbot.waitUntil(lambda: asked.count("stuck_a") == 2)
        assert len(reads._busy_since) <= _delegates._THUMBNAIL_READER_CAP
    finally:
        gate.set()


def test_a_re_asked_read_runs_once_when_the_share_recovers(
    qtbot, monkeypatch
):
    import threading
    from types import SimpleNamespace

    clock = [1000.0]
    monkeypatch.setattr(
        _delegates, "time", SimpleNamespace(monotonic=lambda: clock[0])
    )
    monkeypatch.setattr(_compat, "can_stall", lambda _path: True)
    gate = threading.Event()
    done = []

    def read(path, known, size):
        gate.wait(10)
        done.append(path)
        return 1.0, None

    monkeypatch.setattr(_delegates, "_read_thumbnail", read)
    reads = _delegates._ThumbnailReads()
    paths = [f"//share/{index}.png" for index in range(6)]
    try:
        for _round in range(5):
            for path in paths:
                reads.source(path, (8, 8), None)
            clock[0] += _delegates._STUCK_SECONDS
    finally:
        gate.set()
    qtbot.waitUntil(lambda: not reads._waiting)
    qtbot.wait(100)

    # Past the reads already under way, each path is read once.
    assert sorted(set(done)) == sorted(paths)
    assert len(done) <= len(paths) + len(reads._busy_since)


def test_the_remembered_stamps_are_bounded(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(_delegates, "_STAMP_LIMIT", 3)
    delegate = FXThumbnailDelegate()
    for name in "abcdef":
        delegate._bordered_thumbnail(str(tmp_path / name), 1.0)
    _thumbnails_read(qtbot)
    assert len(_delegates._thumbnail_reads()._stamps) <= 3


def test_the_thumbnail_frame_is_the_border_light_token(qtbot, tmp_path):
    fxstyle.apply_theme("light")
    image = tmp_path / "b.png"
    source = QImage(68, 38, QImage.Format_RGB32)
    source.fill(QColor("#336699"))
    source.save(str(image))
    framed = FXThumbnailDelegate()._bordered_thumbnail(str(image), 2.0)
    assert framed.devicePixelRatio() == 2.0
    middle = framed.toImage().pixelColor(framed.width() // 2, 0)
    assert middle.name() == QColor(fxstyle.colors().border_light).name()


def test_the_floor_follows_a_new_model(qtbot):
    view = QTreeView()
    view.setRootIsDecorated(False)
    view.header().setStretchLastSection(False)
    view.header().setMinimumSectionSize(10)
    view.setItemDelegate(FXThumbnailDelegate(view))
    view.setModel(QStandardItemModel(view))
    qtbot.addWidget(view)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(view)

    model = QStandardItemModel(view)
    item = QStandardItem("Asset")
    item.setData("#ff00ff", FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE)
    item.setData("Ready", FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE)
    model.appendRow(item)
    view.setModel(model)
    view.header().resizeSection(0, 20)
    assert view.header().sectionSize(0) > 60


def test_a_second_floor_replaces_the_first(qtbot):
    tree, _ = _tree(qtbot)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree, floor=100)
    FXThumbnailDelegate.apply_minimum_thumbnail_width(tree, floor=200)
    tree.header().resizeSection(0, 50)
    assert tree.header().sectionSize(0) == 200
    floors = [
        child
        for child in tree.children()
        if type(child).__name__ == "_ColumnFloor"
    ]
    assert len(floors) == 1


def test_owning_the_row_is_one_registered_rule(qtbot):
    tree, _ = _tree(qtbot)
    tree.setStyleSheet("QTreeWidget { color: red; }")
    FXThumbnailDelegate.apply_transparent_selection(tree)
    FXThumbnailDelegate.apply_transparent_selection(tree)
    assert tree.styleSheet() == "QTreeWidget { color: red; }"
    assert tree.property("fxOwnsRow") is True
    assert 'fxOwnsRow="true"' in fxstyle._build_stylesheet()


def test_a_status_label_is_a_coloured_mark_and_muted_words(qtbot):
    delegate = FXThumbnailDelegate()
    ground = QColor(fxstyle.colors().surface)
    color = QColor("#ff0000")
    canvas = QImage(200, 40, QImage.Format_RGB32)
    canvas.fill(ground)
    font = QFont()
    font.setPixelSize(30)
    font.setBold(True)
    painter = QPainter(canvas)
    delegate._INDICATOR_BAND_HEIGHT = 40
    delegate._INDICATOR_BAND_TOP = 0
    try:
        delegate._draw_status_label(
            painter, QRect(0, 0, 200, 40), 0, 200, 0, color, "HHHH", font
        )
    finally:
        painter.end()
    mark = delegate._LABEL_MARK
    words = {
        canvas.pixelColor(x, y).name()
        for x in range(mark + delegate._LABEL_GAP, 200)
        for y in range(40)
    }
    assert canvas.pixelColor(mark // 2, 20) == color
    # The colour is on the mark alone; the words are the muted ink.
    assert color.name() not in words
    assert QColor(fxstyle.colors().text_muted).name() in words


def _paint_row(qtbot, state, text="Asset"):
    """Paint one plain row in `state` and return the canvas and the tree."""
    tree, delegate = _tree(qtbot)
    item = QTreeWidgetItem(tree, [text])
    item.setData(0, FXThumbnailDelegate.THUMBNAIL_VISIBLE_ROLE, False)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 120, 28)
    option.state = QStyle.State_Enabled | state
    option.widget = tree
    option.palette = tree.palette()
    canvas = QImage(120, 28, QImage.Format_RGB32)
    canvas.fill(QColor("#123456"))
    painter = QPainter(canvas)
    try:
        delegate.paint(painter, option, tree.model().index(0, 0))
    finally:
        painter.end()
    return canvas, tree


def test_a_hovered_row_is_the_neutral_hover_fill_not_an_accent(qtbot):
    canvas, _ = _paint_row(qtbot, QStyle.State_MouseOver, text="")
    colors = fxstyle.colors()
    seen = canvas.pixelColor(110, 14).name()
    assert seen == QColor(colors.state_hover).name()
    assert seen not in (
        QColor(colors.accent_primary).name(),
        QColor(colors.accent_secondary).name(),
    )


def test_a_hovered_row_keeps_its_text_ink():
    option = QStyleOptionViewItem()
    option.state = QStyle.State_Enabled | QStyle.State_MouseOver
    assert (
        FXThumbnailDelegate._text_color(option).name()
        == option.palette.text().color().name()
    )


def test_a_selected_row_keeps_its_fill_in_a_view_without_focus(qtbot):
    canvas, tree = _paint_row(qtbot, QStyle.State_Selected, text="")
    assert not tree.hasFocus()
    assert (
        canvas.pixelColor(110, 14).name()
        == QColor(fxstyle.colors().selection).name()
    )


# FXSortFilterProxyModel ---------------------------------------------------


def _proxy(texts):
    model = QStandardItemModel()
    for text in texts:
        model.appendRow(QStandardItem(text))
    proxy = FXSortFilterProxyModel(ratio=0.5)
    proxy.setSourceModel(model)
    return model, proxy


def _rows(proxy):
    return [proxy.index(row, 0).data() for row in range(proxy.rowCount())]


def test_a_substring_hit_ranks_with_a_perfect_score(qapp):
    _, proxy = _proxy(["heron", "character_hero_main"])
    proxy.set_filter_text("hero")
    # A tie keeps the source order.
    assert _rows(proxy) == ["heron", "character_hero_main"]
    assert proxy.score("character_hero_main") == 1.0
    assert proxy.score("heron") == 1.0


def test_a_substring_hit_sorts_above_a_fuzzy_one(qapp):
    _, proxy = _proxy(["hrxo", "the_hero"])
    proxy.set_ratio(0.1)
    proxy.set_filter_text("hero")
    assert _rows(proxy) == ["the_hero", "hrxo"]


def test_each_row_is_scored_once_per_filter(qapp, monkeypatch):
    texts = [f"asset_{n:03d}_hero" for n in range(40)]
    _, proxy = _proxy(texts)
    calls = []
    real = fxcore._score

    def counting(*args):
        calls.append(args)
        return real(*args)

    monkeypatch.setattr(fxcore, "_score", counting)
    proxy.set_filter_text("ast")
    for row in range(proxy.rowCount()):
        proxy.index(row, 0).data(Qt.ForegroundRole)
    assert len(calls) <= len(texts)


# FXSortedTreeWidgetItem ---------------------------------------------------


def test_keyed_and_keyless_rows_sort_in_two_blocks(qtbot):
    tree = QTreeWidget()
    qtbot.addWidget(tree)
    role = fxwidgets.FXSortedTreeWidgetItem.SORT_ROLE
    a = fxwidgets.FXSortedTreeWidgetItem(tree, ["a"])
    b = fxwidgets.FXSortedTreeWidgetItem(tree, ["b"])
    c = fxwidgets.FXSortedTreeWidgetItem(tree, ["c"])
    a.setData(0, role, 2)
    c.setData(0, role, 1)
    assert not (a < b and b < c and c < a)
    tree.sortItems(0, Qt.AscendingOrder)
    assert [tree.topLevelItem(n).text(0) for n in range(3)] == ["c", "a", "b"]


# FXFilteredTree ------------------------------------------------------------


def test_building_the_filtered_tree_shows_no_window(qtbot, qapp):
    from qtpy.QtCore import QEvent, QObject

    shown = []

    class _Spy(QObject):
        def eventFilter(self, watched, event):
            if (
                event.type() == QEvent.Show
                and hasattr(watched, "isWindow")
                and watched.isWindow()
            ):
                shown.append(type(watched).__name__)
            return False

    spy = _Spy()
    qapp.installEventFilter(spy)
    try:
        search = fxwidgets.FXFilteredTree()
        qtbot.addWidget(search)
        qapp.processEvents()
    finally:
        qapp.removeEventFilter(spy)
    assert shown == []
