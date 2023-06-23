import unittest

from ._shared import SchematicsFixture
from arborize import define_model, neuron_build
from arborize.exceptions import (
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

    @unittest.expectedFailure
    def test_double_transmitter_receiver(self):
        # This test verifies that NEURON still only transmits spikes to 1 detector per
        # Section
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

    def test_cable_building(self):
        self.cell010.definition = define_model(
            {
                "cable_types": {
                    "soma": {
                        "cable": {"Ra": 102, "cm": 2.1},
                        "ions": {
                            "k": {"rev_pot": -80.993, "int_con": 60, "ext_con": 4},
                            "na": {"rev_pot": 137.5, "int_con": 20, "ext_con": 130},
                        },
                        "mechanisms": {
                            "pas": {"e": -70, "g": 0.01},
                            "hh": {
                                "gnabar": 0,
                                "gkbar": 0.036,
                                "gl": 0.0003,
                                "el": -54.3,
                            },
                        },
                    },
                },
            },
            use_defaults=True,
        )
        cell = neuron_build(self.cell010)
        psection = cell.soma[0].psection()
        density_mechs = psection["density_mechs"]
        ions = psection["ions"]

        # Cable
        self.assertEqual(102, psection["Ra"])
        self.assertEqual(2.1, psection["cm"][0])

        # Mechanisms
        self.assertIn("pas", density_mechs)
        self.assertIn("hh", density_mechs)

        pas = density_mechs["pas"]
        self.assertEqual(-70, pas["e"][0])
        self.assertEqual(0.01, pas["g"][0])

        hh = density_mechs["hh"]
        self.assertEqual(0, hh["gnabar"][0])
        self.assertEqual(0.036, hh["gkbar"][0])
        self.assertEqual(0.0003, hh["gl"][0])
        self.assertEqual(-54.3, hh["el"][0])

        # Ions
        k = ions["k"]
        na = ions["na"]
        self.assertEqual(-80.993, k["ek"][0])
        self.assertEqual(60, k["ki"][0])
        self.assertEqual(4, k["ko"][0])
        self.assertEqual(-80.993, k["ek"][0])
        self.assertEqual(137.5, na["ena"][0])
        self.assertEqual(20, na["nai"][0])
        self.assertEqual(130, na["nao"][0])


tagsGrC = {
    16: ["axon", "axon_hillock"],
    17: ["axon", "axon_initial_segment"],
    18: ["axon", "ascending_axon"],
    19: ["axon", "parallel_fiber"],
}
