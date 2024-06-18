from abc import abstractmethod

class Serializable:

    @abstractmethod
    def serialize(self, loc):
        ...

    @classmethod
    @abstractmethod
    def deserialize(cls, path, file, renderer):
        ...
