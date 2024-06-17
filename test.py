import asyncio
import logging
import time
from asyncua import Client, Node, ua
from asyncua.common import ua_utils

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('asyncua')

class TestSubHandler():
        def datachange_notification(self, node, value, data):
            print("Data change", node, value,)

async def main():
    client = Client('oct.tpc://172.32.1.236:4840/server/')

    await client.connect()

    subscription = await client.create_subscription(500, TestSubHandler())
    nodes = [client.get_node('ns=21;s=R1d_Joi1')]
    handle = await subscription.subscribe_data_change(nodes)

    # while True:
    #     await asyncio.sleep(1000)

    await subscription.unsubscribe(handle)
    await client.disconnect()
    return 123


if __name__ == "__main__":
    print(asyncio.run(main()))