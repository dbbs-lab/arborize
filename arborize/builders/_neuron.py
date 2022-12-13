import dataclasses
import random
import typing
from collections import deque
from typing import Mapping, Sequence, TYPE_CHECKING, Union

import errr

from ..definitions import CableProperties, MechId, Mechanism, mechdict, to_mech_id
from ..exceptions import ConstructionError

if TYPE_CHECKING:
    from ..schematic import Location, Schematic, TrueBranch
    from glia._glia import MechAccessor


class NeuronModel:
    def __init__(self, sections, locations, cable_types):
        self._sections: Sequence["Section"] = sections
        self._locations: dict["Location", "Section"] = locations
        self._cable_types = cable_types

    @property
    def sections(self) -> Sequence["Section"]:
        return self._sections

    @property
    def locations(self) -> Mapping["Location", "LocationAccessor"]:
        return self._locations

    def insert_synapse(
            self, label: typing.Union[str, "MechId"], loc: "Location", attributes=None
    ):
        import glia

        la = self._locations[loc]
        synapses = la.section.synapse_types
        try:
            synapse = synapses[label]
        except KeyError:
            raise ConstructionError(
                f"Synapse type '{label}' not present on branch with labels "
                f"{errr.quotejoin(la.section.labels)}. Choose from: "
                f"{errr.quotejoin(synapses)}"
            )
        mech = glia.insert(la.section, *synapse.mech_id)
        mech.set(synapse.parameters)

        return mech

    def get_random_location(self):
        return random.choice([*self._locations.keys()])

    def __getattr__(self, item):
        if item in self._cable_types:
            return [s for s in self._sections if item in s.labels]
        else:
            return super().__getattribute__(item)


def neuron_build(schematic: "Schematic"):
    schematic.freeze()
    branchmap = {}
    stack: deque[tuple["TrueBranch", Union["TrueBranch", None]]] = deque(
        (branch, None) for branch in schematic.roots
    )
    sections = []
    locations = {}
    while True:
        try:
            branch, parent = stack.pop()
        except IndexError:
            break
        section, mechs = _build_branch(branch)
        for point in branch.points:
            locations[point.loc] = LocationAccessor(point.loc, section, mechs)
        sections.append(section)
        branchmap[branch] = section
        if branch.parent:
            section.connect(branchmap[branch.parent])
        if branch.children:
            stack.extend((child, branch) for child in reversed(branch.children))
    return NeuronModel(sections, locations, [*schematic.get_cable_types().keys()])


def _build_branch(branch):
    from patch import p

    section = p.Section()
    section.labels = [*branch.labels]
    apply_geometry(section, branch.points)
    apply_cable_properties(section, branch.definition.cable)
    mechs = apply_mech_definitions(section, branch.definition.mechs)
    section.synapse_types = branch.definition.synapses
    return section, mechs


def apply_geometry(section, points):
    coords = []
    diams = []
    for point in points:
        coords.append(point.coords)
        diams.append(point.radius * 2)
    section.add_3d(coords, diams)
    section.nseg = int((section.L // 10) + 1)


def apply_cable_properties(section, cable_props: "CableProperties"):
    for field in dataclasses.fields(cable_props):
        setattr(section, field.name, getattr(cable_props, field.name))


def apply_mech_definitions(section, mech_defs: dict["MechId", "Mechanism"]):
    import glia

    mechs = {}
    for mech_id, mech_def in mech_defs.items():
        if isinstance(mech_id, str):
            mech_id = (mech_id,)
        mech = glia.insert(section, *mech_id)
        mech.set(mech_def.parameters)
        mechs[mech_id] = mech

    return mechs


class LocationAccessor:
    def __init__(self, loc, section, mechs):
        self._loc = loc
        self._section = section
        self._mechs = mechdict(mechs)

    def set_parameter(self, *args, **kwargs):
        """
        Not implemented yet.
        """
        raise NotImplementedError(
            "Parameters cannot be changed yet after cell construction."
        )

    @property
    def section(self):
        return self._section

    @property
    def mechanisms(self) -> Mapping["MechId", "MechAccessor"]:
        return self._mechs
