from asset import *

from connections.opcua import *
from connections.opcuaReceiver import OpcuaReceiver
from connections.opcuaTransmitter import OpcuaTransmitter
from constants import Constants

from scenes.models.interfaces.model import Updatable
from scenes.models.interfaces.interactable import Interactable
from scenes.ui.pages import Pages

from ui.elements.uiSlider import UiSlider
from ui.elements.uiButton import UiButton
from ui.elements.uiWrapper import UiWrapper
from ui.elements.uiText import UiText
from ui.constraintManager import *
from ui.uiHelper import *
from utils.interfaces.pollController import PollController
from utils.debug import *
from utils.kukaiiwaIKSolver import ForwardKinematics, InverseKinematics, Configuration
from utils.mathHelper import rad2Deg, deg2Rad
from window import Window

import numpy as np
from asyncua import ua
import numpy as np
from scipy.spatial.transform import Rotation as R

class KukaRobot:

    def __init__(self, tmat, nid, rid, modelRenderer, hasGripper=True, hasForceVector=False):
        self.joints = [0,0,0,0,0,0,0]
        self.forceVector = np.array([0,0,0], dtype='float32')
        self.tmat = tmat
        self.nodeId = nid
        self.robotId = rid
        self.modelRenderer = modelRenderer
        self.hasGripper = hasGripper
        self.hasForceVector = hasForceVector
        self.colors = np.zeros((8,4), dtype='float32')
        self.isLinkedOpcua = True
        self.attach = None

        self.lastTmats = {}
        self.lastLinkTmats = None
        self.lastJoints = [0,0,0,0,0,0,-1]
        self.forceVectorEndpoint = None
        
        self.endPose = None
        self.lastEndPose = None

        self.lastForceColor = ()
        self.lastForceMat = None

        self.exists = True

        self.__loadModel()
        self.__setupConnections()
    
    @timing
    def __loadModel(self):
        self.modelKukaIds = []
        Robot1_T_0_ , Robot1_T_i_ = self.__T_KUKAiiwa14(self.joints)
        for i in range(0,8):
            mat = Robot1_T_0_[i].copy()
            self.modelKukaIds.append(self.modelRenderer.addModel(Assets.KUKA_IIWA14_MODEL[i], mat))
            self.modelRenderer.setColor(self.modelKukaIds[-1], self.colors[i])
        self.armModels = Assets.KUKA_IIWA14_MODEL
        if self.hasGripper:
            self.modelKukaIds.append(self.modelRenderer.addModel(Assets.GRIPPER, Robot1_T_0_[7].copy()))
            self.gripperModel = Assets.GRIPPER
            self.modelRenderer.setColor(self.modelKukaIds[-1], self.colors[-1])
        self.forceVectorId = None
        if self.hasForceVector:
            self.forceVectorId = self.modelRenderer.addModel(Assets.POLE, np.identity(4))
            self.forceModel = Assets.POLE
            self.modelRenderer.setColor(self.forceVectorId, (0,0,0,0.7))
        for id in self.modelKukaIds:
            self.lastTmats[id] = None
        self.lastLinkTmats = Robot1_T_0_.copy()
        self.exists = True
    
    def __getNodeName(self, name):
        return f'ns={self.nodeId};s={self.robotId}{name}'

    def __setupConnections(self):
        self.opcuaReceiverContainer = OpcuaContainer()
        self.receivers = []
        self.receivers.append(OpcuaReceiver([ 
                    self.__getNodeName('d_Joi1'),
                    self.__getNodeName('d_Joi2'),
                    self.__getNodeName('d_Joi3'),
                    self.__getNodeName('d_Joi4'),
                    self.__getNodeName('d_Joi5'),
                    self.__getNodeName('d_Joi6'),
                    self.__getNodeName('d_Joi7'),
                ], self.opcuaReceiverContainer, Constants.OPCUA_LOCATION))
        self.receivers.append(OpcuaReceiver([ 
                    self.__getNodeName('d_ForX'),
                    self.__getNodeName('d_ForY'),
                    self.__getNodeName('d_ForZ'),
                ], self.opcuaReceiverContainer, Constants.OPCUA_LOCATION))
        self.receivers.append(OpcuaReceiver([
                    self.__getNodeName('d_PosX'),
                    self.__getNodeName('d_PosY'),
                    self.__getNodeName('d_PosZ'),
                    self.__getNodeName('d_RotA'),
                    self.__getNodeName('d_RotB'),
                    self.__getNodeName('d_RotC'),
                ], self.opcuaReceiverContainer, Constants.OPCUA_LOCATION))
    
    @funcProfiler(ftype='kukaupdate')
    def update(self, delta):
        self.__updateFromOpcua()
        self.__updateJoints()
        if self.endPose is not None:
            self.__updateForceVector(self.endPose)
    
    def __updateFromOpcua(self):
        if not self.isLinkedOpcua: return
        for i in range(7):
            nodename = self.__getNodeName(f'd_Joi{i+1}')
            if self.opcuaReceiverContainer.hasUpdated(nodename):
                self.joints[i] = radians(self.opcuaReceiverContainer.getValue(nodename, default=0)[0])

        if (self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_ForX')) and
            self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_ForY')) and
            self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_ForZ'))):
            self.forceVector[0] = self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_ForX'), default=0)[0]
            self.forceVector[1] = self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_ForY'), default=0)[0]
            self.forceVector[2] = self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_ForZ'), default=0)[0]
        if (self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_PosX')) and
            self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_PosY')) and
            self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_PosZ')) and
            self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_RotA')) and
            self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_RotB')) and
            self.opcuaReceiverContainer.hasUpdated(self.__getNodeName(f'd_RotC'))):
            pos =  (self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_PosX'), default=0)[0]/1000,
                    self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_PosY'), default=0)[0]/1000,
                    self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_PosZ'), default=0)[0]/1000)
            rot =  (self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_RotA'), default=0)[0],
                    self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_RotB'), default=0)[0],
                    self.opcuaReceiverContainer.getValue(self.__getNodeName(f'd_RotC'), default=0)[0])
            self.endPose = createTransformationMatrix(*pos, *rot)
    
    def __updateJoints(self):
        if not self.exists: return
        attachFrame = self.attach.getFrame() if self.attach else np.identity(4)
        Robot1_T_0_ = self.lastLinkTmats.copy()
        if not np.array_equal(self.lastJoints, self.joints):
            Robot1_T_0_ , Robot1_T_i_ = self.__T_KUKAiiwa14(self.joints)
            self.lastLinkTmats = Robot1_T_0_.copy()
            self.lastJoints = self.joints.copy()
        
        for i,id in enumerate(self.modelKukaIds):
            mat = Robot1_T_0_[min(i, len(Robot1_T_0_)-1)].copy()
            mat = np.matmul(self.tmat, mat)
            mat = np.matmul(attachFrame, mat)
            hashed = hash(bytes(mat))
            if hashed == self.lastTmats[id]:
                continue
            self.modelRenderer.setTransformMatrix(id, mat)
            self.lastTmats[id] = hashed
        
        self.endPose = Robot1_T_0_[-1]
    
    def __updateUsingPose(self):
        print("update")

        pose, nsparam, rconf, _ = ForwardKinematics(self.joints)
        joints, _, _ = InverseKinematics(pose, nsparam, rconf)

        print(self.joints)
        print(joints)

        return self.joints

    def __updateForceVector(self, transform):
        attachFrame = self.attach.getFrame() if self.attach else np.identity(4)
        if not self.hasForceVector or self.forceVectorId == None: return
        if not self.isLinkedOpcua:
            self.modelRenderer.setColor(self.forceVectorId, (0,0,0,0))
            return
        forceMag = np.linalg.norm(self.forceVector)
        if forceMag < 3.5:
            if self.lastForceColor != (0,0,0,0):
                self.modelRenderer.setColor(self.forceVectorId, (0,0,0,0))
                self.lastForceColor = (0,0,0,0)
            return
        forceTransform = vectorTransform(transform[:3,3], transform[:3,3]+2*self.forceVector, 1, upperLimit=100)
        forceTransform = np.matmul(self.tmat, forceTransform)
        forceTransform = np.matmul(attachFrame, forceTransform)
        if self.lastForceColor != (0,0,0,0.7):
            self.modelRenderer.setColor(self.forceVectorId, (0,0,0,0.7))
            self.lastForceColor = (0,0,0,0.7)
        if self.lastForceMat != hash(bytes(forceTransform)):
            self.modelRenderer.setTransformMatrix(self.forceVectorId, forceTransform)
            self.lastForceMat = hash(bytes(forceTransform))

    @timing
    def start(self):
        if not self.isLinkedOpcua:return
        for r in self.receivers: r.start()

    @timing
    def stop(self):
        for r in self.receivers: r.stop()

    def __DH(self, DH_table):
        T_0_ = np.ndarray(shape=(len(DH_table)+1,4,4))
        T_0_[:][:][0] = np.eye(4)
        T_i_ = np.ndarray(shape=(len(DH_table),4,4))
        for i in range(len(DH_table)):
            alp = DH_table[i][0]
            a = DH_table[i][1]
            d = DH_table[i][2]
            the = DH_table[i][3]

            T = np.array([[np.cos(the)            ,-np.sin(the)           ,0           ,a             ],
                          [np.sin(the)*np.cos(alp),np.cos(the)*np.cos(alp),-np.sin(alp),-np.sin(alp)*d],
                          [np.sin(the)*np.sin(alp),np.cos(the)*np.sin(alp),np.cos(alp) ,np.cos(alp)*d ],
                          [0                      ,0                      ,0           ,1             ]])

            T_0_[:][:][i+1] = np.matmul(T_0_[:][:][i],T)
            T_i_[:][:][i] = T
        return T_0_ ,T_i_

    def __T_KUKAiiwa14(self, q):
        DH_Robot1 = np.array([[0, 0, 0.36, q[0]], 
            [-np.pi/2, 0, 0 , q[1]],
            [np.pi/2, 0, 0.42 , q[2]],
            [np.pi/2, 0, 0, q[3]],
            [-np.pi/2, 0, 0.4, q[4]],
            [-np.pi/2, 0, 0, q[5]],
            [np.pi/2, 0, 0.15194, q[6]]])

        Robot1_T_0_ , Robot1_T_i_ = self.__DH(DH_Robot1)
        return Robot1_T_0_ , Robot1_T_i_

    def setColors(self, colors):
        self.colors = colors
        if not self.exists: return
        for i,id in enumerate(self.modelKukaIds):
            self.modelRenderer.setColor(id, self.colors[min(i,len(colors)-1)])

    def disconnectOpcua(self):
        self.isLinkedOpcua = False
        self.stop()

    def connectOpcua(self):
        self.isLinkedOpcua = True
        self.start()

    def setJoints(self, angles):
        self.joints = angles

    def getJoints(self):
        return self.joints

    def isModel(self, modelId):
        return modelId in self.modelKukaIds

    def getColors(self):
        return self.colors

    def setPos(self, tmat):
        self.tmat = tmat
        self.__updateJoints()

    def setAttach(self, iModel):
        self.attach = iModel
        self.__updateJoints()

    def inViewFrustrum(self, proj, view):
        attachFrame = self.attach.getFrame() if self.attach else np.identity(4)
        frustum = getFrustum(np.matmul(proj.T,view))
        bounds = []
        for i,m in enumerate(self.armModels):
            mat = self.lastLinkTmats[min(i, len(self.lastLinkTmats)-1)].copy()
            mat = np.matmul(self.tmat, mat)
            mat = np.matmul(attachFrame, mat)
            bounds.append(m.getAABBBound(mat))
        mat = self.lastLinkTmats[-1].copy()
        mat = np.matmul(self.tmat, mat)
        mat = np.matmul(attachFrame, mat)
        if self.hasGripper:
            bounds.append(self.gripperModel.getAABBBound(mat))
        if self.hasForceVector:
            bounds.append(self.forceModel.getAABBBound(mat))

        for b in bounds:
            dists = np.matmul(b, frustum.T)
            if not np.any(np.all(dists < 0, axis=0)): return True
            # dists = np.dot(frustum[:,0:3],b[0])+frustum[:,3]+b[1]
            # if np.all(dists>=0): return True
        return False

    def setViewFlag(self, flag):
        if not self.exists: return
        for id in self.modelKukaIds:
            self.modelRenderer.setViewFlag(id, flag)
        if self.forceVectorId:
            self.modelRenderer.setViewFlag(self.forceVectorId, flag)

    @timing
    def remove(self):
        if not self.exists: return
        for id in self.modelKukaIds:
            self.modelRenderer.removeModel(id)
        if self.forceVectorId:
            self.modelRenderer.removeModel(self.forceVectorId)
        self.exists = False
    
    @timing
    def add(self):
        self.__loadModel()

class KukaRobotTwin(Updatable, Interactable, PollController):

    FREE_MOVE_PROG = 2

    FOWARD_KINEMATICS = 0
    INVERSE_KINEMATICS = 1

    def __init__(self, window, tmat, nid, rid, modelRenderer, hasGripper=True, hasForceVector=False):
        self.liveRobot = KukaRobot(tmat, nid, rid, modelRenderer, hasGripper, hasForceVector)
        self.twinRobot = KukaRobot(tmat, nid, rid, modelRenderer, hasGripper, False)
        self.renderer = modelRenderer

        self.window = window
        self.nodeId = nid
        self.robotId = rid

        self.mode = KukaRobotTwin.FOWARD_KINEMATICS

        self.liveJoints = self.liveRobot.getJoints().copy()
        self.twinJoints = self.twinRobot.getJoints().copy()

        self.twinPose = np.identity(4)
        self.twinNSParam = 0
        self.twinTurn = 0
        self.livePose = np.identity(4)
        self.liveNSParam = 0
        self.liveTurn = 0

        self.hasMoved = True

        self.twinRobot.disconnectOpcua()

        self.matchLive = True

        self.progStartFlag = False
        self.executingFlag = False
        self.doneFlag = False

        self.inView = True
        self.viewCheckFrame = -1

        self.__createUi()
        self.__setupConnections()
        self.twinRobot.remove()
    
    def __getNodeName(self, name):
        return f'ns={self.nodeId};s={self.robotId}{name}'

    def __setupConnections(self):
        self.opcuaReceiverContainer = OpcuaContainer()
        self.opcuaTransmitterContainer = OpcuaContainer()
        self.progControlReceiver = OpcuaReceiver([
                    self.__getNodeName('c_ProgID'),
                    self.__getNodeName('c_Start'),
                    self.__getNodeName('f_Ready'),
                    self.__getNodeName('f_End'),
                ], self.opcuaReceiverContainer, Constants.OPCUA_LOCATION, pollingRate=5)
        self.transmitter = OpcuaTransmitter(self.opcuaTransmitterContainer, Constants.OPCUA_LOCATION, pollingRate=5)

    def __createUi(self):
        self.pages = Pages(self.window, Constraints.ALIGN_PERCENTAGE(0, 0, 1, 1))
        self.pages.addPage()
        self.pages.addPage()
        self.pages.addPage()

        self.sendBtn, self.sendBtnText = centeredTextButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0.5, 0.9, 0.5, 0.1, 5))
        self.sendBtnText.setText('Execute')
        self.sendBtnText.setFontSize(20)
        self.sendBtnText.setTextSpacing(8)
        self.sendBtn.setDefaultColor((0,109/255,174/255))
        self.sendBtn.setHoverColor((0,159/255,218/255))
        self.sendBtn.setPressColor((0,172/255,62/255))
        self.sendBtn.setLockColor((0.6, 0.6, 0.6))
        
        self.unlinkBtn, self.unlinkBtnText = centeredTextButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0.0, 0.9, 0.5, 0.1, 5))
        self.unlinkBtnText.setText('Unlink')
        self.unlinkBtnText.setFontSize(20)
        self.unlinkBtnText.setTextSpacing(8)
        self.unlinkBtn.setDefaultColor((0,109/255,174/255))
        self.unlinkBtn.setHoverColor((0,159/255,218/255))
        self.unlinkBtn.setPressColor((0,172/255,62/255))
        self.unlinkBtn.setLockColor((0.6, 0.6, 0.6))

        self.__createPage0()
        self.__createPage1()
    
    def __createPage0(self):
        self.page0 = self.pages.getPage(0)
        self.p0title = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0.5, 0.05))
        self.p0title.setText('Joint Control')
        self.p0title.setTextColor((1,1,1))
        self.p0title.setFontSize(28)
        self.page0.addChild(self.p0title)

        self.P0Wrappers = [None]*7
        for i in range(len(self.P0Wrappers)):
            self.P0Wrappers[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0, 0.1*i+0.1, 1, 0.1, 5))
        self.page0.addChildren(*self.P0Wrappers)

        self.liveTextWrapper = [None]*len(self.P0Wrappers)
        self.liveAngleText = [None]*len(self.P0Wrappers)
        self.twinTextWrapper = [None]*len(self.P0Wrappers)
        self.twinAngleText = [None]*len(self.P0Wrappers)

        self.jointAngleSlider = [None]*len(self.P0Wrappers)
        for i in range(len(self.P0Wrappers)):
            self.liveTextWrapper[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0, 0, 0.5, 0.5))
            self.twinTextWrapper[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0.5, 0, 0.5, 0.5))
            self.P0Wrappers[i].addChild(self.liveTextWrapper[i])
            self.P0Wrappers[i].addChild(self.twinTextWrapper[i])
            self.liveAngleText[i] = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
            self.liveAngleText[i].setFontSize(18)
            self.liveAngleText[i].setTextSpacing(7)
            self.twinAngleText[i] = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
            self.twinAngleText[i].setFontSize(18)
            self.twinAngleText[i].setTextSpacing(7)
            self.liveTextWrapper[i].addChild(self.liveAngleText[i])
            self.twinTextWrapper[i].addChild(self.twinAngleText[i])
            self.jointAngleSlider[i] = UiSlider(self.window, Constraints.ALIGN_PERCENTAGE(0, 0.5, 1, 0.5))
            self.jointAngleSlider[i].setRange(-pi, pi)
            self.jointAngleSlider[i].setBaseColor((1,1,1))
            self.jointAngleSlider[i].setSliderColor((0,109/255,174/255))
            self.jointAngleSlider[i].setSliderPercentage(0.05)
            self.P0Wrappers[i].addChild(self.jointAngleSlider[i])
        
        self.page0.addChild(self.sendBtn)
        self.page0.addChild(self.unlinkBtn)

    def __createPage1(self):
        self.page1 = self.pages.getPage(1)
        self.p1title = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0.5, 0.05))
        self.p1title.setText('Inverse Kinematics')
        self.p1title.setTextColor((1,1,1))
        self.p1title.setFontSize(28)
        self.page1.addChild(self.p1title)

        self.P1Wrappers = [None]*7
        for i in range(len(self.P1Wrappers)):
            self.P1Wrappers[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0, 0.1*i+0.1, 1, 0.1, 5))
        self.page1.addChildren(*self.P1Wrappers)

        self.liveTextWrapper = [None]*7
        self.livePosText = [None]*3
        self.twinTextWrapper = [None]*7
        self.twinPosText = [None]*3
        self.posSlider = [None]*3
        for i in range(3):
            self.liveTextWrapper[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0, 0, 0.5, 0.5))
            self.twinTextWrapper[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0.5, 0, 0.5, 0.5))
            self.P1Wrappers[i].addChild(self.liveTextWrapper[i])
            self.P1Wrappers[i].addChild(self.twinTextWrapper[i])
            self.livePosText[i] = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
            self.livePosText[i].setFontSize(18)
            self.livePosText[i].setTextSpacing(7)
            self.twinPosText[i] = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
            self.twinPosText[i].setFontSize(18)
            self.twinPosText[i].setTextSpacing(7)
            self.liveTextWrapper[i].addChild(self.livePosText[i])
            self.twinTextWrapper[i].addChild(self.twinPosText[i])
            self.posSlider[i] = UiSlider(self.window, Constraints.ALIGN_PERCENTAGE(0, 0.5, 1, 0.5))
            self.posSlider[i].setBaseColor((1,1,1))
            self.posSlider[i].setSliderColor((0,109/255,174/255))
            self.posSlider[i].setSliderPercentage(0.05)
            self.P1Wrappers[i].addChild(self.posSlider[i])
        
        self.posSlider[0].setRange(-(0.42+0.4+0.15194),0.42+0.4+0.15194)
        self.posSlider[1].setRange(-(0.42+0.4+0.15194),0.42+0.4+0.15194)
        self.posSlider[2].setRange(-(0.42+0.4+0.15194)+0.36,0.42+0.4+0.15194+0.36)

        self.liveRotText = [None]*3
        self.twinRotText = [None]*3
        self.rotSlider = [None]*3
        for i in range(3, 6):
            self.liveTextWrapper[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0, 0, 0.5, 0.5))
            self.twinTextWrapper[i] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0.5, 0, 0.5, 0.5))
            self.P1Wrappers[i].addChild(self.liveTextWrapper[i])
            self.P1Wrappers[i].addChild(self.twinTextWrapper[i])
            self.liveRotText[i-3] = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
            self.liveRotText[i-3].setFontSize(18)
            self.liveRotText[i-3].setTextSpacing(7)
            self.twinRotText[i-3] = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
            self.twinRotText[i-3].setFontSize(18)
            self.twinRotText[i-3].setTextSpacing(7)
            self.liveTextWrapper[i].addChild(self.liveRotText[i-3])
            self.twinTextWrapper[i].addChild(self.twinRotText[i-3])
            self.rotSlider[i-3] = UiSlider(self.window, Constraints.ALIGN_PERCENTAGE(0, 0.5, 1, 0.5))
            self.rotSlider[i-3].setRange(-pi, pi)
            self.rotSlider[i-3].setBaseColor((1,1,1))
            self.rotSlider[i-3].setSliderColor((0,109/255,174/255))
            self.rotSlider[i-3].setSliderPercentage(0.05)
            self.P1Wrappers[i].addChild(self.rotSlider[i-3])
        self.rotSlider[1].setRange(-pi/2, pi/2)

        self.liveTextWrapper[6] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0, 0, 0.5, 0.5))
        self.twinTextWrapper[6] = UiWrapper(self.window, Constraints.ALIGN_PERCENTAGE(0.5, 0, 0.5, 0.5))
        self.P1Wrappers[6].addChild(self.liveTextWrapper[6])
        self.P1Wrappers[6].addChild(self.twinTextWrapper[6])
        self.liveNSParamText = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
        self.liveNSParamText.setFontSize(18)
        self.liveNSParamText.setTextSpacing(7)
        self.twinNSParamText = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0, 0.5))
        self.twinNSParamText.setFontSize(18)
        self.twinNSParamText.setTextSpacing(7)
        self.liveTextWrapper[6].addChild(self.liveNSParamText)
        self.twinTextWrapper[6].addChild(self.twinNSParamText)
        self.NSParamSlider = UiSlider(self.window, Constraints.ALIGN_PERCENTAGE(0, 0.5, 1, 0.5))
        self.NSParamSlider.setRange(-pi, pi)
        self.NSParamSlider.setBaseColor((1,1,1))
        self.NSParamSlider.setSliderColor((0,109/255,174/255))
        self.NSParamSlider.setSliderPercentage(0.05)
        self.P1Wrappers[6].addChild(self.NSParamSlider)

        self.armTurnBtn, self.armTurnText = centeredTextToggleButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0/3, 0.8, 1/3, 0.1, 5))
        self.armTurnText.setFontSize(17)
        self.armTurnText.setTextSpacing(7)
        self.armTurnBtn.setUntoggleColor((0,109/255,174/255))
        self.armTurnBtn.setToggleColor((0,69/255,134/255))
        self.armTurnBtn.setLockColor((0.6, 0.6, 0.6))

        self.elbowTurnBtn, self.elbowTurnText = centeredTextToggleButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(1/3, 0.8, 1/3, 0.1, 5))
        self.elbowTurnText.setFontSize(18)
        self.elbowTurnText.setTextSpacing(7)
        self.elbowTurnBtn.setUntoggleColor((0,109/255,174/255))
        self.elbowTurnBtn.setToggleColor((0,69/255,134/255))
        self.elbowTurnBtn.setLockColor((0.6, 0.6, 0.6))

        self.wristTurnBtn, self.wristTurnText = centeredTextToggleButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(2/3, 0.8, 1/3, 0.1, 5))
        self.wristTurnText.setFontSize(18)
        self.wristTurnText.setTextSpacing(7)    
        self.wristTurnBtn.setUntoggleColor((0,109/255,174/255))
        self.wristTurnBtn.setToggleColor((0,69/255,134/255))
        self.wristTurnBtn.setLockColor((0.6, 0.6, 0.6)) 

        self.page1.addChild(self.armTurnBtn)
        self.page1.addChild(self.elbowTurnBtn)
        self.page1.addChild(self.wristTurnBtn)

        # self.page1.addChild(self.sendBtn)
        # self.page1.addChild(self.unlinkBtn)

    @funcProfiler(ftype='kukaupdate')
    def update(self, delta):
        self.liveRobot.update(delta)
        self.twinRobot.update(delta)
        
        if not np.array_equal(self.liveJoints, self.liveRobot.getJoints()): self.hasMoved = True

        self.__updateProgram()

        self.liveJoints = self.liveRobot.getJoints().copy()
        self.__syncModes()
        self.__syncLive()
        self.__updateMode()
        self.__updateGui()
        self.__updateJoints()
        self.hasMoved = False
    
    def __updateProgram(self):
        if not self.opcuaReceiverContainer.getValue(self.__getNodeName('f_Ready'), default=False)[0]:
            self.sendBtn.lock()
        if self.progStartFlag:
            self.sendBtn.lock()
            self.unlinkBtn.lock()
            self.sendBtnText.setText('Waiting')
            if self.__isTransmitClear():
                self.executingFlag = True
                self.progStartFlag = False
                self.opcuaTransmitterContainer.setValue(self.__getNodeName('c_Start'), True, ua.VariantType.Boolean)
        elif self.executingFlag:
            self.sendBtn.lock()
            self.unlinkBtn.lock()
            self.sendBtnText.setText('Executing')
            if self.opcuaReceiverContainer.getValue(self.__getNodeName('c_ProgID'), default=KukaRobotTwin.FREE_MOVE_PROG)[0] == 0:
                self.doneFlag = True
                self.executingFlag = False
        elif self.doneFlag:
            self.doneFlag = False
            self.sendBtn.unlock()
            self.unlinkBtn.unlock()
            self.matchLive = True
            self.unlinkBtnText.setText('Unlink')
            self.sendBtnText.setText('Execute')
            self.__toggleTwin()
        elif self.opcuaReceiverContainer.getValue(self.__getNodeName('f_Ready'), default=False)[0]:
            self.sendBtn.unlock()
    
    def __syncModes(self):
        if self.matchLive: return
        if self.mode == KukaRobotTwin.FOWARD_KINEMATICS:
            for i in range(7):
                self.twinJoints[i] = self.jointAngleSlider[i].getValue()
            try:
                self.twinPose, self.twinNSParam, self.twinTurn, _ = ForwardKinematics(self.twinJoints)
            except:
                pass
        elif self.mode == KukaRobotTwin.INVERSE_KINEMATICS:
            r = R.from_euler('xyz',[
                self.rotSlider[2].getValue(),
                self.rotSlider[1].getValue(),
                self.rotSlider[0].getValue()],degrees=False)
            self.twinPose[:3,:3] = r.as_matrix()
            self.twinPose[0,3] = self.posSlider[0].getValue()
            self.twinPose[1,3] = self.posSlider[1].getValue()
            self.twinPose[2,3] = self.posSlider[2].getValue()
            self.twinNSParam = self.NSParamSlider.getValue()
            self.twinTurn = setBit(self.twinTurn, 0, self.armTurnBtn.isToggled())
            self.twinTurn = setBit(self.twinTurn, 1, self.elbowTurnBtn.isToggled())
            self.twinTurn = setBit(self.twinTurn, 2, self.wristTurnBtn.isToggled())

            try:
                self.twinJoints, _, _ = InverseKinematics(self.twinPose, self.twinNSParam, self.twinTurn)
            except:
                try:
                    self.twinPose, self.twinNSParam, self.twinTurn, _ = ForwardKinematics(self.twinJoints)
                except:
                    pass
                pass

    def __syncLive(self):
        if not self.matchLive: return
        if not self.hasMoved: return
        self.mode = KukaRobotTwin.FOWARD_KINEMATICS
        if self.matchLive:
            self.twinJoints = self.liveRobot.getJoints().copy()
        try:
            self.livePose, self.liveNSParam, self.liveTurn, _ = ForwardKinematics(self.liveJoints)
            self.twinPose = self.livePose.copy()
            self.twinNSParam = self.liveNSParam
            self.twinTurn = self.liveTurn
        except AssertionError as msg: 
            pass
        except Exception as error:
            print(error)
            pass

    def __updateGui(self):
        for i in range(len(self.P0Wrappers)):
            self.jointAngleSlider[i].setValue(self.twinJoints[i])
            self.liveAngleText[i].setText(f'Live: {round(self.liveJoints[i]*180/pi)}')
            self.twinAngleText[i].setText(f'Twin: {round(self.twinJoints[i]*180/pi)}')
        
        if self.twinPose is not None and self.twinNSParam is not None and self.twinTurn is not None:
            self.twinNSParamText.setText(f'Twin R: {round(rad2Deg(self.twinNSParam))}')
            self.twinPosText[0].setText(f'Twin X: {round(self.twinPose[0,3]*1000)}')
            self.twinPosText[1].setText(f'Twin Y: {round(self.twinPose[1,3]*1000)}')
            self.twinPosText[2].setText(f'Twin Z: {round(self.twinPose[2,3]*1000)}')

            r = R.from_matrix(self.twinPose[:3,:3])
            C, B, A = r.as_euler('xyz', degrees=False)

            arm, elbow, wrist = Configuration(self.twinTurn)
            self.armTurnText.setText(f'Arm: {arm}')
            self.elbowTurnText.setText(f'Elbow: {elbow}')
            self.wristTurnText.setText(f'Wrist: {wrist}')
            self.armTurnBtn.setToggle(arm != 1)
            self.elbowTurnBtn.setToggle(elbow != 1)
            self.wristTurnBtn.setToggle(wrist != 1)

            self.twinRotText[0].setText(f'Live A: {round(rad2Deg(A))}')
            self.twinRotText[1].setText(f'Live B: {round(rad2Deg(B))}')
            self.twinRotText[2].setText(f'Live C: {round(rad2Deg(C))}')
            
            self.rotSlider[0].setValue(A or 0)
            self.rotSlider[1].setValue(B or 0)
            self.rotSlider[2].setValue(C or 0)
            self.posSlider[0].setValue(self.twinPose[0,3])
            self.posSlider[1].setValue(self.twinPose[1,3])
            self.posSlider[2].setValue(self.twinPose[2,3])
            self.NSParamSlider.setValue(self.twinNSParam or 0)

        if self.livePose is not None and self.liveNSParam is not None and self.liveTurn is not None:
            self.liveNSParamText.setText(f'Live R: {round(rad2Deg(self.liveNSParam))}')
            self.livePosText[0].setText(f'Live X: {round(self.livePose[0,3]*1000)}')
            self.livePosText[1].setText(f'Live Y: {round(self.livePose[1,3]*1000)}')
            self.livePosText[2].setText(f'Live Z: {round(self.livePose[2,3]*1000)}')

            A = np.arctan2(self.livePose[1,0], self.livePose[0,0])
            B = np.arcsin(-self.livePose[2,0])
            C = np.arctan2(self.livePose[2,1], self.livePose[2,2])

            self.liveRotText[0].setText(f'Live A: {round(rad2Deg(A))}')
            self.liveRotText[1].setText(f'Live B: {round(rad2Deg(B))}')
            self.liveRotText[2].setText(f'Live C: {round(rad2Deg(C))}')
    
    def __updateJoints(self):
        self.twinRobot.setJoints(self.twinJoints)

    def __updateMode(self):
        li = lambda x:x.lastInteracted
        li1 = max(map(li, self.jointAngleSlider))
        li2 = max(max(map(li, self.rotSlider)), 
                  max(map(li, self.posSlider)), 
                  li(self.NSParamSlider),
                  li(self.armTurnBtn),
                  li(self.elbowTurnBtn),
                  li(self.wristTurnBtn))
        if li1 > li2:
            self.mode = KukaRobotTwin.FOWARD_KINEMATICS
        else:
            self.mode = KukaRobotTwin.INVERSE_KINEMATICS

    def handleEvents(self, event):
        self.pages.handleEvents(event)
        if event['action'] == 'release':
            if event['obj'] == self.sendBtn:
                self.sendBtn.lock()
                for i in range(len(self.twinJoints)):
                    self.opcuaTransmitterContainer.setValue(self.__getNodeName(f'c_Joi{i+1}'), self.twinJoints[i]*180/pi, ua.VariantType.Double)
                self.opcuaTransmitterContainer.setValue(self.__getNodeName(f'c_ProgID'), KukaRobotTwin.FREE_MOVE_PROG, ua.VariantType.Int32)
                self.progStartFlag = True
            if event['obj'] == self.unlinkBtn:
                self.__toggleLink()

    def __toggleLink(self):
        self.matchLive = not self.matchLive
        self.unlinkBtnText.setText('Unlink' if self.matchLive else 'Link')
        self.hasMoved = True
        self.__toggleTwin()

    def setLiveColors(self, colors):
        self.liveRobot.setColors(colors)

    def setTwinColors(self, colors):
        self.twinRobot.setColors(colors)

    @timing
    def start(self):
        self.liveRobot.start()
        self.twinRobot.start()
        self.progControlReceiver.start()
        self.transmitter.start()

    @timing
    def stop(self):
        self.liveRobot.stop()
        self.twinRobot.stop()
        self.progControlReceiver.stop()
        self.transmitter.stop()

    def getControlPanel(self):
        self.pages.refreshPage()
        return self.pages.getPageWrapper()

    def __isTransmitClear(self):
        for i in range(len(self.twinJoints)):
            if self.opcuaTransmitterContainer.hasUpdated(self.__getNodeName(f'c_Joi{i+1}')):
                return False
        if self.opcuaTransmitterContainer.hasUpdated(self.__getNodeName('c_ProgID')):
            return False
        if self.opcuaReceiverContainer.getValue(self.__getNodeName('c_ProgID'), default=0)[0] != KukaRobotTwin.FREE_MOVE_PROG:
            return False
        if not self.opcuaReceiverContainer.getValue(self.__getNodeName('f_Ready'), default=False)[0]:
            return False
        return True

    def __toggleTwin(self):
        colors = self.twinRobot.getColors()
        if self.matchLive: self.twinRobot.remove()
        else: self.twinRobot.add()
        self.twinRobot.setColors([(*color[0:3], 0 if self.matchLive else 0.7) for color in colors])

    def isModel(self, modelId):
        return self.twinRobot.isModel(modelId) or self.liveRobot.isModel(modelId)

    def setPos(self, pos):
        self.liveRobot.setPos(pos)
        self.twinRobot.setPos(pos)
    
    def getPos(self):
        return self.liveRobot.pos

    def setAttach(self, mat):
        self.liveRobot.setAttach(mat)
        self.twinRobot.setAttach(mat)

    def setTransform(self, transform):
        self.liveRobot.setPos(transform)
        self.twinRobot.setPos(transform)

    def inViewFrustrum(self, proj, view):
        if self.viewCheckFrame == Window.INSTANCE.frameCount: return self.inView
        self.inView = self.liveRobot.inViewFrustrum(proj, view) or self.twinRobot.inViewFrustrum(proj, view)
        self.viewCheckFrame = Window.INSTANCE.frameCount
        return self.inView

    def setViewFlag(self, flag):
        self.liveRobot.setViewFlag(flag)
        self.twinRobot.setViewFlag(flag)



