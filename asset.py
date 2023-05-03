import os
import cv2
from PIL import Image

from pathlib import Path
import OpenGL.GL as GL
import freetype

from queue import Queue
from threading import Thread

import time

from utils.model import *
from utils.mathHelper import *
from utils.sprite import Sprite

from constants import Constants

class Assets:
    
    INIT = False

    @staticmethod
    def init():
        if Assets.INIT: return

        Assets.KUKA_IIWA14_MODEL = [None]*8
        Assets.KUKA_IIWA14_MODEL[0] = Assets.loadModelFile('res/models/iiwa14/visual/link_0.stl', createTransformationMatrix(0, 0, 0, 0, 0, 0))
        Assets.KUKA_IIWA14_MODEL[1] = Assets.loadModelFile('res/models/iiwa14/visual/link_1.stl', createTransformationMatrix(0,0,-(0.36-0.1575), 0, 0, 0))
        Assets.KUKA_IIWA14_MODEL[2] = Assets.loadModelFile('res/models/iiwa14/visual/link_2.stl', createTransformationMatrix(0, 0, 0, 0, 0, 180))
        Assets.KUKA_IIWA14_MODEL[3] = Assets.loadModelFile('res/models/iiwa14/visual/link_3.stl', createTransformationMatrix(0,0,0.2045-0.42, 0, 0, 0))
        Assets.KUKA_IIWA14_MODEL[4] = Assets.loadModelFile('res/models/iiwa14/visual/link_4.stl', createTransformationMatrix(0, 0, 0, 0, 0, 0))
        Assets.KUKA_IIWA14_MODEL[5] = Assets.loadModelFile('res/models/iiwa14/visual/link_5.stl', createTransformationMatrix(0,0,0.1845-0.4, 0, 0, 180))
        Assets.KUKA_IIWA14_MODEL[6] = Assets.loadModelFile('res/models/iiwa14/visual/link_6.stl', createTransformationMatrix(0, 0, 0, 0, 0, 180))
        Assets.KUKA_IIWA14_MODEL[7] = Assets.loadModelFile('res/models/iiwa14/visual/link_7.stl', createTransformationMatrix(0, 0, 0, 0, 0, 0))

        Assets.GRIPPER = Assets.loadModelFile('res/models/gripper/2F140.stl', createTransformationMatrix(0, 0, 0, 0, 0, 90))
        Assets.KUKA_BASE = Assets.loadModelFile('res/models/Objects/FlexFellow.STL', createTransformationMatrix(0, 0, -0.925, 0, 0, 0))

        Assets.TABLES = [None]*3
        Assets.TABLES[0] = Assets.loadModelFile('res/models/Objects/Benchtop_Custom.stl')
        Assets.TABLES[1] = Assets.loadModelFile('res/models/Objects/Benchtop_Rectangle.STL')
        Assets.TABLES[2] = Assets.loadModelFile('res/models/Objects/Benchtop_Square.STL')

        Assets.TUBE_INSIDE = Assets.loadModelFile('res/models/tube/tube_inside.stl', createTransformationMatrix(0,0,0,0,90,0))
        Assets.TUBE_OUTSIDE = Assets.loadModelFile('res/models/tube/tube_outside.stl', createTransformationMatrix(0,0,0,0,90,0))
        Assets.TUBE_HOLDER = Assets.loadModelFile('res/models/tube/tube_holder.stl')

        Assets.DRAGON = Assets.loadModelFile('res/models/dragon.obj', createScaleMatrix(0.01, 0.01, 0.01).dot(createTransformationMatrix(0,0,0,90,0,0)))
        Assets.POLE = Assets.loadModelFile('res/models/pole.stl', createScaleMatrix(10, 10, 10))

        Assets.ENDER3_3D_PRINTER = Assets.loadModelFile('res/models/Objects/Ender3-V2.STL')
        Assets.SHELF = Assets.loadModelFile('res/models/Objects/Shelving1.stl', createTransformationMatrix(0, 0, 0, 90, 0, 0))

        Assets.BAD_APPLE_VID = Assets.loadVideo('res/videos/badapple.mp4')
        Assets.CUBE_TEX = Assets.loadTexture('res/textures/cube.jpg', flipY=True)
        
        Assets.TEXT_SHADER = Assets.linkShaders('res/shader/ui/textureVertex.glsl', 'res/shader/ui/textFragment.glsl')
        Assets.GUI_SHADER = Assets.linkShaders('res/shader/ui/guiVertex.glsl', 'res/shader/ui/guiFragment.glsl')
        Assets.SCREEN_SHADER = Assets.linkShaders('res/shader/ui/screenVertex.glsl', 'res/shader/ui/screenFragment.glsl')

        Assets.OPAQUE_SHADER = Assets.linkShaders('res/shader/3d/objectVertex.glsl', 'res/shader/3d/opaqueFragment.glsl')
        Assets.TRANSPARENT_SHADER = Assets.linkShaders('res/shader/3d/objectVertex.glsl', 'res/shader/3d/transparentFragment.glsl')
        Assets.COMPOSITE_SHADER = Assets.linkShaders('res/shader/3d/compositeVertex.glsl', 'res/shader/3d/compositeFragment.glsl')

        Assets.VERA_FONT = Assets.loadFont('res/fonts/Vera.ttf')
        Assets.MONACO_FONT = Assets.loadFont('res/fonts/MONACO.TTF')
        Assets.FIRACODE_FONT = Assets.loadFont('res/fonts/FiraCode-Retina.ttf')

        floorVertices = [
            [0,0,0],[1,0,0],[0,1,0],
            [0,1,0],[1,0,0],[1,1,0],
            # [0,0,0],[0,1,0],[1,0,0],
            # [1,0,0],[0,1,0],[1,1,0],
        ]
        Assets.UNIT_WALL = Assets.loadModelVertices(vertices=floorVertices)
        screenVertices = [
            [0, 0, 0.0, 1, 0],[ 2*3/4, 0, 0.0, 1, 1],[ 0, 2, 0.0, 0, 0],
            [0, 2, 0.0, 0, 0],[ 2*3/4, 0, 0.0, 1, 1],[ 2*3/4, 2, 0.0, 0, 1],
            [0, 0, 0.0, 1, 0],[ 0, 2, 0.0, 0, 0],[ 2*3/4, 0, 0.0, 1, 1],
            [0, 2, 0.0, 0, 0],[ 2*3/4, 2, 0.0, 0, 1],[ 2*3/4, 0, 0.0, 1, 1],
        ]
        Assets.SCREEN = Assets.loadModelVertices(vertices=screenVertices)

        Assets.INIT = True
    @staticmethod
    def loadFont(fontFile, size=48*64):
        print(f'Loading font: {fontFile}')
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        characters = {}
        face = freetype.Face(fontFile)
        face.set_char_size(size)
        for i in range(0,128):
            face.load_char(chr(i))
            glyph = face.glyph

            #generate texture
            texture = GL.glGenTextures(1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RED, glyph.bitmap.width, glyph.bitmap.rows, 0,
                        GL.GL_RED, GL.GL_UNSIGNED_BYTE, glyph.bitmap.buffer)

            #texture options
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

            #now store character for later use
            characters[chr(i)] = CharacterSlot(texture,glyph)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        return characters
    @staticmethod
    def complieShader(shaderFile, shaderType):
        print(f'Compiling shader: {shaderFile}')
        shaderCode = Path(shaderFile).read_text()
        shaderCode = shaderCode.replace('%max_textures%', str(Constants.MAX_TEXTURE_SLOTS))
        shaderRef = GL.glCreateShader(shaderType)
        GL.glShaderSource(shaderRef, shaderCode)
        GL.glCompileShader(shaderRef)
        compile_success = GL.glGetShaderiv(shaderRef, GL.GL_COMPILE_STATUS)
        if not compile_success:
            error_message = GL.glGetShaderInfoLog(shaderRef)
            GL.glDeleteShader(shaderRef)
            error_message = '\n' + error_message.decode('utf-8')
            raise Exception(error_message)
        return shaderRef
    @staticmethod
    def linkShaders(vertexShaderFile, fragmentShaderFile):
        vertRef = Assets.complieShader(vertexShaderFile, GL.GL_VERTEX_SHADER)
        fragRef = Assets.complieShader(fragmentShaderFile, GL.GL_FRAGMENT_SHADER)
        print(f'Linking shader: {vertexShaderFile} & {fragmentShaderFile}')
        programRef = GL.glCreateProgram()
        GL.glAttachShader(programRef, vertRef)
        GL.glAttachShader(programRef, fragRef)
        GL.glLinkProgram(programRef)
        link_success = GL.glGetProgramiv(programRef, GL.GL_LINK_STATUS)
        if not link_success:
            error_message = GL.glGetProgramInfoLog(programRef)
            GL.glDeleteProgram(programRef)
            error_message = '\n' + error_message.decode('utf-8')
            raise Exception(error_message)
            return
        return programRef
    @staticmethod
    def loadModelFile(file, tmat=np.identity(4)):
        print(f'Loading model: {file}')
        ext = os.path.splitext(file)[1].lower()
        models = None
        match ext:
            case '.stl':
                models = Model.fromSTL(file=file, transform=tmat)
            case '.obj':
                models = Model.fromOBJ(file=file, transform=tmat)
            case _:
                raise Exception(f'Unknown file type: {ext}')
        if len(models) > 1:
            return models
        return models[0]
    @staticmethod
    def loadModelVertices(vertices):
        return Model.fromVertices(vertices)[0]
    @staticmethod
    def loadTexture(file, flipX=False, flipY=False, rot=0):
        print(f'Loading texture: {file}')
        img = Image.open(file)
        if flipX:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if flipY:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        if rot == 90:
            img = img.transpose(Image.ROTATE_90)
        elif rot == 180:
            img = img.transpose(Image.ROTATE_180)
        elif rot == 270:
            img = img.transpose(Image.ROTATE_270)
        
        imgData = np.array(list(img.getdata()), np.int8)

        texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexEnvf(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_DECAL)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, *img.size, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, imgData)

        sprite = Sprite.fromTexture(texture)
        return sprite
    @staticmethod
    def loadVideo(file):
        print(f'Loading video: {file}')
        capture = cv2.VideoCapture(file)
        return capture

class CharacterSlot:
    def __init__(self, texture, glyph):
        self.texture = texture
        self.ascender  = max(0, glyph.bitmap_top)
        self.descender = max(0, glyph.bitmap.rows-glyph.bitmap_top)
        self.textureSize = (max(0, glyph.bitmap.width), self.ascender + self.descender)

        if isinstance(glyph, freetype.GlyphSlot):
            self.bearing = (glyph.bitmap_left, glyph.bitmap_top)
            self.advance = glyph.advance.x
        elif isinstance(glyph, freetype.BitmapGlyph):
            self.bearing = (glyph.left, glyph.top)
            self.advance = None
        else:
            raise RuntimeError('unknown glyph type')
