from models.interfaces.model import SimpleModel
from models.staticModel import StaticModel
from models.wrapper.kukaBase import KukaBase
from models.wrapper.kukaRobot import KukaRobotTwin

from utils.debug import *

import pickle
import os

class SceneLoader:

    def __init__(self, renderer):
        self.renderer = renderer
        self.attachmentMap = {}
        self.modelMap = {}

    @timing
    def loadSave(self, loc):
        self.__loadKukaArm(loc)
        self.__loadStaticModel(loc)
        self.__loadSimpleModel(loc)
        self.__loadKukaBase(loc)
        self.__loadAttachment(loc)
        self.__addAttachments()
        pass

    @timing
    def __addAttachments(self):
        for k,v in self.attachmentMap.items():
            self.modelMap[k].setAttach(self.modelMap[v])

    @timing
    def __loadSimpleModel(self, loc):
        path = f'{loc}/models/simple'
        ids = os.listdir(path)
        for id in ids:
            self.modelMap[id] = SimpleModel.deserialize(loc, id, self.renderer)
    
    @timing
    def __loadStaticModel(self, loc):
        path = f'{loc}/models/static'
        ids = os.listdir(path)
        for id in ids:
            self.modelMap[id] = StaticModel.deserialize(loc, id, self.renderer)
    
    @timing
    def __loadKukaBase(self, loc):
        path = f'{loc}/models/kuka/base'
        ids = os.listdir(path)
        for id in ids:
            self.modelMap[id] = KukaBase.deserialize(loc, id, self.renderer)

    @timing
    def __loadKukaArm(self, loc):
        path = f'{loc}/models/kuka/arm'
        ids = os.listdir(path)
        for id in ids:
            self.modelMap[id] = KukaRobotTwin.deserialize(loc, id, self.renderer)

    @timing
    def __loadAttachment(self, loc):
        path = f'{loc}/models/attach'
        ids = os.listdir(path)
        for id in ids:
            attachFile = open(f'{path}/{id}', 'rb')
            attachData = pickle.load(attachFile)
            attachFile.close()
            self.attachmentMap[id] = f'{attachData['attach']}'
