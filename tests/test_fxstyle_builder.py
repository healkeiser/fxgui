"""Unit tests for the theme sheet builder and fragment registry."""

from fxgui import fxstyle


def test_build_stylesheet_resolves_all_tokens(qapp):
    sheet = fxstyle.build_stylesheet("dark")
    assert sheet  # non-empty
    assert "@" not in sheet
    assert "~icons" not in sheet


def test_build_stylesheet_defaults_to_current_theme(qapp):
    assert fxstyle.build_stylesheet() == fxstyle.build_stylesheet(
        fxstyle.get_theme()
    )


def test_register_widget_style_appends_fragment(qapp):
    fxstyle.register_widget_style(
        "FXPlanTestWidget { background: @surface; }"
    )
    sheet = fxstyle.build_stylesheet("dark")
    assert "FXPlanTestWidget" in sheet
    assert "@surface" not in sheet


def test_register_widget_style_dedupes_identical_fragments(qapp):
    fragment = "FXPlanDedupe { color: @text; }"
    fxstyle.register_widget_style(fragment)
    fxstyle.register_widget_style(fragment)
    assert fxstyle.build_stylesheet("dark").count("FXPlanDedupe") == 1
