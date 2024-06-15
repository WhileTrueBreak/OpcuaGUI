from ui.glElement import GlElement
from ui.uiRenderer import UiRenderer

from utils.mathHelper import *
from utils.transform import *
from utils.debug import *

from ui.ui3d.modelRenderer import *
from asset import *

class Ui3DScene(GlElement):
    def __init__(self, window, constraints, supportTransparency=True, dim=(0,0,0,0)):
        super().__init__(window, constraints, dim)

        self.hoveredObj = -1

        self.NEAR_PLANE = 0.01
        self.FAR_PLANE = 100
        self.FOV = 90

        self.backgroundColor = (0.15,0.15,0.15)

        self.modelRenderer = Renderer(self.window, supportTransparency=supportTransparency)
        self.modelRenderer.setProjectionMatrix(createProjectionMatrix(self.dim[2], self.dim[3], self.FOV, self.NEAR_PLANE, self.FAR_PLANE))
        self.modelRenderer.setViewMatrix(createViewMatrix(0, 0, 0, 0, 0, 0))

        self.sprite = Sprite.fromTexture(self.modelRenderer.getTexture())
        self.renderer = UiRenderer.fromSprite(self.sprite, Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.backgroundRenderer = UiRenderer.fromColor(self.backgroundColor, Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.renderers.append(self.backgroundRenderer)
        self.renderers.append(self.renderer)

        self.type = '3d scene'

    def reshape(self):
        self.renderer.getTransform().setPos((self.openGLDim[0:2]))
        self.renderer.getTransform().setSize((self.openGLDim[2:4]))
        self.backgroundRenderer.getTransform().setPos((self.openGLDim[0:2]))
        self.backgroundRenderer.getTransform().setSize((self.openGLDim[2:4]))
        self.backgroundRenderer.setColor(self.backgroundColor)
        self.renderer.setDirtyVertex()
        self.backgroundRenderer.setDirtyVertex()
        self.modelRenderer.setProjectionMatrix(createProjectionMatrix(self.dim[2], self.dim[3], self.FOV, self.NEAR_PLANE, self.FAR_PLANE))
        self.modelRenderer.updateCompositeLayers()
        return
    
    @funcProfiler(ftype='uiupdate')
    def update(self, delta):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glEnable(GL.GL_DEPTH_TEST)
        # GL.glViewport(int(self.dim[0]), int(self.window.dim[1]-self.dim[3]-self.dim[1]), int(self.dim[2]), int(self.dim[3]))
        self.modelRenderer.render()
        # GL.glViewport(0, 0, *self.window.dim)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)
        return

    def setViewMatrix(self, matrix):
        self.modelRenderer.setViewMatrix(matrix)
    
    def getRenderer(self):
        return self.modelRenderer

    def setBackgroundColor(self, color):
        self.backgroundColor = color
        self.reshape()
        return

    def onHover(self):
        relPos = [*self.window.getMousePos()]
        relPos[0] = (relPos[0]-self.dim[0])/self.dim[2]
        relPos[1] = (relPos[1]-self.dim[1])/self.dim[3]
        envPos = [int(self.window.dim[0]*relPos[0]), int(self.window.dim[1]-self.window.dim[1]*relPos[1])]
        data = self.modelRenderer.getScreenSpaceObj(*envPos)
        if (data[0], data[1]) == (4294967295, 4294967295):
            self.hoveredObj = None
            return
        if (data[1], data[0]) not in self.modelRenderer.idDict: 
            print(f'Error: invalid {data}')
            return -1
        self.hoveredObj = self.modelRenderer.idDict[(data[1], data[0])]

    def getHoveredObj(self):
        return self.hoveredObj

    def onPress(self, callback=None):
        if self.window.selectedUi != self: return
        self.window.uiEvents.append({'obj':self, 'action':'press', 'type':self.type, 'time':time.time_ns(), 'modelId':self.hoveredObj})
    
    def onRelease(self, callback=None):
        if self.window.selectedUi != self: return
        self.window.uiEvents.append({'obj':self, 'action':'release', 'type':self.type, 'time':time.time_ns(), 'modelId':self.hoveredObj})

    def getModelRenderer(self):
        return self.modelRenderer
