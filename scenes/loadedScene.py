from asset import *

from connections.mjpegStream import MJPEGStream

from scenes.scene import Scene
from scenes.utils.movingCamera import MovingCamera
from scenes.utils.sceneLoader import SceneLoader
from scenes.utils.wallBuilder import WallBuilder

from models.interfaces.model import SimpleModel, Updatable, Serializable
from models.interfaces.interactable import Interactable
from models.staticModel import StaticModel
from models.wrapper.kukaBase import KukaBase
from models.wrapper.kukaRobot import KukaRobotTwin

from ui.elements.uiButton import UiButton
from ui.elements.uiWrapper import UiWrapper
from ui.elements.ui3dScene import Ui3DScene
from ui.elements.uiStream import UiStream
from ui.elements.uiWrapper import UiWrapper
from ui.elements.uiText import UiText
from ui.elements.uiSlider import UiSlider
from ui.constraintManager import *
from ui.uiHelper import *

from utils.interfaces.classBuilder import ClassBuilder
from utils.interfaces.pollController import PollController
from utils.mathHelper import *
from utils.objMesh import *
from utils.videoPlayer import *

import numpy as np
import pickle
import shutil
import time
import os

class LoadedScene(Scene):

    def __init__(self, window, name):
        super().__init__(window, name)
        self.models = []
        
        self.camera = MovingCamera(self.window, [7, 4, 2.5, -90, 0, 0], 2)
        
        self.pointLight = (10, 4, 2.5)
        self.lapsed = 0
    
    @timing
    def createUi(self):
        self.renderWindow = Ui3DScene(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0, 0, 1, 1, 10), supportTransparency=True)
        self.renderWindow.setBackgroundColor((0.25, 0.2, 0.27))
        self.modelRenderer = self.renderWindow.getRenderer()
        self.sceneWrapper.addChild(self.renderWindow)
        
        self.panelWrapper = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0.7,0,0.3,1,10))
        self.renderWindow.addChild(self.panelWrapper)

        loader = SceneLoader(self.modelRenderer)
        loader.loadSave('save')
        for k,v in loader.modelMap.items():
            if isinstance(v, ClassBuilder):
                v.setWindow(self.window)
                v = v.build()
            self.models.append(v)
        return

    def handleUiEvents(self, event):
        for model in self.models:
            if not isinstance(model, Interactable): continue
            model.handleEvents(event)
        if event['action'] == 'release':
            if event['obj'] == self.renderWindow:
                self.__handleSceneEvents(event)
        return
    
    def __handleSceneEvents(self, event):
        modelId = event['modelId']
        self.panelWrapper.removeAllChildren()
        for model in self.models:
            if model.isModel(modelId):
                if not isinstance(model, Interactable): continue
                cp = model.getControlPanel()
                if not cp: break
                self.panelWrapper.addChild(cp)
    
    # @timing
    @funcProfiler(ftype='sceneupdate')
    def update(self, delta):
        self.__updateEnv(delta)
        self.__updateView()

        for model in self.models:
            if not isinstance(model, Updatable): continue
            model.update(delta)
        
        self.pointLight = (7 + 1.5*cos(self.lapsed/4), 4 + 1.5*sin(self.lapsed/4), 2)
        self.lapsed += delta
        self.modelRenderer.setLight(self.pointLight)
        return

    # @timing
    def __updateView(self):
        for model in self.models:
            if not hasattr(model, 'inViewFrustrum'): continue
            if not hasattr(model, 'setViewFlag'): continue
            inView = model.inViewFrustrum(self.modelRenderer.projectionMatrix, self.modelRenderer.viewMatrix)
            # model.setViewFlag(inView)
    
    # @timing
    def __updateEnv(self, delta):
        if self.window.selectedUi == self.renderWindow:
            self.camera.moveCamera(delta)
        if self.camera.hasMoved():
            self.modelRenderer.setViewMatrix(createViewMatrix(*self.camera.getCameraTransform()))

    @timing
    def start(self):
        self.modelRenderer.setViewMatrix(createViewMatrix(*self.camera.getCameraTransform()))
        [model.start() for model in self.models if isinstance(model, PollController)]
        return

    @timing
    def stop(self):
        [model.stop() for model in self.models if isinstance(model, PollController)]
        return
