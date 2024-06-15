from ui.glElement import GlElement
from ui.uiRenderer import UiRenderer
from utils.transform import Transform
from utils.debug import *

from asset import *

import ctypes

class UiSlider(GlElement):
    def __init__(self, window, constraints, dim=(0,0,0,0)):
        super().__init__(window, constraints, dim)
        self.type = 'button'

        self.baseColor = (1, 1, 1)
        self.sliderColor = (0.3, 0.3, 0.3)

        self.lowerMap = 0
        self.upperMap = 1

        self.currentLoc = 0.5
        self.sliderWidth = 0.05

        self.baseRenderer = UiRenderer.fromColor(self.baseColor, Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.sliderRenderer = UiRenderer.fromColor(self.sliderColor, Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.renderers.append(self.baseRenderer)
        self.renderers.append(self.sliderRenderer)

    def reshape(self):
        sliderw = self.openGLDim[2]*self.sliderWidth
        sliderrange = self.openGLDim[2]-sliderw
        leftw = sliderrange*self.currentLoc
        sliderx = self.openGLDim[0]+leftw
        rightw = sliderrange*(1-self.currentLoc)#+sliderw
        rigthx = sliderx+sliderw

        self.baseRenderer.setColor(self.baseColor)
        self.baseRenderer.getTransform().setPos((self.openGLDim[0:2]))
        self.baseRenderer.getTransform().setSize((self.openGLDim[2:4]))
        self.baseRenderer.setDirtyVertex()

        self.sliderRenderer.setColor(self.sliderColor)
        self.sliderRenderer.getTransform().setPos((sliderx, self.openGLDim[1]))
        self.sliderRenderer.getTransform().setSize((sliderw, self.openGLDim[3]))
        self.sliderRenderer.setDirtyVertex()
        return

    @funcProfiler(ftype='uiupdate')
    def update(self, delta):
        return

    def setBaseColor(self, color):
        self.baseColor = color
        self.reshape()
        return

    def setSliderColor(self, color):
        self.sliderColor = color
        self.reshape()
        return
    
    def setSliderPercentage(self, width):
        self.sliderWidth = width
        self.reshape()

    def setRange(self, lower, upper):
        self.lowerMap = lower
        self.upperMap = upper
        self.reshape()

    def getValue(self):
        diff = self.upperMap - self.lowerMap
        return self.currentLoc * diff + self.lowerMap

    def setValue(self, value):
        diff = self.upperMap - self.lowerMap
        newV = (value - self.lowerMap)/diff
        if self.currentLoc == newV: return
        self.currentLoc = newV
        self.reshape()

    def onHeld(self, callback=None):
        sliderWidth = self.dim[2]*self.sliderWidth
        sliderrange = self.dim[2]-sliderWidth

        start = self.window.mousePos[0] - self.dim[0] - sliderWidth/2
        self.currentLoc = start/sliderrange
        self.currentLoc = max(0, min(1, self.currentLoc))
        self.reshape()
