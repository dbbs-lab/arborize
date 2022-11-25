import dataclasses
import typing

if typing.TYPE_CHECKING:
    from .parameter import Parameter

MechId = typing.Union[str, tuple[str, str], tuple[str, str, str]]


class Copy:
    def copy(self):
        other = type(self)()
        for field in dataclasses.fields(self):
            setattr(other, field.name, getattr(self, field.name))
        return other


@dataclasses.dataclass
class CableProperties(Copy):
    Ra: float = None
    """
    Axial resistivity in ohm/cm
    """

    def merge(self, other):
        for field in dataclasses.fields(self):
            value = getattr(other, field.name)
            if value is not None:
                setattr(self, field.name, value)

    def copy(self):
        other = type(self)()
        for field in dataclasses.fields(self):
            setattr(other, field.name, getattr(self, field.name))
        return other

    def assert_(self):
        for field in dataclasses.fields(self):
            if getattr(self, field.name, None) is None:
                raise ValueError(f"Missing '{field.name}' value.", field.name)


@dataclasses.dataclass
class Ion(Copy):
    e: float


class Mechanism:
    parameters: dict[str, float]

    def __init__(self, parameters):
        self.parameters = parameters

    def merge(self, other):
        for key, value in other.parameters.items():
            self.parameters[key] = value

    def copy(self):
        return type(self)(self.parameters.copy())


def is_mech_id(mech_id):
    return str(mech_id) == mech_id or (
        tuple(mech_id) == mech_id
        and 0 < len(mech_id) < 4
        and all(str(part) == part for part in mech_id)
    )


class CableType:
    cable: CableProperties
    mechs: dict["MechId", "Mechanism"]
    ions: dict[str, Ion]

    def __init__(self):
        self.cable = CableProperties()
        self.mechs = {}
        self.ions = {}

    def copy(self):
        def_ = CableType()
        def_.cable = self.cable.copy()
        def_.mechs = {k: v.copy() for k, v in self.mechs.items()}
        return def_

    def set(self, param: "Parameter"):
        if hasattr(param, "set_cable_params"):
            param.set_cable_params(self.cable)
        if hasattr(param, "set_mech_params"):
            param.set_mech_params(self.mechs)

    @staticmethod
    def anchor(
        defs: typing.Iterable["CableType"], use_defaults: bool = False
    ) -> "CableType":
        def_ = CableType() if not use_defaults else CableType.default()
        for def_right in defs:
            if def_right is None:
                continue
            def_.merge(def_right)
        return def_

    def merge(self, def_right: "CableType"):
        self.cable.merge(def_right.cable)
        for key, mech in def_right.mechs.items():
            if key in self.mechs:
                self.mechs[key].merge(def_right.mechs[key])
            else:
                self.mechs[key] = mech.copy()

    def assert_(self):
        self.cable.assert_()

    @classmethod
    def default(cls):
        default = cls()
        default.cable.Ra = 35.4
        return default

    def add_ion(self, key: str, ion: Ion):
        if key in self.ions:
            raise KeyError(f"An ion named '{key}' already exists.")
        self.ions[key] = ion

    def add_mech(self, mech_id: "MechId", mech: Mechanism):
        if not is_mech_id(mech_id):
            raise ValueError(f"'{mech_id}' is not a valid mechanism id.")
        if mech_id in self.mechs:
            raise KeyError(f"A mechanism with id '{mech_id}' already exists.")
        self.mechs[mech_id] = mech


class ModelDefinition:
    def __init__(self, use_defaults=False):
        self._cable_types: dict[str, CableType] = {}
        self._synapse_types: mechdict[MechId, Mechanism] = mechdict()
        self.use_defaults = use_defaults

    def copy(self):
        model = ModelDefinition(self.use_defaults)
        for label, def_ in self._cable_types.items():
            model.add_cable_type(label, def_.copy())
        for label, def_ in self._synapse_types.items():
            model.add_synapse_type(label, def_)
        return model

    def get_cable_types(self):
        return {k: v.copy() for k, v in self._cable_types.items()}

    def get_synapse_types(self):
        return {k: v.copy() for k, v in self._synapse_types.items()}

    def add_cable_type(self, label: str, def_: CableType):
        if label in self._cable_types:
            raise KeyError(f"Cable type {label} already exists.")
        self._cable_types[label] = def_

    def add_synapse_type(self, mech_id: "MechId", synapse: "Mechanism"):
        if not is_mech_id(mech_id):
            raise ValueError(f"'{mech_id}' is not a valid synapse mechanism id.")
        if mech_id in self._synapse_types:
            raise KeyError(f"Synapse type {mech_id} already exists.")
        self._synapse_types[mech_id] = synapse


def define_model(templ_or_def, def_dict=None, /, use_defaults=False):
    if def_dict is None:
        model = _parse_dict_def(templ_or_def)
    else:
        model = templ_or_def.copy()
        model.merge(_parse_dict_def(def_dict))
    model.use_defaults = use_defaults
    return model


def _parse_dict_def(def_dict):
    model = ModelDefinition()
    for label, def_input in def_dict.get("cable_types", {}).items():
        ct = _parse_cable_type(def_input)
        model.add_cable_type(label, ct)
    for label, def_input in def_dict.get("synapse_types", {}).items():
        st = _parse_mech_def(def_input)
        model.add_synapse_type(label, st)
    return model


def _parse_cable_type(def_input):
    def_ = CableType()
    for k, v in def_input.get("cable", {}).items():
        setattr(def_.cable, k, v)
    for k, v in def_input.get("ions", {}).items():
        def_.add_ion(k, _parse_ion_def(v))
    for mech_id, v in def_input.get("mechanisms", {}).items():
        def_.add_mech(mech_id, _parse_mech_def(v))
    return def_


def _parse_ion_def(ion_dict):
    return Ion(**ion_dict)


def _parse_mech_def(mech_dict):
    mech = Mechanism(mech_dict.copy())
    return mech


class mechdict(dict):
    def __getitem__(self, item):
        return super().__getitem__((item,) if isinstance(item, str) else item)

    def __setitem__(self, key, value):
        return super().__setitem__((key,) if isinstance(key, str) else key, value)
