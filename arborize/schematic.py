import dataclasses
import typing
from collections import defaultdict
from typing import Optional, Union

from .exceptions import FrozenError

from .definitions import CableType, ModelDefinition

import errr

if typing.TYPE_CHECKING:
    from .parameter import Parameter

Location = tuple[int, int]
Interval = tuple[Location, Location]


def throw_frozen():
    raise FrozenError("Can't alter finished schematic.")


class Schematic:
    def __init__(self):
        self._frozen = False
        self._definition: ModelDefinition = ModelDefinition()
        self.virtual_branches: list["VirtualBranch"] = []
        self.roots: list["TrueBranch"] = []

    @property
    def definition(self):
        return self._definition.copy()

    @definition.setter
    def definition(self, value):
        if self._frozen:
            raise FrozenError("Can't change definitions of finished schematic.")
        else:
            self._definition = value

    def create_location(self, location, coords, radii, labels, endpoint=None):
        if self._frozen:
            throw_frozen()
        bid, pid = location
        next_bid = len(self.virtual_branches)
        if bid == next_bid:
            branch = VirtualBranch()
            self.virtual_branches.append(branch)
        elif bid == next_bid - 1:
            branch = self.virtual_branches[bid]
        else:
            next_loc = (
                f"({next_bid - 1}.{len(self.virtual_branches[next_bid - 1].points)})"
            )
            raise ConstructionError(
                f"Locations need to be constructed in order. Can't construct "
                f"{location}, should construct {next_loc} or ({next_bid}.0)."
            ) from None
        if pid != len(branch.points):
            raise ConstructionError(
                f"Locations need to be constructed in order. Can't construct {location}"
                f", should have constructed ({bid}, {len(branch.points)}) next."
            ) from None
        point = branch.append(location, coords, radii, labels)
        if endpoint:
            parent = self.virtual_branches[endpoint[0]].points[endpoint[1]].branch
            point.branch.parent = parent
            parent.children.append(point.branch)
        elif pid == 0:
            self.roots.append(point.branch)

    def create_empty(self):
        if self._frozen:
            throw_frozen()
        self.virtual_branches.append(VirtualBranch())

    def set_param(self, location: Union[Location, Interval, str], param: "Parameter"):
        if isinstance(location, str):
            # Set label definition
            self.definition[location].set(param)
        else:
            raise NotImplementedError(
                "Location or interval parameters not implemented yet."
            )

    def freeze(self):
        if not self._frozen:
            self._flatten_branches(self.roots)
            self._frozen = True

    def _flatten_branches(self, branches):
        for branch in branches:
            branch.definition = self._makedef(branch.labels)
            try:
                branch.definition.assert_()
            except ValueError as e:
                if len(branch.points) == 1:
                    loc = branch.points[0].loc
                    locstr = f"location ({loc[0]}.{loc[1]})"
                else:
                    loc1 = branch.points[0].loc
                    loc2 = branch.points[-1].loc
                    locstr = f"interval ({loc1[0]}.{loc1[1]}-{loc2[1]})"

                if not branch.labels:
                    raise ValueError(
                        f"Unlabeled {locstr} is missing value for {e.args[1]}."
                    ) from None
                raise ValueError(
                    f"{locstr} labelled {errr.quotejoin(branch.labels)} misses value for "
                    f"{e.args[1]}"
                ) from None
            self._flatten_branches(branch.children)

    def _makedef(self, labels: typing.Sequence[str]) -> CableType:
        insert_index = [*self._definition._cable_types.keys()].index
        len_ = len(self._definition._cable_types)

        def label_order(lbl):
            try:
                insert = insert_index(lbl)
            except ValueError:
                insert = -1
            return (insert, lbl)

        return CableType.anchor(
            (
                self._definition._cable_types.get(label)
                for label in sorted(labels, key=label_order)
            ),
            synapses=self._definition.get_synapse_types(),
            use_defaults=self.definition.use_defaults,
        )

    def get_cable_types(self):
        return self._definition.get_cable_types()

    def get_synapse_types(self):
        return self._definition.get_synapse_types()


class Point:
    branch: "TrueBranch"

    def __init__(self, loc, branch, coords, radius):
        self.loc = loc
        self.coords = coords
        self.radius = radius
        self.branch = branch


class Branch:
    points: list[Point]

    def __init__(self):
        self.points = []

    def append(self, point):
        self.points.append(point)


class VirtualBranch(Branch):
    def append(self, loc, coords, radius, labels):
        if len(self.points):
            prev = self.points[-1]
            if prev.branch.labels == labels:
                branch = prev.branch
            else:
                branch = TrueBranch()
                branch.parent = prev.branch
                prev.branch.children.append(branch)
        else:
            branch = TrueBranch()
        branch.labels = labels.copy()
        point = Point(loc, branch, coords, radius)
        branch.points.append(point)
        super().append(point)
        return point


class TrueBranch(Branch):
    parent: Optional["TrueBranch"]
    children: list["TrueBranch"]
    labels: list[str]
    definition: CableType

    def __init__(self):
        super().__init__()
        self.parent = None
        self.children = []
