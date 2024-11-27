import json
import aioredis

class Connector:
    @property
    def utils(self):
        return self.__utils
    
    @property
    def redis(self):
        return self.__redis
    
    class Utils:
        def __init__ (self, parent):
            self.__parent: Connector = parent
        
        async def get_celebrity(self, code: str) -> dict:
            return next(x for x in await self.__parent.get_celebrities() if x["code"] == code)
    
    class Redis:
        def __init__ (self, parent, storage, table_data: dict):
            self.__parent: Connector = parent
            self.__generation_queue = aioredis.from_url(f"{storage}", db=table_data["generating_queue_table"])
        
        async def create_generation_request(self, user_id: int, celebrity_code: str, user_name: str) -> None:
            data = json.dumps({
                "user_id": user_id,
                "celebrity_code": celebrity_code,
                "user_name": user_name
            })
            await self.__generation_queue.rpush("queue", data)
    
    def __init__(self, source, target,
                 redis_storage: str, redis_table_data: dict):
        self.source = source
        self.target = target
        self.__utils = self.Utils(self)
        self.__redis = self.Redis(self, redis_storage, redis_table_data)

    async def get_celebrities(self) -> list[dict]:
        return [{'name': 'Test', 'code': 'test'}]

    async def validate_name(self, name: str) -> bool:
        return True