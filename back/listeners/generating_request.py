from listeners.base import Listener
import aioredis

class GeneratingRequestListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, queue_name: str):
        super().__init__(storage, generating_queue_table, channel)
        self.__queue_name = queue_name
    
    async def handler(self, data):
        self._redis.rpush(self.__queue_name, data)