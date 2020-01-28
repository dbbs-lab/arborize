from .core import NeuronModel
from .synapse import Synapse

__version__ = "1.0.0"

_morphology_dirs = []

def add_directory(path):
    global _morphology_dirs
    _morphology_dirs.append(path)
