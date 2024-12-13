import json
import aioredis
import aiohttp
import requests
import enum

class AppType(enum.Enum):
    TELEGRAM = "telegram"
    VK = "vk"

class Gender(enum.Enum):
    MALE = 0,
    FEMALE = 1,
    UNKNOWN = 2
    
    @staticmethod
    def from_str(value: str):
        if value == "MALE":
            return Gender.MALE
        elif value == "FEMALE":
            return Gender.FEMALE
        else:
            return Gender.UNKNOWN

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
        
        async def create_generation_request(self, user_id: int, 
                                            celebrity_code: str, user_name: str,
                                            gender: str) -> None:
            """
            Creates a generation request

            Args:
                user_id (int): User id (eg telegram id)
                celebrity_code (str): Celebrity code (eg vidos_good)
                user_name (str): The name with which the greeting will be generated
                gender (str): Name gender (Example: Gender.MALE / Gender.FEMALE)
            """
            data = json.dumps({
                "app_type": self.__parent.app_type.value,
                "user_id": user_id,
                "celebrity_code": celebrity_code,
                "user_name": user_name,
                "gender": gender
            })
            await self.__generation_queue.publish("queue", data)
    
    def __init__(self, app_type:AppType, server: str, port: str,
                 redis_storage: str):
        self.__app_type = app_type
        self.__server_address = f"{server}:{port}"
        self.__utils = self.Utils(self)
        self.__redis = self.Redis(self, redis_storage, self.get_config()["redis"])
    
    def get_config(self) -> dict:
        """
        Fetches configuration data from the server.

        Raises:
            requests.HTTPError: If the server returns an error response (e.g., 4xx or 5xx status codes).

        Returns:
            dict: A dictionary containing the configuration data, structured as follows:
                {
                    "redis": {
                        "user_data_table": int, 
                        "generating_queue_table": int, 
                        "fsm_storage_table": int  
                    },
                    "MAX_NAME_LENGTH": int  
                }

        Example:
            config = get_config_from_server()
            print(config['MAX_NAME_LENGTH'])
        """
        response = requests.get(f"{self.__server_address}/config")
        if response.status_code == 200:
            return response.json()
        else:
            raise requests.HTTPError(response.text)
    
    async def get_celebrities(self) -> list[dict]:
        """
        Fetches a list of celebrities from the server.

        Raises:
            aiohttp.ClientResponseError: If the server returns an error response
            
        Returns:
            list[dict]: A list of dictionaries representing celebrities. Each dictionary
            has the following structure:
            [
                {
                    'name': str,  # The name of the celebrity
                    'code': str   # A unique code associated with the celebrity
                },
                ...
            ]

        Example:
            celebrities = await get_celebrities()
            for celeb in celebrities:
                print(f"Name: {celeb['name']}, Code: {celeb['code']}")
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.__server_address}/celebrities") as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        status=response.status,
                        message=f"Error {response.status}: {response.reason}",
                        history=response.history,
                    )
                return await response.json()

    async def validate_name(self, name: str) -> tuple[bool, Gender]:
        """
        Validates a given name by sending it to the server for verification.

        Parameters:
            name (str): The name to be validated. It should be a non-empty string.

        Raises:
            aiohttp.ClientResponseError: If the server returns an error response
            (e.g., status code other than 200 or 400).

        Returns:
            tuple: A tuple containing:
                - bool: True if the name is valid, False if the name is invalid.
                - Gender: The gender associated with the name, as determined by the server.
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.__server_address}/validate', json={"name": name}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['valid'], Gender.from_str(data["gender"])
                else:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        status=response.status,
                        message=f"Error {response.status}: {response.reason}",
                        history=response.history,
                    )