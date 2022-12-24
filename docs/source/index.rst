.. Arborize documentation master file, created by
   sphinx-quickstart on Tue Jan 28 23:16:34 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Table of contents
=================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Welcome to Arborize's documentation!
====================================

Arborize lets you describe your model definitions, import schematics from multile sources
and build equivalent multicompartmental models on the supported backends (Arbor and
NEURON).

Defining a model
----------------

Model definitions consist of :guilabel:`cable_types` and :guilabel:`synapse_types`. Cable
types define the cable and ionic properties of the types of compartments in the model,
such as the soma, axon and dendrites, and which biophysical mechanisms should be present.
Synapse types define the properties of the synapses that can be inserted.

.. code-block::

   {
      "cable_types": {...},
      "synapse_types": {...}
   }

You then pass this dictionary style definition to the :func:`~arborize.define_model`
function:

.. code-block:: python

   from arborize import define_model

   definition = define_model({
      "cable_types": {...},
      "synapse_types": {...},
   })

A *definition* can then be combined with a *schematic* by a *builder* to create
instances of your model.

Cable types
~~~~~~~~~~~

Each cable type has a name. A cable type definition consists of :guilabel:`cable`, :guilabel:`ions`,
:guilabel:`mechanisms`, and :guilabel:`synapses`. During the schematic consutrction
multiple cable types can be applied to a single piece of cable in the model.

.. code-block::

   {
      "cable_types": {
         "soma": {
            "cable": {...},
            "ions": {...},
            "mechanisms": {...},
            "synapses": {...}
         }
      }
   }

Cable properties
++++++++++++++++

* ``Ra``: Axial resistivity (ohm/cm)

.. code-block::

   {
      "cable": {
         "Ra": 0.34
      }
   }

Ion properties
++++++++++++++

The :guilabel:`ions` block can contain any key, representing the ion name, conventionally
lowercase, and each can set the following properties:

* ``e``: Reversal potential

.. code-block::

   {
      "ions": {
         "h": {"e": 0},
         "ca": {"e": 30},
      }
   }

Mechanisms
++++++++++

Mechanisms are defined by their mechanism ID, which is either a string name, or a tuple
of up to 3 strings: ``name``, ``variant``, and ``package``; and a set of parameters.

.. code-block::

   {
      "mechanisms": {
         "Kv1": {
            "gbar": 1.4
         },
         ("Kv1", "burst"): {
            "gbar": 1.4
         }
      }
   }

Synapses
++++++++

A synapse definition is defined by its name, mechanism ID and parameter set. If you
do not specify a mechanism ID, the name is used instead.

   {
      "synapses": {
         "AMPA": {
            "gmax": 3200
         },
         "depressing": {
            "mechanism": ("AMPA", "TM"),
            "parameters": {
               "gmax": 1300,
               "U": 0.60
            }
         },
         "facilitating": {
            "mechanism": ("AMPA", "TM"),
            "parameters": {
               "gmax": 10000,
               "U": 0.12,
               "tau_facil": 1.1
            }
         },
      }
   }

Synapse types
~~~~~~~~~~~~~

The previous section described how to add synapses to a cable type, but you can also
define a synapse type available on the entire model by adding them to the
:guilabel:`synapse_types` field.

.. code-block::

   {
      "cable_types": {...},
      "synapse_types": {
         "AMPA": {
            "gmax": 3200
         }
      }
   }


Drawing a schematic
~~~~~~~~~~~~~~~~~~~

Schematics can come from any source, and Arborize supports 2 sources out of the box:

* BSB schematics from BSB morphologies and parameters.
* File schematics load morphologies from file using MorphIO.

.. code-block:: python

   from arborize import file_schematic, define_model, neuron_build

   definition = define_model({
      "cable_types": {...},
      "synapse_types": {...},
   })
   schematic = file_schematic("my_cell.swc", definition)
   n_cells = 100
   cells = [build_neuron(schematic) for i in range(n_cells)]

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
