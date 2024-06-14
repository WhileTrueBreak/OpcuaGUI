import OpenGL.GL as GL

from utils.debug import *
from utils.mathHelper import *

class ShadowCubeFBO:

    FaceInfo = [
        (GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X, (-1, 0, 0), ( 0, 1, 0)), # long
        (GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X, ( 1, 0, 0), ( 0, 1, 0)), # long
        (GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y, ( 0, 1, 0), ( 0, 0,-1)), # short back
        (GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y, ( 0,-1, 0), ( 0, 0, 1)), # short front
        (GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z, ( 0, 0, 1), ( 0, 1, 0)), # up/down
        (GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z, ( 0, 0,-1), ( 0, 1, 0)), # up/down
    ]

    def __init__(self, size):

        self.shadowCubeMapSize = size

        self.shadowFBO = GL.glGenFramebuffers(1)

        self.shadowDepthTexture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.shadowDepthTexture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, size, size, 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_COMPARE_FUNC, GL.GL_LEQUAL)
        GL.glTexParameteri (GL.GL_TEXTURE_2D, GL.GL_TEXTURE_COMPARE_MODE, GL.GL_NONE)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self.shadowCubeMap = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.shadowCubeMap)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_WRAP_R, GL.GL_CLAMP_TO_EDGE)
        for i in range(6):
            GL.glTexImage2D(GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL.GL_R32F, size, size, 0, GL.GL_RED, GL.GL_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, 0)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadowFBO)

        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.shadowDepthTexture, 0)
        GL.glDrawBuffer(GL.GL_NONE)
        GL.glReadBuffer(GL.GL_NONE)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def bindShadowFBO(self, face):
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadowFBO)
        GL.glViewport(0, 0, self.shadowCubeMapSize, self.shadowCubeMapSize)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, face, self.shadowCubeMap, 0)
        GL.glDrawBuffer(GL.GL_COLOR_ATTACHMENT0)
    
    def getFaceInfo(self, index):
        return ShadowCubeFBO.FaceInfo[index]


