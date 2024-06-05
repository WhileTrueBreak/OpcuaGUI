import OpenGL.GL as GL
import numpy as np
import ctypes
import time

from asset import *
from utils.debug import *

import traceback

class BatchRenderer:
    # MAX_OBJECTS = 1000
    MAX_VERTICES = 1000000
    MAX_TEXTURES = 0
    MAX_SSBO_SIZE = 0

    @timing
    def __init__(self, shader, isTransparent=False):
        BatchRenderer.MAX_TEXTURES = Constants.MAX_TEXTURE_SLOTS
        BatchRenderer.MAX_SSBO_SIZE = min(GL.glGetIntegerv(GL.GL_MAX_SHADER_STORAGE_BLOCK_SIZE)//64, 2**16-2)

        self.shader = shader
        self.projectionMatrix = GL.glGetUniformLocation(self.shader, 'projectionMatrix')
        self.viewMatrix = GL.glGetUniformLocation(self.shader, 'viewMatrix')

        self.vertexSize = 15

        # vertex shape [x, y, z, nx, ny, nz, r, g, b, a, matIndex, u, v, texIndex, objid]
        self.vertices = np.zeros((BatchRenderer.MAX_VERTICES, self.vertexSize), dtype='float32')
        self.indices = np.arange(BatchRenderer.MAX_VERTICES, dtype='int32')

        self.isTransparent = isTransparent

        self.isAvaliable = [True]
        self.inView = {}

        self.colors = [(1,1,1,1)]

        self.transformationMatrices = np.array([np.identity(4)]*BatchRenderer.MAX_SSBO_SIZE, dtype='float32')
        self.modelRange = np.zeros((1, 2), dtype='int32')
        self.models = [None]

        self.textureDict = {}
        self.texModelMap = []
        self.textures = []  

        self.boundMin = np.full((3), -np.inf)
        self.boundMax = np.full((3), np.inf)
        
        self.currentIndex = 0

        self.isDirty = False
        self.__initVertices()
    
    @timing
    def __initVertices(self):

        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        self.vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vertices, GL.GL_DYNAMIC_DRAW)

        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, self.vertexSize*4, ctypes.c_void_p(0*4))
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_TRUE, self.vertexSize*4, ctypes.c_void_p(3*4))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(2, 4, GL.GL_FLOAT, GL.GL_FALSE, self.vertexSize*4, ctypes.c_void_p(6*4))
        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(3, 1, GL.GL_FLOAT, GL.GL_FALSE, self.vertexSize*4, ctypes.c_void_p(10*4))
        GL.glEnableVertexAttribArray(3)
        GL.glVertexAttribPointer(4, 2, GL.GL_FLOAT, GL.GL_FALSE, self.vertexSize*4, ctypes.c_void_p(11*4))
        GL.glEnableVertexAttribArray(4)
        GL.glVertexAttribPointer(5, 1, GL.GL_FLOAT, GL.GL_FALSE, self.vertexSize*4, ctypes.c_void_p(13*4))
        GL.glEnableVertexAttribArray(5)
        GL.glVertexAttribPointer(6, 1, GL.GL_FLOAT, GL.GL_FALSE, self.vertexSize*4, ctypes.c_void_p(14*4))
        GL.glEnableVertexAttribArray(6)

        self.ebo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.indices, GL.GL_DYNAMIC_DRAW)

        self.ssbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssbo)
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, self.transformationMatrices, GL.GL_DYNAMIC_DRAW)
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)

        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

    @timing
    def addModel(self, model, transformationMatrix):
        transformationMatrix = transformationMatrix.T
        if not True in self.isAvaliable:
            return -1
        if self.currentIndex + model.vertices.shape[0] > BatchRenderer.MAX_VERTICES:
            return -1

        vShape = model.vertices.shape
        index = self.isAvaliable.index(True)
        self.inView[index] = True

        # added more slots if index is at the end
        if index == len(self.isAvaliable)-1 and index < BatchRenderer.MAX_SSBO_SIZE:
            self.isAvaliable.append(True)
            self.colors.append((1,1,1,1))
            # self.transformationMatrices = np.append(self.transformationMatrices, [np.identity(4)], axis=0)
            self.modelRange = np.append(self.modelRange, [[0,0]], axis=0)
            self.models.append(None)

        self.isAvaliable[index] = False

        self.models[index] = model
        self.transformationMatrices[index] = transformationMatrix
        self.modelRange[index] = [self.currentIndex, self.currentIndex+vShape[0]]

        self.vertices[self.currentIndex:self.currentIndex+vShape[0], 0:6] = model.vertices[::,0:6]
        data = np.tile([1, 1, 1, 1, index], (vShape[0], 1))
        self.vertices[self.currentIndex:self.currentIndex+vShape[0], 6:11] = data
        self.vertices[self.currentIndex:self.currentIndex+vShape[0], 11:13] = model.vertices[::,6:8]
        self.vertices[self.currentIndex:self.currentIndex+vShape[0], 13:14] = np.tile([-1], (vShape[0], 1))
        self.vertices[self.currentIndex:self.currentIndex+vShape[0], 14:15] = np.tile([index+1], (vShape[0], 1))

        self.currentIndex += vShape[0]
        self.isDirty = True
        # self.__calcBounds()

        return index

    @timing
    def removeModel(self, id):
        self.isAvaliable[id] = True
        self.inView.pop(id, None)

        # shift vertices
        lower = self.modelRange[id][0]
        upper = self.modelRange[id][1]
        right = self.vertices[upper::]
        self.vertices[lower:lower+len(right)] = right

        #update all later ranges
        for i in range(len(self.modelRange)):
            if self.modelRange[i][0] < upper: continue
            self.modelRange[i][0] -= upper-lower
            self.modelRange[i][1] -= upper-lower

        self.currentIndex -= upper-lower
        self.isDirty = True
        
        # self.__calcBounds()
        return

    def __updateVertices(self):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, self.vertices.nbytes, self.vertices)

        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        GL.glBufferSubData(GL.GL_ELEMENT_ARRAY_BUFFER, 0, self.indices.nbytes, self.indices)

        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssbo)
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, self.transformationMatrices, GL.GL_DYNAMIC_DRAW)
        # GL.glBufferSubData(GL.GL_SHADER_STORAGE_BUFFER, 0, self.transformationMatrices.nbytes, self.transformationMatrices)
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)

        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
        self.isDirty = False

    def render(self):
        # print(f"trans:{self.isTransparent} | dirty:{self.isDirty} | size:{self.currentIndex} | tex:{len(self.textures)}")

        if not np.any(np.array(list(self.inView.values()))): 
            # print('not rendering nothing in view')
            return

        if self.isDirty:
            self.__updateVertices()

        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)

        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssbo)
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)

        for i in range(len(self.textures)):
            GL.glActiveTexture(GL.GL_TEXTURE0 + i)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.textures[i])

        GL.glEnableVertexAttribArray(0)
        GL.glEnableVertexAttribArray(1)
        GL.glEnableVertexAttribArray(2)
        GL.glEnableVertexAttribArray(3)
        GL.glEnableVertexAttribArray(4)
        GL.glEnableVertexAttribArray(5)
        GL.glEnableVertexAttribArray(6)

        GL.glDrawElements(GL.GL_TRIANGLES, self.currentIndex, GL.GL_UNSIGNED_INT, None)

        GL.glDisableVertexAttribArray(6)
        GL.glDisableVertexAttribArray(5)
        GL.glDisableVertexAttribArray(4)
        GL.glDisableVertexAttribArray(3)
        GL.glDisableVertexAttribArray(2)
        GL.glDisableVertexAttribArray(1)
        GL.glDisableVertexAttribArray(0)

        for i in range(len(self.textures)):
            GL.glActiveTexture(GL.GL_TEXTURE0 + i)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    def setProjectionMatrix(self, matrix):
        GL.glUseProgram(self.shader)
        GL.glUniformMatrix4fv(self.projectionMatrix, 1, GL.GL_FALSE, matrix)
      
    def setViewMatrix(self, matrix):
        GL.glUseProgram(self.shader)
        GL.glUniformMatrix4fv(self.viewMatrix, 1, GL.GL_TRUE, matrix)
    
    def setTransformMatrix(self, id, matrix):
        # print(np.absolute(self.transformationMatrices[id]-matrix.T))
        # print(np.allclose(self.transformationMatrices[id], matrix.T, 1e-06, 1e-09))
        if np.allclose(self.transformationMatrices[id], matrix.T, 1e-06, 1e-09): return
        self.transformationMatrices[id] = matrix.T 
        # data = np.concatenate(self.transformationMatrices, axis=0).astype(np.float32)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssbo)
        mat = self.transformationMatrices[id]
        GL.glBufferSubData(GL.GL_SHADER_STORAGE_BUFFER, mat.nbytes*id, mat.nbytes, mat)

        # self.__calcBounds()
        
        # GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, self.ssbo)
        # GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, self.transformationMatrices, GL.GL_DYNAMIC_DRAW)
        # # GL.glBufferSubData(GL.GL_SHADER_STORAGE_BUFFER, 0, self.transformationMatrices.nbytes, self.transformationMatrices)
        # GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
    
    def setColor(self, id, color):
        if np.array_equal(self.colors[id], color): return
        if color[3] == 0: self.inView[id] = False
        else: self.inView[id] = True
        lower = self.modelRange[id][0]
        upper = self.modelRange[id][1]
        self.colors[id] = color
        colorMat = np.tile(color, (upper-lower, 1))
        self.vertices[lower:upper, 6:10] = colorMat
        self.isDirty = True

    def setTexture(self, id, tex):
        lower = self.modelRange[id][0]
        upper = self.modelRange[id][1]
        if tex == None and id in self.textureDict:
            index = self.texModelMap.index(self.textureDict[id])
            del self.texModelMap[index]
            del self.textures[index]
            del self.textureDict[id]
            self.vertices[lower:upper, 13:14] = np.tile([-1], (upper-lower, 1))
            self.isDirty = True
            return True
        elif tex == None:
            return True
        
        if len(self.textures) >= BatchRenderer.MAX_TEXTURES and not id in self.textureDict:
            return False
        
        if id in self.textureDict:
            texId = self.texModelMap.index(self.textureDict[id])
            if self.textures[texId] == tex: return True
            self.textures[texId] = tex
        else:
            self.textureDict[id] = self.models[id]
            self.texModelMap.append(self.models[id])
            self.textures.append(tex)
            texId = len(self.textures)-1
        # GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
        # pixels = GL.glGetTexImage(GL.GL_TEXTURE_2D,0,GL.GL_RGBA,GL.GL_UNSIGNED_BYTE)
        # print(f'pixel length: {len(pixels)}')
        self.vertices[lower:upper, 13:14] = np.tile([texId], (upper-lower, 1))
        self.isDirty = True
        return True

    def hasTextureSpace(self):
        if len(self.textures) >= BatchRenderer.MAX_TEXTURES:
            return False
        return True

    def getData(self, id):
        if id in self.textureDict:
            tex = self.textures[self.texModelMap.index(self.textureDict[id-1])]
        else:
            tex = None
        data = {'model':self.models[id], 'color':self.colors[id-1], 'matrix':self.transformationMatrices[id].T, 'texture':tex}
        return data

    def setViewFlag(self, id, flag):
        self.inView[id] = flag

    @timing
    def __calcBounds(self):
        minP = np.full((3), np.inf)
        maxP = np.full((3), -np.inf)
        for i,e in enumerate(self.isAvaliable):
            if e: continue
            lower = self.modelRange[i][0]
            upper = self.modelRange[i][1]
            xyz = self.vertices[lower:upper, 0:3]
            xyz = np.pad(xyz, ((0, 0), (0, 1)), mode='constant', constant_values=1)
            T = self.transformationMatrices[i]
            xyz = np.matmul(xyz, T)[:,0:3]
            minP = np.vstack((minP, xyz.min(axis=0))).min(axis=0)
            maxP = np.vstack((maxP, xyz.max(axis=0))).max(axis=0)
        self.boundMin = minP
        self.boundMax = maxP

class Renderer:
    def __init__(self, window, supportTransparency=True):
        self.window = window
        self.supportTransparency = supportTransparency

        self.opaqueShader = Assets.OPAQUE_SHADER
        self.transparentShader = Assets.TRANSPARENT_SHADER
        self.compositeShader = Assets.COMPOSITE_SHADER
        self.screenShader = Assets.SCREEN_SHADER

        textures = np.arange(0, 32, dtype='int32')
        GL.glUseProgram(self.opaqueShader)
        GL.glUniform1iv(GL.glGetUniformLocation(self.opaqueShader, "uTextures"), 32, textures)
        GL.glUseProgram(self.transparentShader)
        GL.glUniform1iv(GL.glGetUniformLocation(self.transparentShader, "uTextures"), 32, textures)

        self.idDict = {}
        self.batchIdMap = {}
        self.nextId = 0

        self.projectionMatrix = np.identity(4)
        self.viewMatrix = np.identity(4)

        self.transparentBatch = []
        self.solidBatch = []
        self.batches = []

        self.__initCompositeLayers()
    
    @timing
    def __initCompositeLayers(self):
        self.backClear = np.array([0,0,0,0], dtype='float32')
        self.accumClear = np.array([0,0,0,0], dtype='float32')
        self.revealClear = np.array([1,0,0,0], dtype='float32')
        self.pickingClear = np.array([0,0,0], dtype='uint')

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


        self.opaqueFBO = GL.glGenFramebuffers(1)
        self.transparentFBO = GL.glGenFramebuffers(1)

        textureDim = self.window.dim

        self.opaqueTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.pickingTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB16UI, textureDim[0], textureDim[1], 0, GL.GL_RGB_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.depthTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.depthTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, textureDim[0], textureDim[1], 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_COMPARE_FUNC, GL.GL_LEQUAL)
        GL.glTexParameteri (GL.GL_TEXTURE_2D, GL.GL_TEXTURE_COMPARE_MODE, GL.GL_NONE)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.opaqueFBO)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.opaqueTexture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT1, GL.GL_TEXTURE_2D, self.pickingTexture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.depthTexture, 0)

        self.opaqueDrawBuffers = (GL.GL_COLOR_ATTACHMENT0, GL.GL_COLOR_ATTACHMENT1)
        GL.glDrawBuffers(self.opaqueDrawBuffers)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

        self.accumTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.accumTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.revealTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.revealTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_R8, textureDim[0], textureDim[1], 0, GL.GL_RED, GL.GL_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.transparentFBO)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.accumTexture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT1, GL.GL_TEXTURE_2D, self.revealTexture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT2, GL.GL_TEXTURE_2D, self.pickingTexture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.depthTexture, 0)

        self.transparentDrawBuffers = (GL.GL_COLOR_ATTACHMENT0, GL.GL_COLOR_ATTACHMENT1, GL.GL_COLOR_ATTACHMENT2)
        GL.glDrawBuffers(self.transparentDrawBuffers)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    @timing
    def updateCompositeLayers(self):
        textureDim = self.window.dim
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB16UI, textureDim[0], textureDim[1], 0, GL.GL_RGB_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.depthTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, textureDim[0], textureDim[1], 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.accumTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.revealTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_R8, textureDim[0], textureDim[1], 0, GL.GL_RED, GL.GL_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    @timing
    def addModel(self, model, matrix):
        if isinstance(model, list):
            return self.addModels(model, matrix)
        for i in range(len(self.batches)):
            if self.batches[i].isTransparent: continue
            id = self.batches[i].addModel(model, matrix)
            if id == -1: continue
            modelId = self.nextId
            self.nextId += 1
            self.idDict[modelId] = [(i, id)]
            self.idDict[(i, id)] = modelId
            return modelId
        self.addBatch()
        id = self.batches[-1].addModel(model, matrix)
        if id != -1:
            modelId = self.nextId
            self.nextId += 1
            self.idDict[modelId] = [(len(self.batches) - 1, id)]
            self.idDict[(len(self.batches) - 1, id)] = modelId
            return modelId

        # add submodels
        submodels = model.generateSubModels(BatchRenderer.MAX_VERTICES)
        return self.addModels(submodels, matrix)
    
    @timing
    def addModels(self, models, matrix):
        ids = []
        modelId = self.nextId
        self.nextId += 1
        while len(models) != 0:
            isAdded = False
            for i in range(len(self.batches)):
                id = self.batches[i].addModel(models[0], matrix)
                if id == -1: continue
                self.idDict[(i, id)] = modelId
                ids.append((i, id))
                isAdded = True
            if isAdded:
                models.pop(0)
                continue
            self.addBatch()
            id = self.batches[-1].addModel(models[0], matrix)
            if id == -1:
                raise Exception(f'Submodel could not be added to model renderer')
            self.idDict[(len(self.batches) - 1, id)] = modelId
            ids.append((len(self.batches) - 1, id))
            models.pop(0)
            continue
        self.idDict[modelId] = ids
        return modelId
        raise Exception(f'Model could not be added to model renderer\n',
                        f'Try increasing BatchRenderer.MAX_VERTICES to above {len(model.vertices)}')
        return -1

    @timing
    def removeModel(self, id):
        for modelid in self.idDict[id]:
            self.batches[modelid[0]].removeModel(modelid[1])
            self.idDict.pop(modelid)
        self.idDict.pop(id)
    
    @timing
    def addBatch(self, transparent=False):
        if transparent:
            self.batches.append(BatchRenderer(self.transparentShader, transparent))
            shader = self.transparentShader
            self.transparentBatch.append(self.batches[-1])
        else:
            self.batches.append(BatchRenderer(self.opaqueShader, transparent))
            shader = self.opaqueShader
            self.solidBatch.append(self.batches[-1])
        self.batches[-1].setProjectionMatrix(self.projectionMatrix)
        self.batches[-1].setViewMatrix(self.viewMatrix)

    def setProjectionMatrix(self, matrix):
        self.projectionMatrix = matrix
        for batch in self.batches:
            batch.setProjectionMatrix(matrix)
    
    def setViewMatrix(self, matrix):
        self.viewMatrix = matrix
        for batch in self.batches:
            batch.setViewMatrix(matrix)

    def setTransformMatrix(self, id, matrix):
        for modelid in self.idDict[id]: 
            self.batches[modelid[0]].setTransformMatrix(modelid[1], matrix)

    def setColor(self, id, color):
        if not self.supportTransparency: color = (*color[0:3], 1)
        self.setViewFlag(id, color[3] != 0)
        for i,modelId in enumerate(self.idDict[id]):
            batch = self.batches[modelId[0]]
            objId = modelId[1]
            isTransparent = color[3] != 1
    
            # matches batch settings
            if isTransparent == batch.isTransparent:
                batch.setColor(objId, color)
                continue

            # remove from batch and added to new batch
            data = batch.getData(objId)
            batch.removeModel(objId)
            del self.idDict[modelId]

            #loop through batches
            for j in range(len(self.batches)):
                if isTransparent ^ self.batches[j].isTransparent: continue
                objId = self.batches[j].addModel(data['model'], data['matrix'])
                if objId == -1: continue
                self.batches[j].setColor(objId, color)
                self.batches[j].setTexture(objId, data['texture'])
                self.idDict[id][i] = (j, objId)
                self.idDict[(j, objId)] = id
                break
            else:
                #if didnt find suitable batch
                self.addBatch(isTransparent)
                batchId = len(self.batches)-1
                objId = self.batches[-1].addModel(data['model'], data['matrix'])
                if objId == -1:
                    print('failed to update color')
                    continue
                self.batches[batchId].setColor(objId, color)
                self.batches[batchId].setTexture(objId, data['texture'])
                self.idDict[id][i] = (batchId, objId)
                self.idDict[(batchId, objId)] = id

    def setTexture(self, id, tex):
        for i in range(len(self.idDict[id])):
            modelId = self.idDict[id][i]
            batch = self.batches[modelId[0]]
            objId = modelId[1]
            if batch.setTexture(objId, tex):
                continue
            
            isTransparent = batch.colors[objId][3] != 1
            data = batch.getData(objId)
            batch.removeModel(objId)
            del self.idDict[modelId]

            #loop through batches
            for j in range(len(self.batches)):
                if not self.batches[j].hasTextureSpace(): continue
                objId = self.batches[j].addModel(data['model'], data['matrix'])
                if objId == -1: continue
                self.batches[j].setColor(objId, data['color'])
                self.batches[j].setTexture(objId, tex)
                self.idDict[id][i] = (j, objId)
                self.idDict[(j, objId)] = id
                break
            else:
                #if didnt find suitable batch
                self.addBatch(isTransparent)
                batchId = len(self.batches)-1
                objId = self.batches[-1].addModel(data['model'], data['matrix'])
                if objId == -1:
                    print('failed to update color')
                    continue
                self.batches[batchId].setColor(objId, data['color'])
                self.batches[batchId].setTexture(objId, tex)
                self.idDict[id][i] = (batchId, objId)
                self.idDict[(batchId, objId)] = id

    def render(self):
        # remember previous values
        depthFunc = GL.glGetIntegerv(GL.GL_DEPTH_FUNC)
        depthTest = GL.glGetIntegerv(GL.GL_DEPTH_TEST)
        depthMask = GL.glGetIntegerv(GL.GL_DEPTH_WRITEMASK)
        blend = GL.glGetIntegerv(GL.GL_BLEND)
        clearColor = GL.glGetFloatv(GL.GL_COLOR_CLEAR_VALUE)

        # config states
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LESS)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)
        GL.glClearColor(0,0,0,0)
        
        # render opaque
        GL.glUseProgram(self.opaqueShader)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.opaqueFBO)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glClearBufferfv(GL.GL_COLOR, 0, self.backClear)
        GL.glClearBufferfv(GL.GL_COLOR, 1, self.pickingClear)
        bidLoc = GL.glGetUniformLocation(self.opaqueShader, "batchId")

        for batch in self.solidBatch:
            GL.glUniform1ui(bidLoc, self.batches.index(batch)+1)
            batch.render()


        if self.supportTransparency:
            # config states
            GL.glDepthMask(GL.GL_FALSE)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunci(0, GL.GL_ONE, GL.GL_ONE)
            GL.glBlendFunci(1, GL.GL_ZERO, GL.GL_ONE_MINUS_SRC_COLOR)
            GL.glBlendEquationi(0, GL.GL_FUNC_ADD)
            GL.glBlendEquationi(1, GL.GL_FUNC_ADD)

            # render transparent
            GL.glUseProgram(self.transparentShader)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.transparentFBO)
            GL.glClearBufferfv(GL.GL_COLOR, 0, self.accumClear)
            GL.glClearBufferfv(GL.GL_COLOR, 1, self.revealClear)
            bidLoc = GL.glGetUniformLocation(self.transparentShader, "batchId")

            for batch in self.transparentBatch:
                GL.glUniform1ui(bidLoc, self.batches.index(batch)+1)
                batch.render()

            # config states
            GL.glDepthMask(GL.GL_TRUE)
            GL.glDepthFunc(GL.GL_ALWAYS)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

            # render composite
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.opaqueFBO)

            GL.glDisable(GL.GL_DEPTH_TEST)

            GL.glUseProgram(self.compositeShader)

            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.accumTexture)
            GL.glUniform1i(GL.glGetUniformLocation(self.compositeShader, "accum"), 0)
            GL.glActiveTexture(GL.GL_TEXTURE1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.revealTexture)
            GL.glUniform1i(GL.glGetUniformLocation(self.compositeShader, "reveal"), 1)
            GL.glActiveTexture(GL.GL_TEXTURE2)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
            GL.glUniform1i(GL.glGetUniformLocation(self.compositeShader, "picking"), 2)
            GL.glBindVertexArray(self.quadVAO)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

            GL.glEnable(GL.GL_DEPTH_TEST)
        
        ##### CELL SHADING #####
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.opaqueFBO)
        GL.glUseProgram(Assets.CELL_SHADER)

        GL.glUniform2f(GL.glGetUniformLocation(Assets.CELL_SHADER, "texture_dim"), *self.window.dim)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueTexture)
        GL.glUniform1i(GL.glGetUniformLocation(Assets.CELL_SHADER, "screen"), 0)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
        GL.glUniform1i(GL.glGetUniformLocation(Assets.CELL_SHADER, "picking"), 1)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.depthTexture)
        GL.glUniform1i(GL.glGetUniformLocation(Assets.CELL_SHADER, "depth"), 2)
        GL.glBindVertexArray(self.quadVAO)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)
        GL.glEnable(GL.GL_DEPTH_TEST)

        # reset states
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glDepthFunc(depthFunc)
        if depthTest:
            GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(depthMask)
        if blend:
            GL.glEnable(GL.GL_BLEND)
        GL.glClearColor(*clearColor)
        # GL.glFinish() #TODO: (for debug) remove this later 
        return

    def getData(self, id):
        data = []
        for modelid in self.idDict[id]: 
            batch = self.batches[modelid[0]]
            data.append(batch.getData(modelid[1]))
        return data

    def getScreenSpaceObj(self, x, y):
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.transparentFBO)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT2)
        data = GL.glReadPixels(x, y, 1, 1, GL.GL_RGB_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glReadBuffer(GL.GL_NONE)
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, 0)
        data = data[0][0]
        data[0] -= 1
        data[1] -= 1
        return data
    
    def getTexture(self):
        return self.opaqueTexture

    def setViewFlag(self, id, flag):
        for modelid in self.idDict[id]: 
            self.batches[modelid[0]].setViewFlag(modelid[1], flag)
