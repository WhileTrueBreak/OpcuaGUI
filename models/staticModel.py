from models.interfaces.model import SimpleModel, Updatable
from utils.debug import *
from utils.objMesh import ObjMesh

import numpy as np
import pickle
import os

class StaticModel(SimpleModel, Updatable):
    
    @timing
    def __init__(self, renderer, model, transform):
        super().__init__(renderer, model, transform)
        self.attach = None
    
    def __updateTranforms(self):
        attachFrame = self.attach.getFrame() if self.attach else np.identity(4)
        self.renderer.setTransformMatrix(self.modelId, np.matmul(attachFrame, self.transform))
        return
    
    def setAttach(self, iModel):
        self.attach = iModel
        self.__updateTranforms()
        return
    
    def setTransform(self, transform):
        self.transform = transform
        self.__updateTranforms()
    
    @timing
    def serialize(self, loc):
        self.model.serialize(loc)
        color = self.renderer.getData(self.modelId)[0]['color']
        data = {
            'model':id(self.model), 
            'transform':self.transform, 
            'color':color
        }
        path = f'{loc}/models/static/{id(self)}'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        modelFile = open(path, 'ab')
        pickle.dump(data, modelFile)
        modelFile.close()
        if self.attach:
            data = {'attach': id(self.attach)}
            path = f'{loc}/models/attach/{id(self)}'
            os.makedirs(os.path.dirname(path), exist_ok=True)
            attachFile = open(path, 'ab')
            pickle.dump(data, attachFile)
            attachFile.close()
        return

    @classmethod
    @timing
    def deserialize(cls, path, file, renderer):
        modelFile = open(f'{path}/models/static/{file}', 'rb')
        modelData = pickle.load(modelFile)
        mesh = ObjMesh.deserialize(path, modelData['model'])
        model = cls(renderer, mesh, modelData['transform'])
        renderer.setColor(model.modelId, modelData['color'])
        return model