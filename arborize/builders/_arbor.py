import typing
from itertools import tee

import arbor

if typing.TYPE_CHECKING:
    from ..schematic import Schematic, Point


def arbor_build(schematic: "Schematic"):
    schematic.freeze()
    tree = arbor.segment_tree()
    # Stores the ids of the segments to append to.
    branch_endpoints = {}
    for bid, branch in enumerate(schematic.virtual_branches):
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
    assert len(schematic.virtual_branches) == morpho.num_branches

    def pid(i):
        try:
            return [*branch_endpoints.keys()].index(i)
        except ValueError:
            # Value for no parent in Arbor
            return 4294967295

    # Assert that the data was transferred correctly.
    for (bid, vb) in enumerate(schematic.virtual_branches):
        assert pid(vb.parent) == morpho.branch_parent(bid)
        segments = morpho.branch_segments(bid)
        pwlin = arbor.place_pwlin(morpho)
        assert len(vb.points) - 1 == len(segments)
        for pt, seg in zip(vb.points, segments):
            assert _mkpt(pt) == seg.prox
            assert pwlin.closest(*pt.coords)[1] < 1e-8
    


def _mkpt(p: "Point") -> arbor.mpoint:
    return arbor.mpoint(*p.coords, p.radius)
