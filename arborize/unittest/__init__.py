import os, unittest, inspect, functools
import nrnsub
import dill

from ._helpers import get_cell_name

def _get_obj_module_path(obj):
    p = inspect.getfile(obj)
    d = os.path.dirname(p)
    if p.endswith("__init__.py"):
        return os.path.dirname(d)
    return d


def _prepend_f(f, pre):
    @functools.wraps(f)
    def prepended(*args, **kwargs):
        pre(*args, **kwargs)
        f(*args, **kwargs)

    return prepended


class TestCase(unittest.TestCase):
    def __init_subclass__(cls, **kwargs):
        classpath = _get_obj_module_path(cls)
        super().__init_subclass__(**kwargs)
        # `unittest` executes the `setUp` before each `test_` function; but it
        # would execute it on the master instead of on the worker, so we prepend
        # it to each `test_` function right before we wrap it in the subprocess
        # isolator.
        f_setup = getattr(cls, "setUp", None)
        for k, v in cls.__dict__.items():
            if k.startswith("test_") and callable(v):
                if f_setup is not None:
                    v = _prepend_f(v, f_setup)
                setattr(cls, k, nrnsub.isolate(v, worker_path=[classpath]))
        # Then we substitute the `setUp` on the master process with a noop
        setattr(cls, "setUp", lambda self: None)


class Results:
    def __init__(self, primary=None):
        self._results = {}
        if primary is not None:
            self.set(primary)

    def set(self, result, name="primary"):
        self._results[name] = result

    def get(self, name="primary"):
        return self._results.get(name, None)

    def set_cell_result(self, cell, result, name="primary"):
        self.set(result, name=get_cell_name(cell, unique=True) + "." + name)
