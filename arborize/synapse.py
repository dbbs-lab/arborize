import glia as g

class Synapse:

    def __init__(self, cell, section, point_process_name, attributes = {}, variant=None):
        self._cell = cell
        self._section = section
        self._point_process_name = point_process_name
        with g.context(pkg=cell._package):
            self._point_process_glia_name = g.resolve(point_process_name, variant=variant)
            self._point_process = g.insert(section, point_process_name, variant=variant)
        section.__ref__(self)
        for key, value in attributes.items():
            setattr(self._point_process, key, value)

    def __neuron__(self):
        return self._point_process.__neuron__()

    def stimulate(self, *args, **kwargs):
        return self._point_process.stimulate(*args, **kwargs)
