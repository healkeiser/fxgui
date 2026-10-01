"""mix and step_toward are the colour steps every derived colour uses."""

from qtpy.QtGui import QColor

from fxgui import fxstyle


def test_mix_goes_the_asked_part_of_the_way():
    assert fxstyle.mix("#000000", "#ffffff", 0) == "#000000"
    assert fxstyle.mix("#000000", "#ffffff", 1) == "#ffffff"
    assert fxstyle.mix("#000000", "#ffffff", 0.5) == "#808080"


def test_mix_takes_a_qcolor_and_answers_hex():
    assert fxstyle.mix(QColor("#ff0000"), QColor("#0000ff"), 0.5) == "#800080"


def test_step_toward_stops_at_the_first_colour_that_is_done():
    first = fxstyle.step_toward(
        "#202020", "#ffffff",
        lambda color: fxstyle.get_contrast_ratio(color, "#202020") >= 4.5)

    assert fxstyle.get_contrast_ratio(first, "#202020") >= 4.5
    assert first != "#ffffff"


def test_step_toward_ends_on_the_target_when_nothing_is_done():
    assert fxstyle.step_toward("#202020", "#303030", lambda _: False) == (
        "#303030")
