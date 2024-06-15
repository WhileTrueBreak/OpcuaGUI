import OpenGL.GL as GL
import numpy as np
import ctypes
import time

from asset import *
from utils.debug import *

import traceback

class BatchRenderer:
    # MAX_OBJECTS = 1000
    MAX_VERTICES = 500000
    MAX_TEXTURES = 0
    MAX_SSBO_SIZE = 0

    @timing
    def __init__(self, shader, isTransparent=False):
        BatchRenderer.MAX_TEXTURES = Constants.MAX_TEXTURE_SLOTS
        BatchRenderer.MAX_SSBO_SIZE = min(GL.glGetIntegerv(GL.GL_MAX_SHADER_STORAGE_BLOCK_SIZE)//64, 2**16-2)

        self.shader = shader
        GL.glUseProgram(self.shader)
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

        self.bounds = None
        
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
        self.__calcBounds()

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
        
        self.__calcBounds()
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

    def render(self, frustum=None):
        # print(f"trans:{self.isTransparent} | dirty:{self.isDirty} | size:{self.currentIndex} | tex:{len(self.textures)}")

        if frustum is not None and self.bounds is not None:
            dists = np.matmul(self.bounds, frustum.T)
            inView = not np.any(np.all(dists < 0, axis=0))
            if not inView: 
                # print('batch not in view')
                return

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

        # for i in range(len(self.textures)):
        #     GL.glActiveTexture(GL.GL_TEXTURE0 + i)
        #     GL.glBindTexture(GL.GL_TEXTURE_2D, self.textures[i])

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

        # for i in range(len(self.textures)):
        #     GL.glActiveTexture(GL.GL_TEXTURE0 + i)
        #     GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

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

        self.__calcBounds()
        
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
            T = self.transformationMatrices[i]
            aabbBound = self.models[i].getAABBBound(T.T)
            minP = np.minimum(minP, aabbBound.min(axis=0)[0:3])
            maxP = np.maximum(maxP, aabbBound.max(axis=0)[0:3])
        corners = np.array(np.meshgrid(
                [minP[0], maxP[0]],
                [minP[1], maxP[1]],
                [minP[2], maxP[2]],
            )).T.reshape(-1,3)
        self.bounds = np.hstack([corners, np.ones((corners.shape[0],1))])
