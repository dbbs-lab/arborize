import dataclasses
import typing
from typing import TYPE_CHECKING, Iterable

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from schematic import Point


def get_location_name(pts: Iterable["Point"]) -> str:
    if len(pts) == 1:
        loc = pts[0].loc
        locstr = f"location ({loc[0]}.{loc[1]})"
    else:
        loc1 = pts[0].loc
        loc2 = pts[-1].loc
        locstr = f"interval ({loc1[0]}.{loc1[1]}-{loc2[1]})"
    return locstr


def get_arclengths(pts: Iterable["Point"]) -> npt.NDArray[float]:
    coords = np.array([pt.coords for pt in pts])
    rel_dist = np.diff(coords, axis=0, prepend=[coords[0, :]])
    arcsums = np.cumsum(np.sum(rel_dist**2, axis=1) ** 0.5)
    return arcsums / arcsums[-1]


MechIdTuple = typing.Union[tuple[str], tuple[str, str], tuple[str, str, str]]
MechId = typing.Union[str, MechIdTuple]


@dataclasses.dataclass
class Copy:
    def copy(self):
        other = type(self)()
        for field in dataclasses.fields(self):
            setattr(other, field.name, getattr(self, field.name))
        return other


@dataclasses.dataclass
class Merge:
    def merge(self, other):
        for field in dataclasses.fields(self):
            value = getattr(other, field.name)
            if value is not None:
                setattr(self, field.name, value)


@dataclasses.dataclass
class Assert:
    def assert_(self):
        for field in dataclasses.fields(self):
            if getattr(self, field.name, None) is None:
                raise ValueError(f"Missing '{field.name}' value.", field.name)
