import unittest
from tests._shared import SchematicsFixture


class TestFileSchematic(SchematicsFixture, unittest.TestCase):
    def test_labels(self):
        self.assertEqual(
            sorted(["soma", "apical_dendrite", "basal_dendrite"]),
            sorted(set(b.labels[0] for b in self.p75)),
            "Missing or added label types",
        )

    def test_tags(self):
        self.assertEqual(
            sorted(["soma", "tag_7"]),
            sorted(set(b.labels[0] for b in self.cell010)),
            "Missing or added label types",
        )
