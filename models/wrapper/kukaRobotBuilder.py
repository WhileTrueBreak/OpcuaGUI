from utils.interfaces.classBuilder import ClassBuilder

class KukaRobotTwinBuilder(ClassBuilder):
    def __init__(self):
        self.window = None
        self.tmat = None
        self.nid = None
        self.rid = None
        self.modelRenderer = None
        self.hasGripper = None
        self.hasForceVector = None
        self.attach = None
        self.twinColors = None
        self.liveColors = None
    
    def setWindow(self, window):
        self.window = window
        
    def setTransform(self, tmat):
        self.tmat = tmat
        
    def setNid(self, nid):
        self.nid = nid
        
    def setRid(self, rid):
        self.rid = rid
        
    def setModelRenderer(self, modelRenderer):
        self.modelRenderer = modelRenderer
        
    def setHasGripper(self, hasGripper):
        self.hasGripper = hasGripper
        
    def setHasForceVector(self, hasForceVector):
        self.hasForceVector = hasForceVector

    def setAttach(self, attach):
        self.attach = attach
    
    def setTwinColors(self, colors):
        self.twinColors = colors
    
    def setLiveColors(self, colors):
        self.liveColors = colors

    def build(self):
        if any(v is None for v in [self.window, self.tmat, self.nid, self.rid, self.modelRenderer]):
            raise Exception("All variables are not set. Please set all variables before building the KukaRobotTwin.")
        from models.wrapper.kukaRobot import KukaRobotTwin
        instance = KukaRobotTwin(self.window, self.tmat, self.nid, self.rid, self.modelRenderer, hasGripper=self.hasGripper, hasForceVector=self.hasForceVector)
        if self.attach:
            instance.setAttach(self.attach)
        if self.liveColors:
            instance.setLiveColors(self.liveColors)
        if self.twinColors:
            instance.setTwinColors(self.twinColors)
        return instance