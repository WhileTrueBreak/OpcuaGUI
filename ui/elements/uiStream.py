from ui.glElement import GlElement
from ui.uiRenderer import UiRenderer
from utils.debug import *

from PIL import Image

from connections.mjpegThread import *
from asset import *

class UiStream(GlElement):
    def __init__(self, window, constraints, url, dim=(0,0,0,0)):
        super().__init__(window, constraints, dim)
        self.type = 'stream'

        self.url = url
        self.container = StreamContainer()
        self.threadStopFlag = True
        self.thread = createMjpegThread(self.container, self.url, lambda:self.threadStopFlag)
        self.image = None
        
        self.texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        
        self.renderer = UiRenderer.fromSprite(Sprite.fromTexture(self.texture), Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.renderers.append(self.renderer)

    def reshape(self):
        self.renderer.getTransform().setPos((self.openGLDim[0:2]))
        self.renderer.getTransform().setSize((self.openGLDim[2:4]))
        self.renderer.setDirtyVertex()

    @funcProfiler(ftype='uiupdate')
    def update(self, delta):
        self.updateImage(delta)
        return

    @funcProfiler(ftype='streamupdate')
    def updateImage(self, delta):
        stream = self.container.getStream()
        if stream == None: 
            return
        image = Image.open(stream).convert("RGBA")
        stream.close()
        self.image = image.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
        
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)

        #texture options
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        GL.glTexImage2D(
                GL.GL_TEXTURE_2D,    # where to load texture data
                0,                # mipmap level
                GL.GL_RGBA8,         # format to store data in
                image.width,                # image dimensions
                image.height,                #
                0,                # border thickness
                GL.GL_RGBA,          # format data is provided in
                GL.GL_UNSIGNED_BYTE, # type to read data as
                self.image)       # data to load as texture
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    def start(self):
        self.threadStopFlag = False
        if self.thread.is_alive(): return
        self.thread = createMjpegThread(self.container, self.url, lambda:self.threadStopFlag)

    def stop(self):
        self.threadStopFlag = True
