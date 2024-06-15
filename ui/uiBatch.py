from asset import Assets

from constants import Constants

from utils.debug import *

import OpenGL.GL as GL

import numpy as np
import ctypes

class UiBatch:

    POS_SIZE = 2
    POS_OFFSET = 0
    COLOR_SIZE = 4
    COLOR_OFFSET = POS_OFFSET+POS_SIZE
    UV_SIZE = 2
    UV_OFFSET = COLOR_OFFSET+COLOR_SIZE
    TEX_ID_SIZE = 1
    TEX_ID_OFFSET = UV_OFFSET+UV_SIZE
    UI_ID_SIZE = 1
    UI_ID_OFFSET = TEX_ID_OFFSET+TEX_ID_SIZE

    VERTEX_SIZE = POS_SIZE+COLOR_SIZE+UV_SIZE+TEX_ID_SIZE+UI_ID_SIZE

    NUM_VERTICES = 4
    NUM_ELEMENTS = 6

    def __init__(self, window, maxRenderers):
        self.window = window
        self.maxRenderers = maxRenderers
        self.maxTextures = Constants.MAX_TEXTURE_SLOTS

        self.numRenderers = 0
        self.uiRenderers = []

        self.vertices = np.zeros((self.maxRenderers*UiBatch.NUM_VERTICES, UiBatch.VERTEX_SIZE), dtype='float32')
        self.indices = self.__genDefaultIndices()
        self.textures = []

        self.textureIds = np.full((self.maxRenderers), -1, dtype='int32')
        
        self.rebufferData = False
        self.__initFrame()
        self.__initVertices()

    @timing
    def __initFrame(self):

        self.colorClear = np.array([0,0,0,0], dtype='float32')
        self.pickingClear = np.array([0,0,0], dtype='float32')

        self.renderFBO = GL.glGenFramebuffers(1)

        textureDim = self.window.dim

        self.screenTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.screenTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.pickingTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_R8UI, textureDim[0], textureDim[1], 0, GL.GL_RED_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.depthTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.depthTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, textureDim[0], textureDim[1], 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.renderFBO)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.screenTexture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT1, GL.GL_TEXTURE_2D, self.pickingTexture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.depthTexture, 0)

        self.renderDrawBuffers = (GL.GL_COLOR_ATTACHMENT0, GL.GL_COLOR_ATTACHMENT1)
        GL.glDrawBuffers(self.renderDrawBuffers)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    @timing
    def __initVertices(self):
        self.quadVertices = np.array([
            [-1,-1,-1, 0, 0],
            [ 1,-1,-1, 1, 0],
            [ 1, 1,-1, 1, 1],
            [ 1, 1,-1, 1, 1],
            [-1, 1,-1, 0, 1],
            [-1,-1,-1, 0, 0],
        ], dtype='float32')

        self.quadVAO = GL.glGenVertexArrays(1)
        self.quadVBO = GL.glGenBuffers(1)
        GL.glBindVertexArray(self.quadVAO)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quadVBO)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quadVertices.nbytes, self.quadVertices, GL.GL_DYNAMIC_DRAW)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 5 * 4, ctypes.c_void_p(0*4))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, GL.GL_FALSE, 5 * 4, ctypes.c_void_p(3*4))
        GL.glBindVertexArray(0)

        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        self.vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vertices, GL.GL_DYNAMIC_DRAW)

        self.ebo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.indices, GL.GL_DYNAMIC_DRAW)

        self.ssboTextureId = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssboTextureId)
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, self.textureIds, GL.GL_DYNAMIC_DRAW)
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, self.ssboTextureId)

        GL.glVertexAttribPointer(0, UiBatch.POS_SIZE, GL.GL_FLOAT, GL.GL_FALSE, UiBatch.VERTEX_SIZE*4, ctypes.c_void_p(UiBatch.POS_OFFSET*4))
        GL.glVertexAttribPointer(1, UiBatch.COLOR_SIZE, GL.GL_FLOAT, GL.GL_FALSE, UiBatch.VERTEX_SIZE*4, ctypes.c_void_p(UiBatch.COLOR_OFFSET*4))
        GL.glVertexAttribPointer(2, UiBatch.UV_SIZE, GL.GL_FLOAT, GL.GL_FALSE, UiBatch.VERTEX_SIZE*4, ctypes.c_void_p(UiBatch.UV_OFFSET*4))
        GL.glVertexAttribPointer(3, UiBatch.TEX_ID_SIZE, GL.GL_FLOAT, GL.GL_FALSE, UiBatch.VERTEX_SIZE*4, ctypes.c_void_p(UiBatch.TEX_ID_OFFSET*4))
        GL.glVertexAttribPointer(4, UiBatch.UI_ID_SIZE, GL.GL_FLOAT, GL.GL_FALSE, UiBatch.VERTEX_SIZE*4, ctypes.c_void_p(UiBatch.UI_ID_OFFSET*4))

        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
    
    @funcProfiler(ftype='uiupdate')
    @timing
    def updateFrame(self):
        textureDim = self.window.dim
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.screenTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB16UI, textureDim[0], textureDim[1], 0, GL.GL_RGB_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.depthTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, textureDim[0], textureDim[1], 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    @funcProfiler(ftype='uirender')
    def render(self):

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.renderFBO)

        clearColor = GL.glGetFloatv(GL.GL_COLOR_CLEAR_VALUE)

        GL.glClearBufferfv(GL.GL_COLOR, 0, self.colorClear)
        GL.glClearBufferfv(GL.GL_COLOR, 1, self.pickingClear)

        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)
        GL.glDisable(GL.GL_DEPTH_TEST)

        for i in range(len(self.uiRenderers)):
            if(self.uiRenderers[i].isDirtyVertex):
                self.__updateVertexData(i)
                self.uiRenderers[i].setCleanVertex()
            rebufferData = True
        if self.rebufferData:
            self.rebuffer()

        GL.glUseProgram(Assets.GUI_SHADER)
        
        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssboTextureId)
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, self.ssboTextureId)

        for i in range(len(self.textures)):
            GL.glActiveTexture(GL.GL_TEXTURE0 + i)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.textures[i])
            GL.glUniform1i(GL.glGetUniformLocation(Assets.GUI_SHADER, "uTextures[" + str(i) + "]"), i)

        GL.glEnableVertexAttribArray(0)
        GL.glEnableVertexAttribArray(1)
        GL.glEnableVertexAttribArray(2)
        GL.glEnableVertexAttribArray(3)
        GL.glEnableVertexAttribArray(4)

        GL.glDrawElements(GL.GL_TRIANGLES, self.numRenderers * UiBatch.NUM_ELEMENTS, GL.GL_UNSIGNED_INT, None)

        GL.glDisableVertexAttribArray(4)
        GL.glDisableVertexAttribArray(3)
        GL.glDisableVertexAttribArray(2)
        GL.glDisableVertexAttribArray(1)
        GL.glDisableVertexAttribArray(0)

        for i in range(len(self.textures)):
            GL.glActiveTexture(GL.GL_TEXTURE0 + i)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glUseProgram(Assets.SCREEN_SHADER)
        GL.glUniform2f(GL.glGetUniformLocation(Assets.SCREEN_SHADER, "texture_dim"), *self.window.dim)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.screenTexture)
        GL.glUniform1i(GL.glGetUniformLocation(Assets.SCREEN_SHADER, "screen"), 0)
        GL.glBindVertexArray(self.quadVAO)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(*clearColor)

    @funcProfiler(ftype='uirender')
    def rebuffer(self):
        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, self.vertices)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        GL.glBufferSubData(GL.GL_ELEMENT_ARRAY_BUFFER, 0, self.indices)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssboTextureId)
        GL.glBufferSubData(GL.GL_SHADER_STORAGE_BUFFER, 0, self.textureIds.nbytes, self.textureIds)
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, self.ssboTextureId)
        
        self.rebufferData = False

    @timing
    def addRenderer(self, renderer):
        index = self.numRenderers
        self.numRenderers += 1
        self.uiRenderers.append(renderer)
        self.__addtexture(renderer.getTexture())
        self.__updateVertexData(index)
    
    def __addtexture(self, texture):
        if texture == None:
            return
        if texture in self.textures:
            return
        self.textures.append(texture)
    
    def __updateVertexData(self, index):
        renderer = self.uiRenderers[index]
        rendererIndex = index
        index = index * UiBatch.NUM_VERTICES
        vertexPos = renderer.getTransform().getVertices()
        for i in range(UiBatch.NUM_VERTICES):
            self.vertices[index][0] = vertexPos[i][0]
            self.vertices[index][1] = vertexPos[i][1]

            self.vertices[index][2] = renderer.getColor()[0]
            self.vertices[index][3] = renderer.getColor()[1]
            self.vertices[index][4] = renderer.getColor()[2]
            self.vertices[index][5] = renderer.getColor()[3]

            self.vertices[index][6] = renderer.getTexCoords()[i][0]
            self.vertices[index][7] = renderer.getTexCoords()[i][1]

            # self.vertices[index][8] = -1 if renderer.getTexture() == None else self.textures.index(renderer.getTexture())

            self.vertices[index][8] = renderer.getId()

            self.vertices[index][9] = rendererIndex

            index += 1
        self.textureIds[rendererIndex] = -1 if renderer.getTexture() == None else self.textures.index(renderer.getTexture())
        self.rebuffer()
    
    @timing
    def __genDefaultIndices(self):
        indices = np.zeros((self.maxRenderers, UiBatch.NUM_ELEMENTS), dtype='int32')
        for i in range(self.maxRenderers):
            self.__genElementIndices(indices, i)
        return indices
    
    def __genElementIndices(self, indices, index):
        indOffset = UiBatch.NUM_VERTICES*index
        indices[index][0] = indOffset + 0
        indices[index][1] = indOffset + 1
        indices[index][2] = indOffset + 2
        indices[index][3] = indOffset + 2
        indices[index][4] = indOffset + 3
        indices[index][5] = indOffset + 0

    def hasRoom(self, renderer):
        if len(self.uiRenderers) >= self.maxRenderers:
            return False
        if not renderer.getTexture() in self.textures and \
                len(self.textures) >= self.maxTextures:
            return False
        return True

    def getScreenSpaceUI(self, x, y):
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.renderFBO)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT1)
        data = GL.glReadPixels(x, self.window.dim[1]-y, 1, 1, GL.GL_RED_INTEGER, GL.GL_UNSIGNED_INT, None)
        return data[0][0]


