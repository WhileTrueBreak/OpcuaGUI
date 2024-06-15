from ui.glElement import GlElement
from ui.constraintManager import *

from ui.uiRenderer import *

from utils.transform import *
from utils.sprite import *
from utils.debug import *

from asset import *

class UiText(GlElement):

    def __init__(self, window, constraints, dim=(0,0,0,0)):
        constraints = constraints.copy()
        constraints.append(RELATIVE(T_W, 1, P_W))
        constraints.append(RELATIVE(T_H, 1, P_H))
        super().__init__(window, constraints, dim)
        self.type = 'text'
        
        self.dirtyText = True
        self.font = Assets.MONACO_FONT
        self.text = 'default'
        self.fontSize = 48
        self.textSpacing = 3
        self.textColor = (1,1,1)
        self.scaledFontSize = self.fontSize
        self.scaledTextSpacing = self.textSpacing

        self.fitParent = False
        self.prevWindowScale = (0,0)
        self.textBounds = (0,0,0,0)

        self.textRenderScale = 4
        self.textIndices = np.array([1,0,3,3,1,2], dtype='int32')
        self.maxDescender = 0
        self.maxAscender = 0

        self.__initTextBuffers()
        self.__initFrame()
        self.__initRenderer()

    def __initTextBuffers(self):
        # GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        
        self.textVao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.textVao)

        self.textVbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.textVbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 4 * 4 * 4, None, GL.GL_DYNAMIC_DRAW)

        GL.glVertexAttribPointer(0, 4, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glEnableVertexAttribArray(0)
        
        self.textEbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.textEbo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.textIndices, GL.GL_DYNAMIC_DRAW)

        # unbind vao vbo ebo
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
    
    def __initFrame(self):
        self.textFrame = GL.glGenFramebuffers(1)

        textureDim = self.window.dim

        self.textFrameTex = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.textFrameTex)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, textureDim[0], textureDim[1], 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.textFrame)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.textFrameTex, 0)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def __initRenderer(self):
        self.sprite = Sprite.fromTexture(self.textFrameTex)
        self.renderer = UiRenderer.fromSprite(self.sprite, Transform.fromPS((self.openGLDim[0:2]),(self.openGLDim[2:4])))
        self.renderers.append(self.renderer)

    def reshape(self):

        self.__updateTextScale()
        self.__updateTextBound()
        self.updateDim()

        GL.glBindTexture(GL.GL_TEXTURE_2D, self.textFrameTex)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16F, int(self.textBounds[2]*self.textRenderScale), int(self.textBounds[3]*self.textRenderScale), 0, GL.GL_RGBA, GL.GL_HALF_FLOAT, None)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        
        self.__updateRenderTexture(self.text, self.font)
        self.__updateRenderer()
        return

    @funcProfiler(ftype='uiupdate')
    def update(self, delta):
        if self.dirtyText:
            self.reshape()
        return
    
    @funcProfiler(ftype='textupdate')
    def __updateTextScale(self):
        self.currScale = (1,1) #self.window.getWindowScale()
        if self.prevWindowScale[1] == self.currScale[1]: return
        self.scaledFontSize = self.fontSize*self.currScale[1]
        self.scaledTextSpacing = self.textSpacing*self.currScale[1]
        self.prevWindowScale = self.currScale
        self.dirtyText = True

    @funcProfiler(ftype='textupdate')
    def __updateTextBound(self):
        if not self.dirtyText: return
        scale = self.scaledFontSize/48
        
        maxdes = 1
        maxasc = 1
        x = 0
        y = self.dim[1]
        for c in self.text:
            ch = self.font[c]
            w, h = ch.textureSize
            maxdes = max(maxdes, ch.descender*scale)
            maxasc = max(maxasc, ch.ascender*scale)

            x += w*scale + self.scaledTextSpacing*scale
            if c == ' ':
                x += self.scaledTextSpacing*scale*2
        x -= self.scaledTextSpacing*scale
        widthAspect = x/(maxasc+maxdes)
        
        self.maxAscender = maxasc
        self.maxDescender = maxdes
        
        self.textBounds = (self.dim[0], self.dim[1], (self.maxDescender + self.maxAscender)*widthAspect, self.maxDescender + self.maxAscender)

        self.updateWidth(RELATIVE(T_W, widthAspect, T_H))
        if self.fitParent:
            if (self.maxDescender + self.maxAscender)*widthAspect < self.parent.dim[2]:
                self.updateHeight(RELATIVE(T_H, 1, P_H))
            else: 
                scale = self.parent.dim[2]/((self.maxDescender + self.maxAscender)*widthAspect)
                self.updateHeight(RELATIVE(T_H, scale, P_H))
        else:
            self.updateHeight(ABSOLUTE(T_H, self.maxDescender + self.maxAscender))
        self.dirtyText = False

    @funcProfiler(ftype='textrender')
    def __updateRenderTexture(self, text, font):
        scale = self.scaledFontSize/48

        GL.glUseProgram(Assets.TEXT_SHADER)
        GL.glViewport(0, 0, int(self.textBounds[2]*self.textRenderScale), int(self.textBounds[3]*self.textRenderScale))
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.textFrame)

        clearColor = GL.glGetFloatv(GL.GL_COLOR_CLEAR_VALUE)
        GL.glClearColor(0, 0, 0, 0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        GL.glBindVertexArray(self.textVao)

        GL.glUniform3f(GL.glGetUniformLocation(Assets.TEXT_SHADER, "textColor"), *self.textColor)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        x = 0
        y = 0
        for c in text:
            ch = font[c]
            w, h = ch.textureSize
            w = w*scale
            h = h*scale
            des = ch.descender*scale

            vertices = self.__getVertexData(x, y + des + self.maxAscender, w, h)

            #render glyph texture over quad
            GL.glBindTexture(GL.GL_TEXTURE_2D, ch.texture)

            #update content of VBO memory
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.textVbo)
            GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

            #render quad
            GL.glBindVertexArray(self.textVao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.textVbo)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.textEbo)
            GL.glEnableVertexAttribArray(0)
            GL.glDrawElements(GL.GL_TRIANGLES, len(self.textIndices), GL.GL_UNSIGNED_INT, None)
            GL.glDisableVertexAttribArray(0)
            #now advance cursors for next glyph (note that advance is number of 1/64 pixels)
            x += w + self.scaledTextSpacing*scale
            if c == ' ':
                x += self.scaledTextSpacing*scale*2

        GL.glBindVertexArray(0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glClearColor(*clearColor)
        GL.glViewport(0, 0, *self.window.dim)

    @funcProfiler(ftype='uiupdate')
    def __updateRenderer(self):
        screenCoords = [
            (self.openGLDim[0], self.openGLDim[1]),
            (self.openGLDim[0]+ self.openGLDim[2], self.openGLDim[1]),
            (self.openGLDim[0]+ self.openGLDim[2], self.openGLDim[1]+ self.openGLDim[3]),
            (self.openGLDim[0], self.openGLDim[1]+ self.openGLDim[3])
        ]
        screenCoords = [((c[0]+1)/2,(c[1]+1)/2)for c in screenCoords]
        uv = [
            (0,0),(1,0),(1,1),(0,1)
        ]

        self.renderer.getSprite().setTexCoords(uv)
        self.renderer.getTransform().setPos((self.openGLDim[0], self.openGLDim[1]))
        self.renderer.getTransform().setSize((self.openGLDim[2], self.openGLDim[3]))
        self.renderer.setDirtyVertex()

    def __getVertexData(self, xpos, ypos, w, h):
        xpos = (2*xpos)/self.textBounds[2] - 1
        ypos = (2*(self.textBounds[3]-ypos))/self.textBounds[3] - 1
        w = (2*w)/self.textBounds[2]
        h = (2*h)/self.textBounds[3]
        return np.array([
            xpos,       ypos + h, 0, 0,
            xpos,       ypos,     0, 1,
            xpos + w,   ypos,     1, 1,
            xpos + w,   ypos + h, 1, 0
        ], np.float32)
    
    def setText(self, text):
        if self.text == text: return
        self.text = text
        self.dirtyText = True
    
    def setFont(self, font):
        self.font = font
        self.dirtyText = True
    
    def setFontSize(self, size):
        self.fontSize = size
        self.__updateTextScale()
        self.dirtyText = True
    
    def setTextSpacing(self, spacing):
        self.textSpacing = spacing
        self.__updateTextScale()
        self.dirtyText = True

    def setTextColor(self, color):
        self.textColor = color
        self.dirtyText = True

    def isFitParent(self, fit):
        self.fitParent = fit

    def setRenderScaling(self, scale):
        self.textRenderScale = scale
        self.dirtyText = True