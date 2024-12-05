import json
import aioredis


class Listener:
    def __init__(self, storage: str, generating_queue_table: int, channel: str):
        self._redis = aioredis.from_url(storage, db=generating_queue_table)
        self.channel = channel

    async def listen(self):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.channel)
        async for message in pubsub.listen():
            print(message)
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await self.handler(data)
    
    async def handler(self, data):
        raise NotImplementedError('Handler not implemented')