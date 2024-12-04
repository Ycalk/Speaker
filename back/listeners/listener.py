import json
import aioredis
import asyncio

from listeners.generating_request import GeneratingRequestListener
class Listener:
    __output_channel = 'generated'
    
    def __init__(self, storage: str, generating_queue_table: int, channel: str = 'queue'):
        self.__redis = aioredis.from_url(f"{storage}", db=generating_queue_table)
        self.channel = channel

    async def listen(self):
        pubsub = self.__redis.pubsub()
        await pubsub.subscribe(self.channel)
        async for message in pubsub.listen():
            print(message)
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await self.handler(data)
    
    async def send_response(self, data):
        await self.__redis.publish(self.__output_channel, json.dumps(data))
    
    async def handler(self, data):
        raise NotImplementedError('Handler not implemented')

def start_listeners(redis_storage, generating_queue_table):
    listener = GeneratingRequestListener(redis_storage, generating_queue_table)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(listener.listen())
    loop.run_forever()