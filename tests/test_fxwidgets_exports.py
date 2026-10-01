"""fxwidgets exports every public class of its modules, from one list."""

# Built-in
import importlib
import inspect
import pkgutil
from pathlib import Path

# Internal
from fxgui import fxwidgets


def _modules():
    for info in pkgutil.iter_modules(fxwidgets.__path__):
        yield importlib.import_module(f"fxgui.fxwidgets.{info.name}")


def test_every_listed_name_imports():
    for name in fxwidgets.__all__:
        assert getattr(fxwidgets, name, None) is not None, name


def test_the_list_is_sorted_and_names_each_once():
    names = fxwidgets.__all__
    assert names == sorted(names, key=str.lower)
    assert len(names) == len(set(names))


def test_every_public_class_of_a_module_is_listed():
    missing = [
        f"{module.__name__}.{name}"
        for module in _modules()
        for name, value in vars(module).items()
        if inspect.isclass(value)
        and not name.startswith("_")
        and value.__module__ == module.__name__
        and name not in fxwidgets.__all__
    ]
    assert missing == []


def test_the_list_is_built_once():
    source = Path(fxwidgets.__file__).read_text(encoding="utf-8")
    assert "__all__ +=" not in source
    assert "noqa: E402" not in source
