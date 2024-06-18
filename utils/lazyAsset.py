class LazyAsset:
    def __init__(self, createFunc):
        self.createFunc = createFunc
        self.asset = None
        self.saved = False
    
    def __get__(self, obj, objtype):
        if not self.saved:
            self.asset = self.createFunc()
            self.saved = True
        return self.asset