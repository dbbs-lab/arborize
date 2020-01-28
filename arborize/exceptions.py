class ArborizeError(Exception):
    pass

class ModelError(ArborizeError):
    pass

class ModelClassError(ModelError):
    pass

class MorphologyBuilderError(ModelError):
    pass

class MechanismAttributeError(ModelClassError):
    pass

class ConnectionError(ArborizeError):
    pass

class AmbiguousSynapseError(ConnectionError):
    pass

class SynapseNotPresentError(ConnectionError):
    pass

class SynapseNotDefinedError(ConnectionError):
    pass
