"""Rez package of fxgui, built from this clone (`lsd release`).

PyPI stays the public release (a `vX.Y.Z` tag, release.yml). This builds
the same `fxgui` folder into a Rez tier in seconds, laid out as `lsd pip`
lays the wheel out: `{root}/python/fxgui`.
"""

# pylint: disable=invalid-name, missing-function-docstring, undefined-variable
# pyright: reportUndefinedVariable=false

name = "fxgui"

# The last version released, to PyPI or a tier; `lsd release` bumps it.
version = "15.4.2"

description = """
    Custom Python classes and utilities tailored for Qt built UI, in
    VFX-oriented DCC applications.
    """

authors = ["Valentin Beaumont"]

build_requires = [
    "python-3+",
    "ls_rez-2.2.4+",
]

# The wheel's own requirements; Qt itself comes from the context (a DCC's,
# or PySide6).
requires = [
    "python-3.9+",
    "QtPy-2.4.2+",
    "PyYAML-6.0+",
    "Pygments-2.2+",
]

build_command = "python {root}/rezbuild.py {install}"

# A list: rez pastes a string into PowerShell, where `;` ends the command.
# The suite itself runs in GitHub Actions on every push.
tests = {
    "import": {
        "command": [
            "python",
            "-c",
            "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; "
            "from qtpy.QtWidgets import QApplication; app = QApplication([]); "
            "import fxgui; from fxgui import fxstyle, fxwidgets; "
            "assert fxgui.__version__ != '0.0.0.dev', fxgui.__version__; "
            "print('fxgui', fxgui.__version__)",
        ],
        "requires": ["PySide6"],
        "run_on": ["default", "pre_release"],
    },
}


def commands():
    # `env` is Rez's, given to commands() when it runs.
    env.PYTHONPATH.append("{root}/python")  # noqa: F821
