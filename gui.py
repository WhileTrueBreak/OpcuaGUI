#!/usr/bin/env python3
import nest_asyncio

from window import *

from scenes.digitalTwinLab import *

from asset import *

import colorama

colorama.init(convert=True)
nest_asyncio.apply()

def run():
    window = Window((1200, 800), 'Digital Twin GUI', fullscreen=False, resizeable=True, vsync=False)

    labScene = DigitalTwinLab(window, 'Digital Twin Lab')
    labScene.createUi()

    windowSceneManager = window.getSceneManager()
    windowSceneManager.addScene(labScene)
    windowSceneManager.createUi()

    window.run()

if __name__ == "__main__":
    run()