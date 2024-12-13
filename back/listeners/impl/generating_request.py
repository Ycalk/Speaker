import json
import datetime
import os
from listeners.base import Listener
import logging
import uuid
import random

class GeneratingRequestListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, 
                 queue_name: str, s3, voice_generated_channel):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        super().__init__(storage, generating_queue_table, channel)
        
        self.__queue_name = queue_name
        self.s3 = s3
        self.generated_bucket = os.getenv('GENERATED_BUCKET')
        self.voice_generated_channel = voice_generated_channel
        
        with open('utils/celebrities.json') as f:
            self.valid_celebrities_codes = ['vidos_good', 'vidos_bad']
            data = json.load(f)
            for celebrity in data:
                if celebrity['code'] != 'vidos':
                    self.valid_celebrities_codes.append(celebrity['code'])
    
    def check_if_voice_generated(self, celebrity_code, name):
        try:
            short_code = celebrity_code.split('_')[0]
            self.s3.head_object(Bucket=self.generated_bucket, 
                                Key=f'voice/{short_code}/{name}.wav')
            return True
        except Exception as _:
            return False
            
    def process_celebrity_code(self, data):
        if 'celebrity_code' not in data or data['celebrity_code'] not in self.valid_celebrities_codes:
            data['celebrity_code'] = random.choice(self.valid_celebrities_codes)
        
        if data['celebrity_code'] == 'vidos_good' :
            data['celebrity_code'] = random.choice(['vidos_good_v1', 'vidos_good_v2'])
        
        if data['celebrity_code'] == 'vidos_bad':
            available_codes = ['vidos_bad_v1', 'vidos_bad_v3']
            print(data['gender'])
            if data['gender'] == "Gender.MALE":
                available_codes.append('vidos_bad_v2')
            data['celebrity_code'] = random.choice(available_codes)
    
    async def handler(self, data : dict):
        self.logger.info("Received data: %s", data)
        
        try:
            data['id'] = str(uuid.uuid4())
            data['generation_start'] = datetime.datetime.now().isoformat()
            data['user_name'] = data['user_name'].lower()
            
            self.process_celebrity_code(data)
            
            if self.check_if_voice_generated(data['celebrity_code'], data['user_name']):
                self.logger.info("Voice already generated for user: %s", data['user_name'])
                data['audio'] = 'generated'
                await self._redis.publish(self.voice_generated_channel, json.dumps(data))
            
            else:
                await self._redis.rpush(self.__queue_name, json.dumps(data))
                self.logger.info("Processed data and pushed to queue: %s", data)
        
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON data: %s", e)
        
        except Exception as e:
            self.logger.error("An error occurred: %s", e)