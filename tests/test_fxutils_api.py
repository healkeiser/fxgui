"""fxutils keeps one helper per job, each with the arguments callers use."""

# Built-in
import inspect

# Third-party
import pytest
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QGraphicsDropShadowEffect, QWidget

# Internal
from fxgui import fxstyle, fxutils


def test_create_action_takes_only_the_arguments_callers_pass(qtbot):
    parameters = inspect.signature(fxutils.create_action).parameters
    assert list(parameters) == [
        "parent", "name", "trigger", "enable", "shortcut", "checkable",
        "icon_name"]

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


def test_add_shadow_casts_the_themes_shadow(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    shadow = fxutils.add_shadow(widget, offset=(0, 4))

    assert isinstance(shadow, QGraphicsDropShadowEffect)
    assert widget.graphicsEffect() is shadow
    assert shadow.parent() is widget
    assert (shadow.xOffset(), shadow.yOffset()) == (0, 4)
    theme = fxstyle.colors()
    assert shadow.color() == QColor(theme.shadow)
    assert shadow.blurRadius() == float(theme.shadow_blur)


def test_a_shadow_follows_a_theme_switch_when_it_draws(qtbot, tmp_path):
    path = tmp_path / "shadow.yaml"
    path.write_text(
        "themes:\n  light:\n    shadow: '#40102030'\n    shadow_blur: 9\n",
        encoding="utf-8")
    fxstyle.overlay_color_file(path)
    holder = QWidget()
    qtbot.addWidget(holder)
    card = QWidget(holder)
    card.setGeometry(20, 20, 40, 40)
    shadow = fxutils.add_shadow(card)
    holder.resize(100, 100)
    holder.show()
    qtbot.waitExposed(holder)

    fxstyle.apply_theme("light")
    holder.grab()

    assert shadow.color() == QColor("#40102030")
    assert shadow.blurRadius() == 9


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
