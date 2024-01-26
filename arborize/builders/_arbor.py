import typing
from collections import defaultdict
from itertools import tee

import arbor

if typing.TYPE_CHECKING:
    from ..schematic import Schematic, Point


class CableCellTemplate:
    def __init__(
        self, morphology: arbor.morphology, labels: arbor.label_dict, decor: arbor.decor
    ):
        self.morphology = morphology
        self.labels = labels
        self.decor = decor

    def build(self):
        return arbor.cable_cell(self.morphology, self.labels, self.decor)


def hash_labelset(labels: list[str]):
    return "&".join(l.replace("&", "&&") for l in sorted(labels))


def get_label_dict(schematic: "Schematic"):
    labelsets = {}
    label_dict = defaultdict(list)
    for b in schematic.cables:
        for p in b.points:
            h = hash_labelset(p.branch.labels)
            if h not in labelsets:
                lset_id = len(labelsets)
                for l in p.branch.labels:
                    label_dict[l].append(lset_id)
                labelsets[h] = lset_id
    return labelsets, arbor.label_dict(
        {
            label: "(join " + " ".join(f"(tag {tag})" for tag in tags) + ")"
            if len(tags) > 1
            else f"(tag {tags[0]})"
            for label, tags in label_dict.items()
        }
    )


def arbor_build(schematic: "Schematic"):
    schematic.freeze()
    if not hasattr(schematic, "arbor"):
        tree = arbor.segment_tree()
        # Stores the ids of the segments to append to.
        branch_endpoints = {}
        labelsets, label_dict = get_label_dict(schematic)
        for bid, branch in enumerate(schematic.cables):
            if len(branch.points) < 2:
                # Empty branches mess up the branch id numbering, so we forbid them
                raise RuntimeError(f"Branch {bid} needs at least 2 points.")
            pts = iter(branch.points)
            pts_a, pts_b = tee(pts)
            first_pt = next(pts_b)
            ptid = branch_endpoints[branch.parent] if branch.parent else arbor.mnpos
            p1: Point
            p2: Point
            for i, (p1, p2) in enumerate(zip(pts_a, pts_b)):
                tag = hash_labelset(p2.branch.labels)
                ptid = tree.append(ptid, _mkpt(p1), _mkpt(p2), tag=labelsets.get(tag))
            branch_endpoints[branch] = ptid
        schematic.arbor = CableCellTemplate(
            arbor.morphology(tree), label_dict, arbor.decor()
        )
    return schematic.arbor.build()


def _mkpt(p: "Point") -> arbor.mpoint:
    return arbor.mpoint(*p.coords, p.radius)
