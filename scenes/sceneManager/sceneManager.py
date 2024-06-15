from ui.elements.uiWrapper import UiWrapper
from ui.constraintManager import *

from abc import abstractmethod

class SceneManager:

    def __init__(self):
        self.scenes = []
        self.sceneMap = {}
        self.currentScene = None
        self.btns = []
    
    def initialize(self, window):
        self.window = window
        self.wrapper = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0, 0, 1, 1))

    @funcProfiler(ftype='eventupdate')
    def handleEvent(self, event):
        if event['action'] == 'release' and event['obj'] in self.btns:
            self.setScene(self.sceneMap[event['obj']])
        if self.currentScene == None: return
        self.currentScene.handleUiEvents(event)

    def setScene(self, scene):
        if self.currentScene == scene: return
        if self.currentScene != None:
            self.sceneWrapper.removeChild(self.currentScene.sceneWrapper)
            self.currentScene.stop()
        self.currentScene = scene
        if self.currentScene != None:
            self.sceneWrapper.addChild(self.currentScene.sceneWrapper)
            self.currentScene.start()

    @abstractmethod
    def createUi(self):
        ...

    @funcProfiler(ftype='sceneupdate')
    def update(self, delta):
        if self.currentScene == None: return
        self.currentScene.recUpdate(delta)

    @timing
    def stop(self):
        if self.currentScene == None: return
        self.sceneWrapper.removeChild(self.currentScene.sceneWrapper)
        self.currentScene.stop()

    def addScene(self, scene):
        self.scenes.append(scene)

    def getCurrentScene(self):
        return self.currentScene
    
    def getWrapper(self):
        return self.wrapper