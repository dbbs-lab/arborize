import unittest
from arborize import file_schematic


class TestFileSchematic(unittest.TestCase):
    def test_path(self):
        print("ELLLLO")
        with open("tests/morphologies/cell010.swc", "r") as f:
            schematic = file_schematic(f)
