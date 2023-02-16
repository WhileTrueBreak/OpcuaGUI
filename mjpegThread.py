from threading import Thread
from mjpeg.client import MJPEGClient
from urllib.request import urlopen
from io import BytesIO

import time

def handler(signum, frame):
    raise Exception("Time is up")

class StreamContainer:
    def __init__(self):
        self.stream = None
    
    def getStream(self):
        stream = self.stream
        self.stream = None
        return stream
    
    def setStream(self, stream):
        self.stream = stream

def createMjpegThread(container, url, stop):
    t = Thread(target = MjpegConnection, args =(container, url, stop))
    t.start()
    return t

def MjpegConnection(container, url, stop):
    print(f'mjpeg thread started: {url}')
    try:
        urlopen(url, timeout=1)
        client = MJPEGClient(url, reconnect_interval=0.1)
        bufs = client.request_buffers(65536, 50)
        for b in bufs:
            client.enqueue_buffer(b)
        client.start()
    except:
        stop = lambda:True
    
    while not stop():
        if client.reconnects > 1:
            stop = lambda:True
        if client.frames == 0:
            time.sleep(0.1)
            continue
        try:
            buf = client.dequeue_buffer(timeout=0.1)
            stream = BytesIO(buf.data)
            container.setStream(stream)
            client.enqueue_buffer(buf)
        except:
            return
    client.stop()
    print(f'mjpeg thread stopped: {url}')
