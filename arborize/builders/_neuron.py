import dataclasses
from collections import deque
from typing import Mapping, Sequence, TYPE_CHECKING, Union
from ..definitions import CableProperties, MechId, Mechanism, mechdict

if TYPE_CHECKING:
    from ..schematic import Location, Schematic, TrueBranch
    from glia._glia import MechAccessor


class NeuronModel:
    def __init__(self, sections, locations, synapse_types):
        self._sections: Sequence["Section"] = sections
        self._locations: dict["Location", "Section"] = locations
        self._synapse_types: mechdict["MechId", "Mechanism"] = synapse_types

    @property
    def sections(self) -> Sequence["Section"]:
        return self._sections

    @property
    def locations(self) -> Mapping["Location", "LocationAccessor"]:
        return self._locations

    def insert_receiver(self, synapse: "MechId", loc: "Location", attributes=None):
        import glia

        mech_def = self._synapse_types.get(synapse)
        la = self._locations.get(loc)
        mech = glia.insert(la.section, *synapse)
        mech.set(mech_def.parameters)

        return mech


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
    return NeuronModel(sections, locations, schematic.get_synapse_types())


def _build_branch(branch):
    from patch import p

    section = p.Section()
    section.labels = [*branch.labels]
    apply_geometry(section, branch.points)
    apply_cable_properties(section, branch.definition.cable)
    mechs = apply_mech_definitions(section, branch.definition.mechs)
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
