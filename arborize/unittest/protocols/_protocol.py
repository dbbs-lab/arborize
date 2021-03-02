class TestProtocol:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        abstracts = ["prepare", "run", "results", "asserts"]
        missing = [a for a in abstracts if not hasattr(cls, a)]
        if missing:
            raise RuntimeError(f"Can't instantiate protocol `{cls.__name__}` with abstract methods " + ",".join(f"`{m}`" for m in missing))

    def __call__(self, test, asserts=True):
        self.prepare(test.setup)
        self.run()
        results = self.results(test.setup)
        if asserts:
            self.asserts(test, results)
        return results
