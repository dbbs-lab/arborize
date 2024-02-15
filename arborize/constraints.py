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
    define_model,
)


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
    pass


ConstraintsDefinitionDict = typing.TypedDict(
    "ConstraintsDefinitionDict",
    {
        "cable_types": dict[str, CableTypeConstraintsDict],
        "synapse_types": dict[MechId, SynapseConstraintsDict],
    },
    total=False,
)


def define_constraints(constraints: ConstraintsDefinitionDict) -> ConstraintsDefinition:
    return typing.cast(
        ConstraintsDefinition,
        define_model(typing.cast(ModelDefinitionDict, constraints)),
    )
