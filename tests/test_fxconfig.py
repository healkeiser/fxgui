"""Tests for `fxgui.fxconfig`: one INI file per application, where Qt puts it."""

# Built-in
from pathlib import Path

# Third-party
import pytest
from qtpy.QtCore import QSettings

# Internal
from fxgui import fxconfig


def _expected(name: str) -> str:
    return QSettings(
        QSettings.IniFormat, QSettings.UserScope, name, "settings"
    ).fileName()


def test_get_set_value_roundtrip(qapp):
    fxconfig.set_value("probe/key", "value-a")
    assert fxconfig.get_value("probe/key") == "value-a"


def test_settings_live_where_qsettings_puts_an_ini(qapp):
    fxconfig.set_value("probe/key", "value")
    path = fxconfig._settings().fileName()
    assert path == _expected("fxgui")
    assert Path(path).exists()


def test_tests_write_settings_under_the_temp_folder_only(qapp, tmp_path):
    fxconfig.set_value("probe/key", "value")
    assert Path(fxconfig._settings().fileName()).is_relative_to(tmp_path)


def test_set_application_name_isolates_settings(qapp):
    fxconfig.set_value("probe/key", "default-ns")

    fxconfig.set_application_name("fxgui_test_ns")
    assert fxconfig._settings().fileName() == _expected("fxgui_test_ns")

    # New namespace starts empty; writes stay in its own file
    assert fxconfig.get_value("probe/key") is None
    fxconfig.set_value("probe/key", "test-ns")
    assert fxconfig.get_value("probe/key") == "test-ns"

    # Switching back restores the original value
    fxconfig.set_application_name("fxgui")
    assert fxconfig.get_value("probe/key") == "default-ns"


def test_get_value_answers_in_the_defaults_type(qapp):
    # Written by hand: QSettings keeps what it wrote typed in memory.
    path = Path(_expected("fxgui_typed"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[probe]\nflag=true\ncount=3\nratio=0.5\n")
    fxconfig.set_application_name("fxgui_typed")

    assert fxconfig.get_value("probe/flag", False) is True
    assert fxconfig.get_value("probe/count", 0) == 3
    assert isinstance(fxconfig.get_value("probe/count", 0), int)
    assert fxconfig.get_value("probe/ratio", 0.0) == 0.5
    assert fxconfig.get_value("probe/missing", 7) == 7


def test_a_new_application_reads_its_own_theme_and_row_size(qapp):
    from fxgui import fxstyle

    fxstyle.apply_theme("light")
    fxstyle.apply_row_size("small")

    fxconfig.set_application_name("fxgui_other_tool")

    assert fxstyle.get_theme() == fxstyle.get_default_theme()
    assert fxstyle.row_size() == fxstyle._DEFAULT_ROW_SIZE
    assert fxstyle.colors().surface == fxstyle._colour_tokens(
        fxstyle.get_default_theme())["surface"]


def test_a_new_application_restyles_live_roots(qtbot):
    from qtpy.QtWidgets import QWidget

    from fxgui import fxstyle

    root = QWidget()
    qtbot.addWidget(root)
    fxstyle.register_themed_root(root)
    fxstyle.apply_theme("light")
    light_sheet = root.styleSheet()
    received = []
    note = received.append
    fxstyle.theme_changed.connect(note)
    try:
        fxconfig.set_application_name("fxgui_restyle_tool")
    finally:
        fxstyle.theme_changed.disconnect(note)

    assert received == [fxstyle.get_default_theme()]
    assert root.styleSheet() != light_sheet


@pytest.mark.parametrize("bad_name", ["", "   ", "a/b", "a\\b", ".."])
def test_set_application_name_rejects_unsafe_names(bad_name):
    with pytest.raises(ValueError):
        fxconfig.set_application_name(bad_name)
