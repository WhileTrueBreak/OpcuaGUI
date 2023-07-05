#!/usr/bin/env python3
import nest_asyncio

from window import *

from scenes.DigitalTwinLab import *

from asset import *

nest_asyncio.apply()

window = Window((1200, 800), 'Digital Twin GUI', fullscreen=False, resizeable=True, vsync=False)

LabScene = DigitalTwinLab(window, 'Digital Twin Lab')
LabScene.createUi()

window.addScene(LabScene)

window.createUi()
window.run()
