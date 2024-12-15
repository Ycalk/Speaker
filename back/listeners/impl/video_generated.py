import json
import aioredis
import os
from listeners.base import Listener
import logging

class VideoGeneratedListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, s3, 
                 generated_channel, generations_data_table, user_data_table):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.generations_data_redis = aioredis.from_url(storage, db=generations_data_table)
        self.user_data_redis = aioredis.from_url(storage, db=user_data_table)
        self.data_storage = os.getenv('DATA_STORAGE')
        super().__init__(storage, generating_queue_table, channel)
        self.generated_channel = generated_channel
        self.s3 = s3
        self.generated_bucket = os.getenv('GENERATED_BUCKET')
    
    async def add_data_to_storage(self, data : dict, json_data : str):
        self.logger.info("Adding data to storage: %s", data)
        await self.generations_data_redis.set(data['id'], json_data)
        user_data = await self.user_data_redis.get(data['user_id'])
        if user_data is None:
            user_data = 1
        else:
            user_data = int(user_data) + 1
        await self.user_data_redis.set(data['user_id'], user_data)
    
    async def handler(self, data : dict):
        self.logger.info("Received data: %s", data)
        try:
            if 'video' not in data:
                self.logger.error("No video data in the message: %s", data)
                return
            json_data = json.dumps(data)
            await self.add_data_to_storage(data, json_data)
            await self._redis.publish(self.generated_channel, json_data)
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON data: %s", e)
        
        except Exception as e:
            self.logger.error("An error occurred: %s", e)