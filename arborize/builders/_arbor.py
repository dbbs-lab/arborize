import typing
from itertools import tee

import arbor

if typing.TYPE_CHECKING:
    from ..schematic import Schematic, Point


def arbor_build(schematic: "Schematic"):
    schematic.freeze()
    if hasattr(schematic, "arbor"):
        return schematic.arbor
    tree = arbor.segment_tree()
    # Stores the ids of the segments to append to.
    branch_endpoints = {}
    for bid, branch in enumerate(schematic.cables):
        if len(branch.points) < 2:
            # Empty branches mess up the branch id numbering, so we forbid them
            raise RuntimeError(f"Branch {bid} needs at least 2 points.")
        pts = iter(branch.points)
        pts_a, pts_b = tee(pts)
        first_pt = next(pts_b)
        ptid = branch_endpoints[branch.parent] if branch.parent else arbor.mnpos
        for i, (p1, p2) in enumerate(zip(pts_a, pts_b)):
            ptid = tree.append(ptid, _mkpt(p1), _mkpt(p2), tag=1)
        branch_endpoints[branch] = ptid
    morpho = arbor.morphology(tree)

    return morpho


def _mkpt(p: "Point") -> arbor.mpoint:
    return arbor.mpoint(*p.coords, p.radius)
