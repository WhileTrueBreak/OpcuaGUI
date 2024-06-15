from ui.glElement import GlElement
from ui.uiRenderer import UiRenderer
from utils.transform import Transform
from utils.debug import *

from asset import *

import ctypes

class UiButton(GlElement):
    def __init__(self, window, constraints, dim=(0,0,0,0)):
        super().__init__(window, constraints, dim)
        self.type = 'button'

        self.mask = None
        self.currentColor = (1, 1, 1)
        self.defaultColor = (1, 1, 1)
        self.hoverColor = (1, 1, 1)
        self.pressColor = (1, 1, 1)
        self.lockColor = (1, 1, 1)

        self.renderer = UiRenderer.fromColor(self.currentColor, Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.renderers.append(self.renderer)

        self.lockFlag = False

    def reshape(self):
        self.renderer.setColor(self.currentColor)
        self.renderer.setTexture(self.mask)
        self.renderer.getTransform().setPos((self.openGLDim[0:2]))
        self.renderer.getTransform().setSize((self.openGLDim[2:4]))
        self.renderer.setDirtyVertex()
        return

    @funcProfiler(ftype='uiupdate')
    def update(self, delta):
        return

    def __setColor(self, color):
        if self.currentColor == color:
            return
        self.currentColor = color
        self.reshape()
        return

    def setDefaultColor(self, color):
        self.defaultColor = color

    def setHoverColor(self, color):
        self.hoverColor = color

    def setPressColor(self, color):
        self.pressColor = color

    def setLockColor(self, color):
        self.lockColor = color
    
    def setMaskingTexture(self, texture):
        self.mask = texture
        self.reshape()

    def onDefault(self, callback=None):
        if self.lockFlag: return
        self.__setColor(self.defaultColor)
    
    def onHover(self, callback=None):
        if self.lockFlag: return
        self.__setColor(self.hoverColor)
    
    def onHeld(self, callback=None):
        if self.lockFlag: return
        self.__setColor(self.pressColor)

    def onPress(self, callback=None):
        if self.lockFlag: return
        self.window.uiEvents.append({'obj':self, 'action':'press', 'type':self.type, 'time':time.time_ns()})
    
    def onRelease(self, callback=None):
        if self.lockFlag: return
        self.window.uiEvents.append({'obj':self, 'action':'release', 'type':self.type, 'time':time.time_ns()})

    def lock(self):
        self.lockFlag = True
        self.__setColor(self.lockColor)
        
    def unlock(self):
        self.lockFlag = False
        self.__setColor(self.defaultColor)
        