import time
import typing
from collections import defaultdict

import bluepyopt.ephys as ephys
import glia

from ..builders import neuron_build

if typing.TYPE_CHECKING:
    from .. import ModelDefinition, Schematic


class ArborizeMorphology(ephys.morphologies.Morphology):
    def __init__(self, schematic: "Schematic"):
        super().__init__()
        self._schematic = schematic

    def instantiate(self, sim, icell):
        self._start = time.time()
        arborized_cell = neuron_build(self._schematic)
        for label in self._schematic.get_cable_types().keys():
            section_list = getattr(icell, label)
            for sec in arborized_cell.filter_sections([label]):
                section_list.append(sec.__neuron__())

    def destroy(self, sim=None):
        """Destroy morphology instantiation"""
        print("Presumably sim took:", round(time.time() - self._start), "seconds")


def get_bpo_cell(schematic, constraints, name_cell="cell"):
    morph = ArborizeMorphology(schematic)
    mechs, params, locations = load_mechs_params(constraints)
    return ephys.models.CellModel(
        name_cell, morph, mechs, params, secarray_names=[], seclist_names=locations
    )


def load_mechs_params(constraints: "ModelDefinition"):
    cable_types = constraints.get_cable_types()

    bpy_seclists = {
        label: ephys.locations.NrnSeclistLocation(label, seclist_name=label)
        for label in cable_types.keys()
    }

    mech_locations = defaultdict(list)
    for label, cable_type in cable_types.items():
        for mech in cable_type.mechs:
            mech_locations[mech].append(bpy_seclists[label])

    bpy_mechs = [
        ephys.mechanisms.NrnMODMechanism(
            name=glia.resolve(mech), prefix=glia.resolve(mech), locations=locations
        )
        for mech, locations in mech_locations.items()
    ]

    bpy_params = [
        ephys.parameters.NrnSectionParameter(
            name=f"{param}_{glia.resolve(mech_id)}_{label}",
            param_name=f"{param}_{glia.resolve(mech_id)}",
            locations=[bpy_seclists[label]],
            frozen=not isinstance(constraint, list),
            bounds=constraint if isinstance(constraint, list) else None,
            value=constraint if not isinstance(constraint, list) else None,
        )
        for label, cable_type in cable_types.items()
        for mech_id, mech in cable_type.mechs.items()
        for param, constraint in mech.parameters.items()
    ]
    for p in bpy_params:
        print("name: ", p.name)
        print("frozen: ", p.frozen)
        print("bounds: ", p.bounds)

    # # todo: params: cable [frozen=true]
    #
    # # todo: params: ions [frozen=True]
    # for i_ion, ion_i in enumerate(constraints.get_cable_types()[sec_i].ions.keys()):
    #     param_name = "%s_%s" % (ion_i, sec_i)
    #     value = constraints.get_cable_types()[sec_i].ions[ion_i].rev_pot
    #     params[param_name] = ephys.parameters.NrnSectionParameter(
    #         name=param_name,
    #         param_name=param_name,
    #         value=value,
    #         locations=[locations[sec_i]],
    #         frozen=True,
    #     )

    return bpy_mechs, bpy_params, [*bpy_seclists.keys()]
