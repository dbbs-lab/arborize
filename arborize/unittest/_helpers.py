import efel

def get_cell_name(cell, unique=False):
    if hasattr(cell, "name"):
        return cell.name
    elif unique:
        return str(cell)
    else:
        return cell.__class__.__module__ + "." + cell.__class__.__name__


_skip_keys = ["__getstate__", "__setstate__"]


class efel_dict(dict):
    def __getattr__(self, k):
        if k in _skip_keys:
            super().__getattribute__(k)
        return efel.getFeatureValues([self], [k])[0][k]


def ezfel(T, signal, **kwargs):
    kwargs["stim_start"] = [kwargs["stim_start"]] if "stim_start" in kwargs else [T[0]]
    kwargs["stim_end"] = [kwargs["stim_end"]] if "stim_end" in kwargs else [T[-1]]
    kwargs["T"] = T
    kwargs["V"] = signal
    kwargs["signal"] = signal
    d = efel_dict(kwargs)
    d.t = T
    d.x = signal
    return d
