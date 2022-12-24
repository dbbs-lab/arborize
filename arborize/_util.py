from typing import Iterable, TYPE_CHECKING
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
    arcsums = np.cumsum(np.sum(rel_dist ** 2, axis=1) ** 0.5)
    return arcsums / arcsums[-1]
