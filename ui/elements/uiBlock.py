from ui.glElement import GlElement
from ui.uiRenderer import UiRenderer

from utils.debug import *
from utils.transform import Transform

from asset import *

import ctypes

class UiBlock(GlElement):
    def __init__(self, window, constraints, dim=(0,0,0,0)):
        super().__init__(window, constraints, dim)
        self.type = 'block'

        self.color = (1, 1, 1)
        self.texture = None

        self.renderer = UiRenderer.fromColor(self.color, Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.renderers.append(self.renderer)

        self.lockFlag = False

    def reshape(self):
        self.renderer.setColor(self.color)
        self.renderer.setTexture(self.texture)
        self.renderer.getTransform().setPos((self.openGLDim[0:2]))
        self.renderer.getTransform().setSize((self.openGLDim[2:4]))
        self.renderer.setDirtyVertex()
        return

    @funcProfiler(ftype='uiupdate')
    def update(self, delta):
        return

    def setColor(self, color):
        if self.color == color:
            return
        self.color = color
        self.reshape()
        return

    def setTexture(self, texture):
        if self.texture == texture:
            return
        self.texture = texture
        self.reshape()
