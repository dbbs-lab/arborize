import dataclasses
import typing
from .exceptions import ModelDefinitionError

if typing.TYPE_CHECKING:
    from .parameter import Parameter

MechIdTuple = typing.Union[tuple[str], tuple[str, str], tuple[str, str, str]]
MechId = typing.Union[str, MechIdTuple]


@dataclasses.dataclass
class Copy:
    def copy(self):
        other = type(self)()
        for field in dataclasses.fields(self):
            setattr(other, field.name, getattr(self, field.name))
        return other


@dataclasses.dataclass
class Merge:
    def merge(self, other):
        for field in dataclasses.fields(self):
            value = getattr(other, field.name)
            if value is not None:
                setattr(self, field.name, value)


@dataclasses.dataclass
class Assert:
    def assert_(self):
        for field in dataclasses.fields(self):
            if getattr(self, field.name, None) is None:
                raise ValueError(f"Missing '{field.name}' value.", field.name)


@dataclasses.dataclass
class CableProperties(Copy, Merge, Assert):
    Ra: float = None
    cm: float = None
    """
    Axial resistivity in ohm/cm
    """

    def copy(self):
        other = type(self)()
        for field in dataclasses.fields(self):
            setattr(other, field.name, getattr(self, field.name))
        return other


CablePropertiesDict = typing.TypedDict(
    "CablePropertiesDict",
    {"Ra": float, "cm": float},
    total=False,
)


@dataclasses.dataclass
class Ion(Copy, Merge, Assert):
    rev_pot: float = None
    int_con: float = None
    ext_con: float = None


IonDict = typing.TypedDict(
    "IonDict",
    {"rev_pot": float, "int_con": float, "ext_con": float},
    total=False,
)


class Mechanism:
    def __init__(self, parameters: dict[str, float]):
        self.parameters = parameters

    def merge(self, other):
        for key, value in other.parameters.items():
            self.parameters[key] = value

    def copy(self):
        return Mechanism(self.parameters.copy())


class Synapse(Mechanism):
    mech_id: MechIdTuple

    def __init__(self, parameters, mech_id: MechId):
        super().__init__(parameters)
        self.mech_id = to_mech_id(mech_id)

    def copy(self):
        return Synapse(self.parameters.copy(), to_mech_id(self.mech_id))


SynapseDict = typing.Union[
    dict[str, float],
    typing.TypedDict(
        "SynapseDict",
        {"mechanism": MechId, "parameters": dict[str, float]},
        total=False,
    ),
]


def is_mech_id(mech_id):
    return str(mech_id) == mech_id or (
        tuple(mech_id) == mech_id
        and 0 < len(mech_id) < 4
        and all(str(part) == part for part in mech_id)
    )


def to_mech_id(mech_id: MechId) -> MechIdTuple:
    if mech_id is None:
        raise ValueError("Mech id may not be None")
    return (mech_id,) if not isinstance(mech_id, tuple) else tuple(mech_id)


class CableType:
    cable: CableProperties
    mechs: dict[MechId, Mechanism]
    ions: dict[str, Ion]
    synapses: dict[str, Synapse]

    def __init__(self):
        self.cable = CableProperties()
        self.mechs = {}
        self.ions = {}
        self.synapses = {}

    def copy(self):
        def_ = CableType()
        def_.cable = self.cable.copy()
        def_.ions = {k: v.copy() for k, v in self.ions.items()}
        def_.mechs = {k: v.copy() for k, v in self.mechs.items()}
        def_.synapses = {k: v.copy() for k, v in self.synapses.items()}
        return def_

    def set(self, param: "Parameter"):
        if hasattr(param, "set_cable_params"):
            param.set_cable_params(self.cable)
        if hasattr(param, "set_mech_params"):
            param.set_mech_params(self.mechs)

    @staticmethod
    def anchor(
        defs: typing.Iterable["CableType"],
        synapses: dict[str, Synapse] = None,
        use_defaults: bool = False,
    ) -> "CableType":
        def_ = CableType() if not use_defaults else CableType.default()
        if synapses is not None:
            # We need to merge the local synapses on top of the global ones,
            # without mutating the global dictionary. So we:
            # - Create a new cable type for the global synapses
            globaldef = CableType()
            # - Add the synapses to it
            for key, value in synapses.items():
                globaldef.add_synapse(key, value)
            # - Merge the local synapses over it
            globaldef._mergedict(globaldef.synapses, def_.synapses)
            # - Transfer the result to our def.
            def_.synapses = globaldef.synapses
        # Merge the definitions onto our def. Each merge overwrites our values, with the
        # last item in the list having the final say.
        for def_right in defs:
            if def_right is None:
                continue
            def_.merge(def_right)
        return def_

    def merge(self, def_right: "CableType"):
        self.cable.merge(def_right.cable)
        self._mergedict(self.ions, def_right.ions)
        self._mergedict(self.mechs, def_right.mechs)
        self._mergedict(self.synapses, def_right.synapses)

    def _mergedict(self, dself, dother):
        for key, value in dother.items():
            if key in dself:
                dself[key].merge(dother[key])
            else:
                dself[key] = value.copy()

    def assert_(self):
        self.cable.assert_()
        for ion_name, ion in self.ions.items():
            try:
                ion.assert_()
            except ValueError as e:
                raise ValueError(
                    f"Missing '{e.args[1]}' value in ion '{ion_name}'",
                    ion_name,
                    e.args[1],
                ) from None

    @classmethod
    def default(cls):
        default = cls()
        default.cable.Ra = 35.4
        default.cable.cm = 1
        default.ions = default_ions_dict()
        return default

    def add_ion(self, key: str, ion: Ion):
        if key in self.ions:
            raise KeyError(f"An ion named '{key}' already exists.")
        self.ions[key] = ion

    def add_mech(self, mech_id: MechId, mech: Mechanism):
        if not is_mech_id(mech_id):
            raise ValueError(f"'{mech_id}' is not a valid mechanism id.")
        if mech_id in self.mechs:
            raise KeyError(f"A mechanism with id '{mech_id}' already exists.")
        self.mechs[mech_id] = mech

    def add_synapse(self, label: typing.Union[str, MechId], synapse: Synapse):
        mech_id = synapse.mech_id or to_mech_id(label)
        if not is_mech_id(mech_id):
            raise ValueError(f"'{mech_id}' is not a valid mechanism id.")
        if label in self.synapses:
            raise KeyError(f"A synapse with label '{label}' already exists.")
        self.synapses[label] = synapse


CableTypeDict = typing.TypedDict(
    "CableTypeDict",
    {
        "cable": CablePropertiesDict,
        "mechanisms": dict[MechId, dict[str, float]],
        "ions": dict[str, IonDict],
        "synapses": dict[str, SynapseDict],
    },
    total=False,
)


class default_ions_dict(dict):
    def __init__(self):
        super().__init__()
        self._defaults = {
            "na": Ion(rev_pot=50.0, int_con=10.0, ext_con=140.0),
            "k": Ion(rev_pot=-77.0, int_con=54.4, ext_con=2.5),
            "ca": Ion(rev_pot=132.4579341637009, int_con=5e-05, ext_con=2.0),
            "h": Ion(rev_pot=0.0, int_con=1.0, ext_con=1.0),
        }

    def __setitem__(self, key, ion):
        if key not in self:
            value = self._defaults[key].copy()
            # Do a criss-cross merge to merge defaults into the original ion object
            value.merge(ion)
            ion.merge(value)
        super().__setitem__(key, ion)


class ModelDefinition:
    def __init__(self, use_defaults=False):
        self._cable_types: dict[str, CableType] = {}
        self._synapse_types: dict[str, Synapse] = {}
        self.use_defaults = use_defaults

    def copy(self):
        model = ModelDefinition(self.use_defaults)
        for label, def_ in self._cable_types.items():
            model.add_cable_type(label, def_.copy())
        for label, def_ in self._synapse_types.items():
            model.add_synapse_type(label, def_)
        return model

    def get_cable_types(self) -> dict[str, CableType]:
        return {k: v.copy() for k, v in self._cable_types.items()}

    def get_synapse_types(self) -> dict[str, Synapse]:
        return {k: v.copy() for k, v in self._synapse_types.items()}

    def add_cable_type(self, label: str, def_: CableType):
        if label in self._cable_types:
            raise KeyError(f"Cable type {label} already exists.")
        self._cable_types[label] = def_

    def add_synapse_type(self, label: typing.Union[str, MechId], synapse: Synapse):
        mech_id = synapse.mech_id or to_mech_id(label)
        if not is_mech_id(mech_id):
            raise ValueError(f"'{mech_id}' is not a valid synapse mechanism.")
        if label in self._synapse_types:
            raise KeyError(f"Synapse type {label} already exists.")
        self._synapse_types[label] = synapse


ModelDefinitionDict = typing.TypedDict(
    "ModelDefinitionDict",
    {"cable_types": dict[str, CableTypeDict], "synapse_types": dict[str, SynapseDict]},
    total=False,
)


@typing.overload
def define_model(
    template: ModelDefinition,
    definition: ModelDefinitionDict,
    /,
    use_defaults: bool = ...,
): ...


@typing.overload
def define_model(definition: ModelDefinitionDict, /, use_defaults: bool = ...): ...


def define_model(templ_or_def, def_dict=None, /, use_defaults=False):
    if def_dict is None:
        model = _parse_dict_def(templ_or_def)
    else:
        model = templ_or_def.copy()
        model.merge(_parse_dict_def(def_dict))
    model.use_defaults = use_defaults
    return model


def _parse_dict_def(def_dict: ModelDefinitionDict):
    model = ModelDefinition()
    for label, def_input in def_dict.get("cable_types", {}).items():
        ct = _parse_cable_type(def_input)
        model.add_cable_type(label, ct)
    for label, def_input in def_dict.get("synapse_types", {}).items():
        st = _parse_synapse_def(label, def_input)
        model.add_synapse_type(label, st)
    return model


def _parse_cable_type(cable_dict: CableTypeDict):
    try:
        def_ = CableType()
        for k, v in cable_dict.get("cable", {}).items():
            setattr(def_.cable, k, v)
        for k, v in cable_dict.get("ions", {}).items():
            parsed = _parse_ion_def(v)
            def_.add_ion(k, parsed)
        for mech_id, v in cable_dict.get("mechanisms", {}).items():
            def_.add_mech(mech_id, _parse_mech_def(v))
        for label, v in cable_dict.get("synapses", {}).items():
            def_.add_synapse(label, _parse_synapse_def(label, v))
        return def_
    except Exception:
        raise ModelDefinitionError(
            f"{cable_dict} is not a valid cable type definition."
        )


def _parse_ion_def(ion_dict: IonDict):
    try:
        return Ion(**ion_dict)
    except Exception:
        raise ModelDefinitionError(f"{ion_dict} is not a valid ion definition.")


def _parse_mech_def(mech_dict: dict[str, float]):
    try:
        mech = Mechanism(mech_dict.copy())
        return mech
    except Exception:
        raise ModelDefinitionError(f"{mech_dict} is not a valid mechanism definition.")


def _parse_synapse_def(key, synapse_dict: SynapseDict):
    try:
        synapse = Synapse(
            synapse_dict.get("parameters", synapse_dict).copy(),
            synapse_dict.get("mechanism", key),
        )
        return synapse
    except Exception:
        raise ModelDefinitionError(f"{synapse_dict} is not a valid synapse definition.")


class mechdict(dict):
    def __getitem__(self, item):
        return super().__getitem__((item,) if isinstance(item, str) else item)

    def __setitem__(self, key, value):
        return super().__setitem__((key,) if isinstance(key, str) else key, value)
