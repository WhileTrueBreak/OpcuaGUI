#!/usr/bin/env python3
import nest_asyncio
import colorama

from asset import *
from scenes.digitalTwinLab import *
from scenes.loadedScene import *
from utils.debug import *
from window import *

colorama.init(convert=True)
nest_asyncio.apply()

@funcProfiler(ftype='init')
def run():
    window = Window((1200, 800), 'Digital Twin GUI', fullscreen=False, resizeable=True, vsync=True)

    labScene = DigitalTwinLab(window, 'Digital Twin Lab')
    labScene.createUi()
    loadedScene = LoadedScene(window, 'Loaded')
    loadedScene.createUi()

    windowSceneManager = window.getSceneManager()
    windowSceneManager.addScene(labScene)
    windowSceneManager.addScene(loadedScene)
    windowSceneManager.createUi()

    window.run()

if __name__ == "__main__":
    run()
    profileReport()