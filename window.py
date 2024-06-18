import pygame
from pygame.locals import *
import asyncio

import random

import time
from OpenGL import GL

from vectors import *
from math import *
import sys

import time

from ui.uiLayer import UiLayer
from ui.constraintManager import *

from scenes.sceneManager.defaultSceneManager import DefaultSceneManager

from asset import *

from constants import Constants

from utils.debug import *

import ctypes

from colorama import Fore, Back, Style

class Window:
    
    TAB_HEIGHT = 40
    INSTANCE = None

    def __init__(self, size, title, sceneManager=DefaultSceneManager(), fullscreen=False, resizeable=False, vsync=True):
        assert Window.INSTANCE == None
        Window.INSTANCE = self
        
        pygame.init()
        display_flags = pygame.DOUBLEBUF | pygame.OPENGL
        self.title = title
        if resizeable:
            display_flags = display_flags | pygame.RESIZABLE
        if fullscreen:
            display_flags = display_flags | pygame.FULLSCREEN
            size = (0,0)

        windowIcon = pygame.image.load('res/icons/malogo_48.png')
        pygame.display.set_icon(windowIcon)
        
        self.screen = pygame.display.set_mode(size, display_flags, vsync=(1 if vsync else 0))

        pygame.display.set_caption(title)

        self.dim = self.screen.get_size()
        self.ogdim = self.dim

        self.initOpenGL()

        self.delta = 1
        self.frameCount = 0

        self.running = True

        self.initialize(sceneManager)

    def initOpenGL(self):
        GL.glEnable(GL.GL_BLEND)
        GL.glCullFace(GL.GL_BACK)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glViewport(0, 0, self.dim[0], self.dim[1]) # Set viewport
        GL.glEnable(GL.GL_DEPTH_TEST) # Enable depth testing
        GL.glDepthFunc(GL.GL_LESS)

        Constants.MAX_TEXTURE_SLOTS = GL.glGetIntegerv(GL.GL_MAX_TEXTURE_IMAGE_UNITS)

    def initialize(self, sceneManager):
        self.timeCounter = 0
        self.frames = 0
        self.resized = False

        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glCullFace(GL.GL_BACK)

        self.uiEvents = []
        self.mousePos = (0,0)
        self.mouseButtons = [False]*5
        self.keyState = {}

        self.uiSelectBuffer = []
        self.selectedUi = None

        self.sceneManager = sceneManager
        self.sceneManager.initialize(self)
        self.uiLayer = UiLayer(self)

        Assets.init()
    
    @funcProfiler(ftype='update')
    def update(self, delta):
        self.resetHovered()
        self.eventHandler()
        self.sceneManager.update(delta)
        self.uiLayer.update(delta)
        GL.glClearColor(0,0,0,1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self.uiLayer.render()
        # GL.glFlush()
        return
    
    @funcProfiler(ftype='eventupdate')
    def eventHandler(self):
        cResized = False
        self.mousePos = pygame.mouse.get_pos()
        self.mouseButtons = pygame.mouse.get_pressed(num_buttons=5)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                cResized = True
            elif event.type == pygame.KEYDOWN:
                self.keyState[event.key] = True
            elif event.type == pygame.KEYUP:
                self.keyState[event.key] = False
        if cResized:
            self.updateWindow()
            self.resized = True
        elif not cResized:
            self.resized = False
        for event in self.uiEvents:
            self.sceneManager.handleEvent(event)
            # if event['action'] == 'release' and event['obj'] in self.tabBtns:
            #     if self.currentScene != None:
            #         self.uiLayer.getMasterElem().removeChild(self.currentScene.sceneWrapper)
            #         self.currentScene.stop()
            #     self.currentScene = self.sceneMap[event['obj']]
            #     if self.currentScene != None:
            #         self.uiLayer.getMasterElem().addChild(self.currentScene.sceneWrapper)
            #         self.currentScene.start()
            # if self.currentScene: self.currentScene.eventHandler(event)
        self.selectedUi = self.uiSelectBuffer[0] if len(self.uiSelectBuffer) > 0 else self.selectedUi
        self.uiSelectBuffer = []
        self.uiEvents = []

    @funcProfiler(ftype='uiupdate')
    def updateWindow(self):
        self.dim = pygame.display.get_window_size()
        return

    @funcProfiler(ftype='other')
    @timing
    def run(self):
        self.uiLayer.getMasterElem().addChild(self.sceneManager.getWrapper())
        start = time.time_ns()
        lastTime = start
        while self.running:
            end = start
            start = time.time_ns()

            self.update(self.delta)

            pygame.display.flip()   

            self.delta = (start - end)/1000000000
            self.timeCounter += self.delta
            self.frameCount += 1
            self.frames += 1
            if self.timeCounter >= 1:
                pygame.display.set_caption(f'{self.title} | frame time: {((time.time_ns()-lastTime)/1000)/self.frames:.0f}us | FPS: {self.frames}')
                lastTime = time.time_ns()
                # print(f'frame time: {Fore.CYAN}{1000000/self.frames:.0f}us{Style.RESET_ALL} | FPS: {Fore.CYAN}{self.frames}{Style.RESET_ALL}')
                self.timeCounter -= 1
                self.frames = 0
        self.sceneManager.stop()
        self.waitStop()
    
    def waitStop(self):
        loop = asyncio.get_event_loop()
        pending = asyncio.all_tasks(loop=loop)
        group = asyncio.gather(*pending)
        loop.run_until_complete(group)
        loop.close()
        self.stop()
    
    def stop(self):
        pygame.quit()

    def getSceneManager(self):
        return self.sceneManager

    def getMousePos(self):
        return self.mousePos
    
    def getMouseState(self, button):
        return self.mouseButtons[button]

    def getKeyState(self, key):
        if not key in self.keyState:
            return False
        return self.keyState[key]

    def getWindowScale(self):
        return (self.dim[0]/self.ogdim[0],self.dim[1]/self.ogdim[1])

    def resetHovered(self):
        self.firstInFrame = True

    def getHoveredUI(self):
        if self.firstInFrame:
            self.hovered = self.uiLayer.getScreenSpaceUI(*self.getMousePos())
            self.firstInFrame = False
        return self.hovered
