"""A status label can lead with an icon in its colour instead of a dot."""

# Third-party
from qtpy.QtGui import QColor, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QStyleOptionViewItem, QTreeView

# Internal
from fxgui.fxwidgets import FXThumbnailDelegate


def _index(qtbot, icon):
    view = QTreeView()
    qtbot.addWidget(view)
    model = QStandardItemModel(view)
    item = QStandardItem("shot_010")
    item.setData(QColor("#05df72"), FXThumbnailDelegate.STATUS_LABEL_COLOR_ROLE)
    item.setData("Done", FXThumbnailDelegate.STATUS_LABEL_TEXT_ROLE)
    if icon:
        item.setData(icon, FXThumbnailDelegate.STATUS_LABEL_ICON_ROLE)
    model.appendRow(item)
    view.setModel(model)
    delegate = FXThumbnailDelegate(view)
    view.setItemDelegate(delegate)
    option = QStyleOptionViewItem()
    option.initFrom(view)
    option.rect = view.visualRect(model.index(0, 0)).adjusted(0, 0, 400, 0)
    return delegate, model.index(0, 0), option, view


def test_an_icon_widens_the_mark_to_the_icon(qtbot, qapp):
    plain, index, option, _view = _index(qtbot, "")
    iconned, icon_index, icon_option, _held = _index(qtbot, "check_circle")
    dot = plain._indicator_metrics(index, option).label_width
    marks = iconned._indicator_metrics(icon_index, icon_option)
    assert marks.label_icon == "check_circle"
    assert marks.label_width - dot == (
        FXThumbnailDelegate._LABEL_ICON - FXThumbnailDelegate._LABEL_MARK
    )
