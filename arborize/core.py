import os, sys
from contextlib import contextmanager
from .exceptions import *
import numpy as np

if not os.getenv('READTHEDOCS'):
    from patch import p
    from patch.objects import Section
    import glia as g
    from .synapse import Synapse
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
    def __init__(self, *pipeline):
        """
            Chain together multiple morphology files and/or builder functions.

            :param pipeline: Morphology file strings or builder functions.
            :type pipeline: vararg. str/function.
        """
        def outer_builder(model, *args, **kwargs):
            for part in pipeline:
                # Apply all builders in the pipeline sequence in order.
                builder = make_builder(part)
                builder.instantiate(model, *args, **kwargs)

        self.builder = outer_builder

class NeuronModel:
    """
        The base class that helps you describe your model. Generate all the required
        sections, insert all mechanisms and define all synapses using the appropriate
        class variables. See the :doc:`/neuron_model`
    """
    def __init__(self, position=None, morphology_id=0):
        # Check if morphologies were specified
        if not hasattr(self.__class__, "morphologies") or len(self.__class__.morphologies) == 0:
            raise ModelClassError("The NeuronModel class '{}' does not specify a non-empty array of morphologies".format(self.__class__.__name__))
        # Import the morphologies if they haven't been imported yet
        if not hasattr(self.__class__, "imported_morphologies"):
            self.__class__._import_morphologies()

        # Initialize variables
        self.position = np.array(position if not position is None else [0., 0., 0.])
        self.dendrites = []
        self.axon = []
        self.soma = []

        morphology_loader = self.__class__.imported_morphologies[morphology_id]
        # Use the Import3D/Builder to instantiate this cell.
        morphology_loader.instantiate(self)

        # Wrap the neuron sections in our own Section, if not done by the Builder
        self.soma = [s if isinstance(s, Section) else Section(p, s) for s in (self.soma or [])]
        self.dend = [s if isinstance(s, Section) else Section(p, s) for s in (self.dend or [])]
        self.axon = [s if isinstance(s, Section) else Section(p, s) for s in (self.axon or [])]
        self.dendrites = self.dend + self.dendrites
        del self.dend
        self.sections = self.soma + self.dendrites + self.axon
        for section in self.sections:
            section.synapses = []

        # Do labelling of sections into special sections
        self._apply_labels()

        # Check whether mechanisms should be chosen from a preferred package
        if hasattr(self.__class__, "glia_package"):
            self._package = self.__class__.glia_package
        else:
            self._package = None

        # Set up preferred glia context
        with g.context(pkg=self._package):
            # Initialize the labelled sections
            # This inserts all mechanisms
            for section in self.sections:
                self._init_section(section)

        # Call boot method so that child classes can easily do stuff after init.
        self.boot()

    def __getattr__(self, attribute):
        if attribute == "Vm":
            raise NotRecordingError("Trying to read Vm of a cell that is not recording." + " Use `.record_soma()` to enable recording of the soma.")

    @classmethod
    def _import_morphologies(cls):
        cls.imported_morphologies = []
        for morphology in cls.morphologies:
            builder = make_builder(morphology)
            cls.imported_morphologies.append(builder)

    def _apply_labels(self):
        for section in self.sections:
            if not hasattr(section, "labels"):
                section.labels = []
        for section in self.soma:
            section.labels.insert(0, "soma")
        for section in self.dendrites:
            section.labels.insert(0, "dendrites")
        for section in self.axon:
            section.labels.insert(0, "axon")

        # Apply special labels
        if hasattr(self.__class__, "labels"):
            for label, category in self.__class__.labels.items():
                targets = self.__dict__[category["from"]]
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


    def _init_section(self, section):
        section.cell = self
        # Set the amount of sections to some standard odd amount
        section.nseg = 1 + (2 * int(section.L / 40))
        for label in section.labels:
            if label not in self.__class__.section_types:
                raise LabelNotDefinedError("Label '{}' given to a section but not defined in {}".format(
                    label,
                    self.__class__.__name__
                ))
            self._init_section_label(section, label)
        if hasattr(section, "_arbz_resolved_mechanisms"):
            del section._arbz_resolved_mechanisms

    def _init_section_label(self, section, label):
        # Store a map of mechanisms to full mod_names for the attribute setter
        if not hasattr(section, "_arbz_resolved_mechanisms"):
            section._arbz_resolved_mechanisms = {}
        definition = self.__class__.section_types[label]
        # Insert the mechanisms
        for mechanism in definition["mechanisms"]:
            # Use Glia to resolve the mechanism selection.
            if isinstance(mechanism, tuple):
                # Mechanism defined as: `(mech_name, mech_variant)`
                mechanism_variant = mechanism[1]
                mechanism = mechanism[0]
                mod_name = g.resolve(mechanism, variant=mechanism_variant)
            else:
                # Mechanism defined as string
                mod_name = g.resolve(mechanism)
            # Map the mechanism to the mod name
            section._arbz_resolved_mechanisms[mechanism] = mod_name
            # Use Glia to insert the resolved mod.
            g.insert(section, mod_name)

        # Set the attributes on this section and its mechanisms
        for attribute, value in definition["attributes"].items():
            mechanism_notice = ""
            if isinstance(attribute, tuple):
                # `attribute` is an attribute of a specific mechanism and defined
                # as `(attribute, mechanism)`. This makes use of the fact that
                # NEURON provides shorthands to a mechanism's attribute as
                # `attribute_mechanism` instead of having to iterate over all
                # the segments and setting `mechanism.attribute` for each
                mechanism = attribute[1]
                mechanism_notice = " specified for '{}'".format(mechanism)
                if not mechanism in section._arbz_resolved_mechanisms:
                    raise MechanismNotPresentError("The attribute " + repr(attribute) + " specifies a mechanism '{}' that was not inserted in this section.".format(mechanism))
                mechanism_mod = section._arbz_resolved_mechanisms[mechanism]
                attribute_name = attribute[0] + "_" + mechanism_mod
            else:
                # `attribute` is an attribute of the section and is defined as string
                attribute_name = attribute
            # Check whether the value is callable, if so, pass it the section diameter
            # and update the local variable to the return value. This allows parameters to
            # depend on the diameter of the section.
            if callable(value):
                value = value(section.diam)
            # Use setattr to set the obtained attribute information. __dict__
            # does not work as NEURON's Python interface is incomplete.
            try:
                setattr(section.__neuron__(), attribute_name, value)
            except AttributeError as e:
                raise SectionAttributeError("The attribute '{}'{} is not found on a section labelled '{}' in the {}.".format(
                    attribute_name,
                    mechanism_notice,
                    ",".join(section.labels),
                    self.__class__.__name__
                )) from None

        # Copy the synapse definitions to this section
        if "synapses" in definition:
            if not hasattr(section, "available_synapse_types"):
                section.available_synapse_types = []
            section.available_synapse_types.extend(definition["synapses"].copy())

    def boot(self):
        pass

    def set_reference_id(self, id):
        '''
            Add an id that can be used as reference for outside software.
        '''
        self.ref_id = id

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
        to_section.synapses.append(synapse)
        from_section.connect_points(synapse._point_process)
        return synapse

    def record_soma(self):
        """
            Create a recording vector for the soma and store it under ``self.Vm``
        """
        self.Vm = self.soma[0].record()
        return self.Vm

    def create_transmitter(self, section, gid):
        """
            Create a parallel simulation spike transmitter on a section of this cell.
            Transmitters fire spikes when the treshold reaches -20mV and broadcast a
            SpikeEvent to all nodes with the specified GID.

            :param section: The section to insert the transmitter on. Each section can only have 1 transmitter
            :param gid: The global identifier of this transmitter. With this number receivers can subscribe to this transmitter's SpikeEvents
        """
        if not hasattr(section, "_transmitter"):
            section._transmitter = p.ParallelCon(section, gid, output=True)
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
            section._receivers = {}
        # Create the requested synapse if it does not exist on the Section yet.
        if synapse_type not in section._receivers:
            section._receivers[synapse_type] = {
                "synapse": self.create_synapse(section, synapse_type),
                "receivers": {},
            }
        synapse_receiver = section._receivers[synapse_type]
        receivers = synapse_receiver["receivers"]
        if gid not in receivers:
            # If this synapse is not receiving from this GID yet, add a ParallelCon for it
            receivers[gid] = p.ParallelCon(gid, synapse_receiver["synapse"]._point_process)
        return receivers[gid]

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
                synapse_definition = synapse_types[section_synapses[0]]
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
        return Synapse(self, section, synapse_point_process, synapse_attributes, variant=synapse_variant)

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
    return {k: v for k, v in section._receivers.items() if k in types}

def get_section_receiver(section, type):
    """
        Collect the section's receiver description matching the given type.

        :param section: Section to inspect.
        :type section: :class:`Section <patch.objects.Section>`
        :param type: Synapse type to look for.
        :type type: str
    """
    r = get_section_receivers(section, [type])
    return r[0] if len(r) else None

def get_section_synapses(section, types=None):
    """
        Collect the section's synapses matching the given types.

        :param section: Section to inspect.
        :type section: :class:`Section <patch.objects.Section>`
        :param types: Synapse types to look for.
        :type types: str
    """
    return {type: receiver["synapse"] for type, receiver in get_section_receivers(section, types).items()}

def get_section_synapse(section, type):
    """
        Collect the section's synapse matching the given type.

        :param section: Section to inspect.
        :type section: :class:`Section <patch.objects.Section>`
        :param type: Synapse type to look for.
        :type type: str
    """
    s = get_section_synapses(section, [type])
    return s[0] if len(s) else None

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
    from . import _morphology_dirs
    for dir in _morphology_dirs:
        file = os.path.join(dir, morphology)
        if not os.path.isfile(file):
            continue
        loader = p.Import3d_Neurolucida3()
        with _suppress_stdout():
            loader.input(file)
        loaded_morphology = p.Import3d_GUI(loader, 0)
        return loaded_morphology
    raise FileNotFoundError("Can't find '{}', use arborize.add_directory to add a morphology directory.".format(morphology))

def import3d(file, model):
    """
        Perform NEURON's Import3D and import ``file`` 3D data into the model.
    """
    loaded_morphology = NeuronModel._import3d_load(file)
    loaded_morphology.instantiate(model)


def make_builder(blueprint):
    """
        Turn a blueprint (morphology string, builder function or tuple of the former)
        into a Builder.
    """
    if type(blueprint) is str:
        # Use Import3D as builder.
        return _import3d_load(blueprint)
    if callable(blueprint):
        # If a function is given as morphology, treat it as a builder function
        return Builder(blueprint)
    elif isinstance(blueprint, staticmethod):
        # If a static method is given as morphology, treat it as a builder function
        return Builder(blueprint.__func__)
    elif (
        hasattr(type(blueprint), "__len__")
        and hasattr(type(blueprint), "__getitem__")
    ):
        # If it is a sequence, construct a ComboBuilder that sequentially applies the builders.
        return ComboBuilder(*blueprint)
    else:
        raise MorphologyBuilderException("Invalid blueprint data: provide a builder function or a path string to a morphology file.")

__all__ = ["NeuronModel", "get_section_synapses", "get_section_synapse", "get_section_receivers", "get_section_receiver"]
