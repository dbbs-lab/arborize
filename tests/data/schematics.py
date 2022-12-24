import os as _os

from arborize import file_schematic as _schema
from .models import empty as _empty, pas as _pas, expsyn as _expsyn

def _mpath(path):
    return _os.path.join(_os.path.dirname(__file__), "morphologies", path)


cell010 = _schema(_mpath("cell010.swc"))
with open(_mpath("P75.swc"), "r") as _file:
    p75 = _schema(_file)
with open(_mpath("P75.swc"), "r") as _file:
    p75_pas = _schema(_file, definitions=_pas)
    p75_expsyn = _schema(_file, definitions=_expsyn)