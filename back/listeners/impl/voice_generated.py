import asyncio
import base64
import io
import json
import logging
import os
from listeners.base import Listener
import numpy as np
from scipy.io.wavfile import write, read

class VoiceGeneratedListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, 
                 queue_name: str, s3, video_generated_channel):
        
        super().__init__(storage, generating_queue_table, channel)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.storage_url = os.getenv('DATA_STORAGE')
        self.s3 = s3
        self.generated_bucket = os.getenv('GENERATED_BUCKET')
        self.video_generated_channel = video_generated_channel
        self.queue_name = queue_name
        self.audio_temp = os.getenv('audio_data_temp')
        
        os.makedirs(self.audio_temp, exist_ok=True)
        
    def save_audio(self, audio_data, file_id) -> str:
        audio_data = base64.b64decode(audio_data)
        buffer = io.BytesIO(audio_data)
        sample_rate, audio_array = read(buffer)
        safe_path = f'{self.audio_temp}/{file_id}.wav'
        write(safe_path, sample_rate, audio_array)
        
        return safe_path
    
    def upload_audio(self, audio_path, celebrity_code, name):
        try:
            short_code = celebrity_code.split('_')[0]
            self.s3.upload_file(audio_path, self.generated_bucket, f'voice/{short_code}/{name}.wav')
        
        except Exception as e:
            self.logger.error("An error occurred while uploading the audio: %s", e)
    
    def _get_uploaded_audio_url(self, data) -> str:
        short_code = data['celebrity_code'].split('_')[0]
        name = data['user_name']
        return f'{self.storage_url}/{self.generated_bucket}/voice/{short_code}/{name}.wav'
    
    def check_if_video_generated(self, celebrity_code, name):
        try:
            path = f'video/{celebrity_code.replace("_", "/")}/{name}.mp4'
            self.s3.head_object(Bucket=self.generated_bucket, 
                                Key=path)
            return True
        except Exception as _:
            return False
    
    def get_video_url(self, path_in_bucket) -> str:
        return f'{self.storage_url}/{self.generated_bucket}/{path_in_bucket}'
    
    async def handler(self, data : dict):
        if 'audio' not in data:
            self.logger.error("No audio data in the message: %s", data)
            return
        if 'error' in data:
            self.logger.error("Error in the message: %s", data)
            return
        
        try:
            if data['audio'] == 'generated':
                data['audio'] = self._get_uploaded_audio_url(data)
                self.logger.info("Voice already generated for user: %s", data['user_name'])
            
            else:
                self.logger.info("Received audio data in voice_generated_queue")
                audio_path = self.save_audio(data['audio'], data['id'])
                self.upload_audio(audio_path, data['celebrity_code'], data['user_name'])
                data['audio'] = self._get_uploaded_audio_url(data)
                self.logger.info("Audio was upload: %s", data)
                self.logger.info("Sleeping for a while",)
                await asyncio.sleep(5)
                os.remove(audio_path)
                
            if self.check_if_video_generated(data['celebrity_code'], data['user_name']):
                self.logger.info("Video already generated for user: %s", data['user_name'])
                path = f'video/{data["celebrity_code"].replace("_", "/")}/{data["user_name"]}.mp4'
                data['video'] = self.get_video_url(path)
                await self._redis.publish(self.video_generated_channel, json.dumps(data))
            else:
                await self._redis.rpush(self.queue_name, json.dumps(data))
        
        except Exception as e:
            self.logger.error("An error occurred while handling the message in voice_generated_queue: %s", e)