class TestProtocol:
    def _wrap_prepare(f):
        pass

    def _wrap_run(f):
        pass

    def _wrap_results(f):
        pass

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        abstracts = ["prepare", "run", "results"]
        missing = [a for a in abstracts if a not in cls.__dict__]
        if missing:
            raise RuntimeError(f"Can't instantiate `{cls.__name__}` with abstract methods " + ",".join(f"`{m}`" for m in missing))

    def __call__(self, test):
        self.prepare(test.setup)
        self.run()
        return self.results(test)
