import re
import typing
from collections import defaultdict

import bluepyopt.ephys as ephys
import glia

from ..builders import neuron_build
from ..constraints import Constraint, ConstraintsDefinition, ConstraintValue

if typing.TYPE_CHECKING:
    from ..schematic import Schematic


class ArborizeMorphology(ephys.morphologies.Morphology):
    def __init__(self, schematic: "Schematic", debug=None):
        super().__init__()
        self._schematic = schematic
        self._debug = debug

    def instantiate(self, sim, icell):
        arborized_cell = neuron_build(self._schematic)
        for label in self._schematic.get_compound_cable_types().keys():
            section_list = getattr(icell, label)
            labels = [l.replace("__", "_") for l in re.split("(?<!_)_(?!_)", label)]
            for sec in arborized_cell.get_sections_with_all_labels(labels):
                section_list.append(sec.__neuron__())

    def destroy(self, sim=None):
        pass


def get_bpo_cell(schematic, name_cell="cell", debug=None):
    morph = ArborizeMorphology(schematic, debug=debug)
    schematic.freeze()
    constraints = schematic.definition
    if not isinstance(constraints, ConstraintsDefinition):
        raise TypeError(
            f"Optimization schematic must contain constraints, got {type(constraints)} instead."
        )
    cable_types = schematic.get_compound_cable_types()

    bpyopt_seclists = {
        label: ephys.locations.NrnSeclistLocation(label, seclist_name=label)
        for label in cable_types.keys()
    }

    mech_locations = defaultdict(list)
    for label, cable_type in cable_types.items():
        for mech in cable_type.mechs:
            mech_locations[mech].append(bpyopt_seclists[label])

    bpyopt_mechs = [
        ephys.mechanisms.NrnMODMechanism(
            name=glia.resolve(mech), prefix=glia.resolve(mech), locations=locations
        )
        for mech, locations in mech_locations.items()
    ]

    bpyopt_cable_params = [
        ephys.parameters.NrnSectionParameter(
            name=f"{label}_{prop}",
            param_name=prop,
            locations=[bpyopt_seclists[label]],
            **_to_bpyopt_kwargs(constraint, f"{label}_{prop}"),
        )
        for label, cable_type in cable_types.items()
        for prop, constraint in cable_type.cable
    ]

    bpyopt_mech_params = [
        ephys.parameters.NrnSectionParameter(
            name=f"{param}_{glia.resolve(mech_id)}_{label}",
            param_name=f"{param}_{glia.resolve(mech_id)}",
            locations=[bpyopt_seclists[label]],
            **_to_bpyopt_kwargs(constraint, ""),
        )
        for label, cable_type in cable_types.items()
        for mech_id, mech in cable_type.mechs.items()
        for param, constraint in mech.parameters.items()
    ]

    bpyopt_params = [
        ephys.parameters.NrnGlobalParameter(
            "temperature", param_name="celsius", value=32, frozen=True
        ),
        *bpyopt_mech_params,
        *bpyopt_cable_params,
    ]

    return ephys.models.CellModel(
        name_cell,
        morph,
        bpyopt_mechs,
        bpyopt_params,
        secarray_names=[],
        seclist_names=[*bpyopt_seclists.keys()],
    )


def load_mechs_params(constraints: "ConstraintsDefinition"):

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

    return bpyopt_mechs, bpyopt_params, [*bpyopt_seclists.keys()]


def _to_bpyopt_kwargs(constraint: "Constraint", label: str):
    frozen = constraint.upper == constraint.lower
    if label == "axon_Ra":
        constraint.upper = 100
    elif label == "axon_cm":
        constraint.upper = 1
    return dict(
        frozen=frozen,
        bounds=[constraint.lower, constraint.upper] if not frozen else None,
        value=constraint.upper if frozen else None,
    )
