import OpenGL.GL as GL

class Constants:
    MAX_TEXTURE_SLOTS = GL.glGetIntegerv(GL.GL_MAX_TEXTURE_IMAGE_UNITS)
    OPCUA_LOCATION = 'oct.tpc://172.32.1.236:4840/server/'

GL_FLOAT_MAX = 3.402823e+38