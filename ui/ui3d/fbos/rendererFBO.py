import OpenGL.GL as GL
from utils.debug import *

class RendererFBO:

    @timing
    def __init__(self, windowDim):
        self.windowDim = windowDim
        self.__initOpaqueFBO()
        self.__initTransparentFBO()

    @timing
    def __initOpaqueFBO(self):
        self.opaqueFBO = GL.glGenFramebuffers(1)

        windowDim = self.windowDim

        self.opaqueTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, windowDim[0], windowDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.pickingTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB16UI, windowDim[0], windowDim[1], 0, GL.GL_RGB_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.depthTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.depthTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, windowDim[0], windowDim[1], 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
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

    @timing
    def __initTransparentFBO(self):
        self.transparentFBO = GL.glGenFramebuffers(1)

        windowDim = self.windowDim

        self.accumTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.accumTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, windowDim[0], windowDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.revealTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.revealTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_R8, windowDim[0], windowDim[1], 0, GL.GL_RED, GL.GL_FLOAT, None)
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

    def bindOpaqueFBO(self):
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.opaqueFBO)

    def bindTransparentFBO(self):
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.transparentFBO)

    @timing
    def updateTextures(self, windowDim):
        self.windowDim = windowDim
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.pickingTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB16UI, windowDim[0], windowDim[1], 0, GL.GL_RGB_INTEGER, GL.GL_UNSIGNED_INT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.opaqueTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, windowDim[0], windowDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.depthTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, windowDim[0], windowDim[1], 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.accumTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, windowDim[0], windowDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.revealTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_R8, windowDim[0], windowDim[1], 0, GL.GL_RED, GL.GL_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

