import unittest

from ._shared import SchematicsFixture
from arborize import neuron_build
from arborize.exceptions import ConstructionError


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
        with self.assertRaises(ConstructionError):
            cell.insert_synapse("unknown", (0, 0))
        syn = cell.insert_synapse("ExpSyn", (0, 0))
        syn.stimulate(start=0, number=3, interval=10)
        r = cell.sections[0].record()
        from patch import p

        r2 = p.Vector()
        r2.record(syn._pp.get_segment()._ref_v)

        p.run(100)

        self.assertEqual(list(r), list(r2), "Recording from same loc should be identical")
        self.assertFalse(min(r) == max(r), "No synaptic currents detected")
