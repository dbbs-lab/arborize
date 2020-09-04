def _details_iter(labels, values):
    i = 0
    while True:
        label = next(labels, None)
        try:
            value = next(values)
            actual_values = True
        except StopIteration:
            actual_values = False
        if label:
            yield (label, value)
        elif actual_values:
            yield (i, value)
        else:
            break
        i += 1

class ArgDetailsException(Exception):
    def __init__(self, *args):
        super().__init__(*args)
        self.details = dict(_details_iter(iter(self.__class__._detail_labels), iter(args)))

    def __getattr__(self, attr):
        if attr in self.__class__._detail_labels:
            return self.details[attr]
        return super().__getattribute__(attr)

    def __str__(self):
        return str(self.args[0])

    def __init_subclass__(cls, details=[], **kwargs):
        super().__init_subclass__(**kwargs)
        cls._detail_labels = details


class ArborizeError(Exception):
    pass

class ModelError(ArborizeError):
    pass

class ModelClassError(ModelError):
    pass

class MorphologyBuilderError(ModelError):
    pass

class MechanismNotPresentError(ArgDetailsException, ModelClassError, details=["mechanism"]):
    pass

class MechanismNotFoundError(ArgDetailsException, ModelClassError, details=["mechanism", "variant"]):
    pass

class LabelNotDefinedError(ModelClassError):
    pass

class SectionAttributeError(ArgDetailsException, ModelClassError):
    pass

class ConnectionError(ArborizeError):
    pass

class AmbiguousSynapseError(ConnectionError):
    pass

class SynapseNotPresentError(ConnectionError):
    pass

class SynapseNotDefinedError(ConnectionError):
    pass
