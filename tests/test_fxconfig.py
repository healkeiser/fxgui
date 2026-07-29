"""Tests for `fxgui.fxconfig`, including the opt-in per-application settings
namespace (by default every fxgui-based tool shares one settings file)."""

# Built-in
from pathlib import Path

# Third-party
import pytest

# Internal
from fxgui import fxconfig


@pytest.fixture
def _sandboxed_config(tmp_path, monkeypatch):
    """Route config dirs into tmp_path and restore the app name afterwards."""
    monkeypatch.setattr(
        fxconfig,
        "_get_config_dir",
        lambda: tmp_path / fxconfig._APP_NAME,
    )
    original = fxconfig.get_application_name()
    # Re-anchor the module globals onto the sandboxed dir
    fxconfig.set_application_name(original)
    yield tmp_path
    fxconfig.set_application_name(original)


def test_get_set_value_roundtrip(_sandboxed_config):
    fxconfig.set_value("probe/key", "value-a")
    assert fxconfig.get_value("probe/key") == "value-a"


def test_set_application_name_isolates_settings(_sandboxed_config):
    fxconfig.set_value("probe/key", "default-ns")

    fxconfig.set_application_name("fxgui_test_ns")
    assert fxconfig.get_application_name() == "fxgui_test_ns"
    assert "fxgui_test_ns" in str(fxconfig.SETTINGS_FILE)

    # New namespace starts empty; writes stay in its own file
    assert fxconfig.get_value("probe/key") is None
    fxconfig.set_value("probe/key", "test-ns")
    assert fxconfig.get_value("probe/key") == "test-ns"
    assert Path(fxconfig.SETTINGS_FILE).exists()

    # Switching back restores the original value
    fxconfig.set_application_name("fxgui")
    assert fxconfig.get_value("probe/key") == "default-ns"


@pytest.mark.parametrize("bad_name", ["", "   ", "a/b", "a\\b", ".."])
def test_set_application_name_rejects_unsafe_names(bad_name):
    with pytest.raises(ValueError):
        fxconfig.set_application_name(bad_name)
