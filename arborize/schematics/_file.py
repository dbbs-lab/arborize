import os
import re
import tempfile
import itertools
import warnings
from typing import Optional, TYPE_CHECKING, Union, TextIO

from morphio import SomaType

from ..schematic import Schematic

if TYPE_CHECKING:
    from ..schematic import ModelDefinition


def file_schematic(
    file_like: Union["str", "os.PathLike", TextIO],
    definitions: Optional["ModelDefinition"] = None,
    fname: str = None,
) -> Schematic:
    if hasattr(file_like, "read"):
        if not file_like.name and not fname:
            raise IOError(
                "The file-driver MorphIO requires a file name to parse files. "
                "Use a file-like object that provides a `name` attribute, "
                "or pass the `fname` keyword argument, "
                "with a suffix matching the file format."
            )
        base = os.path.basename(file_like.name or fname)
        handle, abspath = tempfile.mkstemp(suffix=base)
        os.close(handle)
        try:
            with open(abspath, "w") as f:
                f.write(file_like.read())
            return file_schematic(abspath, definitions)
        finally:
            os.unlink(abspath)
    import morphio

    morpho = morphio.Morphology(os.fspath(file_like))
    schematic = Schematic()
    branches = [
        morpho.soma,
        *itertools.chain.from_iterable(s.iter() for s in morpho.root_sections),
    ]
    endpoints = []
    for bid, branch in enumerate(branches):
        mid = getattr(branch, "id", -1) + 1
        if bid != mid:
            raise AssertionError("MorphIO deviated from depth-first order.")
        parent = None if getattr(branch, "is_root", True) else branch.parent
        if not len(branch.points):
            true_parent = None
            while True:
                if parent is None:
                    break
                elif len(parent.points):
                    true_parent = endpoints[parent.id + 1]
                    break
                parent = None if branch.is_root else branch.parent
            schematic.create_empty()
            endpoints.append(true_parent)
        else:
            if parent is not None:
                endpoint = endpoints[parent.id + 1]
            else:
                endpoint = None
            if isinstance(branch.type, SomaType):
                type = "soma"
            elif "custom" in str(branch.type):
                num = re.search(r"\d+$", str(branch.type)).group()
                type = f"tag_{num}"
            else:
                type = str(branch.type).split(".")[-1]
            for pid, coords, diam in zip(
                itertools.count(), branch.points, branch.diameters
            ):
                endpoint = endpoint if pid == 0 else None
                schematic.create_location((bid, pid), coords, diam / 2, [type], endpoint)
            endpoints.append((bid, pid))
    if definitions is not None:
        schematic.definition = definitions
    return schematic
