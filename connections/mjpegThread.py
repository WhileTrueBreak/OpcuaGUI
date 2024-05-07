from threading import Thread
from mjpeg.client import MJPEGClient
from urllib.request import urlopen
from io import BytesIO

import time

POLLING_RATE = 48

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
    # print(f'mjpeg thread started: {url}')
    connectionOpen = True
    try:
        urlopen(url, timeout=3)
    except:
        connectionOpen = False
        # print(f'{url} timed out')
        stop = lambda:True
    
    if connectionOpen:
        try:
            client = MJPEGClient(url)
            bufs = client.request_buffers(200000, 10)
            for b in bufs:
                client.enqueue_buffer(b)
            client.start()
        except:
            stop = lambda:True
    running = False
    start = time.time_ns()
    delay = 1/POLLING_RATE*1000000000
    rate = 0
    accum = 0
    while not stop():
        time_past = time.time_ns() - start
        start = time.time_ns()
        if not running:
            if client.reconnects > 1:
                stop = lambda:True
            if client.frames == 0:
                time.sleep(0.1)
                continue
            else:
                running = True
        try:
            # print(client._incoming)
            buf = client.dequeue_buffer(timeout=1)
            stream = BytesIO(buf.data)
            container.setStream(stream)
            client.enqueue_buffer(buf)
        except Exception as e:
            # print(f'================error================{client}')
            stop = lambda:True
        rate += 1
        accum += time_past
        time.sleep(max(0.01, (delay-time_past)/1000000000))
        if accum >= 10000000000:
            # print(f'MJPEG Polling Rate: {int(rate/10)}/s')
            accum -= 10000000000
            rate = 0
    if connectionOpen:
        client.stop()
    
    # print(f'mjpeg thread stopped: {url}')
