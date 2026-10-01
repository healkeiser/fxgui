"""fxutils keeps one helper per job, each with the arguments callers use."""

# Built-in
import inspect

# Third-party
import pytest
from qtpy.QtWidgets import QGraphicsDropShadowEffect, QWidget

# Internal
from fxgui import fxutils


def test_create_action_takes_only_the_arguments_callers_pass(qtbot):
    parameters = inspect.signature(fxutils.create_action).parameters
    for name in ("icon", "visible"):
        assert name not in parameters, name

    owner = QWidget()
    qtbot.addWidget(owner)
    fired = []
    action = fxutils.create_action(
        owner, "Save", trigger=lambda: fired.append(1), shortcut="Ctrl+S",
        checkable=True, icon_name="save")
    action.trigger()
    assert fired == [1]
    assert not fxutils.create_action(owner, "Later", enable=False).isEnabled()
    assert action.isCheckable() and not action.icon().isNull()
    assert action.shortcut().toString() == "Ctrl+S"
    assert action.parent() is owner


def test_add_shadow_casts_one_black_shadow(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    shadow = fxutils.add_shadow(widget, blur=24, offset=(0, 4), alpha=100)

    assert isinstance(shadow, QGraphicsDropShadowEffect)
    assert widget.graphicsEffect() is shadow
    assert shadow.blurRadius() == 24
    assert (shadow.xOffset(), shadow.yOffset()) == (0, 4)
    assert shadow.color().getRgb() == (0, 0, 0, 100)


def test_the_one_caller_helpers_are_gone():
    assert not hasattr(fxutils, "get_formatted_time")
    assert "get_formatted_time" not in fxutils.__all__
    assert "add_shadows" not in fxutils.__all__


@pytest.mark.parametrize(
    "name",
    ["set_app_user_model_id", "markdown_to_plain_text", "add_shadow"],
)
def test_public_helpers_are_exported(name):
    assert name in fxutils.__all__
    assert callable(getattr(fxutils, name))


def test_markdown_to_plain_text_passes_plain_text_through():
    assert fxutils.markdown_to_plain_text("") == ""
    assert fxutils.markdown_to_plain_text("-") == "-"


def test_the_qt_helpers_are_defined_in_fxutils():
    for name in ("later", "rehome", "focus_step"):
        assert getattr(fxutils, name).__module__ == "fxgui.fxutils", name


def test_load_ui_needs_no_qfile(qtbot, tmp_path):
    ui = tmp_path / "probe.ui"
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0"><class>Probe</class>'
        '<widget class="QWidget" name="Probe"/></ui>\n',
        encoding="utf-8",
    )
    parent = QWidget()
    qtbot.addWidget(parent)

    loaded = fxutils.load_ui(parent, str(ui))

    assert loaded.objectName() == "Probe"
    assert loaded.parent() is parent
    assert "QFile" not in vars(fxutils)
