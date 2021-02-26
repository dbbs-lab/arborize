import os, unittest, inspect
import nrnsub, dill

class TestCase(unittest.TestCase):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for k, v in cls.__dict__.items():
            if k.startswith("test_") and callable(v):
                setattr(cls, k, nrnsub.isolate(v, incl_obj_path=True))
