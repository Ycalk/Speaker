import json
import aioredis
import aiohttp
import requests
import enum

class AppType(enum.Enum):
    TELEGRAM = "telegram"
    VK = "vk"

class Connector:
    @property
    def utils(self):
        return self.__utils
    
    @property
    def redis(self):
        return self.__redis
    
    @property
    def app_type(self):
        return self.__app_type
    
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
                "app_type": self.__parent.app_type.value,
                "user_id": user_id,
                "celebrity_code": celebrity_code,
                "user_name": user_name
            })
            await self.__generation_queue.rpush("queue", data)
    
    def __init__(self, app_type:AppType, server: str, port: str,
                 redis_storage: str):
        self.__app_type = app_type
        self.__server_address = f"{server}:{port}"
        self.__utils = self.Utils(self)
        self.__redis = self.Redis(self, redis_storage, self.get_config()["redis"])
    
    def get_config(self) -> dict:
        response = requests.get(f"{self.__server_address}/config")
        if response.status_code == 200:
            return response.json()
        else:
            raise requests.HTTPError(response.text)
    
    async def get_celebrities(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.__server_address}/celebrities") as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(response)
                return await response.json()

    async def validate_name(self, name: str) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.__server_address}/validate', json={"name": name}) as response:
                if response.status == 200:
                    return True
                elif response.status == 400:
                    return False
                else:
                    raise aiohttp.ClientResponseError(response)