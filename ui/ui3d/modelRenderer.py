import OpenGL.GL as GL
import numpy as np
import ctypes
import time

from asset import *
from constants import GL_FLOAT_MAX
from ui.ui3d.batchRenderer import BatchRenderer
from ui.ui3d.fbos.rendererFBO import RendererFBO
from ui.ui3d.fbos.shadowCubeFBO import ShadowCubeFBO
from utils.debug import *
from utils.mathHelper import getFrustum

import traceback

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

        self.pointLight = (7, 4, 2.5)

        self.projectionMatrix = np.identity(4)
        self.viewMatrix = np.identity(4)

        self.transparentBatch = []
        self.solidBatch = []
        self.batches = []

        self.__initCompositeLayers()
        self.__updateLight()
    
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

        textureDim = self.window.dim
        self.opaqueBufferTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueBufferTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.rendererFBO = RendererFBO(self.window.dim)
        self.shadowCubeFBO = ShadowCubeFBO(2000)

    def __updateLight(self):
        GL.glUseProgram(self.opaqueShader)
        shaderLightWorldPos = GL.glGetUniformLocation(self.opaqueShader, 'lightPos')
        GL.glUniform3fv(shaderLightWorldPos, 1, self.pointLight)

        GL.glUseProgram(self.transparentShader)
        shaderLightWorldPos = GL.glGetUniformLocation(self.transparentShader, 'lightPos')
        GL.glUniform3fv(shaderLightWorldPos, 1, self.pointLight)

        GL.glUseProgram(Assets.SHADOW_SHADER)
        shaderLightWorldPos = GL.glGetUniformLocation(Assets.SHADOW_SHADER, 'lightWorldPos')
        GL.glUniform3fv(shaderLightWorldPos, 1, self.pointLight)

        self.lightProjMatrix = createProjectionMatrix(self.shadowCubeFBO.shadowCubeMapSize, self.shadowCubeFBO.shadowCubeMapSize, 90, 0.01, 100)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(Assets.SHADOW_SHADER, 'lightProjectionMatrix'), 1, GL.GL_FALSE, self.lightProjMatrix)
        self.lightViewMatLoc = GL.glGetUniformLocation(Assets.SHADOW_SHADER, 'lightViewMatrix')

    @timing
    def updateCompositeLayers(self):
        self.rendererFBO.updateTextures(self.window.dim)
       
        textureDim = self.window.dim
        
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueBufferTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)

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
    
    @funcProfiler(ftype='3dshadow')
    def __shadowPass(self, lightPos):
        oldViewport = GL.glGetIntegerv(GL.GL_VIEWPORT)

        GL.glUseProgram(Assets.SHADOW_SHADER)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LESS)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)
        GL.glClearColor(GL_FLOAT_MAX, GL_FLOAT_MAX, GL_FLOAT_MAX, GL_FLOAT_MAX)

        for i in range(6):
            # t1 = time.time_ns()
            face, target, up = self.shadowCubeFBO.getFaceInfo(i)
            self.shadowCubeFBO.bindShadowFBO(face)
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT|GL.GL_COLOR_BUFFER_BIT)
            lightViewMatrix = createViewMatrixLookAt(lightPos, np.array(lightPos)+np.array(target), up)
            lightFrustum = getFrustum(np.matmul(self.lightProjMatrix.T, lightViewMatrix))

            if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
                raise('frame buffer not complete')

            GL.glUniformMatrix4fv(self.lightViewMatLoc, 1, GL.GL_TRUE, lightViewMatrix)
            for batch in self.solidBatch:
                batch.render(frustum=lightFrustum)
            # GL.glFinish() #TODO: (for debug) remove this later 
            # t2 = time.time_ns()
            # funclog(f'shadow pass {i} time: {(t2-t1)/1000}us')
            
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glViewport(*oldViewport)
        GL.glFinish() #TODO: (for debug) remove this later 
        return

    @funcProfiler(ftype='3drender')
    def render(self):
        # remember previous values
        depthFunc = GL.glGetIntegerv(GL.GL_DEPTH_FUNC)
        depthTest = GL.glGetIntegerv(GL.GL_DEPTH_TEST)
        depthMask = GL.glGetIntegerv(GL.GL_DEPTH_WRITEMASK)
        blend = GL.glGetIntegerv(GL.GL_BLEND)
        clearColor = GL.glGetFloatv(GL.GL_COLOR_CLEAR_VALUE)

        # get shadow
        self.__shadowPass(self.pointLight)
        GL.glActiveTexture(GL.GL_TEXTURE8)
        GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.shadowCubeFBO.shadowCubeMap)

        GL.glUseProgram(self.opaqueShader)
        GL.glUniform1i(GL.glGetUniformLocation(self.opaqueShader, 'shadowMap'), 8)
        GL.glUseProgram(self.transparentShader)
        GL.glUniform1i(GL.glGetUniformLocation(self.transparentShader, 'shadowMap'), 8)

        viewFrustum = getFrustum(np.matmul(self.projectionMatrix.T,self.viewMatrix))

        # config states
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LESS)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)
        GL.glClearColor(0,0,0,0)
        
        # render opaque
        GL.glUseProgram(self.opaqueShader)
        self.rendererFBO.bindOpaqueFBO()
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glClearBufferfv(GL.GL_COLOR, 0, self.backClear)
        GL.glClearBufferfv(GL.GL_COLOR, 1, self.pickingClear)
        bidLoc = GL.glGetUniformLocation(self.opaqueShader, "batchId")

        for batch in self.solidBatch:
            GL.glUniform1ui(bidLoc, self.batches.index(batch)+1)
            batch.render(frustum=viewFrustum)

        if self.supportTransparency:
            # config states
            # GL.glDepthMask(GL.GL_FALSE)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunci(0, GL.GL_ONE, GL.GL_ONE)
            GL.glBlendFunci(1, GL.GL_ZERO, GL.GL_ONE_MINUS_SRC_COLOR)
            GL.glBlendEquationi(0, GL.GL_FUNC_ADD)
            GL.glBlendEquationi(1, GL.GL_FUNC_ADD)

            # render transparent
            GL.glUseProgram(self.transparentShader)
            self.rendererFBO.bindTransparentFBO()
            GL.glClearBufferfv(GL.GL_COLOR, 0, self.accumClear)
            GL.glClearBufferfv(GL.GL_COLOR, 1, self.revealClear)
            bidLoc = GL.glGetUniformLocation(self.transparentShader, "batchId")

            for batch in self.transparentBatch:
                GL.glUniform1ui(bidLoc, self.batches.index(batch)+1)
                batch.render(frustum=viewFrustum)

            # config states
            # GL.glDepthMask(GL.GL_TRUE)
            GL.glDepthFunc(GL.GL_ALWAYS)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

            # render composite
            self.rendererFBO.bindOpaqueFBO()
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glUseProgram(self.compositeShader)

            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.rendererFBO.accumTexture)
            GL.glUniform1i(GL.glGetUniformLocation(self.compositeShader, "accum"), 0)
            GL.glActiveTexture(GL.GL_TEXTURE1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.rendererFBO.revealTexture)
            GL.glUniform1i(GL.glGetUniformLocation(self.compositeShader, "reveal"), 1)
            GL.glActiveTexture(GL.GL_TEXTURE2)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.rendererFBO.pickingTexture)
            GL.glUniform1i(GL.glGetUniformLocation(self.compositeShader, "picking"), 2)
            GL.glBindVertexArray(self.quadVAO)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

            GL.glEnable(GL.GL_DEPTH_TEST)
        
        GL.glActiveTexture(GL.GL_TEXTURE8)
        GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, 0)

        ##### CELL SHADING #####
        GL.glDisable(GL.GL_DEPTH_TEST)
        self.rendererFBO.bindOpaqueFBO()
        GL.glUseProgram(Assets.POST_SHADER)

        GL.glCopyImageSubData(self.rendererFBO.opaqueTexture, GL.GL_TEXTURE_2D, 0, 0, 0, 0,
                            self.opaqueBufferTexture, GL.GL_TEXTURE_2D, 0, 0, 0, 0,
                            *self.window.dim, 1)

        GL.glUniform2f(GL.glGetUniformLocation(Assets.POST_SHADER, "texture_dim"), *self.window.dim)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueBufferTexture)
        GL.glUniform1i(GL.glGetUniformLocation(Assets.POST_SHADER, "screen"), 0)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.rendererFBO.pickingTexture)
        GL.glUniform1i(GL.glGetUniformLocation(Assets.POST_SHADER, "picking"), 1)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.rendererFBO.depthTexture)
        GL.glUniform1i(GL.glGetUniformLocation(Assets.POST_SHADER, "depth"), 2)
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
        GL.glFinish() #TODO: (for debug) remove this later 
        return

    def getData(self, id):
        data = []
        for modelid in self.idDict[id]: 
            batch = self.batches[modelid[0]]
            data.append(batch.getData(modelid[1]))
        return data

    def getScreenSpaceObj(self, x, y):
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.rendererFBO.transparentFBO)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT2)
        data = GL.glReadPixels(x, y, 1, 1, GL.GL_RGB_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glReadBuffer(GL.GL_NONE)
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, 0)
        data = data[0][0]
        data[0] -= 1
        data[1] -= 1
        return data
    
    def getTexture(self):
        return self.rendererFBO.opaqueTexture

    def setViewFlag(self, id, flag):
        for modelid in self.idDict[id]: 
            self.batches[modelid[0]].setViewFlag(modelid[1], flag)

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

    def setLight(self, pointLight):
        self.pointLight = pointLight
        self.__updateLight()

