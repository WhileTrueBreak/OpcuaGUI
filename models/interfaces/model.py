from abc import abstractmethod
import numpy as np
import pickle
import os

from models.interfaces.serializable import Serializable
from utils.debug import *
from utils.mathHelper import getFrustum, pointFrustumDist
from utils.objMesh import ObjMesh
from window import Window

class SimpleModel(Serializable):
    
    def __init__(self, renderer, model, transform):
        self.renderer = renderer
        self.transform = transform
        self.model = model
        self.modelId = self.renderer.addModel(model, transform)

        self.inView = True
        self.viewCheckFrame = -1
    
    def getFrame(self):
        return self.transform

    def isModel(self, modelId):
        return modelId == self.modelId
    
    def inViewFrustrum(self, proj, view):
        if self.viewCheckFrame == Window.INSTANCE.frameCount: return self.inView

        aabbBound = self.model.getAABBBound(self.transform)
        frustum = getFrustum(np.matmul(proj.T,view))
        dists = np.matmul(aabbBound, frustum.T)

        self.inView = not np.any(np.all(dists < 0, axis=0))
        self.viewCheckFrame = Window.INSTANCE.frameCount
        return self.inView

    def setViewFlag(self, flag):
        self.renderer.setViewFlag(self.modelId, flag)

    @timing
    def serialize(self, loc):
        self.model.serialize(loc)
        color = self.renderer.getData(self.modelId)[0]['color']
        data = {'model':id(self.model), 'transform':self.transform, 'color':color}
        path = f'{loc}/models/simple/{id(self)}'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        modelFile = open(path, 'ab')
        pickle.dump(data, modelFile)
        modelFile.close()
        return

    @classmethod
    @timing
    def deserialize(cls, path, file, renderer):
        modelFile = open(f'{path}/models/simple/{file}', 'rb')
        modelData = pickle.load(modelFile)
        mesh = ObjMesh.deserialize(path, modelData['model'])
        model = cls(renderer, mesh, modelData['transform'])
        renderer.setColor(model.modelId, modelData['color'])
        return model

class Updatable:

    @abstractmethod
    def update(self, delta):
        ...

    @abstractmethod
    def setAttach(self, iModel):
        ...
    
    @abstractmethod
    def setTransform(self, mat):
        ...
