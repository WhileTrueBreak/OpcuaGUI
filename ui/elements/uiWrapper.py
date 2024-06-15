from ui.glElement import GlElement
from utils.debug import *

class UiWrapper(GlElement):
    def __init__(self, window, constraints, dim=(0,0,0,0)):
        super().__init__(window, constraints, dim)
        self.type = 'wrapper'

    def reshape(self):
        return

    @funcProfiler(ftype='uiupdate')
    def update(self, delta):
        return
