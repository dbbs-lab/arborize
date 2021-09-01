__all__ = ["NeuronModel", "get_section_synapses", "get_section_receivers", "make_builder", "compose_types", "flatten_composite"]

import os, sys, errr
from contextlib import contextmanager
from .exceptions import *
import numpy as np

if not os.getenv('READTHEDOCS'):
    from patch import p, transform
    from patch.objects import Section
    import glia as g
    from .synapse import Synapse
    import glia.exceptions
    p.load_file('stdlib.hoc')
    p.load_file('import3d.hoc')

class Builder:
    """
        Builders are method interfaces used to build cell models. They are responsible for
        adding and/or labelling sections on the model object during initialization.

        A builder should define an ``instantiate`` method that is passed the model under
        construction.

        This base Builder class can be instantiated with a function to which the model
        under construction is delegated.

        Constructing your own Builders is of limited use, because every model's
        ``morphologies`` field makes Builders out of functions or morphology files:

        .. code-block:: python

            class MyNeuron(NeuronModel):
                @staticmethod
                def build(model, *args, **kwargs):
                    model.soma.append(p.Section())
                    model.dendrites.append(p.Section())
                    model.axon.append(p.Section())

                # Creates 2 different morphologies for this cell model.
                morphologies = [
                    build, # Create 1 soma, dendrite & axonal compartment
                    ('morfo2.swc', self.extend_axon) # First loads morfo2.swc, then run the `extend_axon` method.
                ]
    """
    def __init__(self, builder):
        self.builder = builder

    def instantiate(self, model, *args, **kwargs):
        self.builder(model, *args, **kwargs)

class ComboBuilder(Builder):
    """
        Chains together multiple morphology files and/or builder functions.
    """
    def __init__(self, *pipeline, path=None):
        """
            Chain together multiple morphology files and/or builder functions.

            :param pipeline: Morphology file strings or builder functions.
            :type pipeline: vararg. str/function.
            :param path: Root path that all non absolute path strings will be combined with.
            :type path: string
        """
        builder_pipe = [make_builder(part, path=path) for part in pipeline]
        def outer_builder(model, *args, **kwargs):
            # Apply all builders in the pipeline sequence in order.
            for builder in builder_pipe:
                builder.instantiate(model, *args, **kwargs)

        self.builder = outer_builder

class NeuronModel:
    """
        The base class that helps you describe your model. Generate all the required
        sections, insert all mechanisms and define all synapses using the appropriate
        class variables. See the :doc:`/neuron_model`
    """
    def __init__(self, position=None, morphology=0, candidate=0, synapses=0):
        if self.__class__._abstract:
            raise NotImplementedError(f"Can't instantiate abstract NeuronModel {self.__class__.__name__}")
        # Initialize variables
        self.position = np.array(position if not position is None else [0., 0., 0.])
        self.dendrites = []
        self.axon = []
        self.soma = []

        morphology_loader = self.__class__.imported_morphologies[morphology]
        # Use the Import3D/Builder to instantiate this cell.
        morphology_loader.instantiate(self)
        self._wrap_sections()
        self._collect_sections()
        self._apply_base_labels()

        # Check builder metadata for additional instructions and strip it.
        builder_meta = getattr(self, "builder_meta", None)
        if builder_meta is not None:
            delattr(self, "builder_meta")
            if "taglist" in builder_meta:
                translations = getattr(type(self), "tag_translations", {})
                self._translate_tags(translations, builder_meta["taglist"])
        # Do labelling of sections into special sections
        self._apply_labels()

        # Set up preferred glia context
        with g.context(pkg=self.glia_package):
            # Initialize the labelled sections
            # This inserts all mechanisms
            for section in self.sections:
                self._init_section(section)

        # Call boot method so that child classes can easily do stuff after init.
        self.boot()

    def _wrap_sections(self):
        # Wrap the neuron sections in our own Section, if not done by the Builder
        self.soma = [s if isinstance(s, Section) else Section(p, s) for s in getattr(self, "soma", [])]
        self.dend = [s if isinstance(s, Section) else Section(p, s) for s in getattr(self, "dend", [])]
        self.axon = [s if isinstance(s, Section) else Section(p, s) for s in getattr(self, "axon", [])]

    def _collect_sections(self):
        self.dendrites = self.dend + self.dendrites
        del self.dend
        self.sections = self.soma + self.dendrites + self.axon
        # Unwrap back into a set of neuron sections to check identity
        nrnsec = set(map(transform, self.sections))
        l = len(self.sections)
        self.sections.extend(Section(p, s) for s in self.all if s not in nrnsec)
        self._nrn_section_map = dict(zip(map(transform, self.sections), self.sections))
        for section in self.sections:
            self._prep_section(section)

    def _prep_section(self, section):
        section._synapses = []
        section.synapses = section._synapses

    def __init_subclass__(cls, abstract=False, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._abstract = abstract
        if not abstract:
            cls._init_morphologies()
        if not hasattr(cls, "section_types"):
            cls.section_types = {}
        for default_type in ["soma", "dendrites", "axon"]:
            if default_type not in cls.section_types:
                cls.section_types[default_type] = {}
        if not hasattr(cls, "glia_package"):
            cls.glia_package = None

    @classmethod
    def _init_morphologies(cls):
        # Check if morphologies were specified
        if not hasattr(cls, "morphologies") or len(cls.morphologies) == 0:
            raise ModelClassError("The NeuronModel class '{}' does not specify a non-empty array of morphologies".format(cls.__name__))
        # Import the morphologies if they haven't been imported yet
        if not hasattr(cls, "imported_morphologies"):
            cls._import_morphologies()

    def __getattr__(self, attribute):
        if attribute == "Vm":
            raise NotRecordingError("Trying to read Vm of a cell that is not recording." + " Use `.record_soma()` to enable recording of the soma.")
        if attribute in self.section_types:
            return [s for s in self.sections if attribute in s.labels]
        return super().__getattribute__(attribute)

    @classmethod
    def _import_morphologies(cls):
        m_dir = getattr(cls, "morphology_directory", cls._get_default_morphology_dir())
        cls.morphology_directory = os.path.abspath(m_dir)
        cls.imported_morphologies = []
        for morphology in cls.morphologies:
            builder = cls.make_builder(morphology, path=m_dir)
            cls.imported_morphologies.append(builder)

    @classmethod
    def _get_default_morphology_dir(cls):
        import os, inspect

        try:
            return os.path.abspath(os.path.join(inspect.getfile(cls), "morphologies"))
        except:
            return os.getcwd()

    def _apply_base_labels(self):
        """Add the `soma`, `dendrites` and `axon` labels"""
        for section in self.sections:
            if not hasattr(section, "labels"):
                section.labels = []
        for section in self.soma:
            section.labels.insert(0, "soma")
        for section in self.dendrites:
            section.labels.insert(0, "dendrites")
        for section in self.axon:
            section.labels.insert(0, "axon")

    def _apply_labels(self):
        """Apply special labels according to `diam`, `id` or `tag` rules."""
        if hasattr(self.__class__, "labels"):
            for label, category in self.__class__.labels.items():
                parent = category.get("from", "sections")
                try:
                    targets = getattr(self, parent)
                except AttributeError:
                    raise LabelNotDefinedError(
                        f"`{label}` can't find category parent `{parent}`"
                    ) from None
                if "id" in category:
                    l = category["id"]
                    for id, target in enumerate(targets):
                        if l(id):
                            target.labels.append(label)
                elif "diam" in category:
                    l = category["diam"]
                    for id, target in enumerate(targets):
                        if l(target.diam):
                            target.labels.append(label)
                elif "tag" in category:
                    pass


    def _translate_tags(self, translations, tags):
        """
        Translate builder provided metadata into additional labels using a
        translation list from the model class. e.g. translating SWC tags into
        multiple labels.
        """
        for i, section in enumerate(map(self._nrn_section_map.get, self.all)):
            tag = tags[i]
            labels = translations.get(tag, [])
            section.labels.extend(labels)


    def _init_section(self, section):
        section.cell = self
        # Set the amount of sections to some standard odd amount
        section.nseg = 1 + (2 * int(section.L / 40))
        # Store a map of mechanisms to full mod_names for the attribute setter
        for label in section.labels:
            if label not in self.__class__.section_types:
                raise LabelNotDefinedError("Label '{}' given to a section but not defined in {}".format(
                    label,
                    self.__class__.__name__
                ))
            self._init_section_label(section, label)

    def _init_section_label(self, section, label):
        definition = self.__class__.section_types[label]
        if isinstance(definition, CompositeType):
            # Ignore CompositeType, in NEURON we can overpaint to compose.
            definition = definition._self
        self._apply_section_cable(section, definition.get("cable", {}))
        self._apply_section_mechanisms(section, definition.get("mechanisms", {}))
        self._apply_section_ions(section, definition.get("ions", {}))
        self._apply_section_synapses(section, definition.get("synapses", []))

    def _apply_section_mechanisms(self, section, mechanisms):
        # Insert the mechanisms
        for mechanism, attrs in mechanisms.items():
            try:
                # Use Glia to resolve the mechanism selection.
                if isinstance(mechanism, tuple):
                    # Mechanism defined as: `(mech_name, mech_variant [, package])`
                    name = mechanism[0]
                    variant = mechanism[1]
                    select = {"variant": variant}
                    if len(mechanism) == 3:
                        select["pkg"] = mechanism[2]
                    mod_name = g.resolve(name, **select)
                else:
                    # Mechanism defined as string
                    name = mechanism
                    variant = "0"
                    mod_name = g.resolve(mechanism)
            except glia.exceptions.NoMatchesError as e:
                e = MechanismNotFoundError("Could not find '{}.{}' in the glia library".format(name, variant), name, variant)
                raise e from None
            # Use Glia to insert the resolved mod.
            g.insert(section, mod_name)
            try:
                self._apply_mech_attributes(section, mod_name, attrs or {})
            except SectionAttributeError as e:
                errr.wrap(SectionAttributeError, e, prepend="No mechanisms were inserted! ")

    def _apply_mech_attributes(self, section, mod_name, attributes):
        # Set the attributes on this section and its mechanisms
        for attribute, value in attributes.items():
            # Check whether the value is callable, if so, pass it the section diameter
            # and update the local variable to the return value. This allows parameters to
            # depend on the diameter of the section.
            if callable(value):
                value = value(section.diam)
            try:
                setattr(section.__neuron__(), f"{attribute}_{mod_name}", value)
            except AttributeError as e:
                raise SectionAttributeError("The attribute '{}'{} is not found on a section with labels {}.".format(
                    attribute,
                    f"specified for {mod_name} ",
                    ", ".join("'{}'".format(l) for l in section.labels)
                ), attribute, section.labels) from None

    def _apply_section_cable(self, section, cable):
        for cable_prop, value in cable.items():
            setattr(section.__neuron__(), cable_prop, value)

    def _apply_section_ions(self, section, ions):
        prop = {"e": "e{}", "int": "{}i", "ext": "{}e"}
        for ion_name, ion_props in ions.items():
            for prop_name, value in ion_props.items():
                try:
                    prop_attr = prop[prop_name].format(ion_name)
                except KeyError as e:
                    raise IonAttributeError(f"Unknown ion attribute '{prop_name}'.") from None
                setattr(section.__neuron__(), prop_attr, value)

    def _apply_section_synapses(self, section, synapses):
        if not hasattr(section, "available_synapse_types"):
            section.available_synapse_types = []
        section.available_synapse_types.extend(synapses.copy())

    def boot(self):
        pass

    def set_reference_id(self, id):
        '''
            Add an id that can be used as reference for outside software.
        '''
        self.ref_id = id

    def get_reference_id(self, id):
        '''
            Return the reference id.
        '''
        return self.ref_id

    def connect(self, from_cell, from_section, to_section, synapse_type=None):
        '''
            Connect this cell as the postsynaptic cell in a connection with
            `from_cell` between the `from_section` and `to_section`.
            Additionally a `synapse_type` can be specified if there's multiple
            synapse types present on the postsynaptic section.

            :param from_cell: The presynaptic cell.
            :type from_cell: :class:`.NeuronModel`
            :param from_section: The presynaptic section.
            :type from_section: :class:`.Section`
            :param to_section: The postsynaptic section.
            :type to_section: :class:`.Section`
            :param synapse_type: The name of the synapse type.
            :type synapse_type: string
        '''

        synapse = self.create_synapse(to_section, synapse_type=synapse_type)
        to_section._synapses.append(synapse)
        from_section.connect_points(synapse._point_process)
        return synapse

    def record_soma(self):
        """
            Create a recording vector for the soma and store it under ``self.Vm``
        """
        self.Vm = self.soma[0].record()
        return self.Vm

    def create_transmitter(self, section, gid, source_var=None):
        """
            Create a parallel simulation spike transmitter on a section of this cell.
            Transmitters fire spikes when the treshold reaches -20mV and broadcast a
            SpikeEvent to all nodes with the specified GID.

            :param section: The section to insert the transmitter on. Each section can only have 1 transmitter
            :param gid: The global identifier of this transmitter. With this number receivers can subscribe to this transmitter's SpikeEvents
        """
        if not hasattr(section, "_transmitter"):
            section._transmitter = {
                "gid": gid,
                "connector": p.ParallelCon(section, gid, output=True),
            }
        if source_var is not None and "source" not in section._transmitter:
            p.parallel.source_var(section(0.5)._ref_v, gid, sec=section.__neuron__())
            section._transmitter["source"] = section(0.5)._ref_v
        return section._transmitter

    def create_receiver(self, section, gid, synapse_type):
        """
            Create a parallel simulation spike receiver on a synapse on a section of this
            cell. Receivers link parallel SpikeEvents with a certain GID to a synapse.
            Each synapse can listen to any amount of GID's. Each section can only contain
            1 synapse of each type.

            :param section: The section to insert the transmitter on. Each section can only have 1 transmitter
            :param gid: The global identifier of this transmitter. With this number receivers can subscribe to this transmitter's SpikeEvents
            :param synapse_type: Name of the synapse. It needs to be a valid name defined on the section.
        """
        if not hasattr(section, "_receivers"):
            section._receivers = []
        synapse = self.create_synapse(section, synapse_type)
        receiver_dict = {
            "type": synapse_type,
            "synapse": synapse,
            "gid": gid
        }
        if synapse.source is not None:
            p.parallel.target_var(getattr(synapse._point_process, "_ref_" + synapse.source), gid)
            receiver_dict["source"] = synapse.source
        else:
            parallel_con = p.ParallelCon(gid, synapse._point_process)
            receiver_dict["receiver"] = parallel_con
        section._receivers.append(receiver_dict)
        return receiver_dict

    def create_synapse(self, section, synapse_type=None):
        '''
            Create a synapse in the specified ``section`` based on the synapse definitions
            present on this model. Additionally a `synapse_type` can be specified if
            there's multiple synapse types present on the section.

            :param section: The postsynaptic section.
            :type section: :class:`.Section`
            :param synapse_type: The name of the synapse type.
            :type synapse_type: string
        '''
        labels = section.labels
        labels_name = ",".join(labels)
        if not hasattr(self.__class__, "synapse_types"):
            raise ModelClassError("Can't connect to a NeuronModel that does not specify any `synapse_types` on its class.")
        synapse_types = self.__class__.synapse_types
        if not hasattr(section, "available_synapse_types") or not section.available_synapse_types:
            raise ConnectionError("Can't connect to '{}' labelled section without available synapse types.".format(labels_name))
        section_synapses = section.available_synapse_types

        if synapse_type is None:
            if len(section_synapses) != 1:
                raise AmbiguousSynapseError("Too many possible synapse types: " + ", ".join(section_synapses) + ". Specify a `synapse_type` for the connection.")
            else:
                synapse_type = section_synapses[0]
                synapse_definition = synapse_types[synapse_type]
        else:
            if not synapse_type in section_synapses:
                raise SynapseNotPresentError("The synapse type '{}' is not present on '{}' labelled section in {}.".format(synapse_type, labels_name, self.__class__.__name__))
            elif not synapse_type in synapse_types:
                raise SynapseNotDefinedError("The synapse type '{}' is used on '{}' labelled section but not defined in the model.".format(synapse_type, labels_name))
            else:
                synapse_definition = synapse_types[synapse_type]

        synapse_attributes = synapse_definition["attributes"] if "attributes" in synapse_definition else {}
        synapse_point_process = synapse_definition["point_process"]
        synapse_variant = None
        if isinstance(synapse_point_process, tuple):
            synapse_variant = synapse_point_process[1]
            synapse_point_process = synapse_point_process[0]
        source = synapse_definition.get("source", None)
        synapse = Synapse(self, section, synapse_point_process, synapse_attributes, variant=synapse_variant, type=synapse_type, source=source)
        if not hasattr(section, "_synapses"):
            section._synapses = []
        section._synapses.append(synapse)
        return synapse

    @classmethod
    def make_builder(cls, morphology, path=None):
        return make_builder(morphology, path=path or cls.morphology_directory)

    @classmethod
    def cable_cell(cls, morphology=0, Vm=-40, K=305.15):
        try:
            import arbor
        except ImportError:
            raise ImportError("`arbor` unavailable, can't make arbor models.")

        if not isinstance(cls.morphologies[morphology], str):
            raise NotImplementedError("Can't use builders for cable cells, must import from file. Please export your morphology builder to an SWC or ASC file and update `cls.morphologies`.")
        path = os.path.join(cls.morphology_directory, cls.morphologies[morphology])
        morph, labels = _try_arb_morpho(path)
        _cc_insert_labels(labels, getattr(cls, "labels", {}))
        composites = _arb_resolve_composites(cls.section_types, labels)
        decor = arbor.decor()
        decor.set_property(Vm=Vm, tempK=K)

        #policy = arbor.cv_policy_max_extent(40.0)
        #for l in labels:
        #  policy = policy | arbor.cv_policy_max_extent(40.0, f'"{l}"')

        dflt_policy = arbor.cv_policy_max_extent(40.0)
        soma_policy = arbor.cv_policy_fixed_per_branch(1, '(tag 1)')
        policy = dflt_policy | soma_policy
        decor.discretization(policy)

        for label, definition in composites.items():
            _cc_all(
                decor,
                label,
                definition
            )
        return arbor.cable_cell(morph, labels, decor)


def _try_mech_presence(mech, resolved):
    # Look for a full match, this also covers the
    if mech in resolved:
        return resolved[mech]
    # Look for a name only match to a mod specified as a tuple
    specifics = [v for m, v in resolved.items() if isinstance(m, tuple) and m[0] == mech]
    if len(specifics) == 1:
        return specifics[0]
    elif len(specifics) > 1:
        raise SectionAttributeError(f"Section attributes were specified for `{mech}` but this could apply to: " + ", ".join(specifics))

def _try_arb_morpho(path):
    import arbor
    try:
        morfo = arbor.load_swc_arbor(path)
        labels = arbor.label_dict({})
    except:
        try:
            m = arbor.load_asc(path)
        except:
            raise IOError(f"Can't load '{path}' as an SWC or ASC morphology.")
        morfo, labels = m.morphology, m.labels
    return morfo, labels


def _cc_all(decor, label, definition):
    _cc_insert_cable(decor, label, definition.get("cable", {}))
    _cc_insert_ions(decor, label, definition.get("ions", {}))
    _cc_insert_mechs(decor, label, definition.get("mechanisms", {}))
    # _cc_insert_synapses(decor, label, definition.get("synapses", []))

# Kv1_5: uses 'no' ion

def _cc_insert_mechs(decor, label, mechs):
    import arbor
    i = 0
    for mech_name, mech_attrs in mechs.items():
        if isinstance(mech_name, tuple):
            mech_name = "_".join(mech_name)
        mech = arbor.mechanism(mech_name, mech_attrs or {})
        decor.paint(f'"{label}"', mech)
        i += 1


def _arb_resolve_composites(definitions, label_dict):
    # For each conp, copy the parent definitions, then empty the parents and
    # create virtual intersections that exclude the child composites to
    # avoid overpainting
    resolved = {t: v for t, v in definitions.items() if isinstance(v, dict)}
    comps = {t: v for t, v in definitions.items() if t not in resolved}
    parents = {}
    for name, comp in comps.items():
        try:
            comp._parents = l = []
            for p in comp._parent_types:
                l.append(resolved[p].copy())
        except KeyError:
            if p in comps:
                raise NotImplementedError("Can't make composites of composites yet.")
            raise Exception(f"Unknown section type '{p}' in composite type '{name}'.") from None
        for parent in comp._parent_types:
            parents.setdefault(parent, []).append(name)

    for parent, children in parents.items():
        # The original parent shouldn't paint anything, we make a new parent
        # with all of the children regions excluded that does the restricted
        # painting.
        virtual = f"{parent}(excl:{','.join(children)})"
        resolved[virtual] = resolved[parent]
        cstr = " ".join(f'(region "{c}")' for c in children)
        if len(children) > 1:
            cstr = f"(join {cstr})"
        label_dict[virtual] = f'(difference (region "{parent}") {cstr})'
        resolved[parent] = {}

    # Merge the parent types and the child on top.
    for name, comp in comps.items():
        resolved[name] = _cc_def_merge(*comp._parents, comp._self)

    return resolved


def _cc_def_merge(*dicts):
    carry = dict()
    merger = iter(dicts)
    while (m := next(merger, None)) is not None:
        carry = _deep_merge(carry, m)
    return carry

def _deep_merge(a, b):
    if isinstance(a, dict):
        c = a.copy()
        for k, v in b.items():
            if k in a:
                c[k] = _deep_merge(a[k], v)
            elif hasattr(v, "copy"):
                c[k] = v.copy()
            else:
                c[k] = v
    elif isinstance(a, list):
        c = list(set(a) + set(b))
    else:
        if hasattr(b, "copy"):
            c = b.copy()
        else:
            c = b
    return c

def _cc_insert_labels(label_dict, labels):
    # ASC parser returns broken label_dict, so don't use `in` until
    # https://github.com/arbor-sim/arbor/pull/1541 is merged.
    # if "dendrites" not in label_dict and "dend" in label_dict:
    try:
        label_dict["dendrites"] = '(region "dend")'
    except (RuntimeError, KeyError):
        # KeyErrors thrown as RuntimeError, see
        # https://github.com/arbor-sim/arbor/issues/1550
        pass
    for label, def_ in labels.items():
        if "arbor" in def_:
            label_dict[label] = def_["arbor"]


_cc_ion_prop_map = {
    "e": "rev_pot"
}
_cc_cable_prop_map = {
    "Ra": ("rL", lambda Ra: Ra), "cm": ("cm", lambda cm: cm / 100),
}


def _cc_insert_ions(decor, label, ions):
    for ion, def_ in ions.items():
        kwargs = {_cc_ion_prop_map.get(d): v for d, v in def_.items()}
        decor.set_ion(ion, **kwargs)


def _cc_insert_cable(decor, label, cable):
    kwargs = {(p := _cc_cable_prop_map.get(c))[0]: p[1](v) for c, v in cable.items()}
    decor.paint(f'(region "{label}")', **kwargs)


def get_section_receivers(section, types=None):
    """
        Collect a dictionary of the section's receiver descriptions matching the given
        types.

        :param section: Section to inspect.
        :type section: :class:`Section <patch.objects.Section>`
        :param types: List of names of the synapse types to look for. Collects all types if omitted.
        :type types: list
    """
    if not hasattr(section, "_receivers"):
        return {}
    if types is None:
        return section._receivers
    return [v for v in section._receivers if v["type"] in types]

def get_section_synapses(section, types=None):
    """
        Collect the section's synapses matching the given types.

        :param section: Section to inspect.
        :type section: :class:`Section <patch.objects.Section>`
        :param types: Synapse types to look for.
        :type types: str
    """
    if not hasattr(section, "_synapses"):
        return []
    if types is None:
        return section._synapses
    return [v for v in section._synapses if v._type in types]

@contextmanager
def _suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def _import3d_load(morphology):
    if not os.path.isfile(morphology):
        raise FileNotFoundError(f"'{morphology}' can't be found. Provide a correct absolute path in the `morphologies` array or add a `morphology_directory` class attribute to your NeuronModel.")
    with _suppress_stdout():
        # Placeholder for the exact SWC tags
        sec2tag = None
        # Can't EAFP due to https://github.com/neuronsimulator/nrn/issues/1311
        # so we check the extension and hope it matches the content format.
        if morphology.endswith("swc"):
            loader = p.Import3d_SWC_read()
        else:
            loader = p.Import3d_Neurolucida3()
        try:
            loader.input(morphology)
            loaded_morphology = p.Import3d_GUI(loader, 0)
            try:
                ids = list(loader.id)
            except:
                pass
            else:
                # Scrape NEURON internals for the exact SWC tag on each section
                ids = list(loader.id)
                pts = list(loader.id2pt(id) for id in ids)
                tags = list(loader.type.x)
                sec2tag = dict()
                for pt, tag in zip(map(int, pts), tags):
                    sec = loader.point2sec[pt]
                    sec2tag.setdefault(sec, tag)
        except RuntimeError as e:
            raise MorphologyBuilderError(f"Couldn't parse '{morphology}': {e}") from None
    return loaded_morphology, sec2tag


def make_builder(blueprint, path=None):
    """
        Turn a blueprint (morphology string, builder function or tuple of the former)
        into a Builder.
    """
    if type(blueprint) is str:
        if not os.path.isabs(blueprint):
            if path is None:
                raise MorphologyBuilderError("Morphology filestrings have to be absolute paths or a `path` keyword argument must be provided.")
            else:
                blueprint = os.path.join(path, blueprint)
        # Use Import3D as builder
        builder, tags = _import3d_load(blueprint)
        if tags is not None:
            def set_meta(model):
                model.builder_meta = m = getattr(model, "builder_meta", dict())
                m.setdefault("taglist", dict()).update(tags)

            builder = ComboBuilder(builder.instantiate, set_meta)
        return builder
    if callable(blueprint):
        # If a function is given as morphology, treat it as a builder function
        return Builder(blueprint)
    elif isinstance(blueprint, staticmethod):
        # If a static method is given as morphology, treat it as a builder function
        return Builder(blueprint.__func__)
    elif hasattr(type(blueprint), "__iter__"):
        # If it is iterable, construct a ComboBuilder that sequentially applies the builders.
        return ComboBuilder(*iter(blueprint), path=path)
    else:
        raise MorphologyBuilderError("Invalid blueprint data: provide a builder function or a path string to a morphology file.")


class CompositeType:
    def __init__(self, *types):
        self._parent_types = [t for t in types if isinstance(t, str)]
        try:
            self._self = [t for t in types if isinstance(t, dict)][0].copy()
        except IndexError:
            self._self = {}

    def __copy__(self):
        return self.copy()

    def copy(self):
        return CompositeType(*self._parent_types, self._self)

def compose_types(*args):
    return CompositeType(*args)

def flatten_composite(model, comp):
    if not isinstance(comp, CompositeType):
        return comp
    return _cc_def_merge(*map(model.section_types.get, comp._parent_types), comp._self)
