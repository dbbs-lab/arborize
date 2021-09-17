from .rotation import rotate

def _set_blue_nseg(model):
    for s in model.sections:
        s.nseg = 1 + s.L // 40 * 2

def blue_nseg():
    """
    Set the nseg how BluePyOpt would have during optimization.
    """
    return _set_blue_nseg
