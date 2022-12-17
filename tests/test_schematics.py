import unittest
from arborize import file_schematic


class TestFileSchematic(unittest.TestCase):
    def test_labels(self):
        with open("tests/morphologies/P75.swc", "r") as f:
            schematic = file_schematic(f)
        self.assertEqual(
            sorted(["soma", "apical_dendrite", "basal_dendrite"]),
            sorted(set(b.labels[0] for b in schematic)),
            "Missing or added label types",
        )

    def test_tags(self):
        schematic = file_schematic("tests/morphologies/cell010.swc")
        self.assertEqual(
            sorted(["soma", "tag_7"]),
            sorted(set(b.labels[0] for b in schematic)),
            "Missing or added label types",
        )
