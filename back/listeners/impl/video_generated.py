import json
import datetime
import os
from listeners.base import Listener
import logging
import uuid
import random

class VideoGeneratedListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, s3, generated_channel):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.data_storage = os.getenv('DATA_STORAGE')
        super().__init__(storage, generating_queue_table, channel)
        self.generated_channel = generated_channel
        self.s3 = s3
        self.generated_bucket = os.getenv('GENERATED_BUCKET')
        
    async def handler(self, data : dict):
        self.logger.info("Received data: %s", data)
        try:
            if 'video' not in data:
                self.logger.error("No video data in the message: %s", data)
                return
            
            await self._redis.publish(self.generated_channel, json.dumps(data))
        
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON data: %s", e)
        
        except Exception as e:
            self.logger.error("An error occurred: %s", e)