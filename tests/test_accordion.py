"""Accordion signals name a section's index as it is now, not as it was."""

# Third-party
import pytest
from qtpy.QtWidgets import QLabel

# Internal
from fxgui.fxwidgets import FXAccordion


def test_indexes_follow_a_removed_section(qtbot, qapp):
    accordion = FXAccordion(animation_duration=0)
    qtbot.addWidget(accordion)
    for title in ("a", "b", "c"):
        accordion.add_section(title, QLabel(title))
    accordion.remove_section(0)
    seen = []
    accordion.section_expanded.connect(seen.append)

    accordion.expand_section(0)
    accordion.expand_section(1)

    assert seen == [0, 1]
    assert not accordion.get_section(0).is_expanded()
    assert accordion.get_section(1).is_expanded()


def test_expand_all_refuses_an_exclusive_accordion(qtbot, qapp):
    accordion = FXAccordion(animation_duration=0)
    qtbot.addWidget(accordion)
    accordion.add_section("a", QLabel("a"))

    with pytest.raises(RuntimeError):
        accordion.expand_all()

    accordion.set_exclusive(False)
    accordion.expand_all()
    assert accordion.get_section(0).is_expanded()
    assert accordion.exclusive() is False
