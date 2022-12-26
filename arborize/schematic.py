import typing
from collections import deque
from typing import Optional, Union, Iterable

from ._util import get_location_name
from .exceptions import ConstructionError, FrozenError

from .definitions import CableType, ModelDefinition

import errr

if typing.TYPE_CHECKING:
    from .parameter import Parameter

Location = tuple[int, int]
Interval = tuple[Location, Location]


def throw_frozen():
    raise FrozenError("Can't alter finished schematic.")


def _random_name():
    import random
    import string

    return "".join(random.choices(string.ascii_uppercase, k=10))


class Schematic:
    def __init__(self, name=None):
        self._name = name
        self._frozen = False
        self._definition: ModelDefinition = ModelDefinition()
        self.virtual_branches: list["VirtualBranch"] = []
        self.roots: list["TrueBranch"] = []
        self._named = 0

    def __iter__(self) -> typing.Iterator["TrueBranch"]:
        stack: deque["TrueBranch"] = deque(self.roots)
        while True:
            try:
                branch = stack.pop()
            except IndexError:
                break
            yield branch
            if branch.children:
                stack.extend(reversed(branch.children))

    def __len__(self):
        return len([*iter(self)])

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if self._frozen:
            raise FrozenError("Can't change name of finished schematic.")
        else:
            self._name = value

    @property
    def definition(self):
        return self._definition.copy()

    @definition.setter
    def definition(self, value):
        if self._frozen:
            raise FrozenError("Can't change definitions of finished schematic.")
        else:
            self._definition = value

    def create_name(self):
        if not self._frozen:
            raise FrozenError("Schematic must be finished before naming instances of it.")
        self._named += 1
        return f"{self._name}_{self._named}"

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
            self._name = self._name if self._name is not None else _random_name()
            self._frozen = True

    def _flatten_branches(self, branches: Iterable["TrueBranch"]):
        for branch in branches:
            branch.definition = self._makedef(branch.labels)
            try:
                branch.definition.assert_()
            except ValueError as e:
                locstr = get_location_name(branch.points)
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
