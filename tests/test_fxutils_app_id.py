"""set_app_user_model_id names the process to Windows and is a no-op elsewhere."""

# Built-in
import sys
from types import SimpleNamespace

# Internal
from fxgui import fxutils


def _fake_ctypes(calls, result=0, error=None):
    def claim(app_id):
        calls.append(app_id)
        if error is not None:
            raise error
        return result

    shell32 = SimpleNamespace(SetCurrentProcessExplicitAppUserModelID=claim)
    return SimpleNamespace(windll=SimpleNamespace(shell32=shell32))


def test_on_windows_the_process_takes_the_id(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(fxutils, "ctypes", _fake_ctypes(calls))

    assert fxutils.set_app_user_model_id("Studio.Launcher") is True
    assert calls == ["Studio.Launcher"]


def test_a_refusal_answers_false_and_raises_nothing(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    for fake in (
        _fake_ctypes([], result=-2147024809),
        _fake_ctypes([], error=OSError("no shell32")),
        SimpleNamespace(),
    ):
        monkeypatch.setattr(fxutils, "ctypes", fake)
        assert fxutils.set_app_user_model_id("Studio.Launcher") is False


def test_off_windows_nothing_is_called(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(fxutils, "ctypes", _fake_ctypes(calls))

    assert fxutils.set_app_user_model_id("Studio.Launcher") is False
    assert calls == []
