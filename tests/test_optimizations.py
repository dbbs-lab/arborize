import pathlib
import unittest

from arborize import bluepyopt_build, define_constraints, file_schematic


class TestBluePyOptimization(unittest.TestCase):
    def test_hh_pas(self):
        constraints = define_constraints(
            {
                "cable_types": {
                    "soma": {
                        "cable": {"Ra": 100.0, "cm": 1.0},
                        "ions": {},
                        "mechanisms": {
                            "hh": {
                                "gnabar": [0.05, 0.125],
                                "gkbar": [0.01, 0.075],
                            },
                        },
                    },
                },
            }
        )
        schema = file_schematic(
            pathlib.Path(__file__).parent / "data" / "morphologies" / "simple.swc",
            definitions=constraints,
        )
        cell_model = bluepyopt_build(schema)
        self.assertEquals(["soma"], cell_model.seclist_names)

        self.assertEquals(1, len(cell_model.mechanisms))
        self.assertEquals("hh", cell_model.mechanisms[0].name)
        self.assertEquals("hh", cell_model.mechanisms[0].prefix)
        self.assertEquals(1, len(cell_model.mechanisms[0].locations))
        self.assertEquals("soma", cell_model.mechanisms[0].locations[0].seclist_name)
        self.assertEquals(5, len(cell_model.params))
