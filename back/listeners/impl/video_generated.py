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
        
    
    def get_video_url(self, path_in_bucket) -> str:
        return f'{self.data_storage}/{self.generated_bucket}/{path_in_bucket}'
        
        
    async def handler(self, data : dict):
        self.logger.info("Received data: %s", data)
        try:
            if 'video' not in data:
                self.logger.error("No video data in the message: %s", data)
                return
            
            path_in_bucket = f'video/{data["celebrity_code"].replace("_", "/")}/{data["user_name"]}.mp4'
            
            if data['video'] == 'generated':
                self.logger.info("Video was already generated for user: %s", data['user_name'])
                data['video'] = self.get_video_url(path_in_bucket)
                await self._redis.publish(self.generated_channel, json.dumps(data))
                return 
                
            self.logger.info("Received video data in video_generated_queue")
            self.s3.upload_file(data['video'], self.generated_bucket, path_in_bucket)
            self.logger.info("Video was upload: %s", data)
            os.remove(data['video'])
            data['video'] = f'{self.data_storage}/{self.generated_bucket}/{path_in_bucket}'
            await self._redis.publish(self.generated_channel, json.dumps(data))
        
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON data: %s", e)
        
        except Exception as e:
            self.logger.error("An error occurred: %s", e)