from connections.opcua import *
from utils.debug import *
from utils.interfaces.pollController import PollController

class OpcuaReceiver(PollController):
    def __init__(self, data, container, host, pollingRate=30):
        self.data = data
        self.container = container
        self.host = host
        self.threadStopFlag = False
        self.thread = None
        self.pollingRate = pollingRate
    
    def start(self):
        self.threadStopFlag = False
        if self.thread == None or not self.thread.is_alive():
            self.thread = Opcua.createOpcuaReceiverThread(self.container, self.host, self.data, lambda:self.threadStopFlag, pollingRate=self.pollingRate)

    @timing
    def stop(self):
        self.threadStopFlag = True
        if self.thread:
            self.thread.join(5)