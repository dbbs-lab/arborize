from errr.tree import make_tree as _make_tree, exception as _e
from typing import Type

_make_tree(
    globals(),
    ArborizeError=_e(
        ModelDefinitionError=_e("definition"),
        ModelError=_e(
            "model",
            TransmitterError=_e("section"),
            UnknownLocationError=_e("location"),
            UnknownSynapseError=_e("synapse"),
        ),
        SchematicError=_e("schematic", ConstructionError=_e(), FrozenError=_e()),
    ),
)

ArborizeError: Type[Exception]
ModelDefinitionError: Type[ArborizeError]
ModelError: Type[ArborizeError]
TransmitterError: Type[ModelError]
UnknownLocationError: Type[ModelError]
UnknownSynapseError: Type[ModelError]
SchematicError: Type[ArborizeError]
ConstructionError: Type[SchematicError]
FrozenError: Type[SchematicError]
