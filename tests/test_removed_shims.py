"""The one-release shims of the pull model are gone."""

import inspect

import pytest
from qtpy.QtWidgets import QWidget

from fxgui import fxstyle, fxwidgets
from fxgui.fxwidgets import FXCollapsibleWidget
from fxgui.fxwidgets import _validators


def test_the_mixin_is_gone():
    assert not hasattr(fxstyle, "FXThemeAware")
    assert "FXThemeAware" not in fxstyle.__all__
    assert not hasattr(fxwidgets, "FXThemeAware")
    assert "FXThemeAware" not in fxwidgets.__all__


def test_apply_theme_takes_a_theme_name_only(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    assert list(inspect.signature(fxstyle.apply_theme).parameters) == [
        "theme"]
    with pytest.raises(TypeError):
        fxstyle.apply_theme(widget, "light")


def test_the_collapsible_aliases_are_gone():
    for name in ("header_widget", "content_area", "toggle_button",
                 "title_label", "title_icon_label", "set_title_icon",
                 "get_title_icon"):
        assert not hasattr(FXCollapsibleWidget, name), name


def test_the_validators_name_no_qt4_method():
    assert "setRegExp" not in inspect.getsource(_validators)


def test_the_accordion_section_alias_is_gone():
    assert not hasattr(fxwidgets, "FXAccordionSection")
    assert "FXAccordionSection" not in fxwidgets.__all__
