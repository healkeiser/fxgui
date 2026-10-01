"""Every docstring example that states its output gives that output.

A fragment with no stated output only shows a call; it runs, but nothing
it raises fails the test, since it may name a widget the page assumes.
"""

# Built-in
import doctest
import importlib
import importlib.util
import pkgutil

# Third-party
import pytest

# Internal
import fxgui
from fxgui import fxconfig, fxcore, fxicons, fxstyle, fxutils, fxwidgets


def _stated_tests():
    finder = doctest.DocTestFinder()
    found = []
    for info in pkgutil.walk_packages(fxgui.__path__, "fxgui."):
        if ".icons" in info.name:
            continue
        # Docking is optional: its module imports QtAds.
        if info.name == "fxgui.fxdocking" and importlib.util.find_spec(
            "PySide6QtAds"
        ) is None:
            continue
        module = importlib.import_module(info.name)
        for test in finder.find(module, info.name):
            if test.name.startswith(info.name) and any(
                example.want for example in test.examples
            ):
                found.append(test)
    return found


class _StatedOnly(doctest.DocTestRunner):
    """Count a failure only for an example that states its output."""

    def report_failure(self, out, test, example, got):
        if example.want:
            super().report_failure(out, test, example, got)

    def report_unexpected_exception(self, out, test, example, exc_info):
        if example.want:
            super().report_unexpected_exception(out, test, example, exc_info)


@pytest.mark.parametrize("test", _stated_tests(), ids=lambda test: test.name)
def test_a_stated_output_holds(qapp, test):
    test.globs.update(fxgui=fxgui, fxconfig=fxconfig, fxcore=fxcore,
                      fxicons=fxicons, fxstyle=fxstyle, fxutils=fxutils,
                      fxwidgets=fxwidgets)
    lines = []
    runner = _StatedOnly(optionflags=doctest.ELLIPSIS)
    runner.run(test, out=lines.append)

    assert not lines, "".join(lines)
