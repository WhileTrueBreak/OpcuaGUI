from abc import abstractmethod

class Interactable:

    @abstractmethod
    def handleEvents(self, event):
        ...

    @abstractmethod
    def getControlPanel(self):
        ...
