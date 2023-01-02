import unittest

from ._shared import SchematicsFixture
from arborize import neuron_build
from arborize.exceptions import (
    ConstructionError,
    UnknownLocationError,
    UnknownSynapseError,
)
from patch import p
import numpy as np


class TestModelBuilding(SchematicsFixture, unittest.TestCase):
    def test_mech_insert(self):
        cell = neuron_build(self.p75_pas)
        self.assertEqual(
            len(self.p75_pas), len(cell.sections), "constructed diff n branches"
        )
        soma = cell.filter_sections(["soma"])
        basal = cell.filter_sections(["basal_dendrite"])
        apical = cell.filter_sections(["apical_dendrite"])
        self.assertTrue(
            all("pas" in [mech.name() for mech in sec(0.5)] for sec in soma),
            "pas not inserted in all soma sections",
        )
        self.assertEqual(-70, soma[0](0.5).pas.e, "Param not set")
        self.assertFalse(
            any("pas" in [mech.name() for mech in sec(0.5)] for sec in basal),
            "pas inserted in some basal sections",
        )
        self.assertFalse(
            any("pas" in [mech.name() for mech in sec(0.5)] for sec in apical),
            "pas inserted in some apical sections",
        )

    def test_synapses(self):
        cell = neuron_build(self.p75_expsyn)
        cell_nosyn = neuron_build(self.p75_expsyn)
        with self.assertRaises(UnknownSynapseError):
            cell.insert_synapse("unknown", (0, 0))
        syn = cell.insert_synapse("ExpSyn", (0, 0))
        with self.assertRaises(UnknownLocationError):
            cell.insert_synapse("ExpSyn", (-1, 0))
        syn.stimulate(start=0, number=3, interval=10)
        r = cell.sections[0].record()
        r_nosyn = cell_nosyn.sections[0].record()
        r2 = p.Vector()
        r2.record(syn._pp.get_segment()._ref_v)

        p.run(100)

        self.assertEqual(list(r), list(r2), "Recording from same loc should be identical")
        self.assertFalse(min(r) == max(r), "No synaptic currents detected")
        self.assertTrue(min(r_nosyn) == max(r_nosyn), "Synaptic currents detected")

    def test_transmitter_receiver(self):
        if not p.parallel.id():
            cell2 = neuron_build(self.p75_expsyn)
            ais = cell2.filter_sections(["soma"])[0].locations[-1]
            cell2.insert_transmitter(1, ais)
            cell2.insert_synapse("ExpSyn", (0, 0)).stimulate(
                start=0, number=5, interval=10, weight=1, delay=1
            )

        cell = neuron_build(self.p75_expsyn)
        cell.insert_receiver(1, "ExpSyn", (0, 0), weight=0.04, delay=1)
        r = p.record(cell.get_segment((0, 0), 0.5))
        spt, spid = p.parallel.spike_record()
        p.parallel._warn_new_gids = False

        p.run(100)

        arr = np.array(p.parallel.py_allgather([*r])).T
        self.assertEqual(2, len(spid), "Expected 2 spikes")
        self.assertTrue(np.allclose(np.diff(arr, axis=1), 0), "diff across nodes")
        self.assertNotEqual(min(r), max(r), "no current detected")

    @unittest.expectedFailure()
    def test_double_transmitter_receiver(self):
        if not p.parallel.id():
            cell2 = neuron_build(self.p75_expsyn)
            ais = cell2.filter_sections(["soma"])[0].locations[-1]
            cell2.insert_transmitter(2, ais)
            cell2.insert_transmitter(3, ais)
            cell2.insert_synapse("ExpSyn", (0, 0)).stimulate(
                start=0, number=5, interval=10, weight=1, delay=1
            )

        cell = neuron_build(self.p75_expsyn)
        cell.insert_receiver(2, "ExpSyn", (0, 0), weight=0.04, delay=1)
        cell.insert_receiver(3, "ExpSyn", (0, 0), weight=0.04, delay=50)
        spt, spid = p.parallel.spike_record()
        p.parallel._warn_new_gids = False

        p.run(100)

        # One section can only be registered as 1 gid
        self.assertEqual(4, len(spid), "Expected 4 spikes")
