from asset import *

from connections.opcua import *
from connections.opcuaReceiver import OpcuaReceiver
from connections.opcuaTransmitter import OpcuaTransmitter
from constants import Constants

from models.interfaces.model import Updatable, Serializable
from models.interfaces.interactable import Interactable

from utils.interfaces.pollController import PollController
from utils.mathHelper import deg2Rad, FleetToLocalTransform
from utils.debug import *

from window import Window

class KukaBase(Updatable, PollController, Serializable):

    def __init__(self, modelRenderer, model, opcuaName, posParams=(0,0,0,True)):
        self.modelRenderer = modelRenderer
        self.model = model
        self.nodeId, self.robotId = opcuaName

        self.liveBaseX, self.liveBaseY, self.liveBaseA, self.inLocalFrame = posParams
        self.transform = createTransformationMatrix(self.liveBaseX, self.liveBaseY, 0, 0, 0, self.liveBaseA)
        self.attachRel = np.identity(4)
        self.attachT = np.identity(4)

        self.isLinkedOpcua = True
        self.inView = True
        self.viewCheckFrame = -1

        self.modelId = self.modelRenderer.addModel(self.model, self.transform)

        self.__setupConnections()
    
    def __setupConnections(self):
        self.opcuaReceiverContainer = OpcuaContainer()
        self.receivers = []
        self.receivers.append(OpcuaReceiver([ 
                    self.__getNodeName('d_BaseX'),
                    self.__getNodeName('d_BaseY'),
                    self.__getNodeName('d_BaseA'),
                ], self.opcuaReceiverContainer, Constants.OPCUA_LOCATION))
        
    def __getNodeName(self, varName):
        return f'ns={self.nodeId};s=R{self.robotId}{varName}'
    
    @funcProfiler(ftype='kukaupdate')
    def update(self, delta):
        self.__updateFromOpcua()
        self.transform = createTransformationMatrix(self.liveBaseX, self.liveBaseY, 0, 0, 0, self.liveBaseA)
        self.attachT = np.matmul(self.transform, self.attachRel)
        if not self.inView: return
        self.__updatePos()

    def __updateFromOpcua(self):
        if not self.isLinkedOpcua: return
        if not self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_BaseX')): return
        if not self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_BaseY')): return
        if not self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_BaseA')): return
        self.liveBaseX = self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_BaseX'), default=0)[0]
        self.liveBaseY = self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_BaseY'), default=0)[0]
        self.liveBaseA = self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_BaseA'), default=0)[0]
        if self.inLocalFrame: return
        self.liveBaseX, self.liveBaseY, self.liveBaseA = FleetToLocalTransform(self.liveBaseX, self.liveBaseY, self.liveBaseA)
        
    def __updatePos(self):
        self.modelRenderer.setTransformMatrix(self.modelId, self.transform)

    @timing
    def start(self):
        if not self.isLinkedOpcua:return
        for r in self.receivers: r.start()

    @timing
    def stop(self):
        for r in self.receivers: r.stop()

    def isModel(self, modelId):
        return modelId == self.modelId

    def setTransform(self, transform):
        self.transform = transform

    def inViewFrustrum(self, proj, view):
        if self.viewCheckFrame == Window.INSTANCE.frameCount: return self.inView
        self.viewCheckFrame = Window.INSTANCE.frameCount
        frustum = getFrustum(np.matmul(proj.T,view))
        bound = self.model.getAABBBound(self.transform)
        dists = np.matmul(bound, frustum.T)
        return not np.any(np.all(dists < 0, axis=0))

    def setViewFlag(self, flag):
        self.modelRenderer.setViewFlag(self.modelId , flag)

    def disconnectOpcua(self):
        self.isLinkedOpcua = False
        self.stop()

    def connectOpcua(self):
        self.isLinkedOpcua = True
        self.start()
    
    def setAttachTransform(self, attachT):
        self.attachRel = attachT
        self.attachT = np.matmul(self.transform, attachT)

    def getFrame(self):
        return self.attachT

    @timing
    def serialize(self, loc):
        self.model.serialize(loc)
        color = self.modelRenderer.getData(self.modelId)[0]['color']
        data = {
            'model':id(self.model), 
            'transform':self.transform, 
            'color':color, 
            'opcua':(self.nodeId, self.robotId),
            'posparam':(self.liveBaseX, self.liveBaseY, self.liveBaseA, self.inLocalFrame),
            'attachRel':self.attachRel,
            }
        path = f'{loc}/models/kuka/base/{id(self)}'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        modelFile = open(path, 'ab')
        pickle.dump(data, modelFile)
        modelFile.close()

    @classmethod
    @timing
    def deserialize(cls, path, file, renderer):
        modelFile = open(f'{path}/models/kuka/base/{file}', 'rb')
        modelData = pickle.load(modelFile)
        mesh = ObjMesh.deserialize(path, modelData['model'])
        model = cls(renderer, mesh, modelData['opcua'], posParams=modelData['posparam'])
        model.setTransform(modelData['transform'])
        model.setAttachTransform(modelData['attachRel'])
        renderer.setColor(model.modelId, modelData['color'])
        return model



