"""The helpers every module shares: one resolver, one version, one cap."""

# Built-in
import inspect
import pathlib

# Third-party
import pytest
import yaml
from qtpy.QtCore import qVersion
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QHBoxLayout, QLabel, QSplitter, QWidget

# Internal
from fxgui import _compat, fxconstants, fxstyle, fxutils

_PACKAGE = pathlib.Path(fxstyle.__file__).parent


def test_a_missing_colour_file_raises_at_the_call_and_keeps_the_theme(qapp):
    surface = fxstyle.colors().surface
    with pytest.raises(FileNotFoundError):
        fxstyle.set_color_file("missing.yaml")
    fxstyle._invalidate_theme_namespace()
    assert fxstyle.colors().surface == surface


def test_a_broken_colour_file_raises_at_the_call(qapp, tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("themes: [", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        fxstyle.set_color_file(path)
    assert fxstyle.colors().surface


def test_qcolor_reads_a_token_a_colour_or_nothing(qapp):
    assert fxstyle.qcolor("accent_primary") == QColor(
        fxstyle.colors().accent_primary)
    assert fxstyle.qcolor("#ff0000") == QColor("#ff0000")
    assert fxstyle.qcolor(QColor("red")) == QColor("red")
    assert not fxstyle.qcolor("not a color").isValid()
    assert not fxstyle.qcolor(None).isValid()
    assert "qcolor" in fxstyle.__all__


def test_qcolor_follows_a_switch(qapp):
    dark = fxstyle.qcolor("surface")
    fxstyle.apply_theme("light")
    assert fxstyle.qcolor("surface") != dark


def test_readable_ink_is_cached_once(qapp):
    assert hasattr(fxstyle._readable_ink, "cache_info")
    from fxgui.fxwidgets import _log_widget

    assert not hasattr(_log_widget, "_readable_ink")


def test_one_qt_version_parse(qapp):
    major, minor = (int(part) for part in qVersion().split(".")[:2])
    assert _compat.QT_VERSION == (major, minor)
    for module in ("fxstyle.py", "fxicons.py"):
        source = (_PACKAGE / module).read_text(encoding="utf-8")
        assert "qVersion" not in source and "QT_VERSION.split" not in source


def test_no_widget_calls_the_private_focus_watch():
    for path in (_PACKAGE / "fxwidgets").glob("*.py"):
        assert "_watch_focus" not in path.read_text(encoding="utf-8"), path


def test_the_focus_watch_starts_where_focus_visible_is_asked(
    qapp, monkeypatch
):
    monkeypatch.setattr(fxstyle, "_focus_visibility", None)
    fxstyle.focus_visible(QWidget())
    watch = fxstyle._focus_visibility
    assert watch is not None and watch.parent() is qapp
    qapp.removeEventFilter(watch)
    watch.deleteLater()


def test_the_package_root_is_stated_once():
    source = (_PACKAGE / "fxstyle.py").read_text(encoding="utf-8")
    assert "Path(__file__)" not in source
    assert fxstyle.STYLE_FILE == fxconstants.PACKAGE_ROOT / "qss" / "style.qss"


def test_no_cap_is_one_name():
    assert fxutils.NO_CAP == 16777215
    for path in (_PACKAGE / "fxwidgets").glob("*.py"):
        assert "16777215" not in path.read_text(encoding="utf-8"), path


def test_mark_as_frame_repolishes_direct_children_only(qtbot, monkeypatch):
    band = QWidget()
    qtbot.addWidget(band)
    row = QHBoxLayout(band)
    child = QLabel("child")
    row.addWidget(child)
    inner = QWidget(child)
    QLabel("grandchild", inner)
    polished = []
    monkeypatch.setattr(fxutils, "repolish", polished.append)
    fxstyle.mark_as_frame(band)
    assert polished == [band, child]


def test_mark_as_frame_still_marks_a_splitter(qtbot):
    splitter = QSplitter()
    qtbot.addWidget(splitter)
    fxstyle.mark_as_frame(splitter)
    assert splitter.property(fxstyle.FRAME_PROPERTY) is True
    assert "findChildren(QWidget)" not in inspect.getsource(
        fxstyle.mark_as_frame)
