import dataclasses
import random
import typing
from typing import Mapping, Sequence, TYPE_CHECKING

import errr

from .._util import get_location_name, get_arclengths
from ..definitions import CableProperties, MechId, Mechanism, mechdict, Ion
from ..exceptions import TransmitterError, UnknownLocationError, UnknownSynapseError

if TYPE_CHECKING:
    from ..schematic import Location, Schematic
    from glia._glia import MechAccessor
    from patch.objects import PointProcess, Section, Segment


class NeuronModel:
    def __init__(self, sections, locations, cable_types):
        self._sections: Sequence["Section"] = sections
        self._locations: dict["Location", "LocationAccessor"] = locations
        self._cable_types = cable_types

    @property
    def sections(self) -> Sequence["Section"]:
        return self._sections

    @property
    def locations(self) -> Mapping["Location", "LocationAccessor"]:
        return self._locations

    def get_location(self, loc: "Location") -> "LocationAccessor":
        try:
            return self._locations[tuple(loc)]
        except KeyError:
            raise UnknownLocationError(
                f"No such location '%location%'.", self, loc
            ) from None

    def get_segment(self, loc: "Location", sx=0.5) -> "Segment":
        la = self.get_location(loc)
        return la.section(la.arc(sx))

    def filter_sections(self, labels: list[str]):
        return [s for s in self.sections if any(lbl in labels for lbl in s.labels)]

    def insert_synapse(
        self, label: typing.Union[str, "MechId"], loc: "Location", attributes=None, sx=0.5
    ) -> "PointProcess":
        import glia

        la = self.get_location(loc)
        synapses = la.section.synapse_types
        try:
            synapse = synapses[label]
        except KeyError:
            raise UnknownSynapseError(
                f"Synapse type '%synapse%' not present on branch with labels "
                f"{errr.quotejoin(la.section.labels)}. Choose from: "
                f"{errr.quotejoin(synapses)}",
                self,
                label,
            ) from None
        mech = glia.insert(la.section, *synapse.mech_id, x=la.arc(sx))
        mech.set(synapse.parameters)
        mech.synapse_name = label
        la.section.synapses.append(mech)

        return mech

    def insert_receiver(
        self,
        gid: int,
        label: typing.Union[str, "MechId"],
        loc: "Location",
        attributes=None,
        sx=0.5,
        source=None,
        **kwargs,
    ):
        from patch import p

        synapse = self.insert_synapse(label, loc, attributes, sx)
        if source is None:
            return p.ParallelCon(gid, synapse, **kwargs)
        else:
            spp = synapse._point_process
            p.parallel.target_var(spp, getattr(spp, "_ref_" + source), gid)

    def insert_transmitter(
        self, gid: int, loc: "Location", sx=0.5, source=None, **kwargs
    ):
        from patch import p

        la = self.get_location(loc)
        if source is None:
            if hasattr(la.section, "_transmitter"):
                if gid != la.section._transmitter.gid:
                    raise TransmitterError(
                        f"A transmitter already exists with gid {la.section._transmitter.gid}"
                    )
                return la.section._transmitter
            else:
                tm = p.ParallelCon(self.get_segment(loc, sx), gid, **kwargs)
                la.section._transmitter = tm
        else:
            if hasattr(la.section, "_source"):
                if gid != la.section._source_gid:
                    raise TransmitterError(
                        f"A source variable already exists with gid {la.section._source_gid}"
                    )
                tm = la.section._source
            else:
                source_var = self.get_segment(loc, sx)._ref_v
                tm = p.parallel.source_var(source_var, gid, sec=la.section.__neuron__())
                la.section._source = source_var
                la.section._source_gid = gid
        return tm

    def get_random_location(self):
        return random.choice([*self._locations.keys()])

    def __getattr__(self, item):
        if item in self._cable_types:
            return [s for s in self._sections if item in s.labels]
        else:
            return super().__getattribute__(item)


def neuron_build(schematic: "Schematic"):
    schematic.freeze()
    name = schematic.create_name()
    branchmap = {}
    sections = []
    locations = {}
    for branch in schematic:
        bname = f"{name}_{get_location_name(branch.points)}"
        alens = get_arclengths(branch.points)
        section, mechs = _build_branch(branch, bname)
        section.locations = [point.loc for point in branch.points]
        for i, point in enumerate(branch.points):
            try:
                arcpair = (alens[i], alens[i + 1])
            except IndexError:
                arcpair = (1, 1)
            locations[point.loc] = LocationAccessor(point.loc, section, mechs, arcpair)
        sections.append(section)
        branchmap[branch] = section
        if branch.parent:
            section.connect(branchmap[branch.parent])
    return NeuronModel(sections, locations, [*schematic.get_cable_types().keys()])


def _build_branch(branch, name):
    from patch import p

    section = p.Section(name=name)
    section.labels = [*branch.labels]
    section.synapses = []
    apply_geometry(section, branch.points)
    apply_cable_properties(section, branch.definition.cable)
    mechs = apply_mech_definitions(section, branch.definition.mechs)
    apply_ions(section, branch.definition.ions)
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


def apply_ions(section, ions: typing.Dict[str, "Ion"]):
    prop_map = {"rev_pot": "e{ion}", "int_con": "{ion}i", "ext_con": "{ion}o"}
    for ion_name, ion_props in ions.items():
        for field in dataclasses.fields(ion_props):
            setattr(
                section,
                prop_map[field.name].format(ion=ion_name),
                getattr(ion_props, field.name),
            )


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
    def __init__(self, loc, section, mechs, arcs):
        self._loc = loc
        self._section = section
        self._mechs = mechdict(mechs)
        self._arcs = arcs

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

    def arc(self, x=0):
        a0, a1 = self._arcs
        return (a1 - a0) * x + a0
