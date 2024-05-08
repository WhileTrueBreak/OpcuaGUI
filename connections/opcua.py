from asyncua import Client
import asyncio

from threading import Thread
import time

from utils.debug import *
import random

class OpcuaContainer:
    def __init__(self):
        self.updated = {}
        self.opcuaDict = {}
    
    def getValue(self, key, default=None):
        if not key in self.opcuaDict: return (default, 0)
        self.updated[key] = False
        return self.opcuaDict[key]
    
    def setValue(self, key, value, type):
        self.updated[key] = True
        self.opcuaDict[key] = (value, type)
    
    def hasUpdated(self, key):
        if not key in self.opcuaDict: return False
        return self.updated[key]

class Opcua:

    DEFAULT_POLLING_RATE = 60

    def __init__(self, host):
        self.OpcUaHost = host
        self.opcuaClient = Client(self.OpcUaHost)
        asyncio.run(self.opcuaClient.connect())
        self.nodeDict = {}

    async def setValue(self, node, value, type):
        try:
            if not node in self.nodeDict:
                self.nodeDict[node] = self.opcuaClient.get_node(node)
            return await self.nodeDict[node].set_value(value, type)
        except Exception:
            raise Exception(f'Error setting value')

    async def getValue(self, node):
        try:
            if not node in self.nodeDict:
                self.nodeDict[node] = self.opcuaClient.get_node(node)
            return (await self.nodeDict[node].get_value(), await self.nodeDict[node].read_data_type_as_variant_type())
        except Exception:
            raise Exception(f'Error getting value')
    
    def stop(self):
        asyncio.run(self.opcuaClient.disconnect())

    @staticmethod
    def createOpcuaReceiverThread(container, host, data, stop, pollingRate=DEFAULT_POLLING_RATE):
        t = Thread(target = Opcua.opcuaReceiverConnection, args =(container, host, data, stop, pollingRate))
        t.start()
        return t
    @staticmethod
    def opcuaReceiverConnection(container, host, data, stop, pollingRate=DEFAULT_POLLING_RATE):
        print(f'Opcua receiver thread started: {host}')
        start = time.time_ns()
        nanoPerPoll = 1/pollingRate*1000000000
        try:
            client = Opcua(host)
        except:
            print(f'Opcua receiver thread stopping: {host}')
            stop = lambda:True
        rate = 0
        accum = 0
        timeCounter = 0
        start = time.time_ns()
        while not stop():
            current = time.time_ns()
            time_past = current - start
            accum += time_past
            timeCounter += time_past
            start = current
            if accum >= nanoPerPoll:
                try:
                    loop = asyncio.get_event_loop()
                    task = loop.create_task(Opcua.OpcuaGetData(container, data, client))
                    loop.run_until_complete(task)
                    # asyncio.run(Opcua.OpcuaGetData(container, data, client))
                except:
                    return
                rate += 1
                accum = 0
            else:
                time.sleep((nanoPerPoll - accum)/1000000000)
            if timeCounter >= 10000000000:
                print(f'Opcua receiver polling rate: {int(rate/10)}/s')
                timeCounter -= 10000000000
                rate = 0
        client.stop()
        print(f'Opcua receiver thread stopped: {host}')
    @staticmethod
    async def OpcuaGetData(container, data, client):
        values = await asyncio.gather(*[client.getValue(d) for d in data])
        for d, v in zip(data, values):
            container.setValue(d, *v)
            # container.setValue(d, random.random(), '')
    @staticmethod
    def createOpcuaTransmitterThread(container, host, stop, pollingRate=DEFAULT_POLLING_RATE):
        t = Thread(target = Opcua.opcuaTransmitterConnection, args =(container, host, stop, pollingRate))
        t.start()
        return t
    @staticmethod
    def opcuaTransmitterConnection(container, host, stop, pollingRate=DEFAULT_POLLING_RATE):

        print(f'Opcua transmitter thread started: {host}')
        try:
            client = Opcua(host)
        except:
            print(f'Opcua transmitter thread stopping: {host}')
            stop = lambda:True
        start = time.time_ns()
        nanoPerPoll = 1/pollingRate*1000000000
        rate = 0
        accum = 0
        timeCounter = 0
        while not stop():
            current = time.time_ns()
            time_past = current - start
            accum += time_past
            timeCounter += time_past
            start = current
            if accum >= nanoPerPoll:
                try:
                    for key in container.opcuaDict:
                        if not container.hasUpdated(key): continue
                        v,t = container.getValue(key)
                        
                        loop = asyncio.get_event_loop()
                        task = loop.create_task(client.setValue(key, v, t))
                        loop.run_until_complete(task)
                        # asyncio.run(client.setValue(key, v, t))
                except:
                    return
                rate += 1
                accum = 0
            else:
                time.sleep((nanoPerPoll - accum)/1000000000)
            if timeCounter >= 10000000000:
                print(f'Opcua transmitter polling rate: {int(rate/10)}/s')
                timeCounter -= 10000000000
                rate = 0
        client.stop()
        print(f'Opcua transmitter thread stopped: {host}')





