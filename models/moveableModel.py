from asset import *

from scenes.ui.pages import Pages
from models.interfaces.model import SimpleModel, Updatable
from models.interfaces.interactable import Interactable

from ui.constraintManager import *
from ui.elements.uiButton import UiButton
from ui.elements.uiBlock import UiBlock
from ui.elements.ui3dScene import Ui3DScene
from ui.elements.uiStream import UiStream
from ui.elements.uiWrapper import UiWrapper
from ui.elements.uiText import UiText
from ui.elements.uiSlider import UiSlider

from functools import lru_cache
import numpy as np

class MoveableModel(SimpleModel, Updatable, Interactable):

    @timing
    def __init__(self, window, renderer, model, transform):
        super().__init__(renderer, model, transform)

        self.window = window
        self.attach = None

        self.__createUi()
        return

    @timing
    def __createUi(self):
        self.pages = Pages(self.window, Constraints.ALIGN_PERCENTAGE(0, 0, 1, 1))
        self.pages.addPage()
        movePage = self.pages.getPage(0)
        self.title = UiText(self.window, Constraints.ALIGN_CENTER_PERCENTAGE(0.5, 0.05))
        self.title.setText('Move')
        self.title.setTextColor((1,1,1))
        self.title.setFontSize(28)
        movePage.addChild(self.title)

        wrapper = UiWrapper(self.window, [
            *Constraints.ALIGN_CENTER,
            RELATIVE(T_W, 1, P_W),
            RELATIVE(T_H, 4/3, T_W),
        ])
        movePage.addChild(wrapper)
        
        self.tbuttons = []
        b_l = UiButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0.0,1/4,1/3,1/4,2))
        b_l.setMaskingTexture(Assets.LEFT_ARROW.getTexture())
        self.tbuttons.append(b_l)
        b_u = UiButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(1/3,0.0,1/3,1/4,2))
        b_u.setMaskingTexture(Assets.UP_ARROW.getTexture())
        self.tbuttons.append(b_u)
        b_d = UiButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(1/3,2/4,1/3,1/4,2))
        b_d.setMaskingTexture(Assets.DOWN_ARROW.getTexture())
        self.tbuttons.append(b_d)
        b_r = UiButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(2/3,1/4,1/3,1/4,2))
        b_r.setMaskingTexture(Assets.RIGHT_ARROW.getTexture())
        self.tbuttons.append(b_r)
        for btn in self.tbuttons:
            btn.setDefaultColor((0,109/255,174/255))
            btn.setHoverColor((0,159/255,218/255))
            btn.setPressColor((0,172/255,62/255))
        
        self.rbuttons = []
        b_rl = UiButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(0/3,3/4,1/3,1/4,2))
        b_rl.setMaskingTexture(Assets.LEFT_ARROW.getTexture())
        self.rbuttons.append(b_rl)
        b_rr = UiButton(self.window, Constraints.ALIGN_PERCENTAGE_PADDING(2/3,3/4,1/3,1/4,2))
        b_rr.setMaskingTexture(Assets.RIGHT_ARROW.getTexture())
        self.rbuttons.append(b_rr)
        for btn in self.rbuttons:
            btn.setDefaultColor((0,109/255,174/255))
            btn.setHoverColor((0,159/255,218/255))
            btn.setPressColor((0,172/255,62/255))
        wrapper.addChildren(*self.tbuttons)
        wrapper.addChildren(*self.rbuttons)
        return

    def update(self, delta):
        self.__pollMove(delta)
        return
    
    def __updateTranforms(self):
        attachFrame = self.attach.getFrame() if self.attach else np.identity(4)
        self.renderer.setTransformMatrix(self.modelId, np.matmul(attachFrame, self.transform))
        return

    def __pollMove(self, delta):
        for i in range(4):
            if not self.tbuttons[i].isPressed: continue
            self.__translate(i, delta)
        if self.rbuttons[0].isPressed:
            self.__rotate(-10*delta)
        if self.rbuttons[1].isPressed:
            self.__rotate(10*delta)

    def __translate(self, index, delta):
        d = 0.1*delta
        m = {0:(-d,0),1:(0,d),2:(0,-d),3:(d,0)}
        x,y,z = self.getPos()
        self.setPos((x+m[index][0], y+m[index][1], z))

    def __rotate(self, angle):
        self.transform = np.matmul(self.transform, createTransformationMatrix(0, 0, 0, 0, 0, angle))
        self.__updateTranforms()
        return
    
    def handleEvents(self, event):
        return
    
    def getControlPanel(self):
        return self.pages.getPageWrapper()

    def getPos(self):
        return self.transform[0:3,3]
    
    def setPos(self, pos):
        self.transform[0:3,3] = pos
        self.__updateTranforms()
        return

    def setAttach(self, iModel):
        self.attach = iModel
        self.__updateTranforms()
        return
    
    def setTransform(self, transform):
        self.transform = transform
        self.__updateTranforms()
