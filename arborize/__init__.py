from .core import *
from .synapse import Synapse

__version__ = "1.1.3"

_morphology_dirs = []

def add_directory(path):
    """
        Add a path that Arborize should look through for morphology files.
    """
    global _morphology_dirs
    _morphology_dirs.append(path)
