import typing

if typing.TYPE_CHECKING:
    from arborize.schematic import Schematic


class SchematicsFixture:
    p75: "Schematic"
    cell010: "Schematic"
    p75_pas: "Schematic"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self) -> None:
        super().setUp()
        from .data import schematics

        for k, v in vars(schematics).items():
            if not k.startswith("_"):
                setattr(self, k, v)
