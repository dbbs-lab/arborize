import dataclasses
import typing

from ._util import MechId
from .definitions import (
    CableProperties,
    CableType,
    Definition,
    Ion,
    Mechanism,
    ModelDefinitionDict,
    Synapse,
    _parse_dict_def,
    define_model,
)
import itertools


@dataclasses.dataclass
class Constraint:
    lower: float
    upper: float

    @classmethod
    def from_value(cls, value: "ConstraintValue") -> "Constraint":
        if isinstance(value, Constraint):
            return value
        elif isinstance(value, (list, tuple)):
            return cls(value[0], value[1])
        else:
            return cls(value, value)

    def add_tolerance(self, tolerance=None):
        if tolerance is not None:
            self.lower *= 1 - tolerance
            self.upper *= 1 + tolerance
        return self


ConstraintValue = typing.Union[
    Constraint, float, tuple[float, float], list[float, float]
]


class CablePropertyConstraints(CableProperties):
    Ra: Constraint
    """
    Axial resistivity in ohm/cm
    """
    cm: Constraint
    """
    Membrane conductance
    """


CablePropertyConstraintsDict = typing.TypedDict(
    "CablePropertyConstraintsDict",
    {"Ra": ConstraintValue, "cm": ConstraintValue},
    total=False,
)


class IonConstraints(Ion):
    rev_pot: Constraint
    int_con: Constraint
    ext_con: Constraint


IonConstraintsDict = typing.TypedDict(
    "IonConstraintsDict",
    {
        "rev_pot": ConstraintValue,
        "int_con": ConstraintValue,
        "ext_con": ConstraintValue,
    },
    total=False,
)


class MechanismConstraints(Mechanism):
    parameters: dict[str, Constraint]


class SynapseConstraints(MechanismConstraints, Synapse):
    pass


SynapseConstraintsDict = typing.Union[
    dict[str, ConstraintValue],
    typing.TypedDict(
        "SynapseConstraintsDict",
        {"mechanism": MechId, "parameters": dict[str, ConstraintValue]},
        total=False,
    ),
]


class CableTypeConstraints(CableType):
    cable: CablePropertyConstraints
    mechs: dict[MechId, MechanismConstraints]
    ions: dict[str, IonConstraints]
    synapses: dict[str, SynapseConstraints]


CableTypeConstraintsDict = typing.TypedDict(
    "CableTypeConstraintsDict",
    {
        "cable": CablePropertyConstraintsDict,
        "mechanisms": dict[MechId, dict[str, ConstraintValue]],
        "ions": dict[str, IonConstraintsDict],
        "synapses": dict[str, SynapseConstraintsDict],
    },
    total=False,
)


class ConstraintsDefinition(Definition[CableTypeConstraints, SynapseConstraints]):
    def convert_to_constraints(self, tolerance=None):
        for syn in self._synapse_types.values():
            syn.parameters = {
                k: Constraint.from_value(v).add_tolerance(tolerance)
                for k, v in syn.parameters.items()
            }

        for ct in self._cable_types.values():
            for field in dataclasses.fields(ct.cable):
                _convert_field(ct.cable, field, tolerance)
            for ion in ct.ions.values():
                for field in dataclasses.fields(ion):
                    _convert_field(ion, field, tolerance)
            for mech in itertools.chain(ct.mechs.values(), ct.synapses.values()):
                mech.parameters = {
                    k: Constraint.from_value(v).add_tolerance(tolerance)
                    for k, v in mech.parameters.items()
                }


def _convert_field(obj, field, tolerance):
    constraint = Constraint.from_value(getattr(obj, field.name))
    constraint.add_tolerance(tolerance)
    setattr(obj, field.name, constraint)


ConstraintsDefinitionDict = typing.TypedDict(
    "ConstraintsDefinitionDict",
    {
        "cable_types": dict[str, CableTypeConstraintsDict],
        "synapse_types": dict[MechId, SynapseConstraintsDict],
    },
    total=False,
)


def define_constraints(
    constraints: ConstraintsDefinitionDict, tolerance=None
) -> ConstraintsDefinition:
    constraints = _parse_dict_def(ConstraintsDefinition, constraints)
    constraints.convert_to_constraints(tolerance)
    return constraints
