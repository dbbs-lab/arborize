import unittest

from ._shared import SchematicsFixture
from arborize import arbor_build


class TestModelBuilding(SchematicsFixture, unittest.TestCase):
    def test_arbor_build(self):
        cell = arbor_build(self.p75_pas)
