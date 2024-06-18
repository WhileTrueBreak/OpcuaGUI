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

from utils.interfaces.pollController import PollController
from utils.mathHelper import *
from utils.objMesh import *
from utils.videoPlayer import *

import numpy as np
import pickle
import shutil
import time
import os

class DigitalTwinLab(Scene):

    UI_PADDING = 10

    def __init__(self, window, name):
        super().__init__(window, name)
        self.models = []
        
        self.camera = MovingCamera(self.window, [7, 4, 2.5, -90, 0, 0], 2)
        
        self.pointLight = (10, 4, 2.5)
        self.lapsed = 0
    
    @timing
    def createUi(self):
        self.renderWindow = Ui3DScene(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0, 0, 1, 1, DigitalTwinLab.UI_PADDING), supportTransparency=True)
        self.renderWindow.setBackgroundColor((0.25, 0.2, 0.27))
        self.modelRenderer = self.renderWindow.getRenderer()
        self.sceneWrapper.addChild(self.renderWindow)
        
        self.panelWrapper = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0.7,0,0.3,1, DigitalTwinLab.UI_PADDING))
        self.renderWindow.addChild(self.panelWrapper)

        self.__createRoom()
        self.__addRobots()
        self.__addFurniture()
        return
    
    @timing
    def __createRoom(self):
        roomColor = (0.9,0.9,0.9,1)
        plan = [
            #right
            [(0,0),(0,1.1),(0,2.4)],
            [(0,1.1),(0,1.26),(0,3.1)],
            [(0,1.26),(0,6.92),(0,0.885)],
            [(0,6.92),(0,7),(0,3.1)],
            [(0,1.1),(0,6.92),(2.4,3.1)],

            #front
            [(0,0),(0.47,0),(0,2.4)],
            [(0.47,0),(1.47,0),(0,0.885)],
            [(3.77,0),(5.77,0),(0,0.885)],
            [(5.77,0),(6.39,0),(0,2.4)],
            [(6.39,0),(8.39,0),(0,0.885)],
            [(10.69,0),(11.69,0),(0,0.885)],
            [(11.69,0),(12.34,0),(0,2.4)],
            [(12.34,0),(15.3,0),(0,0.885)],

            #left door
            [(15.3,0),(15.3,1),(0,2.4)],
            [(15.3,1),(15.3,2.75),(0,0.885)],
            [(15.3,2.75),(15.3,2.9),(0,3.1)],
            [(15.3,5),(15.3,7),(0,3.1)],
            [(15.3,1.1),(15.3,7),(2.4,3.1)],

            [(15.43, 2.9), (15.3, 2.9), (0, 2.4)],
            [(15.43, 5), (15.3, 5), (0, 2.4)],

            [(15.43, 1), (15.3, 1), (0.885, 2.4)],
            [(15.43, 2.75), (15.3, 2.75), (0.885, 2.4)],

            #back
            [(0,7),(15.3,7),(0,0.885)],

            [(14.1,7),(15.3,7),(0.885,2.4)],
            [(12.32,7),(13.26,7),(0.885,2.4)],

            [(0,7),(1.3,7),(0.885,2.4)],
            [(2.15,7),(4,7),(0.885,2.4)],
            [(4.84,7),(5.94,7),(0.885,2.4)],

            [(6.31,7),(7.31,7),(0.885,2.4)],
            [(8.16,7),(9.9,7),(0.885,2.4)],
            [(10.75,7),(11.95,7),(0.885,2.4)],

            [(0,7),(15.3,7),(2.4,3.1)],
            
            #back pillars
            [(0,6.92),(0.3,6.92),(0,3.1)],
            [(0.3,6.92),(0.3,7),(0,3.1)],
            [(5.94,6.92),(6.31,6.92),(0,3.1)],
            [(5.94,6.92),(5.94,7),(0,3.1)],
            [(6.31,6.92),(6.31,7),(0,3.1)],
            [(11.95,6.92),(12.32,6.92),(0,3.1)],
            [(11.95,6.92),(11.95,7),(0,3.1)],
            [(12.32,6.92),(12.32,7),(0,3.1)],

            #side room
            [(15.3, 1),(17.96, 1),(0, 2.4)],
            [(17.96, 1),(17.96, 7),(0, 2.4)],
            [(15.43, 5),(15.43, 7),(0, 2.4)],
            [(15.3, 7),(17.96, 7),(0, 2.4)],
            [(15.43,1),(15.43,2.75),(0,0.885)],
            [(15.43,2.75),(15.43,2.9),(0,2.4)]]

        xyPlanes = [
            (0, 0, 2.4, 15.3, 1.1, WallBuilder.S2),
            (0, 0, 0, 15.3, 7, WallBuilder.S1|WallBuilder.S2),
            (0, 1.1, 3.1, 15.3, 5.9, WallBuilder.S2),
            (15.3, 1, 0, 0.13, 6, WallBuilder.S1|WallBuilder.S2),
            (15.3, 1, 0.885, 0.13, 1.75, WallBuilder.S1),
            (15.3, 1, 2.4, 0.13, 6, WallBuilder.S1|WallBuilder.S2),
            (15.43, 1, 0, 2.53, 6, WallBuilder.S1|WallBuilder.S2),
            (15.43, 1, 2.4, 2.53, 6, WallBuilder.S2)]
        
        roomPlan = WallBuilder.buildWallPlan(plan)
        roomPlan.extend([WallBuilder.buildPlaneXY(*plane[0:5], vis=plane[5]) for plane in xyPlanes])
        roomPlan.append(WallBuilder.buildPlaneXZ(0, 1.1, 2.4, 15.3, 0.7, vis=WallBuilder.S2))
        
        roomPlan = ObjMesh.fromSubModels(roomPlan)[0]
        room = SimpleModel(self.modelRenderer, roomPlan, np.identity(4))
        self.models.append(room)
        self.modelRenderer.setColor(room.modelId, roomColor)

        return

    @timing
    def __addRobots(self):
        self.bases = []
        # # ROBOT 3 - KEENANS DEMO ROBOT
        base = KukaBase(self.modelRenderer, Assets.KUKA_FLEX, (23, 3), posParams=(4,4,0,True))
        base.setAttachTransform(createTransformationMatrix(0, 0, 0.89, 0, 0, 0))
        arm = KukaRobotTwin(self.window, createTransformationMatrix(0.315, 0, 0, 0, 0, 0), 23, 'R3', self.modelRenderer, hasForceVector=True, hasGripper=True)
        arm.setLiveColors([(1, 51/255, 51/255, 0.7)for i in range(9)])
        arm.setTwinColors([(1, 178/255, 102/255, 0.0)for i in range(9)])
        arm.setAttach(base)
        self.bases.append(base)
        self.models.append(base)
        self.models.append(arm)
        
        # # ROBOT 4 - MSM Testing ROBOT
        base = KukaBase(self.modelRenderer, Assets.KUKA_FLEX, (24, 4), posParams=(0,0,0,True))
        base.setAttachTransform(createTransformationMatrix(0, 0, 0.89, 0, 0, 0))
        arm = KukaRobotTwin(self.window, createTransformationMatrix(0.315, 0, 0, 0, 0, 0), 24, 'R4', self.modelRenderer, hasForceVector=True, hasGripper=False)
        arm.setLiveColors([(1, 1, 0, 0.7)for i in range(9)])
        arm.setTwinColors([(1, 1, 153/255, 0.0)for i in range(9)])
        arm.setAttach(base)
        self.bases.append(base)
        self.models.append(base)
        self.models.append(arm)

        # # ROBOT 1 - Moblie 1
        base = KukaBase(self.modelRenderer, Assets.OMNIMOVE, (21, 1), posParams=(0,0,0,False))
        base.setAttachTransform(createTransformationMatrix(0, 0, 0.7, 0, 0, 0))
        arm = KukaRobotTwin(self.window, createTransformationMatrix(0.363, -0.184, 0, 0, 0, -90), 21, 'R1', self.modelRenderer, hasForceVector=True, hasGripper=True)
        arm.setLiveColors([(0, 1, 0, 0.7)for i in range(9)])
        arm.setTwinColors([(102/255, 1, 178/255, 0.0)for i in range(9)])
        arm.setAttach(base)
        self.bases.append(base)
        self.models.append(base)
        self.models.append(arm)
        
        # # ROBOT 2 - Moblie 2
        base = KukaBase(self.modelRenderer, Assets.OMNIMOVE, (22, 2), posParams=(0,0,0,False))
        base.setAttachTransform(createTransformationMatrix(0, 0, 0.7, 0, 0, 0))
        arm = KukaRobotTwin(self.window, createTransformationMatrix(0.363, -0.184, 0, 0, 0, -90), 22, 'R2', self.modelRenderer, hasForceVector=True, hasGripper=True)
        arm.setLiveColors([(0, 0.5, 1.0, 0.7)for i in range(9)])
        arm.setTwinColors([(153/255, 153/255, 1, 0.0)for i in range(9)])
        arm.setAttach(base)
        self.bases.append(base)
        self.models.append(base)
        self.models.append(arm)

    @timing
    def __addFurniture(self):
        self.models.append(StaticModel(self.modelRenderer, Assets.SHELF, createTransformationMatrix(16.70,3.6,0,0,0,-90)))
        self.models.append(StaticModel(self.modelRenderer, Assets.SHELF, createTransformationMatrix(0.9,2,0,0,0,90)))
        self.models.append(StaticModel(self.modelRenderer, Assets.SHELF, createTransformationMatrix(0.9,4.5,0,0,0,90)))
        self.models.append(StaticModel(self.modelRenderer, Assets.SHELF, createTransformationMatrix(0.9,6,0,0,0,0)))
        
        self.models.append(SimpleModel(self.modelRenderer, Assets.TABLE_RECT, createTransformationMatrix(4.5,7-0.5,0.85,0,0,90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.TABLE_SQUARE, createTransformationMatrix(10.3,7-0.9,0.85,0,0,0)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.TABLE_RECT, createTransformationMatrix(7,0.8,0.85,0,0,90)))

        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8,6.6,0.5,0,0,-90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8,6.6,1.35,0,0,-90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8+0.73,6.6,0.5,0,0,-90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8+0.73,6.6,1.35,0,0,-90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8+0.73+0.73,6.6,0.5,0,0,-90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8+0.73+0.73,6.6,1.35,0,0,-90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8+0.73+0.73+0.73,6.6,0.5,0,0,-90)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.PRUSA_XL, createTransformationMatrix(5.8+0.73+0.73+0.73,6.6,1.35,0,0,-90)))

        self.models.append(SimpleModel(self.modelRenderer, Assets.THE_MATRIX, createTransformationMatrix(5.6,6,0,0,0,0)))
        self.models.append(SimpleModel(self.modelRenderer, Assets.KUKA_EDU, createTransformationMatrix(4,1.2,0,0,0,-90)))

        self.leftBtn = SimpleModel(self.modelRenderer, Assets.ARROW_BTN, np.matmul(createTransformationMatrix(4.3,6.5,0.85,0,0,180),createScaleMatrix(8, 8, 8)))
        self.rightBtn = SimpleModel(self.modelRenderer, Assets.ARROW_BTN, np.matmul(createTransformationMatrix(4.7,6.5,0.85,0,0,0),createScaleMatrix(8, 8, 8)))
        self.modelRenderer.setColor(self.leftBtn.modelId, (0.3,1,0.7,1))
        self.modelRenderer.setColor(self.rightBtn.modelId, (0.3,1,0.7,1))
        self.models.append(self.leftBtn)
        self.models.append(self.rightBtn)

        self.streamDict = {}

        streams = []
        streams.append(MJPEGStream('http://172.32.1.225:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.226:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.227:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.228:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.90:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.91:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.92:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.93:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.94:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.95:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.96:8080/?action=streams'))
        streams.append(MJPEGStream('http://172.32.1.97:8080/?action=streams'))

        for stream in streams: self.streamDict[stream] = []

        self.screen = SimpleModel(self.modelRenderer, Assets.SCREEN, createTransformationMatrix(5.5,6.99,1,90,0,90))
        self.streamDict[streams[1]].append(self.screen)
        self.screenIndex = 1

        for key in self.streamDict.keys():
            for display in self.streamDict[key]:
                self.modelRenderer.setTexture(display.modelId, key.texture)
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

        if self.rightBtn.isModel(modelId):
            self.__changeScreenDisplay(self.screenIndex+1)
        elif self.leftBtn.isModel(modelId):
            self.__changeScreenDisplay(self.screenIndex-1)

        for model in self.models:
            if model.isModel(modelId):
                if not isinstance(model, Interactable): continue
                cp = model.getControlPanel()
                if not cp: break
                self.panelWrapper.addChild(cp)
    
    def __changeScreenDisplay(self, newIndex):
        self.streamDict[list(self.streamDict.keys())[self.screenIndex]].remove(self.screen)
        self.screenIndex = newIndex%len(self.streamDict.keys())
        stream = list(self.streamDict.keys())[self.screenIndex]
        self.streamDict[stream].append(self.screen)
        self.modelRenderer.setTexture(self.screen.modelId, stream.texture)

    # @timing
    @funcProfiler(ftype='sceneupdate')
    def update(self, delta):
        self.__updateEnv(delta)
        self.__updateModelPos()
        self.__updateView()
        self.__updateStreamControl(delta)

        for model in self.models:
            if not isinstance(model, Updatable): continue
            model.update(delta)
        
        self.pointLight = (7 + 1.5*cos(self.lapsed/4), 4 + 1.5*sin(self.lapsed/4), 2)
        self.lapsed += delta
        self.modelRenderer.setLight(self.pointLight)
        return
    
    # @timing
    def __updateStreamControl(self, delta):
        for stream in self.streamDict.keys():
            active = False
            for display in self.streamDict[stream]:
                if not display.inViewFrustrum(self.modelRenderer.projectionMatrix, self.modelRenderer.viewMatrix): continue
                active = True
            if active:
                stream.start()
                stream.update(delta)
            else:
                stream.stop()

    # @timing
    def __updateView(self):
        for model in self.models:
            if not hasattr(model, 'inViewFrustrum'): continue
            if not hasattr(model, 'setViewFlag'): continue
            inView = model.inViewFrustrum(self.modelRenderer.projectionMatrix, self.modelRenderer.viewMatrix)
            # model.setViewFlag(inView)

    # @timing
    def __updateModelPos(self):
        return
    
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
        self.save('save')

        [model.stop() for model in self.models if isinstance(model, PollController)]
        for i in self.streamDict.keys():
            i.stop()
        return

    @timing
    def save(self, loc):
        if os.path.exists(loc):
            shutil.rmtree(loc)
        for model in self.models:
            if not isinstance(model, Serializable): continue
            model.serialize(loc)



