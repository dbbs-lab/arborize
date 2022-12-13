from errr.tree import make_tree as _make_tree, exception as _e
from typing import Type

_make_tree(
    globals(),
    ArborizeError=_e(
        ModelDefinitionError=_e(),
        SchematicError=_e(ConstructionError=_e(), FrozenError=_e()),
    ),
)

ArborizeError: Type[Exception]
ModelDefinitionError: Type[ArborizeError]
SchematicError: Type[ArborizeError]
ConstructionError: Type[SchematicError]
FrozenError: Type[SchematicError]
