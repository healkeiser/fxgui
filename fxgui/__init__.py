# Built-in
import os
import sys

# Internal
from fxgui import fxdcc, fxicons, fxstyle, fxutils, fxwidgets


__all__ = [fxdcc, fxicons, fxstyle, fxutils, fxwidgets]

if sys.version_info < (3, 11):
    os.environ["QT_API"] = "pyside2"
else:
    os.environ["QT_API"] = "pyside6"
