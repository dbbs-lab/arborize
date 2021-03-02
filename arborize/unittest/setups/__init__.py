from ._setup import TestSetup

class SingleCell(TestSetup):
    def __init__(self, model):
        super().__init__()
        self._model = model

    def setup(self, test):
        self.register_subject("main", self._model())
