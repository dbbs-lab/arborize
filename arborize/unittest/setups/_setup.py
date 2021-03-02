class TestSetup:
    def __init__(self):
        self._cells = []
        self._subjects = {}

    @property
    def cells(self):
        return self._cells.copy()

    @property
    def subjects(self):
        return self._subjects.copy()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        abstracts = ["setup"]
        missing = [a for a in abstracts if a not in cls.__dict__]
        if missing:
            raise RuntimeError(f"Can't instantiate `{cls.__name__}` with abstract methods " + ",".join(f"`{m}`" for m in missing))

    def __call__(self, test):
        print(self, test)
        self.setup(test)
        test.setup = self

    def register_subject(self, name, subject):
        if name in self._subjects:
            raise RuntimeError(f"Test subject name `{name}` is already taken")
        self._subjects[name] = subject
        subject.name = name
        self.register_cell(subject)

    def register_cell(self, cell):
        self._cells.append(cell)
