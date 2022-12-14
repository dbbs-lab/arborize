import os
import tempfile
import itertools
from typing import Optional, TYPE_CHECKING, Union, TextIO
from ..schematic import Schematic


if TYPE_CHECKING:
    from ..schematic import ModelDefinition


def file_schematic(
    pathOrFileLike: Union["os.PathLike", TextIO],
    definitions: Optional["ModelDefinition"] = None,
    fname: str = None,
) -> Schematic:
    if hasattr(pathOrFileLike, "read"):
        if not pathOrFileLike.name and not fname:
            raise IOError(
                "The file-driver MorphIO requires a file name to parse files. "
                "Use a file-like object that provides a `name` attribute, "
                "or pass the `fname` keyword argument, "
                "with a suffix matching the file format."
            )
        base = os.path.basename(pathOrFileLike.name or fname)
        handle, abspath = tempfile.mkstemp(suffix=base)
        os.close(handle)
        try:
            with open(abspath, "w") as f:
                f.write(pathOrFileLike.read())
            return file_schematic(abspath, definitions)
        finally:
            os.unlink(abspath)
    import morphio

    morpho = morphio.Morphology(os.fspath(pathOrFileLike))
    schematic = Schematic()
    print(morpho.soma)
    print(morpho.root_sections)
    print(
        len([*morpho.root_sections[0].iter()]),
        sum(len([*i.iter()]) for i in morpho.root_sections),
    )
    morpho.root_sections
    # branches: list["Branch"] = [*morphology.branches]
    # endpoints = []
    # for bid, branch in enumerate(branches):
    #     branch._tempid = bid
    #     if not len(branch):
    #         true_parent = None
    #         while True:
    #             parent = branch.parent
    #             if parent is None:
    #                 break
    #             elif len(parent):
    #                 true_parent = endpoints[parent._tempid]
    #                 break
    #         schematic.create_empty()
    #         endpoints.append(true_parent)
    #     else:
    #         if branch.parent is not None:
    #             endpoint = endpoints[branch.parent._tempid]
    #         else:
    #             endpoint = None
    #         for pid, coords, radius, labels in zip(
    #             itertools.count(), branch.points, branch.radii, branch.labels.walk()
    #         ):
    #             endpoint = endpoint if pid == 0 else None
    #             schematic.create_location((bid, pid), coords, radius, labels, endpoint)
    #         endpoints.append((bid, pid))
    if definitions is not None:
        schematic.definition = definitions
    return schematic
